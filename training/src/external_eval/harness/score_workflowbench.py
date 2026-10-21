"""Score WorkflowBench generations with the upstream CodeBLEU protocol.

Upstream (workflowllm/code/code/train_bf16.py):
  - extract the first ```python ... ``` block from the response
  - strip comments (line-suffix '#', drop blank lines) from prediction and gold
  - calc_codebleu([gold], [pred], lang="python", weights=(0.1,0.1,0.4,0.4))
    PER SAMPLE, then average.

IMPORTANT — the degenerate data-flow case. When CodeBLEU's extractor finds no
data-flow in the *reference* (common for flat call sequences), that component
"degenerates" and the library hands back its full 0.4 weight regardless of
what was predicted: such a row scores >= 0.400 even for an empty answer.
It does NOT happen on every row — references with real variable chains score
normally, and a bad answer there can land well below 0.4.

So the floor is per-row, not global, and a blanket rescale of the mean would
misreport. This scorer keeps the headline `codebleu` faithful to upstream and
additionally measures `dataflow_degenerate_rate` — the fraction of rows that
received the free 0.4 — so the unearned share is explicit and auditable.
`codebleu_earned_mean` averages only the non-degenerate rows.

Usage: harness/.venv-score/bin/python harness/score_workflowbench.py <run_dir>...
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

logging.disable(logging.WARNING)  # silence the per-sample data-flow warning

from codebleu import calc_codebleu  # noqa: E402

WEIGHTS = (0.1, 0.1, 0.4, 0.4)
FLOOR = 0.4  # degenerate data-flow component, see module docstring
CODE_RE = re.compile(r"```python(.*?)(```|$)", re.DOTALL)
THOUGHT_RE = re.compile(r"Thought:([\s\S]*?)(?:Code:|$)")


def remove_comments(code: str) -> str:
    """Verbatim port of utils_for_llm.remove_comments."""
    out = []
    for line in code.split("\n"):
        idx = line.find("#")
        if idx != -1:
            line = line[:idx].rstrip()
        if line.strip():
            out.append(line)
    return "\n".join(out)


def extract_code(response: str) -> tuple[str, bool]:
    blocks = [m[0] for m in CODE_RE.findall(response)]
    return (blocks[0], True) if blocks else ("", False)


def score_run(run_dir: Path, tasks_by_id: dict[str, dict],
              force: bool = False) -> dict | None:
    gen_path = run_dir / "generations.jsonl"
    if not gen_path.exists():
        return None
    # CodeBLEU is expensive (~minutes per model); skip runs whose scores.json
    # is already newer than their generations. Pass --force to rescore.
    scores_path = run_dir / "scores.json"
    if (not force and scores_path.exists()
            and scores_path.stat().st_mtime >= gen_path.stat().st_mtime):
        return json.loads(scores_path.read_text())
    rows = [json.loads(l) for l in gen_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        return None

    per_sample, n_parsed, n_empty, n_trunc = [], 0, 0, 0
    details = []
    for row in rows:
        task = tasks_by_id.get(row["task_id"])
        if task is None:
            continue
        code, parsed = extract_code(row["response"])
        n_parsed += int(parsed)
        pred = remove_comments(code)
        gold = remove_comments(task["gold"])
        n_empty += int(not pred.strip())
        n_trunc += int(row.get("finish_reason") == "length")
        try:
            r = calc_codebleu([gold], [pred], lang="python", weights=WEIGHTS, tokenizer=None)
        except Exception:
            r = {"codebleu": 0.0, "ngram_match_score": 0.0,
                 "weighted_ngram_match_score": 0.0,
                 "syntax_match_score": 0.0, "dataflow_match_score": 0.0}
        # Detect the degenerate data-flow case: the library reports
        # dataflow_match_score = 0 but folds a full 1.0 into the total, so the
        # returned codebleu exceeds the weighted sum of the four components.
        components = (0.1 * float(r["ngram_match_score"])
                      + 0.1 * float(r["weighted_ngram_match_score"])
                      + 0.4 * float(r["syntax_match_score"])
                      + 0.4 * float(r["dataflow_match_score"]))
        degenerate = float(r["codebleu"]) > components + 1e-6
        r = dict(r, _degenerate=degenerate)
        per_sample.append(r)
        details.append({"task_id": row["task_id"], "parsed": parsed,
                        "codebleu": round(float(r["codebleu"]), 4),
                        "dataflow_degenerate": degenerate})

    n = len(per_sample)
    if not n:
        return None

    def mean(key: str) -> float:
        return sum(float(s[key]) for s in per_sample) / n

    codebleu = mean("codebleu")
    n_degen = sum(1 for s in per_sample if s["_degenerate"])
    earned = [float(s["codebleu"]) for s in per_sample if not s["_degenerate"]]
    scores = {
        "model_id": run_dir.name,
        "bench": rows[0]["bench"],
        "split": rows[0]["split"],
        "n_scored": n,
        "n_tasks_expected": len(tasks_by_id),
        "codebleu": round(codebleu, 4),
        "dataflow_degenerate_rate": round(n_degen / n, 4),
        "codebleu_earned_mean": round(sum(earned) / len(earned), 4) if earned else None,
        "n_earned_rows": len(earned),
        "ngram_match": round(mean("ngram_match_score"), 4),
        "weighted_ngram_match": round(mean("weighted_ngram_match_score"), 4),
        "syntax_match": round(mean("syntax_match_score"), 4),
        "dataflow_match": round(mean("dataflow_match_score"), 4),
        "parse_rate": round(n_parsed / n, 4),
        "empty_code_rate": round(n_empty / n, 4),
        "truncation_rate": round(n_trunc / n, 4),
        "protocol": "upstream per-sample CodeBLEU, weights=(0.1,0.1,0.4,0.4), comments stripped",
        "floor_note": ("rows where the reference has no extractable data-flow receive "
                       "a free 0.4; dataflow_degenerate_rate reports how many"),
    }
    (run_dir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    (run_dir / "per_sample.jsonl").write_text(
        "\n".join(json.dumps(d) for d in details) + "\n", encoding="utf-8")
    return scores


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv[1:]
    run_dirs = [Path(a) for a in args]
    if not run_dirs:
        run_dirs = sorted(
            d for split in ("workflowbench_id_test", "workflowbench_ood_dev")
            for d in (root / "runs" / split).glob("*") if d.is_dir())

    cache: dict[str, dict[str, dict]] = {}
    for run_dir in run_dirs:
        split_dir = run_dir.parent.name
        if split_dir not in cache:
            name = {"workflowbench_id_test": "workflowbench_id_test",
                    "workflowbench_ood_dev": "workflowbench_ood_dev"}[split_dir]
            cache[split_dir] = {
                json.loads(l)["task_id"]: json.loads(l)
                for l in (root / "tasks" / f"{name}.jsonl").read_text().splitlines() if l.strip()}
        s = score_run(run_dir, cache[split_dir], force=force)
        if s:
            print(f"{split_dir:28s} {s['model_id']:34s} "
                  f"codebleu={s['codebleu']:.4f} (degen {s['dataflow_degenerate_rate']:.2f}) "
                  f"parse={s['parse_rate']:.3f} n={s['n_scored']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

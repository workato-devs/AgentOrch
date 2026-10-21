"""Score Seal-Tools generations with the upstream metric.

Ports two upstream pieces so the numbers are comparable to the paper:
  - parsing: LLM_Evaluation/src/llm_tools/evaluation/transform_output.py,
    case 'ToolLearning' (quote-normalise, strip newlines, find the first
    '[ { "api"' and its balanced ']', require api/parameters/responses keys)
  - metric: LLM_Evaluation/src/calculate_pluginscore_detailed.py,
    calculate_score_ToolLearning -> format rate + API P/R/F1 + parameter
    P/R/F1, reported overall and split easy / difficult.

Parameter credit is only counted for a *matched* API, and API matching is by
name against the first gold call with that name — both upstream behaviours,
kept as-is.

Usage: python3 harness/score_sealtools.py <run_dir>...
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

API_START = re.compile(r"\[\s*\{\s*\"api\"", re.DOTALL)


def _match_square_bracket(text: str, pos_s: int) -> int:
    counter = -1
    for i in range(pos_s + 1, len(text)):
        if text[i] == "[":
            counter -= 1
        elif text[i] == "]":
            counter += 1
        if counter == 0:
            return i
    return -1


def transform_output(output_text: str):
    """Upstream 'ToolLearning' parser. Returns a list, or -1 on failure."""
    text = re.sub("'", '"', output_text)
    text = re.sub("\n", "", text)
    m = API_START.search(text)
    if m is None:
        return -1
    pos_s = m.span()[0]
    pos_e = _match_square_bracket(text, pos_s)
    if pos_e == -1:
        return -1
    text = text[pos_s:pos_e + 1]
    if "api" in text and "parameters" in text and "responses" in text:
        try:
            return json.loads(text)
        except Exception:
            return -1
    return -1


RELAXED_START = re.compile(r"\[\s*\{\s*\"api\"", re.DOTALL)


def transform_output_relaxed(output_text: str):
    """Same as transform_output but does NOT require a 'responses' key.

    Diagnostic only. Several trained checkpoints emit the right API with the
    right parameters and simply omit `responses`; upstream's parser rejects
    the whole row, so a one-field formatting regression is scored as total
    capability loss (gemma-31B SFT: format rate 0.994 -> 0.208, F1_api 0.989
    -> 0.362, while the calls themselves are correct). Reporting only the
    upstream number would misattribute that to lost tool-calling ability.
    The upstream metric stays the headline; this isolates selection and
    parameter filling from format compliance.
    """
    text = re.sub("'", '"', output_text)
    text = re.sub("\n", "", text)
    m = RELAXED_START.search(text)
    if m is None:
        return -1
    pos_s = m.span()[0]
    pos_e = _match_square_bracket(text, pos_s)
    if pos_e == -1:
        return -1
    text = text[pos_s:pos_e + 1]
    if "api" not in text or "parameters" not in text:
        return -1
    try:
        out = json.loads(text)
    except Exception:
        return -1
    if not isinstance(out, list):
        return -1
    for call in out:
        if isinstance(call, dict):
            call.setdefault("responses", [])
    return out


def _gold_calls(gold: str):
    # Upstream: eval() of the gold string, which is Python-literal formatted.
    import ast
    try:
        return ast.literal_eval(gold)
    except Exception:
        return []


def calculate(records: list[dict]) -> dict:
    """Verbatim logic of calculate_score_ToolLearning."""
    correct_format = 0
    correct_api = predict_api = gold_api = 0
    correct_param = predict_param = gold_param = 0

    for rec in records:
        gold_answer = rec["gold_calls"]
        gold_api += len(gold_answer)
        for g in gold_answer:
            gold_param += len(g.get("parameters", {}) or {})

        pred = rec["pred"]
        if pred == -1:
            continue
        correct_format += 1
        for p in pred:
            if not isinstance(p, dict) or "api" not in p:
                continue
            predict_api += 1
            params = p.get("parameters")
            if isinstance(params, dict):
                predict_param += len(params)
            gold_idx = next((i for i, g in enumerate(gold_answer)
                             if g.get("api") == p["api"]), -1)
            if gold_idx == -1:
                continue
            correct_api += 1
            if isinstance(params, dict):
                gold_params = gold_answer[gold_idx].get("parameters", {}) or {}
                for name, value in params.items():
                    if name in gold_params and str(value) == str(gold_params[name]):
                        correct_param += 1

    out: dict[str, float | int] = {"n": len(records)}
    if records:
        out["format_rate"] = round(correct_format / len(records), 4)
    if correct_api * predict_api * gold_api > 0:
        p, r = correct_api / predict_api, correct_api / gold_api
        out |= {"P_api": round(p, 4), "R_api": round(r, 4),
                "F1_api": round(2 * p * r / (p + r), 4)}
    else:
        out |= {"P_api": 0.0, "R_api": 0.0, "F1_api": 0.0}
    if correct_param * predict_param * gold_param > 0:
        p, r = correct_param / predict_param, correct_param / gold_param
        out |= {"P_param": round(p, 4), "R_param": round(r, 4),
                "F1_param": round(2 * p * r / (p + r), 4)}
    else:
        out |= {"P_param": 0.0, "R_param": 0.0, "F1_param": 0.0}
    return out


def score_run(run_dir: Path, tasks_by_id: dict[str, dict]) -> dict | None:
    gen_path = run_dir / "generations.jsonl"
    if not gen_path.exists():
        return None
    rows = [json.loads(l) for l in gen_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        return None

    records, details = [], []
    for row in rows:
        task = tasks_by_id.get(row["task_id"])
        if task is None:
            continue
        pred = transform_output(row["response"])
        rec = {
            "task_id": row["task_id"],
            "difficulty": task["meta"]["difficulty"],
            "pred": pred,
            "pred_relaxed": transform_output_relaxed(row["response"]),
            "gold_calls": _gold_calls(task["gold"]),
        }
        records.append(rec)
        details.append({"task_id": rec["task_id"], "parsed": pred != -1,
                        "n_pred_calls": 0 if pred == -1 else len(pred),
                        "n_gold_calls": len(rec["gold_calls"])})

    if not records:
        return None
    easy = [r for r in records if r["difficulty"] == "easy"]
    hard = [r for r in records if r["difficulty"] == "difficult"]

    scores = {
        "model_id": run_dir.name,
        "bench": rows[0]["bench"],
        "split": rows[0]["split"],
        "n_scored": len(records),
        "n_tasks_expected": len(tasks_by_id),
        "overall": calculate(records),
        "easy": calculate(easy) if easy else None,
        "difficult": calculate(hard) if hard else None,
        # Diagnostic: same metric, parser not requiring a 'responses' key.
        "overall_relaxed": calculate(
            [dict(r, pred=r["pred_relaxed"]) for r in records]),
        "truncation_rate": round(
            sum(r.get("finish_reason") == "length" for r in rows) / len(rows), 4),
        "protocol": "upstream calculate_score_ToolLearning + ToolLearning output parser",
    }
    (run_dir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    (run_dir / "per_sample.jsonl").write_text(
        "\n".join(json.dumps(d) for d in details) + "\n", encoding="utf-8")
    return scores


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    run_dirs = [Path(a) for a in sys.argv[1:]]
    if not run_dirs:
        run_dirs = sorted(
            d for split in ("sealtools_test_in_domain", "sealtools_test_out_domain",
                          "sealtools_test_in_domain_64", "sealtools_test_out_domain_64")
            for d in (root / "runs" / split).glob("*") if d.is_dir())

    cache: dict[str, dict[str, dict]] = {}
    for run_dir in run_dirs:
        split_dir = run_dir.parent.name
        if split_dir not in cache:
            cache[split_dir] = {
                json.loads(l)["task_id"]: json.loads(l)
                for l in (root / "tasks" / f"{split_dir}.jsonl").read_text().splitlines() if l.strip()}
        s = score_run(run_dir, cache[split_dir])
        if s:
            o = s["overall"]
            rl = s["overall_relaxed"]
            print(f"{split_dir:30s} {s['model_id']:34s} "
                  f"F1_api={o['F1_api']:.4f} F1_param={o['F1_param']:.4f} "
                  f"fmt={o.get('format_rate', 0):.3f} | relaxed "
                  f"F1_api={rl['F1_api']:.4f} fmt={rl.get('format_rate', 0):.3f} "
                  f"n={s['n_scored']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

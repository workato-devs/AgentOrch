"""Aggregate every scored external run into results/summary.{csv,md}.

Joins each model's external scores against its AgentOrch global-mode
orchestration score (from harness/models.json) so transfer can be read
against home-benchmark strength, and reports each trained model's delta
against its own base model.

Usage: python3 harness/summarize.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ["workflowbench_id_test", "workflowbench_ood_dev",
          "sealtools_test_in_domain", "sealtools_test_out_domain",
          "sealtools_test_in_domain_64", "sealtools_test_out_domain_64"]
# The single headline metric per split, and its display name. The plain
# sealtools splits are the upstream ~5-candidate setting (saturated at base:
# F1_api ~0.98); the _64 splits are the derived 64-tool surface where the
# selection question is actually open. See harness/build_sealtools_hard.py.
HEADLINE = {
    "workflowbench_id_test": ("codebleu", "WFB-ID CodeBLEU"),
    "workflowbench_ood_dev": ("codebleu", "WFB-OOD CodeBLEU"),
    "sealtools_test_in_domain": ("F1_api", "Seal-in F1api (5-cand)"),
    "sealtools_test_out_domain": ("F1_api", "Seal-out F1api (5-cand)"),
    "sealtools_test_in_domain_64": ("F1_api", "Seal-in F1api (64-tool)"),
    "sealtools_test_out_domain_64": ("F1_api", "Seal-out F1api (64-tool)"),
}


def load() -> tuple[list[dict], dict[str, dict]]:
    models = json.loads((ROOT / "harness" / "models.json").read_text())
    by_id = {m["model_id"]: m for m in models}
    for m in models:
        m["scores"] = {}
        for split in SPLITS:
            path = ROOT / "runs" / split / m["model_id"] / "scores.json"
            if path.exists():
                m["scores"][split] = json.loads(path.read_text())
    return models, by_id


def headline(model: dict, split: str, relaxed: bool = False) -> float | None:
    s = model["scores"].get(split)
    if not s:
        return None
    key = HEADLINE[split][0]
    if "overall" not in s:
        return s.get(key)
    block = s.get("overall_relaxed") if relaxed else s["overall"]
    return (block or s["overall"]).get(key)


BASE_OF = {"qwen-27b": "base-qwen27b", "qwen-4b": "base-qwen4b",
           "gemma-26b": "base-gemma26b", "gemma-31b": "base-gemma31b",
           "gemma-12b": "base-gemma12b"}


def main() -> int:
    models, by_id = load()
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)

    cols = ["model_id", "family", "kind", "agentorch_global_orch"]
    for split in SPLITS:
        cols += [f"{split}", f"{split}__delta_vs_base"]
        if split.startswith("sealtools"):
            cols += [f"{split}__relaxed", f"{split}__relaxed_delta_vs_base"]
    cols += ["n_splits_complete"]

    rows = []
    for m in sorted(models, key=lambda x: (x["family"], x["kind"], x["model_id"])):
        base = by_id.get(BASE_OF.get(m["family"], ""))
        row = {"model_id": m["model_id"], "family": m["family"], "kind": m["kind"],
               "agentorch_global_orch": m["agentorch_global_orch"]}
        done = 0
        for split in SPLITS:
            v = headline(m, split)
            row[split] = "" if v is None else round(v, 4)
            done += v is not None
            bv = headline(base, split) if base and base is not m else None
            row[f"{split}__delta_vs_base"] = (
                "" if (v is None or bv is None or m["kind"] == "base")
                else round(v - bv, 4))
            if split.startswith("sealtools"):
                rv = headline(m, split, relaxed=True)
                rbv = headline(base, split, relaxed=True) if base and base is not m else None
                row[f"{split}__relaxed"] = "" if rv is None else round(rv, 4)
                row[f"{split}__relaxed_delta_vs_base"] = (
                    "" if (rv is None or rbv is None or m["kind"] == "base")
                    else round(rv - rbv, 4))
        row["n_splits_complete"] = done
        rows.append(row)

    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # Markdown: one table per family, base row first, deltas in parentheses.
    lines = ["# External-benchmark generalization results", "",
             "Greedy decoding, each model's own chat template, upstream scorers.",
             "`Δ` is against that family's untrained base model.", "",
             "Seal-Tools columns show the upstream metric. Most apparent",
             "degradation there is format compliance, not capability: under a",
             "parser that does not require the `responses` key, most trained",
             "models return to base level (see `*__relaxed` in summary.csv).",
             "gemma-31B is the extreme case -- upstream F1_api 0.989 -> 0.362,",
             "relaxed 0.989 -> 0.989.", ""]
    complete = sum(r["n_splits_complete"] for r in rows)
    lines += [f"Coverage: {complete}/{len(rows) * len(SPLITS)} model-split cells scored.", ""]
    for family in ["qwen-27b", "qwen-4b", "gemma-31b", "gemma-26b", "gemma-12b"]:
        fam = [r for r in rows if r["family"] == family]
        if not fam:
            continue
        lines += [f"## {family}", "",
                  "| model | kind | AgentOrch orch | " +
                  " | ".join(HEADLINE[s][1] for s in SPLITS) + " |",
                  "|---|---|---|" + "---|" * len(SPLITS)]
        fam.sort(key=lambda r: (r["kind"] != "base", r["model_id"]))
        for r in fam:
            cells = []
            for split in SPLITS:
                v, d = r[split], r[f"{split}__delta_vs_base"]
                cells.append("—" if v == "" else
                             (f"{v}" if d == "" else f"{v} ({d:+.4f})"))
            lines.append(f"| {r['model_id']} | {r['kind']} | "
                         f"{r['agentorch_global_orch']} | " + " | ".join(cells) + " |")
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {out_dir/'summary.csv'} and summary.md "
          f"({complete}/{len(rows)*len(SPLITS)} cells scored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

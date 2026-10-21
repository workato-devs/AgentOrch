#!/usr/bin/env python3
"""Paired comparison of a replan-v2 run against the canonical v1 replan rows
on the same (recipe, variant) rows, per model, plus the protocol-attribution
counters. Prints a markdown report and applies the pre-registered decision
rule for promoting v2 to the full 3,220-variant benchmark.

Decision rule (fixed before the smoke ran, 2026-08-28):
  * net orchestration_accuracy gain >= +3.0 pts on >= 3 of 5 models,
  * no model regresses by more than 1.0 pt,
  * the malformed/rejected review share drops visibly (attribution sanity).

Usage:
  PYTHONPATH=verification/backends/shared/src \
    python -m experiments.compare_replan_v2_smoke --run replan-v2-smoke-20260828
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[1]
FULL_EVAL = PUBLIC_ROOT / "outputs/full_eval"
sys.path.insert(0, str(PUBLIC_ROOT / "verification/backends/shared/src"))
from metrics.aggregate import primary_metrics_for_row  # noqa: E402

from experiments.select_replan_v2_smoke_ids import ROSTER  # noqa: E402

GAIN_PTS = 3.0
REGRESS_PTS = 1.0
MIN_MODELS = 3


def load_rows(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.is_file():
        return rows
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[str(row.get("task_id"))] = row
    return rows


def orch(row: dict | None) -> float:
    if not row or row.get("status") != "ok":
        return 0.0
    return primary_metrics_for_row(row)["orchestration_accuracy"]


def final(row: dict | None) -> float:
    if not row or row.get("status") != "ok":
        return 0.0
    return primary_metrics_for_row(row)["final_accuracy"]


def paired_ci(deltas: list[float], seed: int = 0, n_boot: int = 2000) -> tuple[float, float]:
    if not deltas:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        means.append(sum(sample) / len(sample))
    means.sort()
    return (means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1])


def counters(rows: dict[str, dict]) -> dict[str, int]:
    keys = (
        "replan_review_count", "replan_count", "replan_rejected_count",
        "replan_repair_offered_count", "replan_repair_accepted_count",
        "replan_patch_accepted_count", "replan_resolver_review_count",
        "replan_resolver_accepted_count",
    )
    out = Counter()
    for row in rows.values():
        for key in keys:
            out[key] += int(row.get(key) or 0)
    return dict(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="run name under outputs/full_eval")
    parser.add_argument("--ids-dir", default=str(PUBLIC_ROOT / "experiments/replan_v2_smoke"))
    parser.add_argument("--json", help="also write the report as JSON here")
    args = parser.parse_args()

    report = {"run": args.run, "lanes": {}}
    lines = [f"# replan v2 smoke vs v1 — run `{args.run}`", ""]
    lines.append(
        "| lane | rows | v1 orch | v2 orch | Δ pts | Δ CI95 | fail→pass | pass→fail "
        "| v1 final | v2 final | reviews v1→v2 | accepted v1→v2 | rejected v1→v2 "
        "| repairs ok | patches | resolver reviews/ok | v2 rows missing |"
    )
    lines.append("|" + "---|" * 17)
    gains = 0
    regress = False
    for lane, (tier, model) in ROSTER.items():
        ids_file = Path(args.ids_dir) / f"{lane}.txt"
        subset = set(ids_file.read_text().split()) if ids_file.is_file() else set()
        v1 = load_rows(FULL_EVAL / tier / "replan/results.jsonl")
        model_dir = "hf:" + model.replace("/", "__")
        v2 = load_rows(FULL_EVAL / args.run / model_dir / "replan/results.jsonl")
        v1 = {k: r for k, r in v1.items() if str(r.get("recipe_id")) in subset}
        v2 = {k: r for k, r in v2.items() if str(r.get("recipe_id")) in subset}
        common = sorted(set(v1) & set(v2))
        missing = len(set(v1) - set(v2))
        if not common:
            lines.append(f"| {lane} | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | {missing} |")
            report["lanes"][lane] = {"rows": 0, "missing": missing}
            continue
        d_orch = [orch(v2[k]) - orch(v1[k]) for k in common]
        v1_orch = sum(orch(v1[k]) for k in common) / len(common)
        v2_orch = sum(orch(v2[k]) for k in common) / len(common)
        v1_final = sum(final(v1[k]) for k in common) / len(common)
        v2_final = sum(final(v2[k]) for k in common) / len(common)
        delta = (v2_orch - v1_orch) * 100
        lo, hi = paired_ci(d_orch)
        f2p = sum(1 for k in common if orch(v1[k]) < 1.0 <= orch(v2[k]))
        p2f = sum(1 for k in common if orch(v2[k]) < 1.0 <= orch(v1[k]))
        c1 = counters({k: v1[k] for k in common})
        c2 = counters({k: v2[k] for k in common})
        lines.append(
            f"| {lane} | {len(common)} | {v1_orch:.4f} | {v2_orch:.4f} | {delta:+.2f} "
            f"| [{lo*100:+.2f}, {hi*100:+.2f}] | {f2p} | {p2f} "
            f"| {v1_final:.4f} | {v2_final:.4f} "
            f"| {c1['replan_review_count']}→{c2['replan_review_count']} "
            f"| {c1['replan_count']}→{c2['replan_count']} "
            f"| {c1['replan_rejected_count']}→{c2['replan_rejected_count']} "
            f"| {c2['replan_repair_accepted_count']}/{c2['replan_repair_offered_count']} "
            f"| {c2['replan_patch_accepted_count']} "
            f"| {c2['replan_resolver_review_count']}/{c2['replan_resolver_accepted_count']} "
            f"| {missing} |"
        )
        report["lanes"][lane] = {
            "rows": len(common), "missing": missing,
            "v1_orch": v1_orch, "v2_orch": v2_orch, "delta_pts": delta,
            "delta_ci95_pts": [lo * 100, hi * 100],
            "fail_to_pass": f2p, "pass_to_fail": p2f,
            "v1_final": v1_final, "v2_final": v2_final,
            "v1_counters": c1, "v2_counters": c2,
        }
        if delta >= GAIN_PTS:
            gains += 1
        if delta <= -REGRESS_PTS:
            regress = True
    verdict = gains >= MIN_MODELS and not regress
    lines += [
        "",
        f"Decision rule: ≥{MIN_MODELS} lanes with Δ ≥ +{GAIN_PTS} pts and no lane ≤ −{REGRESS_PTS} pt.",
        f"Lanes meeting the gain bar: {gains}. Regression: {'yes' if regress else 'no'}.",
        f"**Verdict: {'PROMOTE v2 to the full benchmark' if verdict else 'do NOT promote (or lanes incomplete)'}**",
        "",
        "Δ is on paired rows only; rows the v2 run has not produced yet are counted in the last column, not in Δ.",
    ]
    report["gain_lanes"] = gains
    report["regression"] = regress
    report["verdict_promote"] = verdict
    print("\n".join(lines))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

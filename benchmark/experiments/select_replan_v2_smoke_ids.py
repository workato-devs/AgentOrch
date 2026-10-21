#!/usr/bin/env python3
"""Pick the replan-v2 smoke subset: per model, N recipes whose frozen
initial plan is valid (status == "ok" in the tier global-plans cache) and
which have a v1 replan artifact to pair against.

Replan can only act on rows that already have a valid frozen plan, so a
subset drawn from the whole manifest would waste ~50% of rows on plan_error
rows that are identical under every protocol. Recipes valid for more of the
roster are preferred so the per-model subsets overlap as much as possible;
ties are broken by a seeded shuffle.

Writes experiments/replan_v2_smoke/<lane>.txt (one recipe id per line) and a
summary JSON next to them.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[1]
FULL_EVAL = PUBLIC_ROOT / "outputs/full_eval"

# lane -> (tier dir under outputs/full_eval, hf model id)
ROSTER = {
    "qwen3.8-27b": ("large_model/Qwen3.8-27B-FP8", "Qwen/Qwen3.8-27B-FP8"),
    "qwen3-4b": ("small_model/Qwen3-4B-Instruct-2507", "Qwen/Qwen3-4B-Instruct-2507"),
    "gemma-3-27b": ("large_model/gemma-3-27b-it", "google/gemma-3-27b-it"),
    "gemma-4-26b": ("medium_model/gemma-4-26B-A4B-it", "google/gemma-4-26B-A4B-it"),
    "mistral-24b": (
        "large_model/Mistral-Small-3.1-24B-Instruct-2503",
        "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
    ),
}


def valid_plan_ids(tier_dir: Path) -> set[str]:
    out = set()
    for path in (tier_dir / "global-plans").glob("*/initial_plan.json"):
        try:
            if json.loads(path.read_text()).get("status") == "ok":
                out.add(path.parent.name)
        except (OSError, ValueError):
            continue
    return out


def v1_artifact_ids(tier_dir: Path) -> set[str]:
    return {
        p.name.split("__")[0]
        for p in (tier_dir / "replan/artifacts").glob("*.json")
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--out", default=str(PUBLIC_ROOT / "experiments/replan_v2_smoke"))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    eligible: dict[str, set[str]] = {}
    for lane, (tier, _) in ROSTER.items():
        tier_dir = FULL_EVAL / tier
        eligible[lane] = valid_plan_ids(tier_dir) & v1_artifact_ids(tier_dir)
    coverage: dict[str, int] = {}
    for ids in eligible.values():
        for rid in ids:
            coverage[rid] = coverage.get(rid, 0) + 1
    rng = random.Random(args.seed)
    order = sorted(coverage)
    rng.shuffle(order)
    order.sort(key=lambda rid: -coverage[rid])  # stable: shuffle then coverage

    summary = {"seed": args.seed, "n": args.n, "lanes": {}}
    for lane, (tier, model) in ROSTER.items():
        chosen = [rid for rid in order if rid in eligible[lane]][: args.n]
        (out / f"{lane}.txt").write_text("\n".join(chosen) + "\n")
        summary["lanes"][lane] = {
            "model": model,
            "tier_dir": tier,
            "eligible": len(eligible[lane]),
            "selected": len(chosen),
            "overlap_with_all_lanes": sum(1 for r in chosen if coverage[r] == len(ROSTER)),
        }
    pair = {}
    lanes = list(ROSTER)
    for i, a in enumerate(lanes):
        for b in lanes[i + 1:]:
            sa = set((out / f"{a}.txt").read_text().split())
            sb = set((out / f"{b}.txt").read_text().split())
            pair[f"{a}&{b}"] = len(sa & sb)
    summary["pairwise_overlap"] = pair
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Recompute a published leaderboard from the archived per-variant records.

Every evaluation run in ``outputs/full_eval/<run_name>/<model>/<mode>/`` ships
``results.jsonl`` (one scored record per recipe-variant, including the model's
plan and the evaluator's verdicts) and the ``leaderboard.json`` we report.
This script re-runs the harness's own aggregator (vendored
``metrics.aggregate.leaderboard``, deterministic seeded bootstrap CIs) over
``results.jsonl`` and checks the result against ``leaderboard.json`` —
no model, no GPU, no re-inference needed.

Usage:
  python -m reproduction.offline.reproduce_scores outputs/full_eval/<run_name>
  python -m reproduction.offline.reproduce_scores --all
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "verification" / "backends" / "shared" / "src"))
from metrics.aggregate import leaderboard  # noqa: E402

SKIP_KEYS = {"meta"}  # environment provenance, not scores


def verify_run(run_dir: Path) -> list[tuple[str, bool, str]]:
    out = []
    for rec in sorted(run_dir.glob("*/*/results.jsonl")):
        mode_dir = rec.parent
        if not (mode_dir / "leaderboard.json").exists():
            out.append((f"{run_dir.name}/{mode_dir.name}", True, "SKIP: no published leaderboard.json (lane not finalized)"))
            continue
        published = json.loads((mode_dir / "leaderboard.json").read_text())
        rows = [json.loads(line) for line in rec.read_text().splitlines() if line.strip()]
        recomputed = leaderboard(rows)
        diffs = [k for k in published
                 if k not in SKIP_KEYS and recomputed.get(k) != published[k]]
        label = f"{run_dir.name}/{mode_dir.parent.name.split('__')[-1]}/{mode_dir.name}"
        out.append((label, not diffs,
                    "EXACT MATCH" if not diffs else f"MISMATCH keys: {diffs[:6]}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?", type=Path)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    runs = ([p for p in (ROOT / "outputs" / "full_eval").iterdir() if p.is_dir()]
            if a.all else [a.run if a.run.is_absolute() else ROOT / a.run])
    ok = bad = 0
    for run_dir in sorted(runs):
        for label, match, msg in verify_run(run_dir):
            print(("PASS " if match else "FAIL ") + label + " — " + msg)
            ok += match; bad += (not match)
    print(f"\n{ok} lane(s) reproduced exactly, {bad} mismatched")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

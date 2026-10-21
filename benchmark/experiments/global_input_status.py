#!/usr/bin/env python3
"""Health/progress snapshot of the GLOBAL+INPUT lanes (doc/global_input.md).

Per lane: Slurm state, rows written, status mix, plan_error rate, running
orchestration accuracy over all rows (failed rows count zero, like the
leaderboard), per-variant planning cost from the rows, and a health verdict:

  ok      - rows land and the recent window is not dominated by errors
  WARN    - >50% of the last 50 rows are non-ok
  ALERT   - every recent row errored, or the job died before 3,220 rows
  done    - 3,220 rows and leaderboard.json present

Usage (repository root):
  PYTHONPATH=benchmark python -m experiments.global_input_status [--run global-input-20260915] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "outputs" / "full_eval"
N_VARIANTS = 3220

# job name -> (run dir, model dir) for the 2026-09-15 campaign
LANES = {
    "Qwen3-4B": ("global-input-20260915", "hf:Qwen__Qwen3-4B-Instruct-2507"),
    "gemma-4-12B": ("global-input-20260915", "hf:google__gemma-4-12B-it"),
    "gemma-4-26B-A4B": ("global-input-20260915", "hf:google__gemma-4-26B-A4B-it"),
    "Qwen3.8-27B": ("global-input-20260915", "hf:Qwen__Qwen3.8-27B-FP8"),
    "Qwen3.8-27B-thinking": ("global-input-20260915-27b-thinking", "hf:Qwen__Qwen3.8-27B-FP8"),
    "DeepSeek-V4-Flash": ("global-input-20260915", "hf:deepseek-ai__DeepSeek-V4-Flash-0731"),
    "claude-opus-5": ("global-input-20260915", "claude-opus-5"),
    "claude-opus-5-thinking": ("global-input-20260915-opus-thinking", "claude-opus-5"),
}


def squeue() -> dict[str, str]:
    """job id (array-expanded) -> 'STATE name reason'."""
    try:
        out = subprocess.run(
            ["squeue", "-u", os.environ.get("USER", ""), "-h", "-o", "%i|%T|%j|%R|%M"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception:
        return {}
    jobs = {}
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) == 5:
            jobs[parts[0]] = f"{parts[1]} {parts[2]} {parts[4]} {parts[3]}"
    return jobs


def lane_snapshot(name: str, run: str, model: str) -> dict:
    mode_dir = FULL / run / model / "global_input"
    rows = []
    if (mode_dir / "results.jsonl").is_file():
        for line in (mode_dir / "results.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    n = len(rows)
    statuses = Counter(r.get("status") for r in rows)
    ok = [r for r in rows if r.get("status") == "ok"]
    recent = rows[-50:]
    recent_err = sum(1 for r in recent if r.get("status") != "ok")
    if n >= N_VARIANTS and (mode_dir / "leaderboard.json").is_file():
        health = "done"
    elif n == 0:
        health = "no rows yet"
    elif recent and recent_err == len(recent) and len(recent) >= 20:
        health = "ALERT: every recent row errored"
    elif recent and recent_err > len(recent) / 2 and len(recent) >= 20:
        health = f"WARN: {recent_err}/{len(recent)} recent rows non-ok"
    else:
        health = "ok"
    orch_all = sum(float(r.get("orchestration_accuracy") or 0) for r in ok) / n if n else None
    pt = [r.get("planner_prompt_tokens") for r in rows if isinstance(r.get("planner_prompt_tokens"), int)]
    ct = [r.get("planner_tokens") for r in rows if isinstance(r.get("planner_tokens"), int)]
    errors = Counter((r.get("error") or "")[:70] for r in rows if r.get("status") != "ok")
    return {
        "lane": name, "run": run, "rows": n, "pct": round(100 * n / N_VARIANTS, 1),
        "ok": statuses.get("ok", 0), "plan_error": statuses.get("plan_error", 0),
        "other_status": {k: v for k, v in statuses.items() if k not in ("ok", "plan_error")},
        "orch_all_rows": round(orch_all, 4) if orch_all is not None else None,
        "plan_error_rate": round(statuses.get("plan_error", 0) / n, 3) if n else None,
        "mean_prompt_tokens": round(sum(pt) / len(pt)) if pt else None,
        "mean_completion_tokens": round(sum(ct) / len(ct)) if ct else None,
        "cache_reused_rows": sum(1 for r in rows if r.get("plan_cache_reused")),
        "top_errors": errors.most_common(3),
        "health": health,
        "leaderboard": (mode_dir / "leaderboard.json").is_file(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    jobs = squeue()
    snaps = [lane_snapshot(n, r, m) for n, (r, m) in LANES.items()]
    if args.json:
        print(json.dumps({"jobs": jobs, "lanes": snaps}, default=str))
        return 0
    print("JOBS:")
    for jid, desc in sorted(jobs.items()):
        print(f"  {jid:>10} {desc}")
    print("\nLANES:")
    print(f"{'lane':<24}{'rows':>6}{'%':>6}{'ok':>6}{'perr':>6}{'orch':>8}{'perr%':>7}{'p_tok':>8}{'c_tok':>7}  health")
    for s in snaps:
        print(f"{s['lane']:<24}{s['rows']:>6}{s['pct']:>6}{s['ok']:>6}{s['plan_error']:>6}"
              f"{(s['orch_all_rows'] if s['orch_all_rows'] is not None else '-'):>8}"
              f"{(round(100*s['plan_error_rate']) if s['plan_error_rate'] is not None else '-'):>7}"
              f"{(s['mean_prompt_tokens'] or '-'):>8}{(s['mean_completion_tokens'] or '-'):>7}  {s['health']}")
        if s["other_status"]:
            print(f"{'':<24}  other statuses: {s['other_status']}")
        if s["top_errors"] and s["rows"]:
            for err, cnt in s["top_errors"][:2]:
                print(f"{'':<24}  {cnt:>4}x {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

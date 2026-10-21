"""Recompute a leaderboard.json from an existing results.jsonl.

Used when the metric aggregation changes after a run completed: the result
rows are the ground record, the leaderboard is derived. The run-protocol
``meta`` block from the existing leaderboard is preserved verbatim so
protocol validation keeps working.

Usage:
    PYTHONPATH=benchmark python -m reproduction.offline.recompute_leaderboard \
        outputs/full_eval/<run>/<model>/<mode>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PUBLIC_ROOT))
sys.path.insert(0, str(PUBLIC_ROOT / "verification" / "backends" / "shared" / "src"))

from metrics.aggregate import leaderboard  # noqa: E402


def recompute(mode_dir: Path) -> dict:
    results_path = mode_dir / "results.jsonl"
    board_path = mode_dir / "leaderboard.json"
    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    previous = (
        json.loads(board_path.read_text(encoding="utf-8"))
        if board_path.is_file()
        else {}
    )
    board = leaderboard(rows)
    if isinstance(previous.get("meta"), dict):
        board["meta"] = previous["meta"]
    board_path.write_text(
        json.dumps(board, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode_dirs", nargs="+", type=Path,
                        help="one or more <run>/<model>/<mode> directories")
    args = parser.parse_args(argv)
    for mode_dir in args.mode_dirs:
        board = recompute(mode_dir)
        print(json.dumps({
            "dir": str(mode_dir),
            "n": board.get("n"),
            "orchestration_accuracy": board.get("orchestration_accuracy"),
            "final_accuracy": board.get("final_accuracy"),
            "side_effect_accuracy": board.get("side_effect_accuracy"),
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

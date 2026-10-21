"""Row-level parity check: the example scorer vs the canonical evaluator.

For every per-task artifact (the ``<model>/<mode>/artifacts/*.json`` files
``evaluation.full_eval`` writes), this replays the recorded trajectory and
final state through the standalone ``cal_acc.score`` entry point and compares
its side-effect, terminal, and final verdicts against the ``run_eval``
verdicts stored in the artifact. The reference for ``final`` is the published
definition (side-effect AND normalized terminal output), not the stricter
``outcome_pass`` diagnostic.

Usage:

    python -m reproduction.offline.verify_calacc_parity <run>/<model>/<mode> ...
    python -m reproduction.offline.verify_calacc_parity --manifest frozen_list.txt \
        [--expected-rows N]

Directories are scanned at invocation time; a run that is still being
written grows between scans, so an auditable claim must be made against a
frozen list: build one with ``find <dirs> -name '*.json' | sort > list.txt``
and pass it via ``--manifest``, recording the list alongside the result.
``--expected-rows`` asserts the exact number of rows compared. The check
fails (non-zero exit) on any disagreement, on any scoring exception, on an
empty input (zero rows can never demonstrate coverage), on a directory that
contributes no artifacts, and on an ``--expected-rows`` mismatch.

Execution-trace components are NOT compared: the public trace metrics are
computed from the published ``tool_expectations`` and are a documented
simplification of the canonical evaluator's runtime trace adjudication.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _artifact_paths(args: argparse.Namespace) -> list[str]:
    if args.manifest:
        paths = [
            line.strip()
            for line in Path(args.manifest).read_text().splitlines()
            if line.strip()
        ]
        missing = [path for path in paths if not os.path.isfile(path)]
        if missing:
            raise SystemExit(
                f"manifest lists {len(missing)} missing files, "
                f"e.g. {missing[:3]} — the archive changed after freezing"
            )
        return paths
    paths = []
    for directory in args.directories:
        found = sorted(glob.glob(os.path.join(directory, "artifacts", "*.json")))
        if not found:
            raise SystemExit(f"no artifacts under {directory} — wrong path?")
        paths.extend(found)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="*",
                        help="run directories containing artifacts/")
    parser.add_argument("--manifest",
                        help="frozen newline-separated list of artifact paths"
                             " (takes precedence over directories)")
    parser.add_argument("--expected-rows", type=int, default=None,
                        help="assert exactly this many rows were compared")
    args = parser.parse_args(argv)
    if not args.manifest and not args.directories:
        parser.error("provide run directories or --manifest")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from examples.smoke_adapter.cal_acc import score
    from examples.smoke_adapter.datasets import load_ground_truth

    total = 0
    exceptions: list[tuple[str, str]] = []
    mismatches: dict[str, list[str]] = {
        "side_effect": [], "terminal": [], "final": [],
    }
    for path in _artifact_paths(args):
        artifact = json.loads(Path(path).read_text())
        output = artifact["output"]
        verdict = artifact["verdict"]
        recipe_id, variant_id = artifact["task_id"].split("__v")
        ground_truth = load_ground_truth(recipe_id, variant_id)
        record = {
            "trajectory": output.get("trajectory") or [],
            "final_state": output.get("final_snapshot") or {},
            "final_answer": output.get("final_answer"),
            "stop_reason": output.get("stop_reason"),
            "status": "ok",
        }
        try:
            result = score(record, ground_truth)
        except Exception as exc:  # pragma: no cover - report and continue
            exceptions.append((artifact["task_id"], repr(exc)))
            continue
        total += 1
        reference_side_effect = bool(verdict.get("side_effect_pass"))
        reference_terminal = bool(verdict.get("terminal_normalized_pass"))
        reference_final = reference_side_effect and reference_terminal
        if bool(result["side_effect_accuracy"]) != reference_side_effect:
            mismatches["side_effect"].append(artifact["task_id"])
        if bool(result["terminal_output_accuracy"]) != reference_terminal:
            mismatches["terminal"].append(artifact["task_id"])
        if bool(result["final_accuracy"]) != reference_final:
            mismatches["final"].append(artifact["task_id"])

    print(f"rows compared: {total}  score() exceptions: {len(exceptions)}")
    failed = bool(exceptions)
    for name, rows in mismatches.items():
        print(f"{name} mismatches: {len(rows)}  e.g. {rows[:8]}")
        failed = failed or bool(rows)
    for task_id, error in exceptions[:5]:
        print("ERROR", task_id, error)
    if total == 0:
        print("FAIL: zero rows compared — an empty input demonstrates nothing")
        return 1
    if args.expected_rows is not None and total != args.expected_rows:
        print(f"FAIL: expected {args.expected_rows} rows, compared {total}")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

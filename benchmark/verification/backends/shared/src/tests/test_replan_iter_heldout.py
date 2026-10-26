"""Unit tests for the held-out-variant self-evolution driver's pure parts:
the variant split, the feedback filter, and subset scoring.

Run with:
  PYTHONPATH=.:verification/backends/simulated/src:verification/backends/shared/src \
    python -m pytest verification/backends/shared/src/tests/test_replan_iter_heldout.py
"""
from __future__ import annotations

from experiments.replan_iter_heldout import filter_feedback_runs, split_variants, subset_rows


def test_split_is_by_index_and_records_next_two():
    assert split_variants([0, 1, 2, 3, 4], 2) == {"seen": [0, 1], "heldout": [2, 3, 4], "heldout2": [2, 3]}
    assert split_variants([4, 0, 2, 1, 3], 2)["seen"] == [0, 1]  # order-independent
    assert split_variants([0, 1], 2) == {"seen": [0, 1], "heldout": [], "heldout2": []}
    assert split_variants([0], 2) == {"seen": [0], "heldout": [], "heldout2": []}
    assert split_variants([0, 1, 2], 1) == {"seen": [0], "heldout": [1, 2], "heldout2": [1, 2]}


def test_subset_rows_and_feedback_filter_never_leak_heldout_variants():
    split = {"r1": split_variants([0, 1, 2, 3], 2), "r2": split_variants([0, 1], 2)}
    rows = [{"recipe_id": "r1", "variant": v} for v in range(4)] + [{"recipe_id": "r2", "variant": v} for v in range(2)]
    assert [r["variant"] for r in subset_rows(rows, split, "seen") if r["recipe_id"] == "r1"] == [0, 1]
    assert [r["variant"] for r in subset_rows(rows, split, "heldout")] == [2, 3]
    assert [r["variant"] for r in subset_rows(rows, split, "heldout2")] == [2, 3]
    assert len(subset_rows(rows, split, "all")) == 6
    runs = {"r1": [{"task_id": f"r1__v{v:02d}"} for v in range(4)], "r2": [{"task_id": "r2__v00"}, {"task_id": "r2__v01"}]}
    kept = filter_feedback_runs(runs, split)
    assert [p["task_id"] for p in kept["r1"]] == ["r1__v00", "r1__v01"]
    assert [p["task_id"] for p in kept["r2"]] == ["r2__v00", "r2__v01"]

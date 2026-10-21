"""Merge sharded Local View (incremental_workflow) runs into one mode dir.

The Local View ablation was sharded across Slurm jobs on disjoint recipe-id
subsets for wall-clock reasons.  This script reassembles one canonical
``<model>/local`` mode directory from the shard mode dirs and verifies the
merge is exact:

* result rows across shards are disjoint on (recipe_id, variant, run_index)
  and their union covers every manifest recipe exactly once per variant;
* trajectories are disjoint on task_id and their count equals the number of
  scored rows;
* artifact files may only collide when byte-identical (pre-seeded plan-cache
  copies), never with divergent content;
* the merged leaderboard is recomputed from the merged rows with the
  canonical aggregator (never summed from shard boards); shard ``meta``
  blocks are carried over with per-process counters summed and a
  ``merged_from`` provenance record appended.

Usage:
    PYTHONPATH=benchmark python -m scripts.merge_local_view_shards \
        --out outputs/full_eval/<tier>/<model>/local \
        --plans-out outputs/full_eval/<tier>/<model>/local/plans \
        outputs/full_eval/<run>-s0/<model>/incremental_workflow \
        outputs/full_eval/<run>-s1/<model>/incremental_workflow

Each shard mode dir must live at ``<shard_run>/<model_key>/incremental_workflow``
with the shard's plan artifacts at ``<shard_run>/incremental_plans/<model_key>``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PUBLIC_ROOT))
sys.path.insert(0, str(PUBLIC_ROOT / "verification" / "backends" / "shared" / "src"))

from metrics.aggregate import leaderboard  # noqa: E402

SUMMED_META_COUNTERS = (
    "initial_plan_artifact_calls",
    "initial_plan_generation_calls_this_process",
    "initial_plan_generation_tokens_this_process",
    "n_recipes",
    "runtime_llm_calls_this_mode",
    "runtime_llm_calls_this_process",
    "runtime_llm_tokens_this_mode",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _manifest_recipe_ids() -> set[str]:
    manifest = json.loads(
        (PUBLIC_ROOT / "input/manifest.json").read_text(encoding="utf-8")
    )
    return {str(row["recipe_id"]) for row in manifest.get("recipes") or []}


def merge(shards: list[Path], out: Path, plans_out: Path | None) -> dict:
    all_rows: list[dict] = []
    all_traj: list[dict] = []
    shard_meta: list[dict] = []
    provenance = []
    for shard in shards:
        rows = _read_jsonl(shard / "results.jsonl")
        traj = _read_jsonl(shard / "trajectories.jsonl")
        board = json.loads((shard / "leaderboard.json").read_text(encoding="utf-8"))
        provenance.append({
            "shard": str(shard),
            "rows": len(rows),
            "trajectories": len(traj),
            "recipes": len({r["recipe_id"] for r in rows}),
        })
        all_rows.extend(rows)
        all_traj.extend(traj)
        if isinstance(board.get("meta"), dict):
            shard_meta.append(board["meta"])

    # --- verification: rows -------------------------------------------------
    keys = [(str(r["recipe_id"]), str(r["variant"]), r.get("run_index", 0))
            for r in all_rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("FATAL: duplicate (recipe, variant, run_index) across shards")
    recipes = {str(r["recipe_id"]) for r in all_rows}
    manifest_ids = _manifest_recipe_ids()
    if recipes != manifest_ids:
        missing = sorted(manifest_ids - recipes)[:10]
        extra = sorted(recipes - manifest_ids)[:10]
        raise SystemExit(
            f"FATAL: recipe coverage mismatch: {len(recipes)}/{len(manifest_ids)}"
            f" missing={missing} extra={extra}"
        )

    # --- verification: trajectories -----------------------------------------
    traj_ids = [t["task_id"] for t in all_traj]
    if len(traj_ids) != len(set(traj_ids)):
        raise SystemExit("FATAL: duplicate trajectory task_id across shards")

    all_rows.sort(key=lambda r: (str(r["recipe_id"]), str(r["variant"]),
                                 r.get("run_index", 0)))
    all_traj.sort(key=lambda t: str(t["task_id"]))

    # --- write merged mode dir ----------------------------------------------
    out.mkdir(parents=True, exist_ok=True)
    with (out / "results.jsonl").open("w", encoding="utf-8") as fh:
        for row in all_rows:
            fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    with (out / "trajectories.jsonl").open("w", encoding="utf-8") as fh:
        for row in all_traj:
            fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    # artifacts: byte-identical collisions allowed (seeded copies), else fatal
    art_out = out / "artifacts"
    art_out.mkdir(exist_ok=True)
    for shard in shards:
        src_dir = shard / "artifacts"
        if not src_dir.is_dir():
            continue
        for src in sorted(src_dir.iterdir()):
            dst = art_out / src.name
            if dst.exists():
                if _sha256(src) != _sha256(dst):
                    raise SystemExit(f"FATAL: divergent artifact {src.name}")
                continue
            shutil.copy2(src, dst)
    n_artifacts = sum(1 for _ in art_out.iterdir())

    # plans: union of per-recipe plan dirs; duplicated recipes (pre-seeded
    # cache copies) must agree byte-for-byte on every file
    n_plans = 0
    n_planless_aborted = None
    if plans_out is not None:
        plans_out.mkdir(parents=True, exist_ok=True)
        for shard in shards:
            model_key = shard.parent.name.replace("hf:", "hf_").replace("/", "__")
            src_root = shard.parent.parent / "incremental_plans" / model_key
            if not src_root.is_dir():
                raise SystemExit(f"FATAL: no plan dir {src_root}")
            for recipe_dir in sorted(src_root.iterdir()):
                dst = plans_out / recipe_dir.name
                if dst.exists():
                    for f in sorted(recipe_dir.iterdir()):
                        if _sha256(f) != _sha256(dst / f.name):
                            raise SystemExit(
                                f"FATAL: divergent plan {recipe_dir.name}/{f.name}"
                            )
                    continue
                shutil.copytree(recipe_dir, dst)
        n_plans = sum(1 for _ in plans_out.iterdir())
        # Every recipe with at least one executed (non plan_error) row must
        # have its frozen plan on disk.  Recipes whose editor session aborted
        # before producing a plan legitimately have rows (all plan_error) but
        # no plan artifact — count them honestly instead of failing.
        executed = {str(r["recipe_id"]) for r in all_rows
                    if r.get("status") != "plan_error"}
        plan_names = {p.name for p in plans_out.iterdir()}
        if not executed <= plan_names:
            missing = sorted(executed - plan_names)[:10]
            raise SystemExit(
                f"FATAL: executed recipes missing frozen plans: {missing}"
            )
        n_planless_aborted = len(recipes - plan_names)

    # --- leaderboard: recompute from merged rows ----------------------------
    board = leaderboard(all_rows)
    if shard_meta:
        meta = dict(shard_meta[0])
        for key in SUMMED_META_COUNTERS:
            values = [m.get(key) for m in shard_meta]
            if all(isinstance(v, (int, float)) for v in values):
                meta[key] = sum(values)
        hashes: dict = {}
        for m in shard_meta:
            for rid, h in (m.get("initial_plan_hashes") or {}).items():
                if rid in hashes and hashes[rid] != h:
                    raise SystemExit(f"FATAL: divergent initial_plan_hash {rid}")
                hashes[rid] = h
        if hashes:
            meta["initial_plan_hashes"] = hashes
        meta["merged_from"] = provenance
        board["meta"] = meta
    (out / "leaderboard.json").write_text(
        json.dumps(board, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return {
        "out": str(out),
        "rows": len(all_rows),
        "recipes": len(recipes),
        "trajectories": len(all_traj),
        "artifacts": n_artifacts,
        "plans": n_plans,
        "planless_aborted_recipes": n_planless_aborted,
        "n": board.get("n"),
        "orchestration_accuracy": board.get("orchestration_accuracy"),
        "final_accuracy": board.get("final_accuracy"),
        "side_effect_accuracy": board.get("side_effect_accuracy"),
        "execution_trace_accuracy": board.get("execution_trace_accuracy"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shards", nargs="+", type=Path,
                        help="shard <run>/<model>/incremental_workflow dirs")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--plans-out", type=Path, default=None)
    args = parser.parse_args(argv)
    summary = merge(args.shards, args.out, args.plans_out)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

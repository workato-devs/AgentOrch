#!/usr/bin/env python3
"""End-to-end self-check of the GLOBAL+INPUT (``global_input``) mode on real
recipes with an oracle planner (no GPU, no API).

For each selected variant the "model" replies with the recipe's reference
plan serialized as ``{"plan": [...]}`` -- exactly the text a model would emit.
That drives the real per-variant path: runtime-input projection ->
``prepare_variant_plan`` (prompt, parse, validate, per-variant cache) ->
deterministic frozen-plan execution -> canonical scorer. The check asserts:

* every row is scored ``ok`` with orchestration accuracy 1.0 (an oracle plan
  must pass, so any failure is harness plumbing, not model quality);
* one planning call per variant, each prompt carrying that variant's own
  trigger input and no other variant's;
* per-variant cache artifacts under ``plans_global_input/`` flagged
  ``contains_runtime_input``; a second pass makes zero model calls;
* Global's variant-blind prompt for the same recipe differs from the
  GLOBAL+INPUT prompt only by the runtime-input section.

Usage (repository root, CPU):
  PYTHONPATH=benchmark python -m experiments.global_input_selfcheck [--limit 2]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PUBLIC_ROOT))
sys.path.insert(0, str(PUBLIC_ROOT / "verification" / "backends" / "simulated" / "src"))
sys.path.insert(0, str(PUBLIC_ROOT / "verification" / "backends" / "shared" / "src"))


class OraclePlanner:
    """Replies with a pre-assigned plan per (recipe, variant); records prompts."""

    def __init__(self, plans: dict[tuple[str, int], list]) -> None:
        self.model = "oracle-global-input"
        self.temperature = 0.0
        self.calls = 0
        self.total_tokens = 0
        self.seen: list[tuple[str, str]] = []
        self._plans = plans
        self.current: tuple[str, int] | None = None

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        assert len(messages) == 1, "one-shot planner must receive a single user turn"
        self.seen.append((system, messages[0]["content"]))
        self.calls += 1
        reply = json.dumps({"plan": self._plans[self.current]})
        self.total_tokens += len(reply) // 4
        return reply


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--variants", default="all", choices=("0", "all"))
    parser.add_argument("--keep", action="store_true", help="keep the temp eval root")
    args = parser.parse_args()

    from evaluation.full_eval import _configure, _recipe_ids

    run_name = "global-input-selfcheck"
    eval_root = _configure(run_name, "simulated", f"selfcheck-{os.getpid()}")
    from task import run_eval
    from task.workflow_plan import stable_hash

    ids = _recipe_ids()[: args.limit]
    plans: dict[tuple[str, int], list] = {}
    tasks: list[tuple[str, int]] = []
    for recipe_id in ids:
        artifact = run_eval._scripted_initial_plan_artifact(recipe_id, "oracle")
        assert artifact["status"] == "ok", (recipe_id, artifact.get("error"))
        for variant in run_eval._selected_variants(recipe_id, args.variants):
            plans[(recipe_id, variant)] = artifact["plan"]
            tasks.append((recipe_id, variant))

    llm = OraclePlanner(plans)
    rows = []
    for recipe_id, variant in tasks:
        llm.current = (recipe_id, variant)
        row = run_eval.run_one(
            recipe_id, variant, "global_input", llm,
            eval_root=eval_root, task_source="task_description",
            tool_surface="broad", enriched_tool_docs=True,
        )
        rows.append(row)
        print(json.dumps({"task_id": row["task_id"], "status": row.get("status"),
                          "orch": row.get("orchestration_accuracy"),
                          "planner_calls": row.get("planner_calls"),
                          "prompt_chars": row.get("planner_prompt_chars")}))

    failures = []
    # 1. every oracle row scored ok and perfect
    bad = [r for r in rows if r.get("status") != "ok"]
    if bad:
        failures.append(f"{len(bad)} rows not ok: " + "; ".join(
            f"{r['task_id']}={r.get('status')}:{str(r.get('error'))[:120]}" for r in bad[:5]))
    from metrics.aggregate import leaderboard
    board = leaderboard(rows)
    if board["orchestration_accuracy"] != 1.0:
        failures.append(f"oracle orchestration accuracy {board['orchestration_accuracy']} != 1.0")
    # 2. one planning call per variant, each prompt carrying its own trigger input
    if llm.calls != len(tasks):
        failures.append(f"planning calls {llm.calls} != variants {len(tasks)}")
    from benchmark.seed_recipe import load_variant_input
    triggers = {}
    for recipe_id, variant in tasks:
        vi = load_variant_input(recipe_id, variant, None)
        triggers[(recipe_id, variant)] = json.dumps(vi["trigger_input"], indent=1, sort_keys=True)
    for (recipe_id, variant), (_, user) in zip(tasks, llm.seen, strict=True):
        if "## Concrete runtime input" not in user:
            failures.append(f"{recipe_id} v{variant}: prompt lacks runtime-input section")
        own = triggers[(recipe_id, variant)]
        if own not in user:
            failures.append(f"{recipe_id} v{variant}: prompt lacks its own trigger input")
        for other_key, other in triggers.items():
            if other_key[0] == recipe_id and other_key != (recipe_id, variant) and other != own and other in user:
                failures.append(f"{recipe_id} v{variant}: prompt leaks variant {other_key[1]}'s input")
    # 3. per-variant artifacts, flagged, and a second pass is pure cache
    safe = llm.model.replace("/", "__").replace(":", "_")
    for recipe_id, variant in tasks:
        p = eval_root / "plans_global_input" / safe / recipe_id / f"variant_{variant:02d}.json"
        if not p.is_file():
            failures.append(f"missing artifact {p}")
            continue
        a = json.loads(p.read_text())
        if not a["planner_input"]["contains_runtime_input"] or a["planner_prompt"] != "recipe-level-symbolic-executable-plan+runtime-input":
            failures.append(f"{p}: not flagged as runtime-input plan")
        if a.get("raw_response") is None:
            failures.append(f"{p}: raw completion not preserved")
    calls_before = llm.calls
    for recipe_id, variant in tasks:
        llm.current = (recipe_id, variant)
        row = run_eval.run_one(recipe_id, variant, "global_input", llm, eval_root=eval_root,
                               task_source="task_description", tool_surface="broad")
        if row.get("status") != "ok" or not row.get("plan_cache_reused"):
            failures.append(f"{row['task_id']}: second pass not a cache hit ({row.get('status')})")
    if llm.calls != calls_before:
        failures.append(f"second pass made {llm.calls - calls_before} model calls; expected 0")
    # 4. Global prompt == GLOBAL+INPUT prompt minus the runtime section
    recipe_id, variant = tasks[0]
    g = run_eval.initial_plan_context(recipe_id, llm, eval_root, model_id=llm.model, enriched_tool_docs=True)
    _, gi_user = llm.seen[0]
    head = gi_user.split("\n\n## Concrete runtime input\n", 1)[0]
    if g["user"] != head + '\nThe top-level response is exactly {"plan":[]}.':
        failures.append("GLOBAL+INPUT user prompt is not Global prompt + runtime section")
    if g["cache_key"] == stable_hash(gi_user):
        failures.append("cache keys collide between Global and GLOBAL+INPUT")

    summary = {
        "recipes": len(ids), "variants": len(tasks), "rows_ok": sum(r.get("status") == "ok" for r in rows),
        "orchestration_accuracy": board["orchestration_accuracy"], "final_accuracy": board["final_accuracy"],
        "planning_calls": calls_before, "eval_root": str(eval_root), "failures": failures,
    }
    print("SUMMARY", json.dumps(summary, indent=1))
    if not args.keep:
        import shutil
        shutil.rmtree(eval_root, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

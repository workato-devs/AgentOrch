"""Iterative replan (self-evolution) with a variant split: feedback comes
from a fixed subset of each recipe's variants, and the revised plan is scored
on the variants the model never received feedback about.

  round 0 : the recipe's frozen initial plan (Global View; pre-seeded cache,
            invalid plans included) — identical to experiments.replan_iter
  round k : the current plan is executed deterministically on EVERY variant
            (fresh simulator state, no runtime LLM call). The model is shown
            [planner prompt, its previous plan, EXECUTION FEEDBACK] where the
            feedback covers ONLY the recipe's first --feedback-variants
            variants (by variant index; default 2, i.e. v00 and v01), and
            emits one complete revised plan (same validator, fail-closed).
            Every round is scored on three row sets:
              seen      = the feedback variants
              heldout   = every other variant of the recipe (v02, v03, ...)
              heldout2  = only the next two variants (v02, v03) — the
                          literal "1,2 -> feedback, 3,4 -> evaluate" reading
              all       = every variant (comparable to replan_iter)

Recipes with <= --feedback-variants variants are still revised (they count
in `seen` and `all`) but contribute no held-out rows.

Feedback content, prompt, validator, executor, scorer and cost are those of
experiments.replan_iter (imported, not copied); the only differences are the
row filter applied before rendering feedback and the per-subset scoring.

Usage (mirrors experiments.replan_iter):
  PYTHONPATH=benchmark python -m experiments.replan_iter_heldout \\
    --run-name replan-iter-heldout --state-namespace ns --backend simulated \\
    --model hf:Qwen/Qwen3.8-27B-FP8 --ids <recipe ids...> --rounds 3 \\
    --feedback-variants 2 --resume
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from evaluation.full_eval import _configure, _recipe_ids
from experiments import replan_iter as base

MODE = "replan_iter_heldout"
SUBSETS = ("all", "seen", "heldout", "heldout2")


# ----------------------------------------------------------------------------
# split (pure)
# ----------------------------------------------------------------------------

def split_variants(variants: list[int], feedback_count: int) -> dict[str, list[int]]:
    """Deterministic split by variant index: the first ``feedback_count``
    variants are the feedback ("seen") set, the rest are held out."""
    ordered = sorted(variants)
    seen = ordered[:feedback_count]
    heldout = ordered[feedback_count:]
    return {"seen": seen, "heldout": heldout, "heldout2": heldout[:2]}


def subset_rows(rows: list[dict[str, Any]], split: dict[str, dict[str, list[int]]],
                subset: str) -> list[dict[str, Any]]:
    if subset == "all":
        return list(rows)
    return [r for r in rows if int(r["variant"]) in split[str(r["recipe_id"])][subset]]


def filter_feedback_runs(runs_by_recipe: dict[str, list[dict[str, Any]]],
                         split: dict[str, dict[str, list[int]]]) -> dict[str, list[dict[str, Any]]]:
    """Keep only the feedback variants' run payloads (task_id = <recipe>__vNN)."""
    out: dict[str, list[dict[str, Any]]] = {}
    for recipe_id, payloads in runs_by_recipe.items():
        allowed = {f"{recipe_id}__v{v:02d}" for v in split[str(recipe_id)]["seen"]}
        out[recipe_id] = [p for p in payloads if p.get("task_id") in allowed]
    return out


def subset_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = base._score_summary(rows) if rows else {"board": {"n": 0}, "per_task": {}}
    summary["board"]["n"] = len(rows)
    return summary


# ----------------------------------------------------------------------------
# driver
# ----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--state-namespace", required=True)
    parser.add_argument("--backend", default="simulated")
    parser.add_argument("--model", required=True)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=3, help="revision rounds K (round 0 = frozen initial plan)")
    parser.add_argument("--feedback-variants", type=int, default=2,
                        help="feedback comes from the first N variants of each recipe (by index); the rest are held out")
    parser.add_argument("--feedback", choices=("full", "errors"), default="full")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--exec-workers", type=int, default=int(os.environ.get("REPLAN_ITER_EXEC_WORKERS", "4")))
    parser.add_argument("--llm-workers", type=int, default=int(os.environ.get("VLLM_REACT_CONCURRENCY", "16")))
    parser.add_argument("--llm-chunk", type=int, default=int(os.environ.get("REPLAN_ITER_LLM_CHUNK", "32")))
    parser.add_argument("--stub-llm", action="store_true",
                        help="offline plumbing check: the 'model' re-emits its previous plan unchanged")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_name):
        parser.error("bad --run-name")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.state_namespace):
        parser.error("bad --state-namespace")
    if args.feedback_variants < 1:
        parser.error("--feedback-variants must be >= 1")

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    eval_root = _configure(args.run_name, args.backend, args.state_namespace)
    import task.run_eval as re_

    ids = list(args.ids) if args.ids else _recipe_ids()
    if args.limit:
        ids = ids[: args.limit]
    run_dir = eval_root / args.model.replace("/", "__") / MODE
    run_dir.mkdir(parents=True, exist_ok=True)

    # fixed, recorded split
    split = {rid: split_variants(re_._selected_variants(rid, "all"), args.feedback_variants) for rid in ids}
    (run_dir / "split.json").write_text(json.dumps(
        {"feedback_variants": args.feedback_variants, "rule": "first N variants by index = seen; rest = heldout; heldout2 = next two",
         "recipes": split}, indent=1) + "\n")
    print(json.dumps({"split": {s: sum(len(v[s]) for v in split.values()) for s in ("seen", "heldout", "heldout2")},
                      "recipes_with_heldout": sum(1 for v in split.values() if v["heldout"]),
                      "recipes": len(ids)}))

    if args.stub_llm:
        llm = base._StubLLM(args.model)
    else:
        from task.llm_client import build_client
        llm = build_client(args.model)

    # round 0: frozen initial plans (identical to replan_iter)
    contexts: dict[str, dict[str, Any]] = {}
    plans: dict[str, dict[str, Any]] = {}
    for recipe_id in ids:
        contexts[recipe_id] = re_.initial_plan_context(
            recipe_id, llm, eval_root, model_id=args.model, enriched_tool_docs=True)
        cache_path = contexts[recipe_id]["cache_path"]
        if args.stub_llm:
            plans[recipe_id] = (
                json.loads(cache_path.read_text()) if cache_path.is_file() else
                {"recipe_id": recipe_id, "status": "invalid_plan", "plan": None,
                 "plan_hash": None, "error": "no cached plan (stub run)", "raw_response": ""}
            )
        else:
            try:
                plans[recipe_id] = re_.prepare_initial_plan(
                    recipe_id, llm, eval_root, model_id=args.model, enriched_tool_docs=True)
            except Exception as exc:
                print(json.dumps({"round": 0, "recipe_id": recipe_id,
                                  "initial_plan_error": f"{type(exc).__name__}: {exc}"[:300]}))
                plans[recipe_id] = {"recipe_id": recipe_id, "status": "invalid_plan", "plan": None,
                                    "plan_hash": None, "raw_response": "",
                                    "error": f"initial planning failed: {exc}"}
        plans[recipe_id]["round"] = 0
    (run_dir / "plans" / "round_0").mkdir(parents=True, exist_ok=True)
    for recipe_id, artifact in plans.items():
        (run_dir / "plans" / "round_0" / f"{recipe_id}.json").write_text(
            json.dumps(artifact, indent=1, default=str) + "\n")
    print(json.dumps({"round": 0, "valid_plans": sum(1 for a in plans.values() if a.get("status") == "ok"),
                      "recipes": len(ids)}))

    curve: list[dict[str, Any]] = []
    round0_tasks: dict[str, dict[str, tuple[float, float]]] = {}
    for k in range(args.rounds + 1):
        rows, runs_by_recipe = base.execute_round(k, ids, plans, llm, args, eval_root, run_dir, mode=MODE)
        entry: dict[str, Any] = {
            "round": k,
            "valid_plans": sum(1 for a in plans.values() if a.get("status") == "ok"),
            "revisions": {
                "accepted": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("status") == "ok"),
                "changed": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("changed") is True),
                "invalid": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("status") == "invalid_plan"),
                "llm_error": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("status") == "llm_error"),
            } if k > 0 else None,
        }
        rdir = run_dir / f"round_{k}"
        for subset in SUBSETS:
            summary = subset_summary(subset_rows(rows, split, subset))
            if k == 0:
                round0_tasks[subset] = summary["per_task"]
            flips = {"orch_up": 0, "orch_down": 0, "final_up": 0, "final_down": 0}
            for task_id, (orch, final) in summary["per_task"].items():
                o0, f0 = round0_tasks[subset].get(task_id, (0.0, 0.0))
                flips["orch_up"] += orch > o0; flips["orch_down"] += orch < o0
                flips["final_up"] += final > f0; flips["final_down"] += final < f0
            entry[subset] = {**summary["board"], "vs_round0": flips}
            (rdir / f"leaderboard_{subset}.json").write_text(json.dumps(
                {**summary["board"], "meta": {"model": args.model, "mode": MODE, "round": k, "subset": subset,
                                               "feedback_variants": args.feedback_variants,
                                               "n_recipes": len(ids), "feedback": args.feedback}},
                indent=2, default=str) + "\n")
        curve.append(entry)
        (run_dir / "curve.json").write_text(json.dumps(
            {"model": args.model, "mode": MODE, "rounds": args.rounds, "feedback": args.feedback,
             "feedback_variants": args.feedback_variants, "n_recipes": len(ids), "curve": curve},
            indent=2, default=str) + "\n")
        print("CURVE round %d: " % k + " ".join(
            f"{s}[n={entry[s]['n']} orch={entry[s].get('orchestration_accuracy')} final={entry[s].get('final_accuracy')}]"
            for s in SUBSETS) + f" valid_plans={entry['valid_plans']}")
        if k == args.rounds:
            break
        feedback_runs = filter_feedback_runs(runs_by_recipe, split)
        plans = base.revise_round(k, ids, {r: base._feedback_for_invalid(a) for r, a in plans.items()},
                                  feedback_runs, contexts, llm, args, run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

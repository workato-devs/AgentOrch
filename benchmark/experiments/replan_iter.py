"""Iterative replan ("self-evolution") evaluation.

Can a model improve its own frozen plan without any parameter update, only
by revising the plan from environment feedback?

  round 0 : the recipe's frozen initial plan (Global View; reused from the
            per-model plan cache so round 0 == Global bit-for-bit, invalid
            plans included)
  round k : every variant of the recipe is executed deterministically with
            the current plan (fresh simulator state, no runtime LLM call);
            the model is shown its previous plan + the execution feedback
            and emits one complete revised plan; the revision is validated
            with the same symbolic schema as the initial plan. An invalid
            revision is recorded and the previous plan is kept (fail-closed).

Feedback contains only what the environment itself returns — validator
errors, tool calls with their observations, runtime errors, the terminal
return — never gold calls, gold state, or scorer verdicts.

Every round is scored with the canonical scorer (same rows/metrics as the
other modes) so the result is a curve: orchestration/final accuracy per
round, plus paired flips against round 0.

Usage (mirrors evaluation.full_eval):
  PYTHONPATH=benchmark python -m experiments.replan_iter \
    --run-name replan-iter-smoke --state-namespace ns --backend simulated \
    --model hf:Qwen/Qwen3.8-27B-FP8 --ids <recipe ids...> --rounds 3 --resume
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from evaluation.full_eval import PUBLIC_ROOT, _configure, _recipe_ids

MODE = "replan_iter"
MAX_OBS_CHARS = 500
MAX_ARGS_CHARS = 300
MAX_FEEDBACK_CHARS = 30_000
MAX_RAW_CHARS = 6_000


# ----------------------------------------------------------------------------
# feedback rendering (pure)
# ----------------------------------------------------------------------------

def _clip(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + f"...<{len(text) - limit} more chars>"


def render_trace(run: dict[str, Any]) -> list[str]:
    """One line per executed step, model-visible information only."""
    lines: list[str] = []
    for step in run.get("steps") or []:
        if not isinstance(step, dict):
            continue
        node = step.get("plan_node_id")
        if "action" in step:
            action = step["action"] or {}
            head = f"[{node}] call {action.get('tool')} args={_clip(action.get('args'), MAX_ARGS_CHARS)}"
            if "error" in step:
                lines.append(f"{head} -> {_clip(step['error'], MAX_OBS_CHARS)}")
            else:
                lines.append(f"{head} -> {_clip(step.get('observation', ''), MAX_OBS_CHARS)}")
        elif "branch" in step:
            lines.append(f"[{node}] if -> {step['branch']}")
        elif "foreach_index" in step:
            lines.append(f"[{node}] foreach item #{step['foreach_index']}")
        elif "repeat_iteration" in step:
            lines.append(f"[{node}] repeat iteration #{step['repeat_iteration']}")
        elif "transform_bind" in step:
            lines.append(f"[{node}] transform -> {step['transform_bind']}")
        elif "caught" in step:
            lines.append(f"[{node}] try caught: {_clip(step['caught'], MAX_OBS_CHARS)}")
        elif "explicit_stop" in step:
            stop = step["explicit_stop"]
            lines.append(f"[{node}] stop error={stop.get('stop_with_error')} reason={_clip(stop.get('stop_reason'), 200)}")
        elif "return" in step:
            lines.append(f"[{node}] return {_clip(step['return'], MAX_OBS_CHARS)}")
        elif "error" in step:
            lines.append(f"ERROR {_clip(step['error'], MAX_OBS_CHARS)}")
    return lines


def render_feedback(round_index: int, artifact: dict[str, Any],
                    rows: list[dict[str, Any]]) -> str:
    """Environment feedback for one recipe after executing ``artifact`` on
    every variant. ``rows`` are run_one results (their ``run`` payload is
    used; verdict fields are deliberately ignored)."""
    parts = [f"EXECUTION FEEDBACK (round {round_index}):"]
    if artifact.get("status") == "ok" and artifact.get("revision_status") == "invalid_plan":
        parts.append(
            "Your previous revision was REJECTED by the plan validator "
            f"(error: {_clip(artifact.get('revision_error'), 600)}), so the plan "
            "shown above was executed unchanged."
        )
    if artifact.get("status") != "ok":
        parts.append(
            "Your previous plan was REJECTED by the plan validator and was not "
            f"executed. Validator error: {_clip(artifact.get('error'), 600)}"
        )
        return "\n".join(parts)
    for row in sorted(rows, key=lambda r: str(r.get("task_id"))):
        run = row.get("run") or {}
        status = row.get("status")
        variant = row.get("task_id")
        if status != "ok":
            parts.append(f"- variant {variant}: not executed ({status}: {_clip(row.get('error'), 300)})")
            continue
        parts.append(
            f"- variant {variant}: trigger_input={_clip(row.get('trigger_input'), MAX_ARGS_CHARS)} "
            f"| stop_reason={run.get('stop_reason')} | failed_calls={run.get('failed_calls')}"
        )
        for line in render_trace(run):
            parts.append("    " + line)
    text = "\n".join(parts)
    if len(text) > MAX_FEEDBACK_CHARS:
        text = text[:MAX_FEEDBACK_CHARS] + "\n...<feedback truncated>"
    return text


REVISION_INSTRUCTION = (
    "Revise your plan using this feedback. Diagnose what went wrong (rejected "
    "by the validator, a tool that failed, an unexpected observation, a branch "
    "or loop that did not do what the task requires) and fix it. Output the "
    "COMPLETE corrected WorkflowPlan in exactly the same JSON format as before "
    "({\"plan\": [...]}) — the whole plan, not a diff. If the plan already "
    "achieves the task on every variant, output it unchanged. No prose "
    "outside the JSON."
)


def build_revision_messages(context: dict[str, Any], artifact: dict[str, Any],
                            feedback: str) -> list[dict[str, str]]:
    """Planner prompt + the model's previous plan + feedback as a chat."""
    if artifact.get("status") == "ok" and isinstance(artifact.get("plan"), list):
        previous = json.dumps({"plan": artifact["plan"]}, indent=1)
    else:
        previous = _clip(artifact.get("raw_response") or "", MAX_RAW_CHARS)
    return [
        {"role": "user", "content": context["user"]},
        {"role": "assistant", "content": previous},
        {"role": "user", "content": feedback + "\n\n" + REVISION_INSTRUCTION},
    ]


def validate_revision(raw: str, context: dict[str, Any], *, round_index: int,
                      previous: dict[str, Any]) -> dict[str, Any]:
    """Parse + validate one revision with the initial-plan validator."""
    from task.agents import parse_plan
    from task.workflow_plan import PlanValidationError, normalize_plan, plan_hash

    parsed = parse_plan(raw)
    repaired = False
    if parsed is None:
        parsed = parse_plan(raw, repair_missing_closers=True)
        repaired = parsed is not None
    artifact: dict[str, Any] = {
        "recipe_id": context["recipe_id"],
        "round": round_index,
        "raw_response": raw,
        "json_syntax_repaired": repaired,
        "prior_plan_hash": previous.get("plan_hash"),
    }
    try:
        if parsed is None:
            raise PlanValidationError("model response does not contain a plan array")
        normalized = normalize_plan(
            parsed,
            context["allowed_tools"],
            tool_specs=context["tool_specs"],
            input_schema=context["validation_input_schema"],
            workspace_context=context["workspace_context"],
        )
    except PlanValidationError as exc:
        artifact.update({"status": "invalid_plan", "error": str(exc),
                         "plan": None, "plan_hash": None})
        return artifact
    artifact.update({"status": "ok", "plan": normalized,
                     "plan_hash": plan_hash(normalized)})
    artifact["changed"] = artifact["plan_hash"] != previous.get("plan_hash")
    return artifact


# ----------------------------------------------------------------------------
# driver
# ----------------------------------------------------------------------------

def _round_dir(run_dir: Path, k: int) -> Path:
    return run_dir / f"round_{k}"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _score_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from metrics.aggregate import leaderboard, primary_metrics_for_row
    board = leaderboard(rows) if rows else {}
    per_task = {}
    for row in rows:
        scored = primary_metrics_for_row(row) if row.get("status") == "ok" else None
        per_task[str(row.get("task_id"))] = (
            scored["orchestration_accuracy"] if scored else 0.0,
            scored["final_accuracy"] if scored else 0.0,
        )
    keys = ("n", "error_rate", "orchestration_accuracy", "orchestration_accuracy_ci95",
            "final_accuracy", "final_accuracy_ci95", "side_effect_accuracy",
            "execution_trace_accuracy", "terminal_output_accuracy", "stop_reasons",
            "excluded")
    return {"board": {k: board.get(k) for k in keys}, "per_task": per_task}


def execute_round(k: int, ids: list[str], plans: dict[str, dict[str, Any]],
                  llm, args, eval_root: Path, run_dir: Path,
                  mode: str = MODE) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Execute the current plan of every recipe on every variant; returns
    (scored rows without run payloads, run payloads by recipe). ``mode`` is
    the label written on rows/leaderboards (the held-out driver passes its
    own); execution semantics never depend on it."""
    import task.run_eval as re_

    rdir = _round_dir(run_dir, k)
    rdir.mkdir(parents=True, exist_ok=True)
    results_path = rdir / "results.jsonl"
    traj_path = rdir / "trajectories.jsonl"
    rows = _load_rows(results_path) if args.resume else []
    runs_by_recipe: dict[str, list[dict[str, Any]]] = {}
    if rows:
        for line in traj_path.read_text().splitlines() if traj_path.is_file() else []:
            payload = json.loads(line)
            runs_by_recipe.setdefault(str(payload["recipe_id"]), []).append(payload)
    done = {r["task_id"] for r in rows}
    tasks = [
        (recipe_id, variant)
        for recipe_id in ids
        for variant in re_._selected_variants(recipe_id, "all")
        if f"{recipe_id}__v{variant:02d}" not in done
    ]

    def evaluate(task):
        recipe_id, variant = task
        row = re_.run_one(
            recipe_id, variant, "plan_execute", llm,
            eval_root=eval_root, task_source="task_description",
            tool_surface="broad", enriched_tool_docs=True,
            initial_plan_artifact=plans[recipe_id], max_replans=0,
        )
        row["mode"] = mode
        row["round"] = k
        row["run_index"] = 0
        return row

    with results_path.open("a" if rows else "w") as rfh, traj_path.open("a" if rows else "w") as tfh:
        with ThreadPoolExecutor(max_workers=args.exec_workers) as pool:
            for row in pool.map(evaluate, tasks):
                run_payload = row.pop("run", None)
                artifact = row.pop("_artifact", None)
                if artifact is not None:
                    (rdir / "artifacts").mkdir(exist_ok=True)
                    (rdir / "artifacts" / f"{row['task_id']}.json").write_text(
                        json.dumps(artifact, indent=1, sort_keys=True, default=str) + "\n")
                rows.append(row)
                rfh.write(json.dumps(row, default=str) + "\n"); rfh.flush()
                payload = {"task_id": row["task_id"], "recipe_id": row["recipe_id"],
                           "status": row.get("status"), "error": row.get("error"),
                           "trigger_input": ((artifact or {}).get("input") or {}).get("trigger_input"),
                           "run": run_payload}
                runs_by_recipe.setdefault(str(row["recipe_id"]), []).append(payload)
                tfh.write(json.dumps(payload, default=str) + "\n"); tfh.flush()
                print(json.dumps({"round": k, "task_id": row["task_id"],
                                  "status": row.get("status"),
                                  "strict": row.get("strict_pass")}))
    summary = _score_summary(rows)
    (rdir / "leaderboard.json").write_text(json.dumps(
        {**summary["board"], "meta": {"model": args.model, "mode": mode, "round": k,
                                       "n_recipes": len(ids), "feedback": args.feedback}},
        indent=2, default=str) + "\n")
    print(f"ROUND {k} LEADERBOARD {args.model}: {json.dumps(summary['board'], default=str)}")
    return rows, runs_by_recipe


def revise_round(k: int, ids: list[str], plans: dict[str, dict[str, Any]],
                 runs_by_recipe: dict[str, list[dict[str, Any]]], contexts: dict[str, dict[str, Any]],
                 llm, args, run_dir: Path) -> dict[str, dict[str, Any]]:
    """Ask the model for a revision of every recipe's plan; returns the plans
    to execute in round k+1 (revised when valid, else unchanged)."""
    from task.llm_client import LLMError

    pdir = run_dir / "plans" / f"round_{k + 1}"
    pdir.mkdir(parents=True, exist_ok=True)
    next_plans: dict[str, dict[str, Any]] = {}
    requests: list[tuple[str, tuple[str, list[dict[str, str]]]]] = []
    for recipe_id in ids:
        cached = pdir / f"{recipe_id}.json"
        if args.resume and cached.is_file():
            next_plans[recipe_id] = json.loads(cached.read_text())
            continue
        context = contexts[recipe_id]
        current = plans[recipe_id]
        feedback_rows = runs_by_recipe.get(recipe_id, [])
        if args.feedback == "errors":
            for payload in feedback_rows:
                run = payload.get("run") or {}
                run["steps"] = [s for s in run.get("steps") or [] if "error" in s or "explicit_stop" in s]
        feedback = render_feedback(k, current, feedback_rows)
        messages = build_revision_messages(context, current, feedback)
        requests.append((recipe_id, (context["system"], messages)))

    # Generate in chunks: a single 650-prompt scheduler batch wedged the
    # Qwen3.8-27B engine for 13 h with no output (2026-08-29), and chunking
    # also gives progress visibility and finer resume granularity (each
    # chunk's plans are written as soon as it returns).
    chunk = max(1, args.llm_chunk)
    raws: list[Any] = []
    for start in range(0, len(requests), chunk):
        part = [req for _, req in requests[start:start + chunk]]
        if hasattr(llm, "complete_many_indexed"):
            got = llm.complete_many_indexed(part)
        else:
            def one(req):
                try:
                    return llm.complete(*req)
                except LLMError as exc:
                    return exc
            with ThreadPoolExecutor(max_workers=args.llm_workers) as pool:
                got = list(pool.map(one, part))
        raws.extend(got)
        _write_revisions(k, plans, contexts, requests[start:start + chunk], got, pdir, next_plans)
        print(json.dumps({"round": k + 1, "revision_progress": f"{min(start + chunk, len(requests))}/{len(requests)}"}))
    return next_plans


def _write_revisions(k: int, plans: dict[str, dict[str, Any]], contexts: dict[str, dict[str, Any]],
                     requests: list, raws: list, pdir: Path,
                     next_plans: dict[str, dict[str, Any]]) -> None:
    for (recipe_id, (_, messages)), raw in zip(requests, raws):
        current = plans[recipe_id]
        if isinstance(raw, Exception) or not isinstance(raw, str):
            revision = {"recipe_id": recipe_id, "round": k + 1, "status": "llm_error",
                        "error": str(raw), "plan": None, "plan_hash": None,
                        "prior_plan_hash": current.get("plan_hash")}
        else:
            revision = validate_revision(raw, contexts[recipe_id], round_index=k + 1, previous=current)
        revision["feedback_chars"] = len(messages[-1]["content"])
        revision["feedback"] = messages[-1]["content"]  # audit: exactly what the model saw
        if revision["status"] == "ok":
            executed = revision
        else:
            # fail-closed: keep executing the last valid plan (or stay
            # plan_error), but remember this attempt for the next feedback
            executed = dict(current)
            executed["last_attempt"] = {key: revision.get(key) for key in
                                        ("status", "error", "round", "raw_response")}
            executed["round"] = k + 1
            executed["revision_status"] = revision["status"]
            executed["revision_error"] = revision.get("error")
        executed["revision_record"] = {key: revision.get(key) for key in
                                       ("status", "error", "changed", "plan_hash",
                                        "prior_plan_hash", "json_syntax_repaired",
                                        "feedback_chars", "feedback", "raw_response")}
        (pdir / f"{recipe_id}.json").write_text(json.dumps(executed, indent=1, default=str) + "\n")
        next_plans[recipe_id] = executed
        print(json.dumps({"round": k + 1, "recipe_id": recipe_id,
                          "revision": revision["status"],
                          "changed": revision.get("changed"),
                          "error": (revision.get("error") or "")[:160]}))


def _feedback_for_invalid(artifact: dict[str, Any]) -> dict[str, Any]:
    """Round-0 invalid plans expose the validator error of the *last attempt*
    (the cached initial response) — same shape the revision loop uses."""
    if artifact.get("status") == "ok":
        return artifact
    attempt = artifact.get("last_attempt")
    if attempt and attempt.get("status") == "invalid_plan":
        out = dict(artifact)
        out["error"] = attempt.get("error")
        out["raw_response"] = attempt.get("raw_response") or artifact.get("raw_response")
        return out
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--state-namespace", required=True)
    parser.add_argument("--backend", default="simulated")
    parser.add_argument("--model", required=True)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=3, help="revision rounds K (round 0 = frozen initial plan)")
    parser.add_argument("--feedback", choices=("full", "errors"), default="full")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--exec-workers", type=int, default=int(os.environ.get("REPLAN_ITER_EXEC_WORKERS", "4")))
    parser.add_argument("--llm-workers", type=int, default=int(os.environ.get("VLLM_REACT_CONCURRENCY", "16")))
    parser.add_argument("--llm-chunk", type=int, default=int(os.environ.get("REPLAN_ITER_LLM_CHUNK", "32")),
                        help="revision requests per engine batch (progress + resume granularity)")
    parser.add_argument("--stub-llm", action="store_true",
                        help="offline plumbing check: the 'model' re-emits its previous plan unchanged")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_name):
        parser.error("bad --run-name")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.state_namespace):
        parser.error("bad --state-namespace")

    try:
        sys.stdout.reconfigure(line_buffering=True)  # Slurm logs: show progress promptly
    except (AttributeError, ValueError):
        pass
    eval_root = _configure(args.run_name, args.backend, args.state_namespace)
    import task.run_eval as re_

    ids = list(args.ids) if args.ids else _recipe_ids()
    if args.limit:
        ids = ids[: args.limit]
    run_dir = eval_root / args.model.replace("/", "__") / MODE
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.stub_llm:
        llm = _StubLLM(args.model)
    else:
        from task.llm_client import build_client
        llm = build_client(args.model)

    # round 0: frozen initial plans (cache hit when pre-seeded)
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
            except Exception as exc:  # same policy as full_eval: a planner failure is a plan_error row
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
    round0_tasks: dict[str, tuple[float, float]] = {}
    for k in range(args.rounds + 1):
        rows, runs_by_recipe = execute_round(k, ids, plans, llm, args, eval_root, run_dir)
        summary = _score_summary(rows)
        if k == 0:
            round0_tasks = summary["per_task"]
        flips = {"orch_up": 0, "orch_down": 0, "final_up": 0, "final_down": 0}
        for task_id, (orch, final) in summary["per_task"].items():
            o0, f0 = round0_tasks.get(task_id, (0.0, 0.0))
            flips["orch_up"] += orch > o0; flips["orch_down"] += orch < o0
            flips["final_up"] += final > f0; flips["final_down"] += final < f0
        entry = {"round": k, **summary["board"],
                 "valid_plans": sum(1 for a in plans.values() if a.get("status") == "ok"),
                 "revisions": {
                     "accepted": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("status") == "ok"),
                     "changed": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("changed") is True),
                     "invalid": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("status") == "invalid_plan"),
                     "llm_error": sum(1 for a in plans.values() if (a.get("revision_record") or {}).get("status") == "llm_error"),
                 } if k > 0 else None,
                 "vs_round0": flips}
        curve.append(entry)
        (run_dir / "curve.json").write_text(json.dumps(
            {"model": args.model, "mode": MODE, "rounds": args.rounds, "feedback": args.feedback,
             "n_recipes": len(ids), "curve": curve}, indent=2, default=str) + "\n")
        print(f"CURVE round {k}: orch={entry['orchestration_accuracy']} final={entry['final_accuracy']} "
              f"error_rate={entry['error_rate']} valid_plans={entry['valid_plans']} vs_round0={flips}")
        if k == args.rounds:
            break
        plans = revise_round(k, ids, {r: _feedback_for_invalid(a) for r, a in plans.items()},
                             runs_by_recipe, contexts, llm, args, run_dir)
    return 0


class _StubLLM:
    """Offline plumbing stub: returns the previous plan unchanged."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.calls = 0
        self.total_tokens = 0

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        for m in reversed(messages):
            if m["role"] == "assistant":
                return m["content"]
        return '{"plan": []}'


if __name__ == "__main__":
    raise SystemExit(main())

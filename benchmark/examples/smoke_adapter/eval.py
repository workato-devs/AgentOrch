"""Evaluation entry point. Interactive execution is delegated to an adapter.

The evaluator owns variants and ground truth. Adapters receive the public
input for exactly one of four modes and, in interactive modes, simulator
observations supplied by the benchmark runtime.
"""

from __future__ import annotations

import argparse
import importlib
import itertools
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator

from .cal_acc import aggregate, failed_score, score
from .datasets import (INTERACTIVE_MODES, MODES, PLANNING_MODES, iter_cases,
                       load_ground_truth, load_interactive_input,
                       load_model_input)
from .model_corpus import make_run_record


OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "outputs"
INTERACTIVE_FAILURE_STATUSES = {"action_budget_exhausted", "stopped_without_final_answer"}


def _trace(enabled: bool, event: str, **payload: Any) -> None:
    if enabled:
        print(f"\n[DEBUG] {event}")
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                rendered = json.dumps(value, indent=2, sort_keys=True, default=str)
            else:
                rendered = str(value)
            print(f"  {key}: {rendered}")


def _progress(enabled: bool, completed: int, record: dict[str, Any]) -> None:
    if enabled:
        print(json.dumps({
            "progress": completed,
            "recipe_id": record["recipe_id"],
            "variant_id": record["variant_id"],
            "status": record["status"],
            "scores": record.get("scores"),
        }, sort_keys=True), flush=True)


def _adapter(spec: str) -> Any:
    module_name, separator, attribute = spec.partition(":")
    if not separator:
        raise ValueError("adapter must use module:factory syntax")
    return getattr(importlib.import_module(module_name), attribute)()


def _schema_error_observation(tool: str, args: Any,
                              schema: dict[str, Any]) -> dict[str, Any] | None:
    """Return precise, public-schema-only feedback for one invalid action."""
    error = next(Draft202012Validator(schema).iter_errors(args), None)
    if error is None:
        return None
    path = list(error.absolute_path)
    location = "args" + "".join(
        f"[{item}]" if isinstance(item, int) else f".{item}" for item in path
    )
    expected: Any = None
    if error.validator == "type":
        expected = error.validator_value
        message = f"{location} must have JSON type {expected}; received {type(error.instance).__name__}."
        if expected in {"array", "object"} and isinstance(error.instance, str):
            message += f" Send a JSON {expected} directly, not JSON encoded as a string."
    elif error.validator == "required":
        missing = next(
            (name for name in error.validator_value if name not in error.instance),
            "required field",
        )
        path.append(missing)
        location += f".{missing}"
        expected = "required"
        message = f"{location} is required by the public tool schema."
    elif error.validator == "enum":
        expected = list(error.validator_value)
        message = f"{location} must be one of {expected!r}; received {error.instance!r}."
    elif error.validator == "additionalProperties":
        expected = "no additional properties"
        message = f"{location} contains a field not allowed by the public tool schema."
    else:
        expected = error.validator_value
        message = f"{location} violates public schema rule {error.validator}: {error.message}"
    return {
        "tool": tool,
        "error": "SCHEMA_VALIDATION_ERROR",
        "argument_path": path,
        "expected": expected,
        "received": error.instance,
        "message": message,
    }


def evaluate_plans(adapter: Any, *, mode: str, model_id: str,
                   limit: int | None = None, trace: bool = False,
                   progress: bool = False,
                   recipe_id: str | None = None) -> list[dict[str, Any]]:
    if mode not in PLANNING_MODES:
        raise ValueError(f"planning mode must be one of {sorted(PLANNING_MODES)}")
    rows: list[dict[str, Any]] = []
    cases = iter_cases(mode=mode, recipe_id=recipe_id)
    plan_cache: dict[str, Any] = {}
    model_errors: dict[str, str] = {}
    for case in itertools.islice(cases, limit):
        task = load_model_input(case.recipe_id, mode)
        _trace(trace, "input.mode_to_model", recipe_id=case.recipe_id,
               variant_id=case.variant_id, mode=mode, model_input=task,
               private_variant="not loaded or exposed in planning mode")
        record = make_run_record(recipe_id=case.recipe_id, variant_id=case.variant_id,
                                 mode=mode, model_id=model_id,
                                 model_input=task)
        if case.recipe_id not in plan_cache:
            try:
                plan_cache[case.recipe_id] = (
                    adapter.propose_incremental_plan(task)
                    if mode == "local" and hasattr(adapter, "propose_incremental_plan")
                    else adapter.propose_plan(task)
                )
            except Exception as exc:
                plan_cache[case.recipe_id] = None
                model_errors[case.recipe_id] = f"{type(exc).__name__}: {exc}"
        record["plan"] = plan_cache[case.recipe_id]
        _trace(trace, "model.plan_to_evaluator", recipe_id=case.recipe_id,
               variant_id=case.variant_id, plan=record["plan"])
        from verification.smoke import build_case
        if case.recipe_id in model_errors:
            record.update({
                "status": "model_error",
                "error": model_errors[case.recipe_id],
                "final_state": build_case(case.recipe_id, case.variant_id).final_state(),
                "scores": failed_score(),
            })
            _trace(trace, "model_error_to_scorer", recipe_id=case.recipe_id,
                   variant_id=case.variant_id, error=record["error"],
                   scores=record["scores"])
            rows.append(record)
            _progress(progress, len(rows), record)
            continue
        verification = build_case(case.recipe_id, case.variant_id).execute_plan(record["plan"])
        record.update(verification)
        _trace(trace, "plan_verifier_to_evaluator", recipe_id=case.recipe_id,
               variant_id=case.variant_id, verification=verification)
        record["scores"] = score(record, load_ground_truth(case.recipe_id, case.variant_id))
        _trace(trace, "groundtruth_to_scorer", recipe_id=case.recipe_id,
               variant_id=case.variant_id, groundtruth_path=str(
                   Path(__file__).resolve().parents[2] / "groundtruth" / "recipes"
                   / case.recipe_id / f"variant_{int(case.variant_id):02d}.json"),
               scores=record["scores"])
        rows.append(record)
        _progress(progress, len(rows), record)
    return rows


def evaluate_interactive(adapter: Any, *, mode: str, model_id: str,
                         limit: int | None = None, trace: bool = False,
                         progress: bool = False,
                         recipe_id: str | None = None) -> list[dict[str, Any]]:
    """Run a ReAct/replan adapter against a fresh private deterministic simulator."""
    if mode not in INTERACTIVE_MODES:
        raise ValueError(f"interactive mode must be one of {sorted(INTERACTIVE_MODES)}")
    from verification.smoke import build_case
    rows: list[dict[str, Any]] = []
    cases = iter_cases(mode=mode, recipe_id=recipe_id)
    for case in itertools.islice(cases, limit):
        model_task = load_interactive_input(case.recipe_id, case.variant_id, mode)
        simulator = build_case(case.recipe_id, case.variant_id)
        tool_specs = simulator.tool_specs
        schemas = {item["name"]: item["input_schema"] for item in tool_specs}
        allowed = set(schemas)
        _trace(trace, "input.mode_and_simulator_tools_to_model", recipe_id=case.recipe_id,
               variant_id=case.variant_id, mode=mode, model_input=model_task,
               private_seed_path=str(
                   Path(__file__).resolve().parents[2] / "verification" / "seeds"
                   / case.recipe_id / f"variant_{int(case.variant_id):02d}.json"),
               private_seed_exposed_to_model=False)
        record = make_run_record(recipe_id=case.recipe_id, variant_id=case.variant_id,
                                 mode=mode, model_id=model_id,
                                 model_input=model_task)
        adapter.start(model_task, mode=mode, tool_specs=tool_specs)
        observation: dict[str, Any] | None = None
        budget = 8
        for _ in range(budget):
            decision = adapter.act(observation)
            _trace(trace, "model_decision_to_simulator", recipe_id=case.recipe_id,
                   variant_id=case.variant_id, decision=decision)
            if not isinstance(decision, dict):
                observation = {"error": "adapter response must be a JSON object"}
                continue
            if "plan" in decision:
                record["plan"] = decision["plan"]
            if "final_answer" in decision:
                record["final_answer"] = decision["final_answer"]
                record["status"] = "ok"
                break
            tool = decision.get("tool")
            args = decision.get("args")
            if tool in {"finish", "stop"} and isinstance(args, dict):
                record["trajectory"].append({"tool": tool, "args": args})
                if tool == "stop":
                    record["final_answer"] = {
                        "stop_reason": args.get("stop_reason"),
                        "stop_with_error": args.get("stop_with_error"),
                    }
                record["status"] = "ok"
                break
            if tool not in allowed or not isinstance(args, dict):
                observation = {"error": "tool must be model-visible and args must be an object"}
                record["trajectory"].append({"tool": tool, "args": args, **observation})
                continue
            schema_error = _schema_error_observation(str(tool), args, schemas[str(tool)])
            if schema_error is not None:
                observation = schema_error
                record["trajectory"].append({"tool": tool, "args": args,
                                             "error": schema_error})
                _trace(trace, "schema_feedback_to_model", recipe_id=case.recipe_id,
                       variant_id=case.variant_id, observation=observation)
                continue
            try:
                result = simulator.call(str(tool), args)
                observation = {"tool": tool, "result": result}
                _trace(trace, "simulator_observation_to_model", recipe_id=case.recipe_id,
                       variant_id=case.variant_id, observation=observation)
                record["trajectory"].append({"tool": tool, "args": args, "result": result})
            except RuntimeError as exc:
                observation = {"tool": tool, "error": str(exc)}
                record["trajectory"].append({"tool": tool, "args": args, "error": str(exc)})
            if simulator.terminal:
                record["final_answer"] = simulator.terminal_result
                record["status"] = "ok"
                break
        else:
            record["status"] = "action_budget_exhausted"
        if record["status"] == "started":
            record["status"] = "stopped_without_final_answer"
        record["final_state"] = simulator.final_state()
        record["scores"] = (
            failed_score()
            if record["status"] in INTERACTIVE_FAILURE_STATUSES
            else score(record, load_ground_truth(case.recipe_id, case.variant_id))
        )
        _trace(trace, "groundtruth_to_scorer", recipe_id=case.recipe_id,
               variant_id=case.variant_id, groundtruth_path=str(
                   Path(__file__).resolve().parents[2] / "groundtruth" / "recipes"
                   / case.recipe_id / f"variant_{int(case.variant_id):02d}.json"),
               scores=record["scores"])
        rows.append(record)
        _progress(progress, len(rows), record)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=sorted(MODES))
    parser.add_argument("--adapter", required=True, help="Python module:factory")
    parser.add_argument("--model-id", required=True)
    parser.add_argument(
        "--recipe-id",
        help="evaluate one recipe (useful with the bundled smoke simulator)",
    )
    parser.add_argument("--limit", type=int,
                        help="evaluate only the first N cases (use 1 for an API smoke test)")
    parser.add_argument("--debug", "--trace-data-flow", dest="debug", action="store_true",
                        help="print human-readable per-case handoffs; never prints HF tokens")
    parser.add_argument("--progress", action="store_true",
                        help="print one compact JSON progress line after each scored case")
    parser.add_argument(
        "--run-name", default="test",
        help="experiment directory below benchmark/outputs (default: test)",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_name):
        parser.error("--run-name may contain only letters, digits, dot, underscore, and hyphen")
    adapter = _adapter(args.adapter)
    rows = (evaluate_plans(adapter, mode=args.mode, model_id=args.model_id,
                           limit=args.limit, trace=args.debug, progress=args.progress,
                           recipe_id=args.recipe_id)
            if args.mode in PLANNING_MODES
            else evaluate_interactive(adapter, mode=args.mode,
                                      model_id=args.model_id, limit=args.limit,
                                      trace=args.debug, progress=args.progress,
                                      recipe_id=args.recipe_id))
    model_slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", args.model_id).strip("._") or "model"
    output_path = OUTPUT_ROOT / args.run_name / model_slug / f"{args.mode}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    _trace(args.debug, "scored_record_to_output", output_path=str(output_path),
           records=len(rows))
    print(json.dumps({"output": str(output_path),
                      "summary": aggregate([row["scores"] for row in rows])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

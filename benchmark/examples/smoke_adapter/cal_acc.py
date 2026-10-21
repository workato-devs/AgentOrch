"""Public scorer for trace quality, orchestration, side effects, and outcome.

Side-effect, terminal-output, and final accuracy are NOT reimplemented
here: they delegate to ``metrics.outcome.evaluate_outcome`` — the same
vendored module the canonical ``evaluation.full_eval`` pipeline scores with
— applied to the ground-truth files' exported canonical gold
(``outcome_gold_calls``, the projected ``final_snapshot``, and
``structural_return``). Row-level parity with the stored canonical verdicts
is verified by ``reproduction/offline/verify_calacc_parity.py`` against a frozen
artifact manifest: zero disagreements on side-effect, normalized-terminal,
and final across every archived canonical row (see the dated parity-audit
entry in ``doc/change.md`` for the frozen row count; two ReAct lanes were
still appending artifacts at audit time, so the archive itself is not a
stable number).

Execution-trace components are computed from the published per-variant
``tool_expectations`` and remain a documented simplification of the
canonical evaluator's runtime trace adjudication, so the trace half of
``orchestration_accuracy`` can differ from the released leaderboards.
Released numbers come from ``evaluation.full_eval``.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import os
from pathlib import Path
import sys
from typing import Any


CONTROL_TOOLS = {"finish", "submit_answer", "stop"}
TERMINAL_TOOLS = {"workato_api_platform.return_response"}


def _outcome_module() -> Any:
    """Import the canonical outcome evaluator from the vendored backend."""

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    # The canonical task module resolves its dataset routing from these
    # variables at import time; default them to the published bundle the
    # same way evaluation/full_eval.py does (an embedding harness that has
    # already routed them keeps its own values).
    verification = root / "verification"
    support = verification / "evaluation_support"
    for key, value in {
        "BENCHMARK_GROUND_TRUTH_DIR": verification / "groundtruth/reference_outputs",
        "BENCHMARK_TASK_DESCRIPTION_PACKAGE_DIR": root / "input/recipes",
        "BENCHMARK_TASK_DESCRIPTION_WORKFLOW_DIR": support / "canonical_ir",
        "BENCHMARK_TASK_DESCRIPTION_GROUNDTRUTH_DIR": support / "workflow_groundtruth",
        "BENCHMARK_TASK_DESCRIPTION_CRITIC_DIR": support / "critic",
        "BENCHMARK_SCORING_CONTRACT_REGISTRY": support / "scoring_contract_registry.json",
    }.items():
        os.environ.setdefault(key, str(value))
    from verification.backend import activate

    activate("simulated")
    from metrics import outcome

    return outcome


def _outcome_call_projection(
    recipe_id: str, calls: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply run_eval's semantic outcome-call canonicalization.

    The override argument is the empty string: published scoring runs on the
    simulated backend with no live Slack isolation, so only the per-recipe
    canonicalizations apply — identically to both gold and agent calls.
    """

    from task.run_eval import _task_description_outcome_calls

    return _task_description_outcome_calls(recipe_id, calls, "")


def failed_score() -> dict[str, Any]:
    """Return the documented all-zero score for a failed benchmark row."""
    return {
        "execution_trace_accuracy": 0.0,
        "execution_trace_components": {
            "tool_selection": False,
            "tool_order": False,
            "tool_execution": False,
            "required_semantic_arguments": False,
            "control_path": False,
        },
        "side_effect_accuracy": 0.0,
        "orchestration_accuracy": 0.0,
        "terminal_output_accuracy": 0.0,
        "final_accuracy": 0.0,
    }


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _contains(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _calls(record: dict[str, Any]) -> list[dict[str, Any]]:
    trajectory = record.get("trajectory")
    if isinstance(trajectory, list) and trajectory:
        return [
            item for item in trajectory
            if isinstance(item, dict) and isinstance(item.get("tool"), str)
            and item["tool"] not in CONTROL_TOOLS
        ]
    plan = record.get("plan")
    if isinstance(plan, list):
        return [item for item in plan if isinstance(item, dict) and "tool" in item]
    if isinstance(plan, dict):
        nodes = plan.get("plan") if isinstance(plan.get("plan"), list) else plan.get("steps")
        if isinstance(nodes, list):
            return [item for item in nodes if isinstance(item, dict) and "tool" in item]
    return []


def _expected_error_messages(ground_truth: dict[str, Any]) -> set[str]:
    contract = ground_truth.get("output_contract") or {}
    return {
        str(value) for value in contract.get("constants") or []
        if isinstance(value, str) and value
    }


def _outcome_calls(
    outcome: Any, recipe_id: str, record: dict[str, Any]
) -> list[dict[str, Any]]:
    """Executed calls in the canonical outcome projection.

    Mirrors run_eval: protocol pseudo-tools and raw authoring-layer returns
    are structural; the per-recipe outcome canonicalization applies; a
    symbolic plan-level ``return`` stop and any explicit structural return
    call each contribute the uniform synthetic return call so Global/Local
    plans and ReAct traces expose the same semantic terminal output.
    """

    trajectory = record.get("trajectory")
    trajectory = trajectory if isinstance(trajectory, list) else []
    calls = [
        deepcopy(item)
        for item in trajectory
        if isinstance(item, dict) and isinstance(item.get("tool"), str)
        and item["tool"] not in CONTROL_TOOLS
        and item["tool"] not in outcome.STRUCTURAL_RETURN_TOOLS
    ]
    calls = _outcome_call_projection(recipe_id, calls)
    if record.get("stop_reason") == "return":
        calls.append(outcome.synthetic_return_call(record.get("final_answer")))
    for item in trajectory:
        if not isinstance(item, dict):
            continue
        if str(item.get("tool") or "") not in outcome.STRUCTURAL_RETURN_TOOLS:
            continue
        args = item.get("args") or {}
        if isinstance(args, dict) and "result" in args:
            calls.append(outcome.synthetic_return_call(args["result"]))
    return calls


def _gold_outcome_calls(outcome: Any, ground_truth: dict[str, Any]) -> list[dict[str, Any]]:
    """Gold calls exactly as the canonical evaluator hands them to
    ``evaluate_outcome``: the exported ``outcome_gold_calls`` projection plus
    the synthetic terminal return for structural-return recipes. Older
    ground-truth files without those fields fall back to the reference trace."""

    exported = ground_truth.get("outcome_gold_calls")
    if isinstance(exported, list):
        calls = deepcopy(exported)
    else:
        calls = [
            deepcopy(item)
            for item in ground_truth.get("reference_tool_calls") or []
            if isinstance(item, dict) and isinstance(item.get("tool"), str)
            and item["tool"] not in outcome.STRUCTURAL_RETURN_TOOLS
        ]
    structural = ground_truth.get("structural_return") or {}
    if structural.get("present") is True:
        calls.append(outcome.synthetic_return_call(structural.get("value")))
    return calls


def score(record: dict[str, Any], ground_truth: dict[str, Any]) -> dict[str, Any]:
    """Score one executed recipe-variant row using the published metrics."""
    expected = [item for item in ground_truth.get("tool_expectations") or [] if isinstance(item, dict)]
    observed_all = _calls(record)
    expected_errors = _expected_error_messages(ground_truth)
    expected_failure_calls = [
        call for call in observed_all
        if isinstance(call.get("error"), str) and call["error"] in expected_errors
    ]
    observed = [call for call in observed_all if call not in expected_failure_calls]

    expected_tools = [str(item.get("tool") or "") for item in expected]
    observed_tools = [str(item.get("tool") or "") for item in observed]
    selection = Counter(observed_tools) == Counter(expected_tools)
    order = observed_tools == expected_tools
    execution = len(observed) == len(expected) and all(
        "error" not in call and isinstance(call.get("result"), dict)
        for call in observed
    )
    execution = execution and all(call.get("error") in expected_errors for call in expected_failure_calls)
    arguments = len(observed) == len(expected) and all(
        call.get("tool") == requirement.get("tool")
        and _contains(call.get("args") or {}, requirement.get("args_contains") or {})
        for call, requirement in zip(observed, expected)
    )
    structural_return = ground_truth.get("structural_return") or {}
    terminal_required = (
        ground_truth.get("terminal_result") is not None
        or structural_return.get("present") is True
    )
    terminal_reached = record.get("final_answer") is not None
    terminal_calls = [
        call for call in observed_all if call.get("tool") in TERMINAL_TOOLS
    ]
    control_path = (
        record.get("status") in {"ok", "stopped_without_terminal"}
        and terminal_reached == terminal_required
        and (terminal_required or not terminal_calls)
        and not any(
            isinstance(call.get("error"), str) and call["error"] not in expected_errors
            for call in observed_all
        )
    )
    components = {
        "tool_selection": selection,
        "tool_order": order,
        "tool_execution": execution,
        "required_semantic_arguments": arguments,
        "control_path": control_path,
    }
    execution_trace = round(sum(int(value) for value in components.values()) * 0.2, 4)

    # Side effect, terminal output, and final accuracy come from the
    # canonical evaluator, applied to the published ground truth: the
    # per-variant expected final snapshot, the reference trace, and the
    # declared terminal contract (a verbatim copy of the recipe's public
    # output schema).
    outcome_module = _outcome_module()
    boolean_paths = outcome_module.public_output_boolean_argument_paths(
        ground_truth.get("terminal_contract") or {}
    )
    outcome = outcome_module.evaluate_outcome(
        _gold_outcome_calls(outcome_module, ground_truth),
        ground_truth.get("final_snapshot") or {},
        _outcome_calls(
            outcome_module, str(ground_truth.get("recipe_id") or ""), record
        ),
        record.get("final_state") or {},
        terminal_boolean_paths=(
            {"workato_api_platform.return_response": boolean_paths}
            if boolean_paths
            else None
        ),
    )
    # Identical to run_eval's side-effect verdict: every canonical outcome
    # check except the terminal comparison, plus the transient-event trace.
    side_effect_checks = [
        check
        for check in outcome["checks"]
        if check.get("name") != "terminal_outputs_match"
    ]
    side_effect_pass = all(bool(check.get("ok")) for check in side_effect_checks)
    if outcome["transient_event_checked"]:
        side_effect_pass = side_effect_pass and bool(outcome["transient_event_pass"])
    side_effect = float(side_effect_pass)
    orchestration = round(
        0.5 * execution_trace + 0.5 * side_effect,
        4,
    )
    terminal_output = float(bool(outcome["terminal_normalized_pass"]))
    final = float(side_effect == 1.0 and terminal_output == 1.0)
    return {
        "execution_trace_accuracy": execution_trace,
        "execution_trace_components": components,
        "side_effect_accuracy": side_effect,
        "orchestration_accuracy": orchestration,
        "terminal_output_accuracy": terminal_output,
        "final_accuracy": final,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    return {
        "n": n,
        **{
            key: round(sum(float(row.get(key) or 0.0) for row in rows) / n, 4)
            if n else None
            for key in (
                "orchestration_accuracy",
                "side_effect_accuracy",
                "final_accuracy",
                "execution_trace_accuracy",
                "terminal_output_accuracy",
            )
        },
    }

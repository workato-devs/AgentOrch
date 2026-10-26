"""Leaderboard aggregation over eval result rows.

Canonical trace/orchestration correctness is exact after representation-only
normalization. Semantic outcome and argument equivalence are diagnostics and
cannot promote a different recipe trace to primary correctness.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any


_STRICT_COMPONENTS = (
    "tool_selection",
    "tool_order",
    "tool_execution_success",
    "tool_argument_required",
    "tool_argument_required_raw",
    "tool_argument_full",
    "tool_argument_full_raw",
    "condition_path",
    "tool_sequence",
    "tool_call",
    "tool_argument",
    "tool_argument_semantic",
    "result_count",
    "response",
    "write_state",
    "other",
)


def bootstrap_ci(rows: list[dict[str, Any]], key: str,
                 n_resamples: int = 2000, seed: int = 0) -> list[float]:
    """95% CI on the per-task pass rate via cluster bootstrap: tasks are the
    resampling unit so repeated runs (--runs k) of the same task stay
    together. Deterministic (fixed seed) so leaderboards are reproducible."""
    by_task: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        by_task[str(row.get("task_id"))].append(1 if row.get(key) else 0)
    task_means = [sum(v) / len(v) for v in by_task.values()]
    if not task_means:
        return [0.0, 0.0]
    rng = random.Random(seed)
    samples = []
    for _ in range(n_resamples):
        draw = [task_means[rng.randrange(len(task_means))] for _ in task_means]
        samples.append(sum(draw) / len(draw))
    samples.sort()
    lo = samples[int(0.025 * n_resamples)]
    hi = samples[min(int(0.975 * n_resamples), n_resamples - 1)]
    return [round(lo, 4), round(hi, 4)]


# The five equally weighted binary checks behind execution-trace accuracy
# (doc/metric.md section 1): tool selection, order, execution, required
# semantic arguments, and control path.
_PRIMARY_TRACE_COMPONENTS = (
    "tool_selection",
    "tool_order",
    "tool_execution_success",
    "tool_argument_required",
    "condition_path",
)


def primary_metrics_for_row(row: dict[str, Any]) -> dict[str, float]:
    """The doc/metric.md primary metrics for one scored result row.

    ``execution_trace_accuracy`` weights the five binary components equally;
    a component that is not applicable to the task (``*_checked`` false)
    passes vacuously.
    ``side_effect_accuracy`` is the row's binary side-effect verdict,
    ``orchestration_accuracy`` weights trace and side effect equally, and
    ``final_accuracy`` requires the side effect AND the normalized terminal
    output. Callers score failed rows as zero on every metric.
    """
    components = []
    for name in _PRIMARY_TRACE_COMPONENTS:
        if row.get(f"{name}_checked") is True:
            components.append(1.0 if row.get(f"{name}_pass") is True else 0.0)
        else:
            components.append(1.0)
    execution_trace = round(0.2 * sum(components), 4)
    side_effect = 1.0 if row.get("side_effect_pass") else 0.0
    terminal = 1.0 if row.get("terminal_normalized_pass") else 0.0
    return {
        "execution_trace_accuracy": execution_trace,
        "side_effect_accuracy": side_effect,
        "orchestration_accuracy": round(
            0.5 * execution_trace + 0.5 * side_effect, 4
        ),
        "terminal_output_accuracy": terminal,
        "final_accuracy": float(side_effect == 1.0 and terminal == 1.0),
    }


def bootstrap_ci_mean(values_by_task: dict[str, list[float]],
                      n_resamples: int = 2000, seed: int = 0) -> list[float]:
    """95% CI on a graded per-task mean via the same cluster bootstrap as
    ``bootstrap_ci``, for metrics that take values in [0, 1] rather than
    binary passes."""
    task_means = [sum(v) / len(v) for v in values_by_task.values() if v]
    if not task_means:
        return [0.0, 0.0]
    rng = random.Random(seed)
    samples = []
    for _ in range(n_resamples):
        draw = [task_means[rng.randrange(len(task_means))] for _ in task_means]
        samples.append(sum(draw) / len(draw))
    samples.sort()
    lo = samples[int(0.025 * n_resamples)]
    hi = samples[min(int(0.975 * n_resamples), n_resamples - 1)]
    return [round(lo, 4), round(hi, 4)]


def _strict_component_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate each strict dimension over cases where it is applicable."""

    summary: dict[str, Any] = {}
    for component in _STRICT_COMPONENTS:
        checked_key = f"{component}_checked"
        pass_key = f"{component}_pass"
        checked = [row for row in rows if row.get(checked_key) is True]
        passed = sum(1 for row in checked if row.get(pass_key) is True)
        check_count = sum(
            int(row.get(f"{component}_check_count") or 0) for row in checked
        )
        passed_check_count = sum(
            int(row.get(f"{component}_passed_check_count") or 0)
            for row in checked
        )
        summary[f"{component}_checked_n"] = len(checked)
        summary[f"{component}_pass"] = passed
        summary[f"{component}_rate"] = round(
            passed / len(checked), 4
        ) if checked else None
        summary[f"{component}_check_n"] = check_count
        summary[f"{component}_check_pass"] = passed_check_count
        summary[f"{component}_check_rate"] = round(
            passed_check_count / check_count, 4
        ) if check_count else None
    return summary


def _plan_fidelity_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate frozen-plan quality once per recipe, never once per variant."""

    by_recipe: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("plan_fidelity_applicable") is not True:
            continue
        recipe_id = str(row.get("recipe_id") or "")
        if recipe_id:
            by_recipe.setdefault(recipe_id, row)
    plans = list(by_recipe.values())
    exact = [row for row in plans if row.get("plan_fidelity_pass") is not None]
    fields = (
        "plan_fidelity_macro_f1",
        "plan_tool_selection_f1",
        "plan_partial_order_f1",
        "plan_condition_control_flow_f1",
        "plan_symbolic_arguments_f1",
        "plan_coverage_recall",
    )
    summary: dict[str, Any] = {
        "plan_fidelity_recipe_n": len(plans),
        "plan_fidelity_exact_checked_n": len(exact),
        "plan_fidelity_exact_pass": sum(
            row.get("plan_fidelity_pass") is True for row in exact
        ),
        "plan_fidelity_exact_rate": (
            round(
                sum(row.get("plan_fidelity_pass") is True for row in exact)
                / len(exact),
                4,
            )
            if exact
            else None
        ),
    }
    for field in fields:
        summary[f"mean_{field}"] = (
            round(sum(float(row.get(field) or 0.0) for row in plans) / len(plans), 4)
            if plans
            else None
        )
    return summary


def leaderboard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Success rates are computed over ALL attempted rows: a task whose run
    errored (llm_error/infra_error/crash) did not pass, so it stays in the
    denominator (benmark_rules.md reproducibility — failures must not be
    silently dropped). Descriptive per-run means (actions, efficiency, stop
    reasons) are over scored rows only."""
    ok = [r for r in rows if r.get("status") == "ok"]
    excluded = Counter(r.get("status") or "unknown" for r in rows if r.get("status") != "ok")
    n = len(rows) or 1
    n_ok = len(ok) or 1
    outcome = sum(1 for r in ok if r.get("outcome_pass"))
    semantic_outcome = sum(1 for r in ok if r.get("outcome_semantic_pass"))
    strict = sum(1 for r in ok if r.get("strict_pass"))
    side_effect = sum(1 for r in ok if r.get("side_effect_pass"))
    # doc/metric.md primary metrics. Failed rows stay in the denominator at
    # zero, so sums run over scored rows while means divide by n.
    primary = [primary_metrics_for_row(r) for r in ok]
    primary_by_task: dict[str, dict[str, list[float]]] = {
        key: defaultdict(list)
        for key in ("orchestration_accuracy", "final_accuracy")
    }
    for r in rows:
        task = str(r.get("task_id"))
        scored = primary_metrics_for_row(r) if r.get("status") == "ok" else None
        for key in primary_by_task:
            primary_by_task[key][task].append(scored[key] if scored else 0.0)

    def _primary_mean(key: str) -> float:
        return round(sum(p[key] for p in primary) / n, 4)
    transient_event_rows = [
        r for r in ok if r.get("transient_event_checked") is True
    ]
    transient_event_pass = sum(
        1 for r in transient_event_rows if r.get("transient_event_pass") is True
    )
    outcome_and_strict = sum(
        1 for r in ok if r.get("outcome_pass") and r.get("strict_pass")
    )
    plan = sum(1 for r in ok if r.get("plan_struct"))
    plan_rows = [r for r in ok if r.get("plan_struct")]
    eff = sum(float(r.get("action_efficiency") or 0) for r in ok) / n_ok
    eff_on_plan = (sum(float(r.get("action_efficiency") or 0) for r in plan_rows)
                   / len(plan_rows)) if plan_rows else 0.0
    runtime_diagnostic_rows = [
        row for row in ok if row.get("tool_selection_exact_pass") is not None
    ]
    dependency_dag_rows = [
        row
        for row in runtime_diagnostic_rows
        if row.get("tool_order_dependency_mode") == "dependency_dag"
    ]
    diagnostic_n = len(runtime_diagnostic_rows)
    return {
        "n": len(rows),
        "n_scored": len(ok),
        "error_rate": round((len(rows) - len(ok)) / n, 4),
        "outcome_pass": outcome, "outcome_rate": round(outcome / n, 4),
        "outcome_semantic_pass": semantic_outcome,
        "outcome_semantic_rate": round(semantic_outcome / n, 4),
        # Primary metrics (doc/metric.md): orchestration, side effect, final,
        # plus the two published diagnostics. These are the reported numbers;
        # everything else in this leaderboard is a diagnostic breakdown.
        "orchestration_accuracy": _primary_mean("orchestration_accuracy"),
        "orchestration_accuracy_ci95": bootstrap_ci_mean(
            primary_by_task["orchestration_accuracy"]
        ),
        "side_effect_accuracy": _primary_mean("side_effect_accuracy"),
        "final_accuracy": _primary_mean("final_accuracy"),
        "final_accuracy_ci95": bootstrap_ci_mean(
            primary_by_task["final_accuracy"]
        ),
        "execution_trace_accuracy": _primary_mean("execution_trace_accuracy"),
        "terminal_output_accuracy": _primary_mean("terminal_output_accuracy"),
        "side_effect_pass": side_effect,
        "side_effect_rate": round(side_effect / n, 4),
        "replan_review_count": sum(
            int(row.get("replan_review_count") or 0) for row in ok
        ),
        "accepted_replan_count": sum(
            int(row.get("replan_count") or 0) for row in ok
        ),
        **{
            key: sum(int(row.get(key) or 0) for row in ok)
            for key in (
                "replan_rejected_count",
                "replan_repair_offered_count",
                "replan_repair_accepted_count",
                "replan_patch_accepted_count",
                "replan_resolver_review_count",
                "replan_resolver_accepted_count",
            )
        },
        "transient_event_checked_n": len(transient_event_rows),
        "transient_event_pass": transient_event_pass,
        "transient_event_rate": round(
            transient_event_pass / len(transient_event_rows), 4
        ) if transient_event_rows else None,
        "outcome_rate_ci95": bootstrap_ci(rows, "outcome_pass"),
        "strict_pass": strict, "strict_rate": round(strict / n, 4),
        "strict_rate_ci95": bootstrap_ci(rows, "strict_pass"),
        "outcome_and_strict_pass": outcome_and_strict,
        "outcome_and_strict_rate": round(outcome_and_strict / n, 4),
        **_strict_component_summary(ok),
        # Exact selection/order are primary. The fields below retain explicit
        # diagnostics for historical relaxed policies and efficiency analysis.
        "tool_selection_exact_rate": (
            round(
                sum(
                    row.get("tool_selection_exact_pass") is True
                    for row in runtime_diagnostic_rows
                )
                / diagnostic_n,
                4,
            )
            if diagnostic_n
            else None
        ),
        "tool_order_exact_rate": (
            round(
                sum(
                    row.get("tool_order_exact_pass") is True
                    for row in runtime_diagnostic_rows
                )
                / diagnostic_n,
                4,
            )
            if diagnostic_n
            else None
        ),
        "tool_trace_exact_rate": (
            round(
                sum(
                    row.get("tool_trace_exact_pass") is True
                    for row in runtime_diagnostic_rows
                )
                / diagnostic_n,
                4,
            )
            if diagnostic_n
            else None
        ),
        "dependency_dag_order_checked_n": len(dependency_dag_rows),
        "multiple_topological_orders_n": sum(
            row.get("tool_order_multiple_topological_orders") is True
            for row in dependency_dag_rows
        ),
        "extra_read_call_count": sum(
            int(row.get("tool_selection_extra_read_count") or 0)
            for row in runtime_diagnostic_rows
        ),
        "extra_write_call_count": sum(
            int(row.get("tool_selection_extra_write_count") or 0)
            for row in runtime_diagnostic_rows
        ),
        "episodes_with_extra_reads": sum(
            int(row.get("tool_selection_extra_read_count") or 0) > 0
            for row in runtime_diagnostic_rows
        ),
        "episodes_with_extra_writes": sum(
            int(row.get("tool_selection_extra_write_count") or 0) > 0
            for row in runtime_diagnostic_rows
        ),
        "mean_orchestration_action_count_ratio": (
            round(
                sum(
                    float(row.get("orchestration_action_count_ratio") or 0.0)
                    for row in runtime_diagnostic_rows
                )
                / diagnostic_n,
                4,
            )
            if diagnostic_n
            else None
        ),
        "orchestration_efficiency_within_2x_rate": (
            round(
                sum(
                    row.get("orchestration_efficiency_within_2x") is True
                    for row in runtime_diagnostic_rows
                )
                / diagnostic_n,
                4,
            )
            if diagnostic_n
            else None
        ),
        **_plan_fidelity_summary(ok),
        "plan_struct_pass": plan, "plan_struct_rate": round(plan / n, 4),
        # graded outcome: mean per-task state-accuracy F1 (near-misses show up
        # here even when binary outcome_pass is 0; errored rows contribute 0)
        "mean_state_accuracy": round(
            sum(float(r.get("state_accuracy") or 0.0) for r in ok) / n, 4),
        # planning-vs-derivation decomposition: execution quality GIVEN the
        # right plan shape, and how often a right-shaped plan still fails.
        "outcome_rate_given_plan_struct": round(
            sum(1 for r in plan_rows if r.get("outcome_pass")) / max(len(plan_rows), 1), 4),
        "plan_struct_without_outcome": sum(
            1 for r in plan_rows if not r.get("outcome_pass")),
        "value_checked_n": sum(1 for r in ok if r.get("value_checked")),
        "mean_action_efficiency": round(eff, 3),
        "mean_efficiency_on_plan_correct": round(eff_on_plan, 3),
        "mean_redundant_actions": round(
            sum(int(r.get("redundant_actions") or 0) for r in ok) / n_ok, 2),
        # Terminal exactness is primary; normalized equivalence diagnoses the
        # subset of failures attributable to alternate representations.
        "terminal_normalized_rate": round(
            sum(1 for r in ok if r.get("terminal_normalized_pass")) / n, 4),
        "terminal_exact_rate": round(
            sum(1 for r in ok if r.get("terminal_exact_pass")) / n, 4),
        "mean_terminal_similarity": round(
            sum(float(r.get("terminal_similarity_score") or 0.0) for r in ok) / n, 4),
        # Budget sensitivity: distinguishes "cannot solve" from "budget too
        # tight". Enforcement runs at 2.0x; pass@k derives from actions_used.
        "outcome_rate_at_1x": round(
            sum(1 for r in ok if r.get("outcome_pass_at_1x")) / n, 4),
        "outcome_rate_at_1_5x": round(
            sum(1 for r in ok if r.get("outcome_pass_at_1_5x")) / n, 4),
        "outcome_rate_at_2x": round(
            sum(1 for r in ok if r.get("outcome_pass_at_2x")) / n, 4),
        "budget_exhaustion_rate": round(
            sum(1 for r in ok if str(r.get("stop_reason")) == "budget") / n_ok, 4),
        "rescued_by_extra_budget_rate": round(
            sum(1 for r in ok if r.get("outcome_pass") and not r.get("outcome_pass_at_1x")) / n, 4),
        "mean_model_reads": round(
            sum(int(r.get("model_reads") or 0) for r in ok) / n_ok, 2),
        "mean_model_mutations": round(
            sum(int(r.get("model_mutations") or 0) for r in ok) / n_ok, 2),
        # Broad-catalog diagnostics complement the exact canonical trace score.
        "mean_tools_exposed": round(
            sum(int(r.get("tools_exposed_count") or 0) for r in ok) / n_ok, 2),
        "mean_distractor_tools": round(
            sum(int(r.get("distractor_tools_count") or 0) for r in ok) / n_ok, 2),
        "mean_gold_tool_coverage": round(
            sum(float(r.get("gold_tool_coverage") or 0.0) for r in ok) / n_ok, 4),
        "mean_useful_action_rate": round(
            sum(float(r.get("useful_action_rate") or 0.0) for r in ok) / n_ok, 4),
        "mean_extraneous_actions": round(
            sum(int(r.get("extraneous_actions") or 0) for r in ok) / n_ok, 2),
        "stop_reasons": dict(Counter(str(r.get("stop_reason")) for r in ok)),
        "excluded": dict(excluded),
    }

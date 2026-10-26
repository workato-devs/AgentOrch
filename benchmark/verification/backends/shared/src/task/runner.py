"""The act-observe loop: one LLM agent driving the benchmark ToolRegistry.
The runner sees `expect` ONLY to assert the prompt does not leak it. Tool
RuntimeErrors become observations (recovery is part of what is measured);
everything else stays fail-fast."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from .agents import get_agent, parse_action, parse_protocol_response
from .llm_client import LLMError
from .prompt import brief_leaks, build_first_user_turn, build_system_prompt
from .workflow_plan import (
    FrozenPlanGuard,
    PlanValidationError,
    ResolverState,
    SymbolicResolutionError,
    evaluate_condition,
    materialize_call_arguments,
    expand_materialized_call_arguments,
    normalize_plan,
    plan_hash,
    resolve_symbolic_value,
)


class _ReplaceWorkflow(Exception):
    def __init__(self, plan: list[dict[str, Any]]) -> None:
        self.plan = plan


class _PlanToolFailure(RuntimeError):
    pass


class _PlanStopped(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


class _PlanResolutionFailure(Exception):
    """A resolver error that was already reviewed (protocol v2) and not
    replanned away; outer frames must not review it again."""


_LOOP_KINDS = {"foreach", "repeat", "try"}
_RESOURCE_HINT_MAX_RESOURCES = 40
_RESOURCE_HINT_MAX_FIELDS = 12


def _resource_hint(workspace_context: dict[str, Any]) -> str:
    """Compact restatement of the public workspace cards (already part of the
    first turn's PUBLIC WORKFLOW CONTEXT) next to a resource/tool error."""
    resources = [
        item for item in (workspace_context.get("workspace_resources") or [])
        if isinstance(item, dict)
    ]
    if not resources:
        return ""
    lines = [
        "AVAILABLE WORKSPACE RESOURCES (address a table by its public_id; "
        "resource_ref is only a label):"
    ]
    for card in resources[:_RESOURCE_HINT_MAX_RESOURCES]:
        fields = ", ".join(
            f"{f.get('field_id')}={str(f.get('label') or '')!r}"
            for f in (card.get("fields") or [])[:_RESOURCE_HINT_MAX_FIELDS]
            if isinstance(f, dict)
        )
        lines.append(
            f"- public_id {card.get('public_id')} | {card.get('resource_kind')}"
            f" | name {str(card.get('name') or '')!r}"
            f" | ref {card.get('resource_ref')}"
            + (f" | fields [{fields}]" if fields else "")
        )
    if len(resources) > _RESOURCE_HINT_MAX_RESOURCES:
        lines.append(f"- ... {len(resources) - _RESOURCE_HINT_MAX_RESOURCES} more")
    return "\n".join(lines)


def _node_ids(nodes: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        out.append(str(node.get("id")))
        for region in ("then", "else", "body", "catch"):
            if isinstance(node.get(region), list):
                out.extend(_node_ids(node[region]))
    return out


def _replace_node(nodes: list[dict[str, Any]], node_id: str,
                  replacement: dict[str, Any]) -> bool:
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        if str(node.get("id")) == node_id:
            nodes[index] = deepcopy(replacement)
            return True
        for region in ("then", "else", "body", "catch"):
            if isinstance(node.get(region), list) and _replace_node(
                node[region], node_id, replacement
            ):
                return True
    return False


def _short(value: Any, limit: int) -> str:
    try:
        text = json.dumps(value, default=str)
    except (TypeError, ValueError):
        text = str(value)
    return text if len(text) <= limit else text[:limit] + " …(truncated)"


@dataclass
class RunResult:
    mode: str
    model: str
    trajectory: list[dict[str, Any]]
    final_answer: Any
    steps: list[dict[str, Any]]
    plan: list[Any] | None
    failed_calls: int
    stop_reason: str
    plan_versions: list[list[Any]] = field(default_factory=list)
    replan_count: int = 0
    initial_plan_hash: str | None = None
    protocol_violations: int = 0
    replan_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentRunner:
    # Observation cap must exceed the largest gold tool result in the corpus
    # (currently ~47KB) — a truncated observation would hide data the gold
    # recipe consumed and make the task unsolvable for reasons unrelated to
    # the model.
    def __init__(self, llm, mode: str, max_obs_chars: int = 100_000,
                 replan_protocol: str = "v1") -> None:
        self.llm = llm
        self.agent = get_agent(mode, replan_protocol)
        self.max_obs_chars = max_obs_chars
        self.replan_protocol = replan_protocol

    def run(self, brief: dict[str, Any], seed: dict[str, Any], registry,
            expect: dict[str, Any], max_actions: int,
            schema_text: str | None = None,
            allowed_brief_values: set[str] | None = None,
            tool_families: set[str] | None = None,
            public_tool_specs: list[dict[str, Any]] | None = None,
            public_input_schema: dict[str, Any] | None = None,
            public_workspace_context: dict[str, Any] | None = None,
            contract_text: str | None = None,
            enriched_tool_docs: bool = False,
            initial_plan: list[dict[str, Any]] | None = None,
            max_replans: int = 2) -> RunResult:
        # Tool surface = the software families this task's environment
        # involves (a configured workspace, not the global catalog). The
        # "harness" family is never exposable regardless of the filter.
        registry_specs = {
            str(spec["name"]): spec
            for spec in registry.exposed_specs()
            if not str(spec["name"]).startswith("harness.")
        }
        if public_tool_specs is not None:
            # Task-description runs use the exact same published capability
            # contracts for planning and execution.  The live registry remains
            # the authority for which names are actually callable; a published
            # private/unknown name is an infrastructure error, never an extra
            # execution channel.
            specs = deepcopy(public_tool_specs)
            published_names = {
                str(spec.get("name") or "")
                for spec in specs
                if isinstance(spec, dict)
            }
            unknown = sorted(name for name in published_names if name not in registry_specs)
            if unknown:
                raise RuntimeError(
                    f"published tool surface contains unregistered tools: {unknown}"
                )
        else:
            specs = [
                spec
                for name, spec in registry_specs.items()
                if tool_families is None or name.split(".", 1)[0] in tool_families
            ]
        if not specs:
            raise RuntimeError(f"tool families {sorted(tool_families or set())} "
                               "expose no tools; task environment is empty")
        if enriched_tool_docs:
            from .tool_catalog import enrich_tool_specs
            specs = enrich_tool_specs(specs)
        exposed = {spec["name"] for spec in specs}
        declared_terminal_tools = {
            str(spec.get("name") or "")
            for spec in specs
            if isinstance(spec, dict)
            and isinstance(spec.get("side_effects"), dict)
            and spec["side_effects"].get("terminal_on_success") is True
        }
        system = build_system_prompt(brief, specs, self.agent.system_suffix,
                                     contract_text=contract_text,
                                     response_rules=self.agent.response_rules)
        first = build_first_user_turn(seed, schema_text)
        # Leak surface = the model-authored brief text only. Tool specs, the
        # control/format rules, and the first user turn (trigger_input +
        # environment card) are benchmark-owned or agent-visible by design —
        # expect values colliding with them (copy/transform recipes, generic
        # words in tool descriptions) are not leaks. Values also present in
        # the first turn are whitelisted even in brief text; check_briefs.py
        # remains the stricter pre-run gate on generated briefs.
        # allowed_brief_values = the recipe's business CONSTANTS: the brief
        # policy REQUIRES stating them (an operator cannot guess them), so
        # they are task requirements, not leaks.
        first_lower = first.lower()
        allowed = {value.lower() for value in (allowed_brief_values or set())}
        brief_text = " ".join(str(v) for v in brief.values())
        leaks = [value for value in brief_leaks(brief_text, expect)
                 if value.lower() not in first_lower and value.lower() not in allowed]
        if leaks:
            raise RuntimeError(f"prompt leaks expect values: {leaks}")

        if self.agent.request_initial_plan:
            if initial_plan is None:
                raise RuntimeError(
                    f"{self.agent.mode} requires a cached recipe-level initial plan"
                )
            return self._run_symbolic(
                registry=registry,
                exposed=exposed,
                specs=specs,
                seed=seed,
                first=first,
                system=system,
                initial_plan=initial_plan,
                max_actions=max_actions,
                max_replans=max_replans,
                input_schema=public_input_schema or {},
                workspace_context=public_workspace_context or {},
            )

        messages: list[dict[str, str]] = []
        steps: list[dict[str, Any]] = []
        plan: list[Any] | None = None
        plan_versions: list[list[Any]] = []
        replan_events: list[dict[str, Any]] = []
        protocol_violations = 0
        initial_hash: str | None = None
        observation_step = 0
        failed_calls = 0
        consecutive_format_errors = 0
        final_answer: Any = None
        stop_reason = "max_turns"

        guard: FrozenPlanGuard | None = None
        if self.agent.request_initial_plan:
            if initial_plan is None:
                raise RuntimeError(
                    f"{self.agent.mode} requires a cached recipe-level initial plan"
                )
            plan = deepcopy(initial_plan)
            plan_versions = [deepcopy(plan)]
            initial_hash = plan_hash(plan)
            guard = FrozenPlanGuard(plan, exposed)
            messages.append({
                "role": "user",
                "content": (
                    first
                    + "\n\nFROZEN WORKFLOW PLAN (the same plan is reused for every "
                    "runtime variant of this recipe):\n"
                    + json.dumps({"plan_hash": initial_hash, "plan": plan}, indent=1)
                    + "\n\nExecute the applicable branch. Emit one typed JSON response."
                ),
            })
        else:
            messages.append({"role": "user", "content": first})

        max_turns = max_actions * 2 + max_replans + 6
        for _ in range(max_turns):
            if len(registry.call_log(exposed)) >= max_actions:
                stop_reason = "budget"
                break
            try:
                text = self.llm.complete(system, messages)
            except LLMError as exc:
                stop_reason = f"llm_error:{exc}"
                break
            messages.append({"role": "assistant", "content": text})

            record: dict[str, Any]
            if guard is not None:
                response = parse_protocol_response(text)
                if response is None:
                    failed_calls += 1
                    consecutive_format_errors += 1
                    protocol_violations += 1
                    steps.append({"error": "unparseable_typed_protocol_response"})
                    messages.append({
                        "role": "user",
                        "content": (
                            "PROTOCOL ERROR: return exactly one typed JSON object "
                            "using the frozen-plan response schema. No action was "
                            "executed."
                        ),
                    })
                    if consecutive_format_errors >= 3:
                        stop_reason = "format_error_budget"
                        break
                    continue
                consecutive_format_errors = 0
                response_type = response["type"]
                if response_type == "replan":
                    error: str | None = None
                    if not self.agent.allow_replan:
                        error = "this mode does not permit replanning"
                    elif observation_step < 1:
                        error = "replanning is forbidden before a tool observation"
                    elif len(replan_events) >= max_replans:
                        error = f"replan limit exceeded (max_replans={max_replans})"
                    elif response["based_on_observation_step"] != observation_step:
                        error = (
                            "based_on_observation_step must cite the most recent "
                            f"observation ({observation_step})"
                        )
                    revised: list[dict[str, Any]] | None = None
                    if error is None:
                        try:
                            revised = normalize_plan(
                                response["remaining_workflow"],
                                exposed,
                                id_prefix=f"r{len(replan_events) + 1}p",
                            )
                        except PlanValidationError as exc:
                            error = str(exc)
                    if error is None and revised == plan:
                        error = "unchanged plan restatement is not a replan"
                    if error is not None:
                        failed_calls += 1
                        protocol_violations += 1
                        steps.append({
                            "replan_rejected": response,
                            "error": f"invalid_replan: {error}",
                        })
                        messages.append({
                            "role": "user",
                            "content": (
                                f"PROTOCOL ERROR: replan rejected: {error}. "
                                "No plan change or tool action occurred."
                            ),
                        })
                        continue
                    assert revised is not None
                    event = {
                        "reason": response["reason"],
                        "based_on_observation_step": observation_step,
                        "prior_plan_hash": plan_hash(plan or []),
                        "remaining_plan_hash": plan_hash(revised),
                    }
                    replan_events.append(event)
                    plan = revised
                    plan_versions.append(deepcopy(revised))
                    guard.replace_remaining(revised)
                    steps.append({"replan_accepted": event})
                    messages.append({
                        "role": "user",
                        "content": (
                            "REPLAN ACCEPTED. Current remaining workflow:\n"
                            + json.dumps({"plan": revised}, indent=1)
                            + "\nEmit the next typed action on a later turn."
                        ),
                    })
                    continue
                if response_type == "finish":
                    stop_reason = "finish"
                    steps.append({"finish": True})
                    break
                if response_type == "submit_answer":
                    final_answer = response.get("answer")
                    stop_reason = "answer"
                    steps.append({"submit_answer": True})
                    break
                if response_type == "stop":
                    node_id = response["plan_node_id"]
                    error = guard.validate_action(node_id=node_id, tool="stop")
                    if error is not None:
                        failed_calls += 1
                        protocol_violations += 1
                        steps.append({"action": response, "error": error})
                        messages.append({
                            "role": "user",
                            "content": f"PROTOCOL ERROR: {error}. No action was executed.",
                        })
                        continue
                    guard.record_action(node_id, failed=False)
                    raw_error = response["stop_with_error"]
                    is_error = raw_error.strip().lower() == "true"
                    steps.append({
                        "action": response,
                        "explicit_stop": {
                            "stop_reason": response["stop_reason"],
                            "stop_with_error": is_error,
                        },
                    })
                    stop_reason = "explicit_stop_error" if is_error else "explicit_stop"
                    break
                action = {
                    "tool": response["tool"],
                    "args": response["args"],
                    "plan_node_id": response["plan_node_id"],
                    "thought": response.get("thought"),
                }
                error = guard.validate_action(
                    node_id=action["plan_node_id"], tool=action["tool"]
                )
                if error is not None:
                    failed_calls += 1
                    protocol_violations += 1
                    steps.append({"action": action, "error": error})
                    messages.append({
                        "role": "user",
                        "content": f"PROTOCOL ERROR: {error}. No action was executed.",
                    })
                    continue
                record = {
                    "thought": action.get("thought"),
                    "plan_node_id": action["plan_node_id"],
                }
            else:
                action = parse_action(text)
                record = {"thought": (action or {}).get("thought")}
                if action is None:
                    failed_calls += 1
                    consecutive_format_errors += 1
                    record["error"] = "unparseable_action"
                    steps.append(record)
                    messages.append({"role": "user", "content":
                        'Could not parse an action. Reply with exactly one JSON '
                        'object: {"tool": "...", "args": {...}}.'})
                    if consecutive_format_errors >= 3:
                        stop_reason = "format_error_budget"
                        break
                    continue
                consecutive_format_errors = 0

            tool = action["tool"]
            record["action"] = {"tool": tool, "args": action["args"]}
            if tool == "finish":
                stop_reason = "finish"
                steps.append(record)
                break
            if tool == "submit_answer":
                final_answer = action["args"].get("answer")
                stop_reason = "answer"
                steps.append(record)
                break
            if tool == "stop":
                explicit_reason = str(action["args"].get("stop_reason") or "").strip()
                raw_error = action["args"].get("stop_with_error", False)
                is_error = raw_error is True or str(raw_error).strip().lower() == "true"
                record["explicit_stop"] = {
                    "stop_reason": explicit_reason,
                    "stop_with_error": is_error,
                }
                stop_reason = "explicit_stop_error" if is_error else "explicit_stop"
                steps.append(record)
                break

            if tool not in exposed:
                # Registry.call would happily execute registered-but-hidden
                # harness tools (seeding, snapshots, cleanup) — an unscored,
                # unbudgeted channel into hidden state. Agents may only call
                # what their tool schemas advertise.
                failed_calls += 1
                observation = f"ERROR: unknown tool: {tool}"
                record["error"] = observation
                steps.append(record)
                messages.append({"role": "user", "content":
                    f"OBSERVATION:\n{observation}\n\nEmit your next action as JSON."})
                continue

            try:
                result = registry.call(tool, action["args"])
                observation = _short(result, self.max_obs_chars)
                record["observation"] = observation
            except RuntimeError as exc:
                failed_calls += 1
                observation = f"ERROR: {exc}"
                record["error"] = observation
            observation_step += 1
            if guard is not None:
                guard.record_action(
                    action["plan_node_id"], failed="error" in record
                )
            steps.append(record)
            terminal_after_call = getattr(
                registry,
                "terminal_after_call",
                None,
            )
            if (
                "error" not in record
                and (
                    tool in declared_terminal_tools
                    or (
                        callable(terminal_after_call)
                        and terminal_after_call(tool, result)
                    )
                )
            ):
                stop_reason = "terminal_tool"
                break
            messages.append({"role": "user", "content":
                f"OBSERVATION:\n{observation}\n\nEmit your next action as JSON."})

        return self._result(
            registry, exposed, final_answer, steps, plan, failed_calls,
            stop_reason, plan_versions, initial_hash, protocol_violations,
            replan_events,
        )

    def _run_symbolic(
        self,
        *,
        registry,
        exposed: set[str],
        specs: list[dict[str, Any]],
        seed: dict[str, Any],
        first: str,
        system: str,
        initial_plan: list[dict[str, Any]],
        max_actions: int,
        max_replans: int,
        input_schema: dict[str, Any],
        workspace_context: dict[str, Any],
    ) -> RunResult:
        """Interpret a frozen symbolic plan without a second LLM arg policy.

        Plan-Execute is fully deterministic after its one recipe-level plan.
        Replan uses the model only after a real observation, where it may
        return ``continue`` or replace the unexecuted suffix with another
        validated symbolic workflow. Tool names and arguments always come
        from the current plan, never from an execution-time action response.
        """

        runtime = deepcopy((seed.get("variant_input") or {}).get("trigger_input") or {})
        execution_context = (seed.get("variant_input") or {}).get("execution_context")
        if isinstance(execution_context, dict) and execution_context:
            runtime["execution_context"] = deepcopy(execution_context)
        state = ResolverState(
            inputs=runtime,
            workspace_resources=deepcopy(
                [
                    *(workspace_context.get("workspace_resources") or []),
                    *(workspace_context.get("communication_templates") or []),
                ]
            ),
        )
        declared_terminal_tools = {
            str(spec.get("name") or "")
            for spec in specs
            if isinstance(spec, dict)
            and isinstance(spec.get("side_effects"), dict)
            and spec["side_effects"].get("terminal_on_success") is True
        }
        plan = deepcopy(initial_plan)
        initial_hash = plan_hash(plan)
        plan_versions = [deepcopy(plan)]
        replan_events: list[dict[str, Any]] = []
        steps: list[dict[str, Any]] = []
        counters = {"failed": 0, "protocol": 0, "observation": 0}
        final_answer: Any = None
        stop_reason = "plan_complete"
        messages: list[dict[str, str]] = []
        if self.agent.allow_replan:
            messages.append({
                "role": "user",
                "content": (
                    first
                    + "\n\nCURRENT SYMBOLIC WORKFLOW PLAN:\n"
                    + json.dumps({"plan_hash": initial_hash, "plan": plan}, indent=1)
                    + "\n\nThe benchmark executes this plan deterministically. After each "
                    "observation reply only with {\"type\":\"continue\"}, or "
                    "replace the unexecuted suffix using the typed symbolic "
                    "replan schema. Do not emit tool calls or concrete args."
                ),
            })

        v2 = self.agent.protocol == "v2"
        # Execution frames (innermost last): the node currently executing at
        # each nesting level. Protocol v2 derives the unexecuted suffix from
        # them so a patch can be applied without the model restating it.
        frames: list[dict[str, Any]] = []

        def continuation(include_current: bool) -> list[dict[str, Any]] | None:
            """Unexecuted suffix as a flat top-level plan, or None when the
            observation sits inside a loop/try body or a partial call
            expansion (restarting those would repeat side effects)."""
            if not frames:
                return None
            if any(frame["node"]["kind"] in _LOOP_KINDS for frame in frames[:-1]):
                return None
            inner = frames[-1]
            if inner["node"]["kind"] in _LOOP_KINDS and not include_current:
                return None
            if inner.get("partial") and not include_current:
                return None
            start = inner["index"] if include_current else inner["index"] + 1
            out: list[dict[str, Any]] = list(inner["nodes"][start:])
            for frame in reversed(frames[:-1]):
                out.extend(frame["nodes"][frame["index"] + 1:])
            return deepcopy(out)

        def maybe_replan(observation: str, *, trigger: str = "observation") -> None:
            if not self.agent.allow_replan:
                return
            counters["observation"] += 1
            observation_step = counters["observation"]
            is_error = trigger != "observation"
            observation_message = (
                f"OBSERVATION {observation_step}:\n{observation}\n\n"
                "Continue the current suffix or emit a symbolic replacement."
            )
            suffix: list[dict[str, Any]] | None = None
            if v2:
                suffix = continuation(include_current=is_error)
                if is_error:
                    hint = _resource_hint(workspace_context)
                    if hint:
                        observation_message += "\n\n" + hint
                if suffix is not None:
                    observation_message += (
                        "\n\nPatchable node ids (unexecuted): "
                        + ", ".join(_node_ids(suffix))
                    )
            # Strict-alternation chat templates (e.g. gemma) reject
            # consecutive user turns; the first observation follows the
            # initial-plan user message with no assistant turn between, so
            # fold it into the open user turn instead of appending one.
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += "\n\n" + observation_message
            else:
                messages.append({"role": "user", "content": observation_message})
            attempts = 2 if v2 else 1
            counters["reviewing"] = 1
            try:
                _review(observation_step, trigger, suffix, attempts)
            finally:
                counters["reviewing"] = 0

        def _review(observation_step: int, trigger: str,
                    suffix: list[dict[str, Any]] | None, attempts: int) -> None:
            for attempt in range(1, attempts + 1):
                try:
                    raw = self.llm.complete(system, messages)
                except LLMError as exc:
                    raise _PlanStopped(f"llm_error:{exc}") from exc
                messages.append({"role": "assistant", "content": raw})
                response = parse_protocol_response(raw)
                if response is not None and response.get("type") == "continue":
                    review: dict[str, Any] = {
                        "based_on_observation_step": observation_step,
                        "decision": "continue",
                    }
                    if v2:
                        review["attempt"] = attempt
                        review["trigger"] = trigger
                    steps.append({"replan_review": review})
                    return
                error: str | None = None
                revised: list[dict[str, Any]] | None = None
                response_type = response.get("type") if response else None
                if response is None:
                    error = ("reply is not one valid typed JSON object "
                             "(continue or replan); malformed JSON is fail-closed")
                elif response_type not in (("replan", "patch") if v2 else ("replan",)):
                    error = "expected continue or replan"
                elif len(replan_events) >= max_replans:
                    error = f"replan limit exceeded (max_replans={max_replans})"
                elif response["based_on_observation_step"] != observation_step:
                    error = (
                        "based_on_observation_step must cite the most recent "
                        f"observation ({observation_step})"
                    )
                else:
                    if response_type == "patch":
                        if suffix is None:
                            error = (
                                "patch is unavailable here (the observation is "
                                "inside a foreach/repeat/try body or a partial "
                                "call expansion); use replan instead"
                            )
                        else:
                            candidate = deepcopy(suffix)
                            if not _replace_node(
                                candidate, response["node_id"], response["node"]
                            ):
                                error = (
                                    f"patch node_id {response['node_id']!r} is not "
                                    "in the unexecuted suffix; patchable ids: "
                                    + ", ".join(_node_ids(suffix))
                                )
                    else:
                        candidate = response["remaining_workflow"]
                    if error is None:
                        try:
                            revised = normalize_plan(
                                candidate,
                                exposed,
                                id_prefix=f"r{len(replan_events) + 1}p",
                                tool_specs=specs,
                                input_schema=input_schema,
                                workspace_context=workspace_context,
                                available_bindings=(
                                    set(state.outputs) | set(state.loops) | set(state.errors)
                                ),
                            )
                        except PlanValidationError as exc:
                            error = str(exc)
                if error is not None:
                    counters["failed"] += 1
                    counters["protocol"] += 1
                    limit_hit = error.startswith("replan limit exceeded")
                    repair = v2 and attempt < attempts and not limit_hit
                    rejected: dict[str, Any] = {
                        "replan_rejected": response,
                        # raw reply kept for audit: a None response otherwise
                        # leaves no evidence of what the model actually said
                        "raw_response": raw[:2000],
                        "error": f"invalid_replan: {error}",
                    }
                    if v2:
                        rejected["attempt"] = attempt
                        rejected["repair_offered"] = repair
                        rejected["trigger"] = trigger
                    steps.append(rejected)
                    if not repair:
                        return
                    messages.append({
                        "role": "user",
                        "content": (
                            f"REPLAN REJECTED (attempt {attempt}): {error}. "
                            "No change was applied. Reply again with exactly ONE "
                            "typed JSON object: {\"type\":\"continue\"}, a "
                            "replan whose remaining_workflow contains only "
                            "unexecuted work and re-declares no existing "
                            "binding, or a patch of one patchable node id. "
                            f"Cite based_on_observation_step {observation_step}."
                        ),
                    })
                    continue
                assert revised is not None
                event: dict[str, Any] = {
                    "reason": response["reason"],
                    "based_on_observation_step": observation_step,
                    "prior_plan_hash": plan_hash(plan),
                    "remaining_plan_hash": plan_hash(revised),
                }
                if v2:
                    event["kind"] = response_type
                    event["attempt"] = attempt
                    event["trigger"] = trigger
                    if response_type == "patch":
                        event["node_id"] = response["node_id"]
                replan_events.append(event)
                plan_versions.append(deepcopy(revised))
                steps.append({"replan_accepted": event})
                if v2:
                    # Later patches must address the benchmark-assigned ids of
                    # the revised workflow, so show them once.
                    messages.append({
                        "role": "user",
                        "content": (
                            "REPLAN ACCEPTED. Current workflow (normalized node "
                            "ids):\n" + json.dumps(revised, indent=1)
                        ),
                    })
                raise _ReplaceWorkflow(revised)

        resolver_errors = (SymbolicResolutionError, KeyError, TypeError, ValueError)

        def execute_nodes(nodes: list[dict[str, Any]]) -> None:
            for index, node in enumerate(nodes):
                frames.append({
                    "nodes": nodes, "index": index, "node": node, "partial": False,
                })
                try:
                    _execute_node(node)
                except resolver_errors as exc:
                    if not v2 or counters.get("reviewing"):
                        # v1 ends the row (handled by the caller); an error
                        # raised inside a review turn is never re-reviewed
                        raise
                    # Protocol v2: a resolver failure is an ERROR observation
                    # the model may replan from (v1 ends the row here).
                    counters["failed"] += 1
                    counters["protocol"] += 1
                    steps.append({"error": f"plan_resolution_error:{exc}"})
                    maybe_replan(
                        f"ERROR: plan resolution failed at node {node['id']}: {exc}",
                        trigger="resolution_error",
                    )
                    raise _PlanResolutionFailure(str(exc)) from exc
                finally:
                    frames.pop()

        def _execute_node(node: dict[str, Any]) -> None:
            nonlocal final_answer
            kind = node["kind"]
            node_id = str(node["id"])
            if kind == "transform":
                value = resolve_symbolic_value(node["expression"], state)
                state.bind_output(node["bind"], value)
                steps.append({
                    "plan_node_id": node_id,
                    "transform_bind": node["bind"],
                })
                return
            if kind == "if":
                choice = "then" if evaluate_condition(node["condition"], state) else "else"
                steps.append({"plan_node_id": node_id, "branch": choice})
                execute_nodes(node[choice])
                return
            if kind == "foreach":
                items = resolve_symbolic_value(node["items"], state)
                if items is None:
                    items = []
                if not isinstance(items, (list, tuple)):
                    raise SymbolicResolutionError(
                        f"foreach {node_id} resolved to {type(items).__name__}, not array"
                    )
                batch_size_value = node.get("batch_size")
                if batch_size_value is not None:
                    batch_size = int(
                        resolve_symbolic_value(batch_size_value, state)
                    )
                    if batch_size <= 0:
                        raise SymbolicResolutionError(
                            f"foreach {node_id} batch_size must be positive"
                        )
                    items = [
                        list(items[index : index + batch_size])
                        for index in range(0, len(items), batch_size)
                    ]
                bind = str(node["item_bind"])
                had_previous = bind in state.loops
                previous = state.loops.get(bind)
                try:
                    for index, item in enumerate(items):
                        state.loops[bind] = item
                        steps.append({
                            "plan_node_id": node_id,
                            "foreach_index": index,
                        })
                        execute_nodes(node["body"])
                finally:
                    if had_previous:
                        state.loops[bind] = previous
                    else:
                        state.loops.pop(bind, None)
                return
            if kind == "repeat":
                # Repeat-until is post-tested: the body executes once,
                # then repeats while the public condition is false.  Tool
                # calls inside the body remain protected by max_actions.
                repeat_iterations = 0
                while True:
                    repeat_iterations += 1
                    if repeat_iterations > max_actions:
                        raise _PlanStopped("budget")
                    steps.append({
                        "plan_node_id": node_id,
                        "repeat_iteration": repeat_iterations - 1,
                    })
                    execute_nodes(node["body"])
                    if evaluate_condition(node["until"], state):
                        break
                return
            if kind == "try":
                try:
                    execute_nodes(node["body"])
                except _PlanToolFailure as exc:
                    state.errors[node["error_bind"]] = {
                        "message": str(exc), "type": type(exc).__name__
                    }
                    steps.append({"plan_node_id": node_id, "caught": str(exc)})
                    execute_nodes(node["catch"])
                return
            if kind == "stop":
                arguments = {
                    key: resolve_symbolic_value(value, state)
                    for key, value in node.get("arguments", {}).items()
                }
                is_error = arguments.get("stop_with_error") is True or str(
                    arguments.get("stop_with_error", False)
                ).strip().lower() == "true"
                steps.append({
                    "plan_node_id": node_id,
                    "explicit_stop": {
                        "stop_reason": str(arguments.get("stop_reason") or ""),
                        "stop_with_error": is_error,
                    },
                })
                raise _PlanStopped(
                    "explicit_stop_error" if is_error else "explicit_stop"
                )
            if kind == "return":
                final_answer = resolve_symbolic_value(node["value"], state)
                steps.append({
                    "plan_node_id": node_id,
                    "return": deepcopy(final_answer),
                })
                raise _PlanStopped("return")

            expanded_arguments = expand_materialized_call_arguments(node, state)
            expanded_results: list[Any] = []
            for expansion_index, args in enumerate(expanded_arguments):
                if len(registry.call_log(exposed)) >= max_actions:
                    raise _PlanStopped("budget")
                tool = str(node["tool"])
                record: dict[str, Any] = {
                    "plan_node_id": node_id,
                    "action": {"tool": tool, "args": args},
                }
                if node.get("call_expansion") is not None:
                    record["call_expansion_index"] = expansion_index
                try:
                    result = registry.call(tool, args)
                    expanded_results.append(deepcopy(result))
                    state.bind_output(
                        node.get("bind"),
                        (
                            expanded_results
                            if node.get("call_expansion") is not None
                            else result
                        ),
                    )
                    observation = _short(result, self.max_obs_chars)
                    record["observation"] = observation
                    steps.append(record)
                    terminal_after_call = getattr(
                        registry, "terminal_after_call", None
                    )
                    if (
                        tool in declared_terminal_tools
                        or (
                            callable(terminal_after_call)
                            and terminal_after_call(tool, result)
                        )
                    ):
                        raise _PlanStopped("terminal_tool")
                    if frames:
                        frames[-1]["partial"] = (
                            expansion_index < len(expanded_arguments) - 1
                        )
                    maybe_replan(observation)
                except RuntimeError as exc:
                    counters["failed"] += 1
                    observation = f"ERROR: {exc}"
                    record["error"] = observation
                    steps.append(record)
                    maybe_replan(observation, trigger="tool_error")
                    raise _PlanToolFailure(str(exc)) from exc

        while True:
            try:
                execute_nodes(plan)
                stop_reason = "plan_complete"
                break
            except _ReplaceWorkflow as replacement:
                plan = replacement.plan
                continue
            except _PlanStopped as stopped:
                stop_reason = stopped.reason
                break
            except _PlanToolFailure as exc:
                stop_reason = f"plan_tool_error:{exc}"
                break
            except _PlanResolutionFailure as exc:
                # counters and the error step were recorded at the frame
                stop_reason = f"plan_resolution_error:{exc}"
                break
            except (SymbolicResolutionError, KeyError, TypeError, ValueError) as exc:
                counters["failed"] += 1
                counters["protocol"] += 1
                stop_reason = f"plan_resolution_error:{exc}"
                steps.append({"error": stop_reason})
                break

        return self._result(
            registry,
            exposed,
            final_answer,
            steps,
            plan,
            counters["failed"],
            stop_reason,
            plan_versions,
            initial_hash,
            counters["protocol"],
            replan_events,
        )

    def _result(self, registry, exposed: set[str], final_answer: Any,
                steps: list[dict[str, Any]], plan: list[Any] | None,
                failed_calls: int, stop_reason: str,
                plan_versions: list[list[Any]], initial_plan_hash: str | None,
                protocol_violations: int,
                replan_events: list[dict[str, Any]]) -> RunResult:
        return RunResult(
            mode=self.agent.mode,
            model=self.llm.model,
            trajectory=registry.call_log(exposed),
            final_answer=final_answer,
            steps=steps,
            plan=plan,
            failed_calls=failed_calls,
            stop_reason=stop_reason,
            plan_versions=plan_versions,
            replan_count=max(0, len(plan_versions) - 1),
            initial_plan_hash=initial_plan_hash,
            protocol_violations=protocol_violations,
            replan_events=replan_events,
        )

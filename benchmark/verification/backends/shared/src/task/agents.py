"""Agent mode strategies + robust parsing of model replies into actions/plans.
Parsers never raise: unparseable replies yield None so the runner can feed an
error observation back and count a failed step."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _iter_json_objects(text: str):
    for match in _FENCE_RE.finditer(text):
        yield match.group(1).strip()
    depth, start = 0, -1
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                yield text[start:i + 1]


def _loads(candidate: str) -> Any | None:
    try:
        return json.loads(candidate)
    except (TypeError, ValueError):
        return None


def parse_action(text: str) -> dict[str, Any] | None:
    # ``args`` must be an object; any other shape (list, string, number) is
    # a malformed action and takes the format-error feedback path rather
    # than reaching a tool implementation that assumes a mapping.
    def _dict_args(container: dict[str, Any]) -> dict[str, Any] | None:
        args = container.get("args")
        if args is None:
            return {}
        return args if isinstance(args, dict) else None

    for candidate in _iter_json_objects(text):
        obj = _loads(candidate)
        if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
            args = _dict_args(obj)
            if args is None:
                continue
            action = {"tool": obj["tool"], "args": args}
            if "thought" in obj:
                action["thought"] = obj["thought"]
            return action
        if isinstance(obj, dict) and isinstance(obj.get("action"), dict):
            inner = obj["action"]
            if isinstance(inner.get("tool"), str):
                args = _dict_args(inner)
                if args is None:
                    continue
                action = {"tool": inner["tool"], "args": args}
                if "thought" in obj:
                    action["thought"] = obj["thought"]
                return action
    return None


def parse_protocol_response(text: str) -> dict[str, Any] | None:
    """Parse one typed frozen-plan execution response without legacy fallback."""

    for candidate in _iter_json_objects(text):
        obj = _loads(candidate)
        if not isinstance(obj, dict) or not isinstance(obj.get("type"), str):
            continue
        response_type = obj["type"]
        if response_type == "continue":
            return {"type": "continue"}
        if response_type == "act":
            if not isinstance(obj.get("plan_node_id"), str):
                return None
            if not isinstance(obj.get("tool"), str):
                return None
            args = obj.get("args")
            if args is not None and not isinstance(args, dict):
                return None
            return {
                "type": "act",
                "plan_node_id": obj["plan_node_id"],
                "tool": obj["tool"],
                "args": args or {},
                "thought": obj.get("thought"),
            }
        if response_type == "replan":
            if not isinstance(obj.get("reason"), str) or not obj["reason"].strip():
                return None
            if not isinstance(obj.get("based_on_observation_step"), int):
                return None
            remaining = obj.get("remaining_workflow")
            if not isinstance(remaining, list):
                return None
            return {
                "type": "replan",
                "reason": obj["reason"].strip(),
                "based_on_observation_step": obj["based_on_observation_step"],
                "remaining_workflow": remaining,
            }
        if response_type == "patch":
            if not isinstance(obj.get("reason"), str) or not obj["reason"].strip():
                return None
            if not isinstance(obj.get("based_on_observation_step"), int):
                return None
            if not isinstance(obj.get("node_id"), str) or not obj["node_id"].strip():
                return None
            if not isinstance(obj.get("node"), dict) or not obj["node"]:
                return None
            return {
                "type": "patch",
                "reason": obj["reason"].strip(),
                "based_on_observation_step": obj["based_on_observation_step"],
                "node_id": obj["node_id"].strip(),
                "node": obj["node"],
            }
        if response_type == "finish":
            return {"type": "finish"}
        if response_type == "submit_answer":
            return {"type": "submit_answer", "answer": obj.get("answer")}
        if response_type == "stop":
            if not isinstance(obj.get("plan_node_id"), str):
                return None
            if not isinstance(obj.get("stop_reason"), str):
                return None
            if not isinstance(obj.get("stop_with_error"), str):
                return None
            return {
                "type": "stop",
                "plan_node_id": obj["plan_node_id"],
                "stop_reason": obj["stop_reason"],
                "stop_with_error": obj["stop_with_error"],
            }
        return None
    return None


def _repair_missing_json_closers(text: str) -> str | None:
    """Insert only missing object/array closers; never change JSON tokens.

    This handles a common long-output truncation-shaped syntax error such as
    ``{"items":[{"fields":{...}]}``, where ``}`` closers are omitted before
    an existing ``]``. Mismatched or extra closing tokens fail closed.
    """

    source = text.strip()
    if not source.startswith(("{", "[")):
        return None
    stack: list[str] = []
    output: list[str] = []
    in_string = False
    escaped = False
    pairs = {"{": "}", "[": "]"}
    open_for = {"}": "{", "]": "["}
    for char in source:
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            output.append(char)
        elif char in pairs:
            stack.append(char)
            output.append(char)
        elif char in open_for:
            wanted = open_for[char]
            if wanted not in stack:
                return None
            while stack and stack[-1] != wanted:
                output.append(pairs[stack.pop()])
            stack.pop()
            output.append(char)
        else:
            output.append(char)
    if in_string:
        return None
    while stack:
        output.append(pairs[stack.pop()])
    repaired = "".join(output)
    return repaired if repaired != source else None


def parse_plan(text: str, *, repair_missing_closers: bool = False) -> list[Any] | None:
    for candidate in _iter_json_objects(text):
        obj = _loads(candidate)
        if isinstance(obj, dict) and isinstance(obj.get("plan"), list):
            return obj["plan"]
    if repair_missing_closers:
        repaired = _repair_missing_json_closers(text)
        obj = _loads(repaired) if repaired is not None else None
        if isinstance(obj, dict) and isinstance(obj.get("plan"), list):
            return obj["plan"]
    return None


def parse_incremental_plan_action(text: str) -> dict[str, Any] | None:
    """Parse one append-only workflow-compilation editor action."""

    for candidate in _iter_json_objects(text):
        obj = _loads(candidate)
        if not isinstance(obj, dict):
            continue
        action_type = obj.get("type")
        if action_type == "finish_plan":
            return {"type": "finish_plan"}
        if action_type != "append_node":
            continue
        if not isinstance(obj.get("parent"), str):
            return None
        if not isinstance(obj.get("node"), dict):
            return None
        # Fail closed on stray top-level keys instead of silently dropping
        # them: a model that closes the node object one brace early puts
        # fields like ``bind`` next to type/parent, and accepting the
        # bind-less node dooms the append-only session (nothing can
        # reference the lost binding and the prefix is immutable).
        extra = sorted(set(obj) - {"type", "parent", "node"})
        if extra:
            return {
                "type": "invalid_action",
                "error": (
                    "append_node accepts only the keys type/parent/node; "
                    f"found stray top-level keys {extra}. Node fields such "
                    "as bind/arguments/condition belong INSIDE the node "
                    "object. No node was added; re-send the full corrected "
                    "operation."
                ),
            }
        return {
            "type": "append_node",
            "parent": obj["parent"],
            "node": obj["node"],
        }
    return None


def updated_plan(text: str, current: list[Any] | None) -> list[Any] | None:
    """Return the revised plan carried by a reply, or None. A plan counts as
    a revision only when it parses and differs from the current plan —
    models often restate the unchanged plan, which is not a replan event."""
    candidate = parse_plan(text)
    if candidate is None or candidate == current:
        return None
    return candidate


class Agent:
    mode: str = "react"
    request_initial_plan: bool = False
    allow_replan: bool = False
    # Replan review-turn protocol version ("v1" = canonical fail-closed single
    # shot; "v2" adds a repair turn, the patch op, resolver-error reviews and
    # a resource hint on error observations). Only meaningful for replan.
    protocol: str = "v1"
    system_suffix: str = ""
    response_rules: str | None = None


class ReActAgent(Agent):
    mode = "react"
    system_suffix = (
        "Work step by step: think, emit exactly one JSON action, observe the "
        "result, repeat. Do not announce a full plan up front."
    )


class PlanThenExecuteAgent(Agent):
    mode = "plan_execute"
    request_initial_plan = True
    system_suffix = (
        "The benchmark deterministically executes the supplied frozen symbolic "
        "WorkflowPlan. It resolves arguments, branches, loops, and dataflow; "
        "there is no second model decision during runtime."
    )
    response_rules = (
        "Response format: reply with exactly ONE typed JSON object per turn. "
        "For a tool call use {\"type\":\"act\",\"plan_node_id\":\"p3\","
        "\"tool\":\"<tool>\",\"args\":{...}}. The node id and tool must "
        "match the frozen plan. To finish use {\"type\":\"finish\"}. For an "
        "explicit stop node use {\"type\":\"stop\",\"plan_node_id\":\"p3\","
        "\"stop_reason\":\"...\",\"stop_with_error\":\"false\"}. No prose "
        "outside the JSON."
    )


class GlobalInputAgent(PlanThenExecuteAgent):
    """GLOBAL+INPUT information-control ablation (doc/global_input.md).

    Same one-shot planner, schema, validator and deterministic frozen-plan
    execution as Global View (``plan_execute``); the plan is generated once
    per runtime variant with that variant's concrete public runtime input in
    the planning prompt, and never shared across variants."""

    mode = "global_input"


class IncrementalWorkflowAgent(Agent):
    """Execute a plan compiled one node at a time before runtime."""

    mode = "incremental_workflow"
    request_initial_plan = True
    system_suffix = (
        "The benchmark deterministically executes the frozen symbolic "
        "WorkflowPlan that was compiled incrementally before runtime. It "
        "resolves arguments, branches, loops, and dataflow without any "
        "runtime model decisions."
    )
    response_rules = PlanThenExecuteAgent.response_rules


class ReplanAgent(Agent):
    mode = "replan"
    request_initial_plan = True
    allow_replan = True
    system_suffix = (
        "The benchmark deterministically executes the supplied symbolic plan. "
        "After each real tool observation, either continue it or revise and replace only "
        "the unexecuted suffix. The executed prefix is immutable. A replacement "
        "must use the same typed symbolic node/value schema; never emit a tool "
        "call or concrete runtime arguments."
    )
    response_rules = (
        "Response format: reply with exactly ONE typed JSON object per turn. "
        "Continue with {\"type\":\"continue\"}, or explicitly replan with "
        "{\"type\":\"replan\",\"reason\":\"...\","
        "\"based_on_observation_step\":1,\"remaining_workflow\":[...]}. A "
        "remaining_workflow uses the same node shapes as the initial plan and "
        "contains only unexecuted work. No prose outside the JSON."
    )


class ReplanV2Agent(ReplanAgent):
    """Replan protocol v2. Same mode, same frozen initial plan, same symbolic
    validator; differs only in the review-turn protocol (task/runner.py)."""

    protocol = "v2"
    system_suffix = (
        ReplanAgent.system_suffix
        + " A rejected revision is returned to you once with the validator "
        "error so you can repair it. Resolver failures (an expression that "
        "cannot be evaluated) are also shown as ERROR observations you may "
        "replan from."
    )
    response_rules = (
        "Response format: reply with exactly ONE typed JSON object per turn. "
        "Continue with {\"type\":\"continue\"}. Replace the whole unexecuted "
        "suffix with {\"type\":\"replan\",\"reason\":\"...\","
        "\"based_on_observation_step\":1,\"remaining_workflow\":[...]}. "
        "Replace exactly ONE unexecuted node (the smallest fix) with "
        "{\"type\":\"patch\",\"reason\":\"...\","
        "\"based_on_observation_step\":1,\"node_id\":\"p3\","
        "\"node\":{...}} where node_id is one of the patchable ids listed "
        "with the observation and node uses the same typed node shape as the "
        "plan. A remaining_workflow contains only unexecuted work and must "
        "not re-declare bindings that already exist. No prose outside the "
        "JSON."
    )


class AgentSDKAgent(Agent):
    """claude-agent-sdk harness mode: the SDK owns the loop and native tool
    calling, so there is no JSON-action protocol and no system_suffix here —
    task/agent_sdk_runner.py builds the prompt variant."""
    mode = "agent_sdk"


DEFAULT_AGENT_MODES = (
    ReActAgent.mode,
    ReplanAgent.mode,
    PlanThenExecuteAgent.mode,
)


AGENT_MODES: dict[str, type[Agent]] = {
    ReActAgent.mode: ReActAgent,
    PlanThenExecuteAgent.mode: PlanThenExecuteAgent,
    GlobalInputAgent.mode: GlobalInputAgent,
    IncrementalWorkflowAgent.mode: IncrementalWorkflowAgent,
    ReplanAgent.mode: ReplanAgent,
    AgentSDKAgent.mode: AgentSDKAgent,
}


REPLAN_PROTOCOLS: dict[str, type[Agent]] = {
    "v1": ReplanAgent,
    "v2": ReplanV2Agent,
}


def get_agent(mode: str, replan_protocol: str = "v1") -> Agent:
    if mode not in AGENT_MODES:
        raise ValueError(f"unknown agent mode {mode!r}; choices: {sorted(AGENT_MODES)}")
    if replan_protocol not in REPLAN_PROTOCOLS:
        raise ValueError(
            f"unknown replan protocol {replan_protocol!r}; "
            f"choices: {sorted(REPLAN_PROTOCOLS)}"
        )
    if mode == ReplanAgent.mode:
        return REPLAN_PROTOCOLS[replan_protocol]()
    return AGENT_MODES[mode]()

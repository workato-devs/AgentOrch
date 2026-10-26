"""Replan protocol v2 (repair turn, patch op, resolver-error review, resource
hint). v1 behaviour must be byte-for-byte unchanged: every test here that
exercises v1 pins the legacy semantics.

Run with:
  PYTHONPATH=verification/backends/simulated/src:verification/backends/shared/src \
    python -m pytest verification/backends/shared/src/tests/test_replan_v2.py
"""
from __future__ import annotations

import json

import pytest

from task.agents import get_agent, parse_protocol_response
from task.llm_client import LLMError, ScriptedLLM
from task.runner import AgentRunner
from task.workflow_plan import normalize_plan


BRIEF = {
    "objective": "Read a record and write its value.",
    "input_contract": [],
    "completion_criteria": [],
    "constraints": [],
}
SEED = {"variant_input": {"trigger_input": {"record_id": "runtime-only"}}}
TOOLS = {"alpha.read", "beta.write", "gamma.recover"}
WORKSPACE = {
    "workspace_resources": [
        {
            "public_id": "7201",
            "name": "Workspaces",
            "resource_ref": "resource_ab78322f7955",
            "resource_kind": "resource",
            "fields": [
                {"field_id": "col1", "label": "Email", "type": "string"},
                {"field_id": "col2", "label": "Active", "type": "string"},
            ],
        }
    ]
}


def _lit(value):
    return {"kind": "literal", "value": value}


def _input(*path):
    return {"kind": "input_ref", "path": list(path)}


def _output(binding, *path):
    return {"kind": "output_ref", "binding": binding, "path": list(path)}


class Registry:
    def __init__(self, failing: set[str] | None = None) -> None:
        self.calls = []
        self.failing = failing or set()

    def exposed_specs(self):
        return [
            {"name": name, "description": name, "input_schema": {"type": "object"}}
            for name in sorted(TOOLS)
        ]

    def call(self, tool, args):
        if tool in self.failing:
            raise RuntimeError(
                "workato_db_table resource_ab78322f7955 is not part of the "
                "seeded benchmark state"
            )
        if tool == "alpha.read":
            result = {
                "ok": True,
                "record": {"id": args["record_id"], "value": "resolved-value"},
            }
        else:
            result = {"ok": True, "tool": tool}
        self.calls.append({"tool": tool, "args": args, "result": result})
        return result

    def call_log(self, exposed):
        return [call for call in self.calls if call["tool"] in exposed]


class RecordingLLM(ScriptedLLM):
    """ScriptedLLM that keeps every prompt it was shown."""

    def __init__(self, replies):
        super().__init__(replies)
        self.seen: list[list[dict[str, str]]] = []

    def complete(self, system, messages):
        self.seen.append([dict(m) for m in messages])
        return super().complete(system, messages)


def _read_then_write():
    return normalize_plan(
        [
            {
                "kind": "call",
                "tool": "alpha.read",
                "arguments": {"record_id": _input("record_id")},
                "bind": "read_result",
            },
            {
                "kind": "call",
                "tool": "beta.write",
                "arguments": {
                    "record_id": _output("read_result", "record", "id"),
                },
            },
        ],
        TOOLS,
    )


def _recover_node():
    return {
        "kind": "call",
        "tool": "gamma.recover",
        "arguments": {"record_id": _input("record_id")},
    }


def _replan(step, remaining):
    return json.dumps({
        "type": "replan",
        "reason": "fix",
        "based_on_observation_step": step,
        "remaining_workflow": remaining,
    })


def _patch(step, node_id, node):
    return json.dumps({
        "type": "patch",
        "reason": "fix one node",
        "based_on_observation_step": step,
        "node_id": node_id,
        "node": node,
    })


def _run(llm, plan, *, protocol, registry=None, workspace=None):
    return AgentRunner(llm, "replan", replan_protocol=protocol).run(
        BRIEF, SEED, registry or Registry(), {}, 6,
        initial_plan=plan, max_replans=6,
        public_workspace_context=workspace,
    )


# --- protocol plumbing -------------------------------------------------------

def test_parse_patch_response():
    parsed = parse_protocol_response(_patch(2, "p3", _recover_node()))
    assert parsed["type"] == "patch"
    assert parsed["node_id"] == "p3"
    assert parsed["based_on_observation_step"] == 2
    assert parsed["node"]["tool"] == "gamma.recover"
    # required fields are fail-closed
    assert parse_protocol_response(
        json.dumps({"type": "patch", "node_id": "p3", "node": {}})
    ) is None


def test_get_agent_v2_is_replan_mode_with_patch_rules():
    v1 = get_agent("replan")
    v2 = get_agent("replan", replan_protocol="v2")
    assert v1.mode == v2.mode == "replan"
    assert v1.protocol == "v1" and v2.protocol == "v2"
    assert "patch" not in v1.response_rules
    assert "patch" in v2.response_rules
    with pytest.raises(ValueError):
        get_agent("replan", replan_protocol="v9")


def test_runner_default_protocol_is_v1():
    assert AgentRunner(ScriptedLLM([]), "replan").replan_protocol == "v1"
    assert AgentRunner(ScriptedLLM([]), "react").replan_protocol == "v1"


# --- F2: rejection repair turn ----------------------------------------------

def test_v1_rejection_gets_no_repair_turn():
    llm = RecordingLLM(["not json at all", json.dumps({"type": "continue"})])
    result = _run(llm, _read_then_write(), protocol="v1")
    assert result.protocol_violations == 1
    assert result.replan_count == 0
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "beta.write"]
    rejected = [s for s in result.steps if "replan_rejected" in s]
    assert len(rejected) == 1
    assert "attempt" not in rejected[0]
    # second LLM call was the second observation, not a repair prompt
    assert "REJECTED" not in llm.seen[1][-1]["content"]


def test_v2_rejection_offers_one_repair_turn_then_accepts():
    llm = RecordingLLM(["not json at all", _replan(1, [_recover_node()])])
    result = _run(llm, _read_then_write(), protocol="v2")
    assert result.replan_count == 1
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "gamma.recover"]
    rejected = [s for s in result.steps if "replan_rejected" in s]
    accepted = [s for s in result.steps if "replan_accepted" in s]
    assert len(rejected) == 1 and rejected[0]["attempt"] == 1
    assert rejected[0]["repair_offered"] is True
    assert len(accepted) == 1 and accepted[0]["replan_accepted"]["attempt"] == 2
    assert accepted[0]["replan_accepted"]["kind"] == "replan"
    assert accepted[0]["replan_accepted"]["trigger"] == "observation"
    repair_prompt = llm.seen[1][-1]["content"]
    assert "REPLAN REJECTED" in repair_prompt
    assert "not one valid typed JSON object" in repair_prompt


def test_v2_second_rejection_continues_on_current_plan():
    llm = RecordingLLM(["garbage", "still garbage", json.dumps({"type": "continue"})])
    result = _run(llm, _read_then_write(), protocol="v2")
    assert result.replan_count == 0
    assert result.protocol_violations == 2
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "beta.write"]
    rejected = [s for s in result.steps if "replan_rejected" in s]
    assert [s["attempt"] for s in rejected] == [1, 2]
    assert rejected[1]["repair_offered"] is False


def test_v2_limit_exceeded_gets_no_repair_turn():
    llm = RecordingLLM([
        _replan(1, [_recover_node(), _recover_node()]),
        _replan(2, [_recover_node()]),  # over the cap → rejected, no repair
        json.dumps({"type": "continue"}),
    ])
    result = AgentRunner(llm, "replan", replan_protocol="v2").run(
        BRIEF, SEED, Registry(), {}, 6, initial_plan=_read_then_write(),
        max_replans=1,
    )
    assert result.replan_count == 1
    rejected = [s for s in result.steps if "replan_rejected" in s]
    assert len(rejected) == 1
    assert "limit" in rejected[0]["error"]
    assert rejected[0]["repair_offered"] is False


# --- F3: patch op ------------------------------------------------------------

def test_v2_patch_replaces_one_unexecuted_node():
    llm = RecordingLLM([_patch(1, "p2", _recover_node())])
    result = _run(llm, _read_then_write(), protocol="v2")
    assert result.replan_count == 1
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "gamma.recover"]
    assert result.trajectory[1]["args"] == {"record_id": "runtime-only"}
    event = result.replan_events[0]
    assert event["kind"] == "patch" and event["node_id"] == "p2"


def test_v2_patch_after_acceptance_shows_normalized_ids():
    llm = RecordingLLM([
        _patch(1, "p2", {
            "kind": "call", "tool": "beta.write",
            "arguments": {"record_id": _lit("x")}, "bind": "w",
        }),
        json.dumps({"type": "continue"}),
    ])
    plan = normalize_plan(
        [
            {"kind": "call", "tool": "alpha.read",
             "arguments": {"record_id": _input("record_id")}, "bind": "r"},
            {"kind": "call", "tool": "beta.write",
             "arguments": {"record_id": _lit("y")}},
            {"kind": "call", "tool": "gamma.recover",
             "arguments": {"record_id": _lit("z")}},
        ],
        TOOLS,
    )
    result = _run(llm, plan, protocol="v2")
    assert [c["tool"] for c in result.trajectory] == [
        "alpha.read", "beta.write", "gamma.recover",
    ]
    second_prompt = llm.seen[1][-1]["content"]
    assert "REPLAN ACCEPTED" in second_prompt
    assert '"r1p1"' in second_prompt and '"r1p2"' in second_prompt


def test_v2_patch_can_target_a_node_nested_in_a_pending_branch():
    plan = normalize_plan(
        [
            {"kind": "call", "tool": "alpha.read",
             "arguments": {"record_id": _input("record_id")}, "bind": "read_result"},
            {
                "kind": "if",
                "condition": {"kind": "expression", "op": "is_present",
                              "args": [_output("read_result", "record", "id")]},
                "then": [{"kind": "call", "tool": "beta.write",
                          "arguments": {"record_id": _lit("a")}}],
                "else": [],
            },
        ],
        TOOLS,
    )
    llm = RecordingLLM([_patch(1, "p3", _recover_node())])
    result = _run(llm, plan, protocol="v2")
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "gamma.recover"]


def test_v2_patch_rejected_when_node_is_not_in_unexecuted_suffix():
    llm = RecordingLLM([
        _patch(1, "p1", _recover_node()),   # p1 already executed
        json.dumps({"type": "continue"}),   # repair turn
        json.dumps({"type": "continue"}),
    ])
    result = _run(llm, _read_then_write(), protocol="v2")
    assert result.replan_count == 0
    rejected = [s for s in result.steps if "replan_rejected" in s]
    assert len(rejected) == 1 and "p1" in rejected[0]["error"]
    assert "p2" in rejected[0]["error"]  # the message lists patchable ids
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "beta.write"]


def test_v2_patch_rejected_inside_a_loop_body():
    plan = normalize_plan(
        [
            {
                "kind": "foreach",
                "items": _lit(["a", "b"]),
                "item_bind": "item",
                "body": [{"kind": "call", "tool": "alpha.read",
                          "arguments": {"record_id": {"kind": "loop_ref",
                                                      "binding": "item",
                                                      "path": []}}}],
            },
        ],
        TOOLS,
    )
    llm = RecordingLLM([
        _patch(1, "p2", _recover_node()),
        json.dumps({"type": "continue"}),
        json.dumps({"type": "continue"}),
    ])
    result = _run(llm, plan, protocol="v2")
    rejected = [s for s in result.steps if "replan_rejected" in s]
    assert len(rejected) == 1 and "patch" in rejected[0]["error"]
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "alpha.read"]


def test_v1_treats_patch_as_wrong_type():
    llm = RecordingLLM([_patch(1, "p2", _recover_node()),
                        json.dumps({"type": "continue"})])
    result = _run(llm, _read_then_write(), protocol="v1")
    rejected = [s for s in result.steps if "replan_rejected" in s]
    assert len(rejected) == 1 and "expected continue or replan" in rejected[0]["error"]
    assert [c["tool"] for c in result.trajectory] == ["alpha.read", "beta.write"]


# --- F1: resolver errors become reviewable -----------------------------------

def _plan_with_resolver_error():
    # foreach over a string input → SymbolicResolutionError at runtime
    return normalize_plan(
        [
            {
                "kind": "foreach",
                "items": _input("record_id"),
                "item_bind": "item",
                "body": [{"kind": "call", "tool": "alpha.read",
                          "arguments": {"record_id": _lit("never")}}],
            },
        ],
        TOOLS,
    )


def test_v1_resolver_error_ends_the_row_without_review():
    result = _run(ScriptedLLM([]), _plan_with_resolver_error(), protocol="v1")
    assert result.stop_reason.startswith("plan_resolution_error:")
    assert result.trajectory == []
    assert not any("replan_review" in s or "replan_rejected" in s for s in result.steps)


def test_v2_resolver_error_is_reviewed_and_can_be_replanned():
    llm = RecordingLLM([_replan(1, [_recover_node()]),
                        json.dumps({"type": "continue"})])
    result = _run(llm, _plan_with_resolver_error(), protocol="v2")
    assert result.stop_reason == "plan_complete"
    assert [c["tool"] for c in result.trajectory] == ["gamma.recover"]
    assert result.failed_calls == 1  # the resolution failure still counts
    accepted = [s for s in result.steps if "replan_accepted" in s][0]
    assert accepted["replan_accepted"]["trigger"] == "resolution_error"
    assert any(str(s.get("error", "")).startswith("plan_resolution_error:")
               for s in result.steps)
    observation = llm.seen[0][-1]["content"]
    assert "OBSERVATION 1:" in observation and "ERROR" in observation
    assert "not array" in observation


def test_v2_resolver_error_continue_ends_the_row_like_v1():
    llm = RecordingLLM([json.dumps({"type": "continue"})])
    result = _run(llm, _plan_with_resolver_error(), protocol="v2")
    assert result.stop_reason.startswith("plan_resolution_error:")
    assert result.trajectory == []
    assert len(llm.seen) == 1


# --- F4: resource hint on error observations --------------------------------

def test_v2_error_observation_carries_resource_hint():
    llm = RecordingLLM([json.dumps({"type": "continue"})])
    result = _run(
        llm, _read_then_write(), protocol="v2",
        registry=Registry(failing={"alpha.read"}), workspace=WORKSPACE,
    )
    assert result.stop_reason.startswith("plan_tool_error:")
    prompt = llm.seen[0][-1]["content"]
    assert "AVAILABLE WORKSPACE RESOURCES" in prompt
    assert "7201" in prompt and "resource_ab78322f7955" in prompt
    assert "Email" in prompt
    assert "Patchable node ids" in prompt and "p1" in prompt and "p2" in prompt


def test_v2_success_observation_has_no_resource_hint():
    llm = RecordingLLM([json.dumps({"type": "continue"})] * 2)
    _run(llm, _read_then_write(), protocol="v2", workspace=WORKSPACE)
    assert "AVAILABLE WORKSPACE RESOURCES" not in llm.seen[0][-1]["content"]


def test_v1_error_observation_has_no_resource_hint():
    llm = RecordingLLM([json.dumps({"type": "continue"})])
    _run(
        llm, _read_then_write(), protocol="v1",
        registry=Registry(failing={"alpha.read"}), workspace=WORKSPACE,
    )
    prompt = llm.seen[0][-1]["content"]
    assert "AVAILABLE WORKSPACE RESOURCES" not in prompt
    assert "Patchable" not in prompt

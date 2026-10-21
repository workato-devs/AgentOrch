"""Unit tests for the iterative-replan (self-evolution) driver's pure parts:
feedback rendering, revision prompt, revision validation.

Run with:
  PYTHONPATH=.:verification/backends/simulated/src:verification/backends/shared/src \
    python -m pytest verification/backends/shared/src/tests/test_replan_iter.py
"""
from __future__ import annotations

import json

from experiments.replan_iter import (
    build_revision_messages,
    render_feedback,
    render_trace,
    validate_revision,
)
from task.workflow_plan import normalize_plan, plan_hash

TOOLS = {"alpha.read", "beta.write"}
CONTEXT = {
    "recipe_id": "r1",
    "system": "planner system",
    "user": "planner user prompt",
    "allowed_tools": TOOLS,
    "tool_specs": [{"name": t, "description": t, "input_schema": {"type": "object"}} for t in sorted(TOOLS)],
    "validation_input_schema": {"type": "object", "properties": {"record_id": {"type": "string"}}},
    "workspace_context": {},
}


def _plan():
    return normalize_plan(
        [{"kind": "call", "tool": "alpha.read",
          "arguments": {"record_id": {"kind": "input_ref", "path": ["record_id"]}},
          "bind": "r"}],
        TOOLS,
    )


def _ok_artifact():
    plan = _plan()
    return {"status": "ok", "plan": plan, "plan_hash": plan_hash(plan)}


def _row(task_id, steps, status="ok", stop="plan_complete", trigger=None):
    return {"task_id": task_id, "status": status, "trigger_input": trigger,
            "run": {"steps": steps, "stop_reason": stop, "failed_calls": 0}}


def test_render_trace_covers_every_step_kind_and_clips_observations():
    steps = [
        {"plan_node_id": "p1", "action": {"tool": "alpha.read", "args": {"record_id": "x"}},
         "observation": "o" * 2000},
        {"plan_node_id": "p2", "branch": "else"},
        {"plan_node_id": "p3", "foreach_index": 1},
        {"plan_node_id": "p4", "action": {"tool": "beta.write", "args": {}},
         "error": "ERROR: table 9 is not part of the seeded benchmark state"},
        {"plan_node_id": "p5", "explicit_stop": {"stop_reason": "missing", "stop_with_error": True}},
        {"plan_node_id": "p6", "return": {"ok": True}},
        {"error": "plan_resolution_error:foreach p3 resolved to dict, not array"},
    ]
    lines = render_trace({"steps": steps})
    assert lines[0].startswith("[p1] call alpha.read")
    assert "<1500 more chars>" in lines[0]
    assert lines[1] == "[p2] if -> else"
    assert "foreach item #1" in lines[2]
    assert "not part of the seeded" in lines[3]
    assert "stop error=True" in lines[4]
    assert lines[5].startswith("[p6] return")
    assert lines[6].startswith("ERROR plan_resolution_error")


def test_feedback_for_invalid_plan_is_the_validator_error_only():
    art = {"status": "invalid_plan", "error": "plan[0].tool is unavailable: foo.bar",
           "raw_response": "{...}"}
    text = render_feedback(0, art, [_row("r1__v00", [])])
    assert "REJECTED by the plan validator" in text
    assert "foo.bar" in text
    assert "variant" not in text  # nothing was executed


def test_feedback_lists_each_variant_with_trigger_and_trace_and_never_gold():
    rows = [
        _row("r1__v01", [{"plan_node_id": "p1", "action": {"tool": "alpha.read", "args": {"record_id": "b"}},
                          "observation": "{\"ok\": true}"}], trigger={"record_id": "b"}),
        _row("r1__v00", [], status="infra_error"),
    ]
    rows[0]["expect"] = {"gold": "MUST NOT LEAK"}
    rows[0]["strict_pass"] = False
    text = render_feedback(1, _ok_artifact(), rows)
    assert text.index("variant r1__v00") < text.index("variant r1__v01")  # sorted
    assert "not executed (infra_error" in text
    assert "trigger_input={\"record_id\": \"b\"}" in text
    assert "[p1] call alpha.read" in text
    assert "MUST NOT LEAK" not in text and "strict" not in text


def test_feedback_mentions_a_rejected_revision_when_plan_ran_unchanged():
    art = {**_ok_artifact(), "revision_status": "invalid_plan",
           "revision_error": "plan[1].bind duplicates binding 'r'"}
    text = render_feedback(2, art, [_row("r1__v00", [])])
    assert "previous revision was REJECTED" in text
    assert "duplicates binding" in text


def test_feedback_is_capped():
    steps = [{"plan_node_id": f"p{i}", "action": {"tool": "alpha.read", "args": {}},
              "observation": "x" * 400} for i in range(200)]
    text = render_feedback(1, _ok_artifact(), [_row("r1__v00", steps)])
    assert len(text) <= 30_000 + 40
    assert text.endswith("<feedback truncated>")


def test_revision_messages_replay_previous_plan_as_assistant_turn():
    msgs = build_revision_messages(CONTEXT, _ok_artifact(), "FEEDBACK")
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[0]["content"] == "planner user prompt"
    assert json.loads(msgs[1]["content"])["plan"][0]["tool"] == "alpha.read"
    assert msgs[2]["content"].startswith("FEEDBACK")
    assert "COMPLETE corrected WorkflowPlan" in msgs[2]["content"]
    # invalid previous plan: replay the raw response instead
    msgs = build_revision_messages(CONTEXT, {"status": "invalid_plan", "raw_response": "garbage {"}, "F")
    assert msgs[1]["content"] == "garbage {"


def test_validate_revision_accepts_valid_plan_and_flags_change():
    prev = _ok_artifact()
    revised = {"plan": [
        {"kind": "call", "tool": "alpha.read",
         "arguments": {"record_id": {"kind": "input_ref", "path": ["record_id"]}}, "bind": "r"},
        {"kind": "call", "tool": "beta.write",
         "arguments": {"record_id": {"kind": "output_ref", "binding": "r", "path": ["id"]}}},
    ]}
    art = validate_revision(json.dumps(revised), CONTEXT, round_index=1, previous=prev)
    assert art["status"] == "ok" and art["changed"] is True
    assert [n["tool"] for n in art["plan"]] == ["alpha.read", "beta.write"]
    assert art["prior_plan_hash"] == prev["plan_hash"]
    same = validate_revision(json.dumps({"plan": prev["plan"]}), CONTEXT, round_index=1, previous=prev)
    assert same["status"] == "ok" and same["changed"] is False


def test_validate_revision_is_fail_closed():
    prev = _ok_artifact()
    bad_tool = validate_revision(json.dumps({"plan": [{"kind": "call", "tool": "nope.x", "arguments": {}}]}),
                                 CONTEXT, round_index=1, previous=prev)
    assert bad_tool["status"] == "invalid_plan" and "unavailable" in bad_tool["error"]
    no_json = validate_revision("I would change step 2.", CONTEXT, round_index=1, previous=prev)
    assert no_json["status"] == "invalid_plan" and "does not contain a plan" in no_json["error"]
    truncated = validate_revision('{"plan": [{"kind": "call", "tool": "alpha.read", "arguments": {}', CONTEXT,
                                  round_index=1, previous=prev)
    assert truncated["status"] == "ok" and truncated["json_syntax_repaired"] is True

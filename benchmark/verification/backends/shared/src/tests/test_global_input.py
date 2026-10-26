"""GLOBAL+INPUT (``global_input``) information-control ablation, doc/global_input.md.

Pins the protocol invariants that make the Global -> Global+Input -> ReAct
decomposition interpretable:

* the planner prompt is the Global prompt plus ONE runtime-input section,
  rendered byte-identically to the first ReAct user turn's runtime-input text;
* without a runtime input the Global prompt is unchanged (Global rows stay
  reproducible bit-for-bit);
* the mode is a frozen-plan mode for execution and scoring, never a replan;
* per-variant plans are cached per variant, never shared, and record the
  efficiency counters the spec asks for.

Run with:
  PYTHONPATH=.:verification/backends/simulated/src:verification/backends/shared/src \
    python -m pytest verification/backends/shared/src/tests/test_global_input.py
"""
from __future__ import annotations

import json

import pytest

from metrics.plan_fidelity import evaluate_for_mode
from task.agents import AGENT_MODES, get_agent
from task.llm_client import LLMError, ScriptedLLM
from task.prompt import build_first_user_turn, runtime_input_parts
from task.workflow_plan import (
    GLOBAL_INPUT_PLANNER_PROMPT,
    PLANNER_PROMPT_VERSION,
    planner_prompts,
)

TOOLS = [
    {"name": "alpha.read", "description": "read", "input_schema": {"type": "object"}},
    {"name": "beta.write", "description": "write", "input_schema": {"type": "object"}},
]
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "request": {"type": "object", "properties": {"record_id": {"type": "string"}}},
        "execution_context": {"type": "object"},
    },
}
WORKSPACE = {"execution_context_schema": {}, "workspace_resources": [], "communication_templates": []}
RUNTIME = {
    "trigger_input": {"request": {"record_id": "rec_001"}, "context": {"actor": "U1"}},
    "execution_context": {"recipe_url": "https://example.test/r/1"},
}


def _prompts(runtime_input=None, incremental=False):
    return planner_prompts(
        objective="Read a record and write it back.",
        input_schema=INPUT_SCHEMA,
        output_schema={},
        tool_specs=TOOLS,
        workspace_context=WORKSPACE,
        incremental=incremental,
        runtime_input=runtime_input,
    )


# --------------------------------------------------------------------------
# prompt construction
# --------------------------------------------------------------------------
def test_global_prompt_is_unchanged_without_runtime_input():
    system, user = _prompts()
    assert "Concrete runtime input" not in user
    assert "Never copy a concrete runtime value" in system
    assert user.endswith('The top-level response is exactly {"plan":[]}.')


def test_global_input_prompt_adds_exactly_one_runtime_section():
    g_system, g_user = _prompts()
    system, user = _prompts(RUNTIME)
    # user prompt = Global user prompt + runtime section, nothing else touched
    head, sep, _ = user.partition("\n\n## Concrete runtime input\n")
    assert sep, "runtime-input section missing"
    assert g_user.startswith(head)
    assert g_user == head + '\nThe top-level response is exactly {"plan":[]}.'
    assert user.endswith('The top-level response is exactly {"plan":[]}.')
    assert user.count("## Concrete runtime input") == 1
    # the three protocol sentences from the spec
    assert "Generate one complete executable workflow for this runtime instance." in user
    assert "The workflow must be fully specified before execution." in user
    assert "You will not receive tool results or execution feedback while constructing it." in user
    # system prompt: only the copy-a-runtime-value clause is narrowed
    assert "Never copy a concrete runtime value" not in system
    assert "the only\nconcrete values you may use are those in the supplied runtime input" in system
    assert system.replace(
        "Never assume a tool result or invent a private identifier; the only\n"
        "concrete values you may use are those in the supplied runtime input.",
        "Never copy a concrete runtime value, assume a tool result, or invent a private\n"
        "identifier.",
    ) == g_system


def test_runtime_input_text_matches_react_first_turn_exactly():
    """Fairness check: GLOBAL+INPUT sees the runtime input in the very same
    rendering ReAct gets before its first tool call, and nothing from after."""
    _, user = _prompts(RUNTIME)
    parts = runtime_input_parts(RUNTIME)
    assert len(parts) == 2 and parts[0].startswith("TRIGGER EVENT:\n") and parts[1].startswith("EXECUTION CONTEXT:\n")
    for part in parts:
        assert part in user
    react_first = build_first_user_turn({"variant_input": RUNTIME})
    for part in parts:
        assert part in react_first
    # nothing seeded/observed leaks into the planner: only the two blocks
    section = user.split("## Concrete runtime input\n", 1)[1].split("\n\nGenerate one complete", 1)[0]
    assert section == "\n\n".join(parts)
    assert "ENVIRONMENT:" not in user  # the seeded-table card is not runtime input
    assert json.dumps(RUNTIME["trigger_input"], indent=1, sort_keys=True) in user


def test_execution_context_block_is_omitted_when_absent_like_react():
    runtime = {"trigger_input": {"request": {"record_id": "x"}}}
    _, user = _prompts(runtime)
    assert "EXECUTION CONTEXT:" not in user
    assert "EXECUTION CONTEXT:" not in build_first_user_turn({"variant_input": runtime})


def test_runtime_input_is_rejected_for_the_incremental_editor():
    with pytest.raises(ValueError):
        _prompts(RUNTIME, incremental=True)


def test_prompt_versions_are_distinct():
    assert GLOBAL_INPUT_PLANNER_PROMPT != PLANNER_PROMPT_VERSION
    assert GLOBAL_INPUT_PLANNER_PROMPT.startswith(PLANNER_PROMPT_VERSION)


# --------------------------------------------------------------------------
# mode registration and scoring route
# --------------------------------------------------------------------------
def test_global_input_is_a_frozen_plan_mode_without_replanning():
    agent = get_agent("global_input")
    assert "global_input" in AGENT_MODES
    assert agent.request_initial_plan is True
    assert agent.allow_replan is False
    # execution-time system prompt identical to Global View
    global_agent = get_agent("plan_execute")
    assert agent.system_suffix == global_agent.system_suffix
    assert agent.response_rules == global_agent.response_rules


def test_plan_fidelity_scores_global_input_against_the_reference_plan():
    reference = {"workflow_plan": {"workflow": []}}
    result = evaluate_for_mode("global_input", reference, [])
    assert isinstance(result, dict)
    with pytest.raises(Exception):
        evaluate_for_mode("global_input")  # needs both plans, like plan_execute


# --------------------------------------------------------------------------
# per-variant planning artifact (prepare_variant_plan)
# --------------------------------------------------------------------------
class RecordingLLM(ScriptedLLM):
    def __init__(self, replies, fail=False):
        super().__init__(replies, model="scripted-planner")
        self.seen = []
        self.calls = 0
        self.total_tokens = 0
        self.fail = fail
        self.temperature = 0.0

    def complete(self, system, messages):
        self.seen.append((system, [dict(m) for m in messages]))
        if self.fail:
            raise LLMError("prompt has 999999 tokens, exceeding pinned limit")
        self.calls += 1
        self.total_tokens += 7
        return super().complete(system, messages)

    def prompt_token_count(self, system, messages):
        return len(system) // 4 + sum(len(m["content"]) for m in messages) // 4


@pytest.fixture
def variant_planner(monkeypatch, tmp_path):
    """Drive prepare_variant_plan against a stubbed task description."""
    import task.run_eval as run_eval

    description = {
        "task_description": "Read a record and write it back.",
        "public_tool_surface": TOOLS,
        "public_input_schema": INPUT_SCHEMA,
        "public_output_schema": {},
        "public_execution_context_schema": {"type": "object"},
        "public_workspace_cards": [],
        "public_communication_templates": [],
        "public_package_hash": "pkg-hash",
    }
    monkeypatch.setattr(run_eval, "load_task_description", lambda recipe_id: description)
    monkeypatch.setenv("BENCHMARK_OUTPUT_DIR", str(tmp_path / "state"))

    def run(llm, variant=3, runtime=RUNTIME):
        return run_eval.prepare_variant_plan(
            "r1", variant, llm, tmp_path,
            model_id="scripted-planner", enriched_tool_docs=False, runtime_input=runtime,
        )

    return run, tmp_path


VALID_PLAN = json.dumps({"plan": [
    {"kind": "call", "tool": "alpha.read",
     "arguments": {"record_id": {"kind": "input_ref", "path": ["request", "record_id"]}},
     "bind": "read_result"},
    {"kind": "call", "tool": "beta.write",
     "arguments": {"record_id": {"kind": "output_ref", "binding": "read_result", "path": ["record", "id"]}}},
]})


def test_variant_plan_artifact_records_runtime_input_and_costs(variant_planner):
    run, root = variant_planner
    llm = RecordingLLM([VALID_PLAN])
    artifact = run(llm)
    assert artifact["status"] == "ok"
    assert artifact["planner_prompt"] == GLOBAL_INPUT_PLANNER_PROMPT
    assert artifact["variant"] == 3
    assert artifact["planner_input"]["contains_runtime_input"] is True
    assert artifact["planner_input"]["prompt_tokens"] > 0
    assert artifact["planner_input"]["prompt_chars"] > 0
    assert artifact["planner_calls"] == 1 and artifact["planner_tokens"] == 7
    assert artifact["raw_response"] == VALID_PLAN
    assert artifact["runtime_input"] == RUNTIME
    assert "variant" in artifact["cache_key_payload"]
    # exactly one planning call, whose prompt carries the runtime input
    assert len(llm.seen) == 1
    system, messages = llm.seen[0]
    assert len(messages) == 1 and "## Concrete runtime input" in messages[0]["content"]
    assert "rec_001" in messages[0]["content"]
    # cached per variant, under its own tree, never in the Global plan cache
    cached = root / "plans_global_input" / "scripted-planner" / "r1" / "variant_03.json"
    assert cached.is_file()
    assert not (root / "plans").exists()


def test_variant_plan_cache_hit_makes_no_model_call(variant_planner):
    run, _ = variant_planner
    first = run(RecordingLLM([VALID_PLAN]))
    llm = RecordingLLM([])  # any call would raise "script exhausted"
    again = run(llm)
    assert llm.seen == []
    assert again["cache_reused"] is True
    assert again["plan_hash"] == first["plan_hash"]


def test_variant_plans_are_independent_across_variants(variant_planner):
    run, _ = variant_planner
    a = run(RecordingLLM([VALID_PLAN]), variant=0, runtime=RUNTIME)
    other = {"trigger_input": {"request": {"record_id": "rec_002"}}}
    llm = RecordingLLM([VALID_PLAN])
    b = run(llm, variant=1, runtime=other)
    assert len(llm.seen) == 1, "variant 1 must not reuse variant 0's plan"
    assert a["cache_key"] != b["cache_key"]
    assert "rec_002" in llm.seen[0][1][0]["content"]
    assert "rec_001" not in llm.seen[0][1][0]["content"]


def test_invalid_plan_is_cached_and_counted_like_global(variant_planner):
    run, root = variant_planner
    artifact = run(RecordingLLM(['{"plan": [{"kind": "call", "tool": "nope.tool", "arguments": {}}]}']))
    assert artifact["status"] == "invalid_plan"
    assert artifact["plan"] is None and artifact["error"]
    assert (root / "plans_global_input" / "scripted-planner" / "r1" / "variant_03.json").is_file()


def test_transport_failure_of_the_single_call_is_cached_as_invalid_plan(variant_planner):
    run, _ = variant_planner
    artifact = run(RecordingLLM([VALID_PLAN], fail=True))
    assert artifact["status"] == "invalid_plan"
    assert artifact["error"].startswith("planning call failed")
    assert artifact["raw_response"] is None
    # resume path: cache hit, no second attempt
    llm = RecordingLLM([VALID_PLAN], fail=True)
    again = run(llm)
    assert again["cache_reused"] is True and llm.seen == []


# --------------------------------------------------------------------------
# Anthropic prompt caching (opt-in, billing-only) splits at the runtime marker
# --------------------------------------------------------------------------
def _anthropic_client(monkeypatch, cache: str):
    from task import llm_client
    monkeypatch.setenv("ANTHROPIC_PROMPT_CACHE", cache)
    monkeypatch.setattr(llm_client, "_api_key", lambda: "test-key")
    monkeypatch.setattr(llm_client, "_setting", lambda key: {"ANTHROPIC_PROMPT_CACHE": cache}.get(key))
    return llm_client.AnthropicClient("claude-opus-5")


def test_anthropic_body_is_unchanged_without_prompt_cache(monkeypatch):
    client = _anthropic_client(monkeypatch, "0")
    _, user = _prompts(RUNTIME)
    body = client._body("sys", [{"role": "user", "content": user}])
    assert body["messages"] == [{"role": "user", "content": user}]
    assert "cache_control" not in json.dumps(body)


def test_anthropic_prompt_cache_marks_the_shared_prefix_only(monkeypatch):
    client = _anthropic_client(monkeypatch, "1")
    _, user = _prompts(RUNTIME)
    body = client._body("sys", [{"role": "user", "content": user}])
    blocks = body["messages"][0]["content"]
    assert [b["type"] for b in blocks] == ["text", "text"]
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in blocks[1]
    # text is preserved exactly: prefix + tail == original prompt
    assert blocks[0]["text"] + blocks[1]["text"] == user
    assert blocks[1]["text"].startswith("\n\n## Concrete runtime input\n")
    assert "rec_001" not in blocks[0]["text"]  # runtime input is outside the cached prefix
    # a second variant of the same recipe shares the cached prefix byte-for-byte
    _, user2 = _prompts({"trigger_input": {"request": {"record_id": "rec_002"}}})
    blocks2 = client._body("sys", [{"role": "user", "content": user2}])["messages"][0]["content"]
    assert blocks2[0]["text"] == blocks[0]["text"]


def test_anthropic_prompt_cache_without_marker_caches_whole_message(monkeypatch):
    client = _anthropic_client(monkeypatch, "1")
    body = client._body("sys", [{"role": "user", "content": "plain prompt"},
                                {"role": "assistant", "content": "x"}])
    first, second = body["messages"]
    assert first["content"] == [{"type": "text", "text": "plain prompt", "cache_control": {"type": "ephemeral"}}]
    assert second == {"role": "assistant", "content": "x"}


def test_anthropic_usage_counters_accumulate(monkeypatch):
    client = _anthropic_client(monkeypatch, "1")
    client._record_usage({"usage": {"input_tokens": 10, "output_tokens": 2,
                                    "cache_read_input_tokens": 50000, "cache_creation_input_tokens": 0}})
    client._record_usage({"usage": {"input_tokens": 5, "output_tokens": 1}})
    assert client.api_usage == {"requests": 2, "input_tokens": 15, "output_tokens": 3,
                                "cache_creation_input_tokens": 0, "cache_read_input_tokens": 50000}


class ConcurrentStyleLLM(RecordingLLM):
    """Client exposing per-thread per-call counters (vLLM / Anthropic style);
    its shared totals are deliberately inflated as they are under concurrency."""

    def complete(self, system, messages):
        text = super().complete(system, messages)
        self.total_tokens += 100000  # other threads' tokens landed meanwhile
        self.calls += 15
        self.last_call_completion_tokens = 321
        self.last_call_prompt_tokens = 61000
        return text


def test_variant_plan_costs_use_per_call_counters_under_concurrency(variant_planner):
    run, _ = variant_planner
    artifact = run(ConcurrentStyleLLM([VALID_PLAN]))
    assert artifact["planner_calls"] == 1
    assert artifact["planner_tokens"] == 321
    assert artifact["planner_tokens_source"] == "per_call"
    assert artifact["planner_input"]["prompt_tokens"] == 61000


def test_variant_plan_costs_fall_back_to_client_delta_for_serial_clients(variant_planner):
    run, _ = variant_planner
    artifact = run(RecordingLLM([VALID_PLAN]))
    assert artifact["planner_tokens"] == 7 and artifact["planner_tokens_source"] == "client_delta"
    assert artifact["planner_input"]["prompt_tokens"] > 0  # from prompt_token_count()

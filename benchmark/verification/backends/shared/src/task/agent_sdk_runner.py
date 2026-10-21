"""agent_sdk eval mode: claude-agent-sdk (Claude Code as a library) drives the
benchmark ToolRegistry through an in-process MCP bridge. The SDK owns the
agentic loop and native tool calling; seeding, budget accounting, leak gating,
and scoring reuse the exact react/plan_execute machinery. The runner exposes
only benchmark tools and disables built-in coding tools."""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import threading
from typing import Any

from task.prompt import ACTION_GUIDANCE, brief_leaks, build_first_user_turn
from task.runner import RunResult, _short

SDK_SERVER_NAME = "bench"
MAX_OBS_CHARS = 100_000

# Every Claude Code built-in is blocked explicitly: allowed_tools is only an
# auto-approval list, and permission_mode="bypassPermissions" would otherwise
# auto-approve these. Filesystem/shell access would invalidate the run — gold
# answers live in output/<recipe>/variant_xx/output.json.
BUILTIN_TOOLS = [
    "Bash", "BashOutput", "KillShell", "Read", "Write", "Edit", "MultiEdit",
    "NotebookEdit", "Glob", "Grep", "WebFetch", "WebSearch", "Task", "Skill",
    "TodoWrite", "ExitPlanMode", "ListMcpResources", "ReadMcpResource",
    "ToolSearch", "AskUserQuestion", "SlashCommand", "EnterPlanMode",
]

SDK_MODE_SUFFIX = (
    "Use the provided tools to complete the task. When the task requires a "
    "final answer, call submit_answer exactly once with the answer. When the "
    "required business effect is complete, stop."
)


def mcp_tool_name(registry_name: str) -> str:
    """MCP tool names cannot contain dots; '.' -> '__' is reversible only
    while registry names never contain '__', so enforce that."""
    if "__" in registry_name:
        raise RuntimeError(f"registry tool name not mappable to MCP: {registry_name}")
    return registry_name.replace(".", "__")


def build_sdk_system_prompt(brief: dict[str, Any],
                            contract_text: str | None = None) -> str:
    """Same brief content build_system_prompt gives the API loop, minus the
    JSON tool listing (the SDK passes tool schemas natively) and minus the
    JSON-action protocol (the SDK uses native tool_use)."""
    for field in ("objective", "input_contract", "completion_criteria", "constraints"):
        if field not in brief:
            raise RuntimeError(f"task brief missing required field: {field}")
    parts = [
        "You are an automation agent. Complete the task using ONLY the provided tools.",
        f"OBJECTIVE:\n{json.dumps(brief['objective'], indent=1)}",
        f"INPUT CONTRACT:\n{json.dumps(brief['input_contract'], indent=1)}",
        f"COMPLETION CRITERIA:\n{json.dumps(brief['completion_criteria'], indent=1)}",
        f"CONSTRAINTS:\n{json.dumps(brief['constraints'], indent=1)}",
    ]
    if contract_text:
        parts.append(contract_text)
    parts += [ACTION_GUIDANCE.strip(), SDK_MODE_SUFFIX]
    return "\n\n".join(parts)


def sdk_first_turn(seed: dict[str, Any], schema_text: str | None = None) -> str:
    """Identical first user turn, with only the trailing emit-JSON instruction
    swapped — derived from build_first_user_turn so card changes stay in sync."""
    base = build_first_user_turn(seed, schema_text)
    head, _sep, _tail = base.rpartition("\n\n")
    return head + "\n\nBegin."


class _Bridge:
    """Mutable state shared between the SDK tool handlers and the runner:
    budget accounting on registry calls, failed-call count, submitted answer."""

    def __init__(self, registry, exposed: set[str], max_actions: int) -> None:
        self.registry = registry
        self.exposed = exposed
        self.max_actions = max_actions
        self.failed_calls = 0
        self.budget_hit = False
        self.final_answer: Any = None
        self.answered = False
        self._lock = threading.Lock()

    def actions_used(self) -> int:
        return len(self.registry.call_log(self.exposed))

    def execute(self, registry_name: str, args: dict[str, Any] | None) -> tuple[str, bool]:
        """Synchronous core: budget check, registry call, error-as-observation.
        query() cannot be interrupted, so past the cap every call is refused
        without executing and the runner reports stop_reason='budget'.
        The SDK dispatches parallel tool_use calls as concurrent asyncio tasks
        (each running this via asyncio.to_thread), so the budget check-then-act
        and the registry call itself are serialized under a lock to avoid a
        TOCTOU race where two calls both pass the cap check."""
        with self._lock:
            if self.actions_used() >= self.max_actions:
                self.budget_hit = True
                return "ERROR: action budget exhausted", True
            try:
                result = self.registry.call(registry_name, dict(args or {}))
            except RuntimeError as exc:
                self.failed_calls += 1
                return f"ERROR: {exc}", True
            return _short(result, MAX_OBS_CHARS), False


def _bind(bridge: _Bridge, registry_name: str):
    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        text, _ = await asyncio.to_thread(bridge.execute, registry_name, args)
        return {"content": [{"type": "text", "text": text}]}
    return handler


def make_sdk_tools(bridge: _Bridge, specs: list[dict[str, Any]]) -> list[Any]:
    from claude_agent_sdk import tool
    sdk_tools = [
        tool(mcp_tool_name(spec["name"]), spec["description"],
             spec["input_schema"])(_bind(bridge, spec["name"]))
        for spec in specs
    ]

    async def submit_answer(args: dict[str, Any]) -> dict[str, Any]:
        bridge.final_answer = args.get("answer")
        bridge.answered = True
        return {"content": [{"type": "text",
                             "text": "answer recorded; the task is complete — stop now"}]}

    sdk_tools.append(tool(
        "submit_answer",
        "Return the final answer when the task asks for one, then stop.",
        {"type": "object",
         "properties": {"answer": {"description": "the final answer value"}},
         "required": ["answer"]},
    )(submit_answer))
    return sdk_tools


def build_options(model: str, system: str, server: Any,
                  allowed: list[str], max_actions: int, cwd: str):
    from claude_agent_sdk import ClaudeAgentOptions
    return ClaudeAgentOptions(
        model=model,
        system_prompt=system,                      # full override, never the preset
        mcp_servers={SDK_SERVER_NAME: server},
        allowed_tools=list(allowed),               # auto-approval only
        # Primary defense: disables the built-in core toolset outright (MCP
        # tools from mcp_servers are unaffected). BUILTIN_TOOLS below is an
        # enumerated blocklist that chases a moving target as the CLI adds
        # new built-ins (e.g. ToolSearch) — kept as belt-and-suspenders.
        tools=[],
        disallowed_tools=list(BUILTIN_TOOLS),      # belt-and-suspenders enforcement
        setting_sources=[],                        # no user/project/local settings
        strict_mcp_config=True,                    # ignore .mcp.json / plugins
        permission_mode="bypassPermissions",
        max_turns=max_actions + 4,                 # backstop; budget is primary
        cwd=cwd,
    )


class AgentSDKRunner:
    """Drop-in replacement for AgentRunner when mode == 'agent_sdk'."""
    mode = "agent_sdk"

    def __init__(self, model: str) -> None:
        self.model = model

    def run(self, brief: dict[str, Any], seed: dict[str, Any], registry,
            expect: dict[str, Any], max_actions: int,
            schema_text: str | None = None,
            allowed_brief_values: set[str] | None = None,
            tool_families: set[str] | None = None,
            contract_text: str | None = None,
            enriched_tool_docs: bool = False) -> RunResult:
        specs = [s for s in registry.exposed_specs()
                 if not s["name"].startswith("harness.")
                 and (tool_families is None
                      or s["name"].split(".", 1)[0] in tool_families)]
        if not specs:
            raise RuntimeError(f"tool families {sorted(tool_families or set())} "
                               "expose no tools; task environment is empty")
        if enriched_tool_docs:
            from task.tool_catalog import enrich_tool_specs
            specs = enrich_tool_specs(specs)
        exposed = {s["name"] for s in specs}
        system = build_sdk_system_prompt(brief, contract_text)
        first = sdk_first_turn(seed, schema_text)
        # Leak gate — identical semantics to AgentRunner.run.
        first_lower = first.lower()
        allowed_values = {v.lower() for v in (allowed_brief_values or set())}
        brief_text = " ".join(str(v) for v in brief.values())
        leaks = [v for v in brief_leaks(brief_text, expect)
                 if v.lower() not in first_lower and v.lower() not in allowed_values]
        if leaks:
            raise RuntimeError(f"prompt leaks expect values: {leaks}")

        bridge = _Bridge(registry, exposed, max_actions)
        from claude_agent_sdk import ClaudeSDKError
        try:
            steps, stop_reason = asyncio.run(
                self._session(bridge, specs, system, first, max_actions))
        except (ClaudeSDKError, TimeoutError, ConnectionError) as exc:
            # Only SDK/CLI transport failures are campaign-survivable model
            # errors. Harness defects (bridge, MCP construction, temp-dir
            # handling) re-raise and fail the benchmark loudly
            # (benmark_rules.md reproducibility: no broad recovery).
            steps, stop_reason = [], f"llm_error:{type(exc).__name__}: {exc}"
        return RunResult(
            mode=self.mode,
            model=self.model,
            trajectory=registry.call_log(exposed),
            final_answer=bridge.final_answer,
            steps=steps,
            plan=None,
            failed_calls=bridge.failed_calls,
            stop_reason=stop_reason,
        )

    async def _session(self, bridge: _Bridge, specs: list[dict[str, Any]],
                       system: str, first: str,
                       max_actions: int) -> tuple[list[dict[str, Any]], str]:
        from claude_agent_sdk import (AssistantMessage, ResultMessage,
                                      TextBlock, ToolUseBlock,
                                      create_sdk_mcp_server, query)
        server = create_sdk_mcp_server(
            name=SDK_SERVER_NAME, tools=make_sdk_tools(bridge, specs))
        allowed = [f"mcp__{SDK_SERVER_NAME}__{mcp_tool_name(s['name'])}" for s in specs]
        allowed.append(f"mcp__{SDK_SERVER_NAME}__submit_answer")
        cwd = tempfile.mkdtemp(prefix="agent_sdk_task_")
        options = build_options(self.model, system, server, allowed, max_actions, cwd)

        steps: list[dict[str, Any]] = []
        result_msg = None
        try:
            async for message in query(prompt=first, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock) and block.text.strip():
                            steps.append({"thought": block.text})
                        elif isinstance(block, ToolUseBlock):
                            steps.append({"action": {"tool": block.name,
                                                     "args": block.input}})
                elif isinstance(message, ResultMessage):
                    result_msg = message
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

        if result_msg is not None:
            steps.append({"result_meta": {
                "total_cost_usd": result_msg.total_cost_usd,
                "num_turns": result_msg.num_turns,
                "duration_ms": result_msg.duration_ms,
                "usage": result_msg.usage,
            }})

        if result_msg is not None and result_msg.is_error:
            detail = result_msg.subtype
            if result_msg.subtype == "success":
                detail += (f" api_error_status={result_msg.api_error_status} "
                           f"errors={result_msg.errors}")
            stop_reason = f"llm_error:{detail}"
        elif bridge.answered:
            stop_reason = "answer"
        elif bridge.budget_hit:
            stop_reason = "budget"
        elif result_msg is not None and result_msg.num_turns >= max_actions + 4:
            stop_reason = "max_turns"
        else:
            stop_reason = "finish"
        return steps, stop_reason

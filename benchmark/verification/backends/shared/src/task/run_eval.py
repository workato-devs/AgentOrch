"""Eval orchestrator: seed -> registry -> agent loop -> score -> artifacts.

MUST be started fresh per process: it sets BENCHMARK_OUTPUT_DIR before
importing benchmark.* so agent-run state never touches the ground-truth
output/ tree. Ground truth is read from the REAL output dir via GT_ROOT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import traceback
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from functools import cache
from pathlib import Path
from typing import Any

from benchmark._paths import BENCHMARK_ROOT, WORKSPACE_ROOT

DATASET_ROOT = Path(
    os.environ.get("BENCHMARK_DATASET_DIR", WORKSPACE_ROOT / "dataset")
)
RECIPE_DATA_DIR = DATASET_ROOT / "input_recipes"
TASK_SPEC_DIR = DATASET_ROOT / "task_specs"
GT_ROOT = Path(
    os.environ.get("BENCHMARK_GROUND_TRUTH_DIR", BENCHMARK_ROOT / "output")
)
BRIEF_DIR = TASK_SPEC_DIR / "goal_only"
CONTRACT_DIR = TASK_SPEC_DIR / "output_contract"
TASK_DESCRIPTION_FILE = Path(
    os.environ.get(
        "BENCHMARK_TASK_DESCRIPTION_FILE",
        WORKSPACE_ROOT
        / "artifacts"
        / "task_description"
        / "redesign_pilot_10"
        / "exports"
        / "pilot_tasks.jsonl",
    )
)
TASK_DESCRIPTION_PACKAGE_DIR = (
    Path(os.environ["BENCHMARK_TASK_DESCRIPTION_PACKAGE_DIR"])
    if os.environ.get("BENCHMARK_TASK_DESCRIPTION_PACKAGE_DIR")
    else None
)
TASK_DESCRIPTION_WORKFLOW_DIR = Path(
    os.environ.get(
        "BENCHMARK_TASK_DESCRIPTION_WORKFLOW_DIR",
        WORKSPACE_ROOT / "artifacts" / "task_description" / "01_canonical_ir",
    )
)
TASK_DESCRIPTION_GROUNDTRUTH_DIR = Path(
    os.environ.get(
        "BENCHMARK_TASK_DESCRIPTION_GROUNDTRUTH_DIR",
        WORKSPACE_ROOT
        / "artifacts"
        / "task_description"
        / "redesign_pilot_10"
        / "07_groundtruth",
    )
)
TASK_DESCRIPTION_CRITIC_DIR = Path(
    os.environ.get(
        "BENCHMARK_TASK_DESCRIPTION_CRITIC_DIR",
        WORKSPACE_ROOT
        / "artifacts"
        / "task_description"
        / "redesign_pilot_10"
        / "06_critic",
    )
)
TASK_DESCRIPTION_PUBLICATION_DIR = Path(
    os.environ.get(
        "BENCHMARK_TASK_DESCRIPTION_PUBLICATION_DIR",
        WORKSPACE_ROOT
        / "artifacts"
        / "task_description"
        / "redesign_pilot_10"
        / "08_publication",
    )
)
TASK_DESCRIPTION_PILOT_MANIFEST = Path(
    os.environ.get(
        "BENCHMARK_TASK_DESCRIPTION_PILOT_MANIFEST",
        WORKSPACE_ROOT
        / "artifacts"
        / "task_description"
        / "redesign_pilot_10"
        / "manifest.json",
    )
)
EVAL_ROOT_DEFAULT = GT_ROOT / "eval_runs"
SCORING_CONTRACT_REGISTRY = Path(
    os.environ.get(
        "BENCHMARK_SCORING_CONTRACT_REGISTRY",
        WORKSPACE_ROOT / "task_description" / "config" / "scoring_contract_registry.json",
    )
)

# Seed sections -> tool family prefixes: a seeded backend is part of the
# task's environment even when the gold path never touches it.
_SEED_SECTION_FAMILIES = {
    "workato_db_table": "workato_db_table",
    "lookup_table": "lookup_table",
    "salesforce_live": "salesforce",
    "snowflake": "snowflake",
    "snowflake_live": "snowflake",
}


def _tool_families(recipe_id: str, seed: dict[str, Any]) -> set[str]:
    """The task's tool surface is RECIPE-level (one workspace per recipe):
    the union of families used by ANY variant's gold run plus any seeded
    backend. A do-nothing branch variant gets the same surface as its
    siblings — restraint with tools available is part of what is measured."""
    families: set[str] = set()
    for gold_path in sorted((GT_ROOT / recipe_id).glob("variant_*/output.json")):
        gold = json.loads(gold_path.read_text())
        for call in gold.get("tool_calls") or []:
            if call.get("tool"):
                families.add(str(call["tool"]).split(".", 1)[0])
        details = gold.get("details") or {}
        snapshot = details.get("final_snapshot") or {}
        for section, family in _SEED_SECTION_FAMILIES.items():
            if snapshot.get(section):
                families.add(family)
    for section, family in _SEED_SECTION_FAMILIES.items():
        if seed.get(section):
            families.add(family)
    families.discard("harness")  # never an agent surface
    families.discard("")
    return families

_MOCK_SNAPSHOT_TOOLS = ("harness.workato_db_table.snapshot", "harness.lookup_table.snapshot")
_LIVE_SNAPSHOT_TOOLS = {"salesforce": "harness.salesforce.snapshot",
                        "snowflake": "harness.snowflake.snapshot"}
# Sheets snapshot returns its fields at top level; wrap under a section key so
# the agent-side snapshot matches the gold outputs' `google_sheets` section.
_SHEETS_SNAPSHOT_TOOL = "harness.google_sheets.snapshot"
# Live-state hygiene (benchmark cleanup policy 'Cleanup principle'):
# benchmark-owned live records seeded/created during an eval run must not
# leak into later runs. Snapshot first, then cleanup, fail-fast on residue.
_LIVE_CLEANUP_TOOLS = {"salesforce": "harness.salesforce.cleanup",
                       "snowflake": "harness.snowflake_live.cleanup"}

# Keys that assert ground-truth VALUES on an expectation object. Targeting
# keys (table_id, lookup_table_id, match_fields, channel) narrow WHERE a check
# looks but pin no values, so they do not count.
_VALUE_KEYS = ("args_contains", "result_count", "response_contains",
               "result_contains", "created", "http_status_code",
               "text_fragments", "options_contains")
_CONTROL_ACTIONS = {"finish", "submit_answer", "stop"}
_STRUCTURAL_RETURN_TOOLS = {
    "workato_genie.workflow_return_result",
    "workato_recipe_function.return_result",
}
_FORCED_ERROR_SELECTOR_KEYS = {
    "agent_id": "agent_id",
    "board_id": "board_id",
    "channel": "channel",
    "flow_id": "flow_id",
    "list_id": "list_id",
    "lookup_table_id": "lookup_table_id",
    "object_name": "object_name",
    "project_id": "project_id",
    "sobject_name": "sobject",
    "table_id": "table_id",
    "topic_id": "topic_id",
}


def _task_description_workflow(recipe_id: str) -> dict[str, Any]:
    workflow_path = TASK_DESCRIPTION_WORKFLOW_DIR / f"{recipe_id}.json"
    if not workflow_path.is_file():
        raise RuntimeError(
            f"missing canonical task-description workflow: {workflow_path}"
        )
    artifact = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow = artifact.get("workflow_A")
    if not isinstance(workflow, dict) or not isinstance(
        workflow.get("nodes"), list
    ):
        raise RuntimeError(
            f"invalid canonical task-description workflow: {workflow_path}"
        )
    return workflow


def _tool_effect_class(
    tool: str,
    tool_specs: list[dict[str, Any]] | None,
) -> str:
    """Return the public side-effect class, with a conservative fallback."""

    for spec in tool_specs or []:
        if not isinstance(spec, dict) or str(spec.get("name") or "") != tool:
            continue
        effect = str((spec.get("side_effects") or {}).get("class") or "")
        if effect:
            return effect
    from metrics.planning import is_exploration

    return "read" if is_exploration(tool) else "unknown_write"


def _call_resource_identity(call: dict[str, Any]) -> tuple[Any, ...]:
    """Conservatively identify the state namespace touched by a public call."""

    tool = str(call.get("tool") or "")
    family = tool.split(".", 1)[0]
    args = call.get("args") or {}
    keys = (
        "sobject",
        "object_name",
        "table",
        "table_id",
        "lookup_table_id",
        "spreadsheet",
        "sheet",
        "channel",
        "recipe_id",
        "topic_id",
        "list_name",
        "name",
    )
    targets = tuple(
        (key, json.dumps(args[key], sort_keys=True, default=str))
        for key in keys
        if isinstance(args, dict) and args.get(key) not in (None, "")
    )
    return (family, *targets) if targets else (family, "__family__")


def _task_description_runtime_order_spec(
    recipe_id: str,
    task_id: str,
    gold_calls: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Build active dependency/hazard edges for order diagnostics.

    Canonical recipe order is primary. This graph reports whether a different
    serialization at least preserves data/control, resource-hazard, and public
    temporal dependencies; it cannot make that serialization correct.
    """

    match = re.search(r"(?:variant_|__v)(\d+)$", str(task_id))
    if match is None:
        raise RuntimeError(f"cannot recover variant id from task id {task_id!r}")
    variant_id = match.group(1).zfill(2)
    bundle_path = TASK_DESCRIPTION_GROUNDTRUTH_DIR / f"{recipe_id}.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    variant = next(
        (
            item
            for item in bundle.get("variants") or []
            if str(item.get("variant_id") or "").zfill(2) == variant_id
        ),
        None,
    )
    if not isinstance(variant, dict):
        raise RuntimeError(
            f"missing task-description active trace for {recipe_id}/{variant_id}"
        )
    active_events = [
        event
        for event in (variant.get("active_trace") or {}).get("events") or []
        if isinstance(event, dict)
        and event.get("event_type") == "tool_call"
        and str(event.get("tool") or "") not in _STRUCTURAL_RETURN_TOOLS
    ]
    source_mapping = {
        str(plan_id): str(source_id)
        for plan_id, source_id in (bundle.get("private_source_mapping") or {}).items()
    }

    # ActiveTrace and raw gold align by construction.  A small number of
    # audited public projections add a business call not present in the raw
    # recipe; align those by tool subsequence and leave the synthetic slot
    # unmapped.  Equal-length connector projections align positionally even
    # when their public tool identity is intentionally normalized.
    sources: list[str | None] = [None] * len(gold_calls)
    if len(active_events) == len(gold_calls):
        for index, event in enumerate(active_events):
            sources[index] = source_mapping.get(str(event.get("plan_node_ref") or ""))
    else:
        cursor = 0
        for event in active_events:
            event_tool = str(event.get("tool") or "")
            found = next(
                (
                    index
                    for index in range(cursor, len(gold_calls))
                    if str(gold_calls[index].get("tool") or "") == event_tool
                ),
                None,
            )
            if found is None:
                continue
            sources[found] = source_mapping.get(
                str(event.get("plan_node_ref") or "")
            )
            cursor = found + 1

    indexes = {
        str(row.get("node_id") or ""): row
        for row in (bundle.get("derived_indexes") or {}).get("indexes") or []
        if isinstance(row, dict) and row.get("node_id")
    }
    predecessors: dict[str, set[str]] = {node_id: set() for node_id in indexes}
    for node_id, row in indexes.items():
        dependencies = row.get("direct_dependencies") or {}
        predecessors[node_id].update(
            str(value) for value in dependencies.get("data") or []
        )
        for value in dependencies.get("control") or []:
            dependency = str(value)
            dependency_row = indexes.get(dependency) or {}
            # A direct model-action -> model-action control link is normally
            # just authoring serialization. Structural controllers remain
            # relevant because they encode active branch/try/loop dependence.
            if not (
                row.get("runtime_class") == "model_action"
                and dependency_row.get("runtime_class") == "model_action"
            ):
                predecessors[node_id].add(dependency)

    ancestor_cache: dict[str, set[str]] = {}

    def ancestors(node_id: str, visiting: set[str] | None = None) -> set[str]:
        if node_id in ancestor_cache:
            return ancestor_cache[node_id]
        visiting = set(visiting or ())
        if node_id in visiting:
            return set()
        visiting.add(node_id)
        result: set[str] = set()
        for predecessor in predecessors.get(node_id, set()):
            result.add(predecessor)
            result.update(ancestors(predecessor, visiting))
        ancestor_cache[node_id] = result
        return result

    edge_reasons: dict[tuple[int, int], set[str]] = {}

    def add_edge(before: int, after: int, reason: str) -> None:
        if before == after:
            return
        if before > after:
            raise RuntimeError(
                "runtime order dependency points backward in the active gold "
                f"trace: {before} -> {after} ({reason})"
            )
        edge_reasons.setdefault((before, after), set()).add(reason)

    positions_by_source: dict[str, list[int]] = {}
    for index, source in enumerate(sources):
        if source:
            positions_by_source.setdefault(source, []).append(index)

    def add_source_precedence(before_source: str, after_source: str, reason: str) -> None:
        before_positions = positions_by_source.get(before_source, [])
        after_positions = positions_by_source.get(after_source, [])
        if not before_positions or not after_positions:
            return
        before_loops = tuple((indexes.get(before_source) or {}).get("loop_stack") or [])
        after_loops = tuple((indexes.get(after_source) or {}).get("loop_stack") or [])
        for after in after_positions:
            eligible = [before for before in before_positions if before < after]
            if not eligible:
                continue
            if before_loops and before_loops != after_loops:
                for before in eligible:
                    add_edge(before, after, reason)
            else:
                add_edge(max(eligible), after, reason)

    active_sources = set(positions_by_source)
    for after_source in sorted(active_sources):
        for before_source in sorted(ancestors(after_source) & active_sources):
            add_source_precedence(
                before_source,
                after_source,
                "data_or_structural_control_dependency",
            )

    temporal_requirement_ids: list[str] = []
    critic_path = TASK_DESCRIPTION_CRITIC_DIR / f"{recipe_id}.json"
    if critic_path.is_file():
        critic = json.loads(critic_path.read_text(encoding="utf-8"))
        taskspec = critic.get("accepted_taskspec") or {}
        execution_index = {
            node_id: int(row.get("execution_index") or 0)
            for node_id, row in indexes.items()
        }
        for requirement in taskspec.get("business_requirements") or []:
            if not isinstance(requirement, dict):
                continue
            text = str(requirement.get("text") or "")
            is_temporal = requirement.get("kind") == "temporal_business_constraint"
            is_temporal = is_temporal or bool(
                re.search(r"\b(?:after|before|then|only once)\b", text, re.I)
            )
            evidence = sorted(
                {
                    str(node_id)
                    for node_id in requirement.get("evidence_node_ids") or []
                    if str(node_id) in active_sources
                },
                key=lambda node_id: (execution_index.get(node_id, 0), node_id),
            )
            if not is_temporal or len(evidence) < 2:
                continue
            temporal_requirement_ids.append(
                str(requirement.get("requirement_id") or "")
            )
            for before_source, after_source in zip(evidence, evidence[1:]):
                add_source_precedence(
                    before_source,
                    after_source,
                    "public_temporal_business_requirement",
                )

    for before, left in enumerate(gold_calls):
        left_effect = _tool_effect_class(str(left.get("tool") or ""), tool_specs)
        left_resource = _call_resource_identity(left)
        for after in range(before + 1, len(gold_calls)):
            right = gold_calls[after]
            right_effect = _tool_effect_class(
                str(right.get("tool") or ""), tool_specs
            )
            if (
                left_resource == _call_resource_identity(right)
                and (left_effect != "read" or right_effect != "read")
            ):
                add_edge(before, after, "same_resource_read_write_hazard")

    for index, source in enumerate(sources):
        if source is not None:
            continue
        for other in range(len(gold_calls)):
            if other < index:
                add_edge(other, index, "unmapped_public_projection")
            elif index < other:
                add_edge(index, other, "unmapped_public_projection")

    edges = [
        {
            "before_gold_index": before,
            "after_gold_index": after,
            "reasons": sorted(reasons),
        }
        for (before, after), reasons in sorted(edge_reasons.items())
    ]
    graph: dict[int, set[int]] = {
        index: set() for index in range(len(gold_calls))
    }
    for before, after in edge_reasons:
        graph[before].add(after)

    def reachable(start: int) -> set[int]:
        seen: set[int] = set()
        pending = list(graph[start])
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            pending.extend(graph[node] - seen)
        return seen

    reachability = {
        index: reachable(index) for index in range(len(gold_calls))
    }
    possible_pairs = len(gold_calls) * max(len(gold_calls) - 1, 0) // 2
    comparable_pairs = sum(
        int(after in reachability[before])
        for before in range(len(gold_calls))
        for after in range(before + 1, len(gold_calls))
    )
    payload = {
        "schema_version": "agentorch-active-runtime-order-spec-v1",
        "recipe_id": recipe_id,
        "variant_id": variant_id,
        "gold_call_count": len(gold_calls),
        "mapped_call_count": sum(source is not None for source in sources),
        "dependency_edges": edges,
        "dependency_edge_count": len(edges),
        "dependency_reachable_pair_count": comparable_pairs,
        "multiple_topological_orders": comparable_pairs < possible_pairs,
        "public_temporal_requirement_ids": sorted(temporal_requirement_ids),
    }
    payload["spec_hash"] = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return payload


def _public_task_description_runtime_input(
    recipe_id: str,
    variant_input: dict[str, Any],
) -> dict[str, Any]:
    """Use the pipeline's one canonical private-to-public runtime projection."""

    workspace_path = str(WORKSPACE_ROOT)
    if workspace_path not in sys.path:
        sys.path.insert(0, workspace_path)
    from task_description._internal.shared.public_execution_context import (
        canonical_public_runtime_input,
    )

    return canonical_public_runtime_input(
        variant_input,
        _task_description_workflow(recipe_id),
    )


def _task_description_outcome_calls(
    recipe_id: str,
    calls: list[dict[str, Any]],
    slack_channel_override: str,
) -> list[dict[str, Any]]:
    """Undo the live-isolation Slack alias for public semantic scoring.

    Raw execution deliberately routes configured Slack channels to the safe
    evaluator override. A task-description agent correctly addresses the
    configured public channel, while its in-process connector remains isolated.
    Canonicalize both sides of outcome comparison: when the task has exactly
    one published channel, translate only the exact override token back to that
    destination. Ambiguous multi-channel tasks remain unchanged and fail closed.
    """

    override = str(slack_channel_override or "")
    channels = (
        {
            str(card.get("public_id") or "")
            for card in load_task_description(recipe_id).get(
                "public_workspace_cards"
            )
            or []
            if isinstance(card, dict)
            and card.get("resource_type") == "channel"
            and card.get("public_id")
        }
        if override
        else set()
    )
    normalized = deepcopy(calls)
    if override and len(channels) == 1:
        configured_channel = next(iter(channels))
        for call in normalized:
            if not str(call.get("tool") or "").startswith(("slack.", "slack_bot.")):
                continue
            args = call.get("args")
            if isinstance(args, dict) and str(args.get("channel") or "") == override:
                args["channel"] = configured_channel

    if recipe_id in {"120700492", "92726378"}:
        from benchmark.argument_semantics import canonical_slack_home_args

        def strip_anon(value: Any) -> Any:
            if isinstance(value, dict):
                return {key: strip_anon(item) for key, item in value.items()}
            if isinstance(value, list):
                return [strip_anon(item) for item in value]
            if isinstance(value, str):
                return value.replace("<anon>", "").replace("</anon>", "")
            return value

        for call in normalized:
            if call.get("tool") != "slack_bot.open_bot_app_home":
                continue
            intent_args = strip_anon(canonical_slack_home_args(call.get("args") or {}))
            intent = intent_args.get("view_intent") if isinstance(intent_args, dict) else None
            if not isinstance(intent, dict):
                continue
            if recipe_id == "120700492":
                intent["controls"] = [
                    {"label": control.get("label")}
                    for control in intent.get("controls") or []
                    if isinstance(control, dict) and control.get("label")
                ]
                intent["images"] = [
                    {"present": True} for _image in intent.get("images") or []
                ]
            else:
                # The stored recipe contains a decorative private image that
                # the published task neither requests nor describes.
                intent.pop("images", None)
            call["args"] = intent_args
    if recipe_id == "130740169":
        for call in normalized:
            if call.get("tool") != "slack.update_blocks_by_block_id":
                continue
            args = call.get("args") or {}
            message = args.get("message_json") or {}
            updates = args.get("blocks_to_update") or []
            visible_parts: list[str] = []
            for block in updates:
                if not isinstance(block, dict):
                    continue
                if block.get("section_text") not in (None, ""):
                    visible_parts.append(str(block["section_text"]))
                for element in block.get("elements") or []:
                    if isinstance(element, dict) and element.get("text") not in (
                        None,
                        "",
                    ):
                        visible_parts.append(str(element["text"]))
            call["tool"] = "slack.post_message"
            call["args"] = {
                "channel": message.get("channel"),
                "text": "\n".join(visible_parts),
                "thread_ts": message.get("thread_ts", ""),
                "ts": message.get("ts", ""),
            }
    return normalized


def _task_description_business_calls(
    calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove raw authoring-layer recipe returns from business tool traces."""

    return [
        deepcopy(call)
        for call in calls
        if str(call.get("tool") or "") not in _STRUCTURAL_RETURN_TOOLS
    ]


def _gold_structural_return(
    gold: dict[str, Any], recipe_id: str = ""
) -> dict[str, Any]:
    """Recover the active recipe return hidden by canonical trace projection."""

    calls = [
        call
        for call in (gold.get("details") or {}).get("structural_terminal_calls") or []
        if isinstance(call, dict)
        and str(call.get("tool") or "") in _STRUCTURAL_RETURN_TOOLS
    ]
    if len(calls) > 1:
        raise RuntimeError("ground truth has multiple active structural returns")
    if not calls:
        return {"present": False, "value": None}
    args = calls[0].get("args") or {}
    if not isinstance(args, dict) or "result" not in args:
        raise RuntimeError("ground-truth structural return has no result argument")
    value = deepcopy(args["result"])
    if recipe_id in {"124154692", "124154895"} and isinstance(value, dict):
        # The published business contract names this caller field ``Message``;
        # the legacy recipe-function transport used lowercase ``message``.
        if "message" in value and "Message" not in value:
            value["Message"] = value.pop("message")
    if recipe_id == "130740169" and isinstance(value, dict):
        if "message_id_to_update" in value and "Message ID to update" not in value:
            value["Message ID to update"] = value.pop("message_id_to_update")
    return {"present": True, "value": value}


def _synthetic_return_call(value: Any) -> dict[str, Any]:
    """Represent plan-level return uniformly for semantic outcome scoring."""

    from metrics.outcome import synthetic_return_call

    return synthetic_return_call(value)


def _task_description_public_gold_projection(
    recipe_id: str,
    variant_input: dict[str, Any],
    gold_calls: list[dict[str, Any]],
    gold_snapshot: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Project legacy traces onto the published business-task surface.

    Most Workato runtime helpers are private implementation details and stay
    outside public scoring. Two selected tasks expose logging as a business
    effect, however. Their historical persisted traces predate that public
    projection, so provide the public gold action/state without changing the
    frozen task-description package or the strict raw-trace diagnostic.
    """

    calls = deepcopy(gold_calls)
    snapshot = deepcopy(gold_snapshot)
    trigger = variant_input.get("trigger_input") or {}
    expect = variant_input.get("expect") or {}
    if recipe_id == "105071555" and not any(
        call.get("tool") == "lookup_table.add_entry" for call in calls
    ):
        request = trigger.get("request") or {}
        parameters = {
            "Affected user": request.get("email_address"),
            "Destination profile": request.get("new_profile"),
        }
        calls.insert(0, {
            "tool": "lookup_table.add_entry",
            "args": {
                "lookup_table_id": "3629882",
                "parameters": parameters,
            },
            "result": {"ok": True},
        })
        tables = snapshot.setdefault("lookup_table", {}).setdefault("tables", {})
        rows = tables.setdefault("3629882", [])
        rows.append({**deepcopy(parameters), "_created_by": "agent"})
    if recipe_id == "88674737" and not any(
        call.get("tool") == "workato_runtime.log_message" for call in calls
    ):
        message = expect.get("log_message")
        calls.append({
            "tool": "workato_runtime.log_message",
            "args": {"message": message},
            "result": {"ok": True, "message": message},
        })
    if recipe_id == "91033108":
        schedule_search = next((
            call
            for call in calls
            if call.get("tool") == "lookup_table.search_entries"
            and str((call.get("args") or {}).get("lookup_table_id")) == "3357223"
        ), None)
        entries = (
            (schedule_search.get("result") or {}).get("entries")
            if isinstance(schedule_search, dict)
            else []
        ) or []
        required_ids = [
            entry.get("id", entry.get("_row_id"))
            for entry in entries
            if isinstance(entry, dict)
            and entry.get("id", entry.get("_row_id")) is not None
        ]
        deleted_ids = {
            (call.get("args") or {}).get("id")
            for call in calls
            if call.get("tool") == "lookup_table.delete_entry"
            and str((call.get("args") or {}).get("lookup_table_id")) == "3357223"
        }
        for entry_id in required_ids:
            if entry_id in deleted_ids:
                continue
            calls.append({
                "tool": "lookup_table.delete_entry",
                "args": {
                    "lookup_table_id": "3357223",
                    "id": entry_id,
                    "ignore_not_found": "false",
                },
                "result": {
                    "ok": True,
                    "lookup_table_id": "3357223",
                    "id": entry_id,
                    "deleted": True,
                },
            })
        if required_ids:
            tables = snapshot.setdefault("lookup_table", {}).setdefault("tables", {})
            rows = tables.get("3357223") or []
            required_text = {str(value) for value in required_ids}
            tables["3357223"] = [
                row
                for row in rows
                if str(row.get("id", row.get("_row_id"))) not in required_text
            ]
    if recipe_id == "121898837":
        table_id = "26786"
        search = next((
            call
            for call in calls
            if call.get("tool") == "workato_db_table.get_records"
            and str((call.get("args") or {}).get("table_id")) == table_id
        ), None)
        records = (
            (search.get("result") or {}).get("records")
            if isinstance(search, dict)
            else []
        ) or []

        def record_id(row: dict[str, Any]) -> Any:
            for key in (
                "record_id",
                "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
                "id",
                "_row_id",
            ):
                if row.get(key) not in (None, ""):
                    return row[key]
            return None

        required_ids = [
            record_id(row)
            for row in records[:100]
            if isinstance(row, dict) and record_id(row) is not None
        ]
        deleted_ids = {
            (call.get("args") or {}).get("record_id")
            for call in calls
            if call.get("tool") == "workato_db_table.delete_record"
            and str((call.get("args") or {}).get("table_id")) == table_id
        }
        for value in required_ids:
            if value in deleted_ids:
                continue
            calls.append({
                "tool": "workato_db_table.delete_record",
                "args": {"table_id": table_id, "record_id": value},
                "result": {
                    "ok": True,
                    "table_id": table_id,
                    "record_id": value,
                },
            })
        if required_ids:
            tables = snapshot.setdefault("workato_db_table", {}).setdefault(
                "tables", {}
            )
            required_text = {str(value) for value in required_ids}
            tables[table_id] = [
                row
                for row in tables.get(table_id) or []
                if str(record_id(row)) not in required_text
            ]
    if recipe_id in {"131710998", "131716751"}:
        table_id = "58840" if recipe_id == "131710998" else "58841"
        search = next((
            call
            for call in calls
            if call.get("tool") == "workato_db_table.get_records"
            and str((call.get("args") or {}).get("table_id")) == table_id
        ), None)
        records = (
            (search.get("result") or {}).get("records")
            if isinstance(search, dict)
            else []
        ) or []
        existing_updates = [
            call
            for call in calls
            if call.get("tool") == "workato_db_table.update_record"
            and str((call.get("args") or {}).get("table_id")) == table_id
        ]
        if existing_updates:
            template_record = deepcopy(
                (existing_updates[0].get("args") or {}).get("record") or {}
            )
            updated_ids = {
                str((call.get("args") or {}).get("record_id"))
                for call in existing_updates
            }
            for row in records[:100]:
                if not isinstance(row, dict):
                    continue
                value = next((
                    row.get(key)
                    for key in (
                        "record_id",
                        "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
                        "id",
                        "_row_id",
                    )
                    if row.get(key) not in (None, "")
                ), None)
                if value is None or str(value) in updated_ids:
                    continue
                calls.append({
                    "tool": "workato_db_table.update_record",
                    "args": {
                        "table_id": table_id,
                        "record_id": value,
                        "record": deepcopy(template_record),
                    },
                    "result": {
                        "ok": True,
                        "table_id": table_id,
                        "record_id": value,
                    },
                })
                for state_row in (
                    snapshot.setdefault("workato_db_table", {})
                    .setdefault("tables", {})
                    .get(table_id) or []
                ):
                    state_id = next((
                        state_row.get(key)
                        for key in (
                            "record_id",
                            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
                            "id",
                            "_row_id",
                        )
                        if state_row.get(key) not in (None, "")
                    ), None)
                    if str(state_id) == str(value):
                        state_row.update(deepcopy(template_record))
                        state_row["_modified_by"] = "agent"
                        break
        if recipe_id == "131716751":
            parameters = trigger.get("parameters") or {}
            if str(parameters.get("CSM_Approval") or "").casefold() == "approved":
                reason_field = "460b9c17_a8c9_4692_9aab_081e64450f9e"
                updated_ids = set()
                for call in calls:
                    if call.get("tool") != "workato_db_table.update_record":
                        continue
                    args = call.get("args") or {}
                    if str(args.get("table_id")) != table_id:
                        continue
                    updated_ids.add(str(args.get("record_id")))
                    record = args.get("record")
                    if isinstance(record, dict):
                        record[reason_field] = ""
                for state_row in (
                    snapshot.setdefault("workato_db_table", {})
                    .setdefault("tables", {})
                    .get(table_id) or []
                ):
                    state_id = next((
                        state_row.get(key)
                        for key in (
                            "record_id",
                            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
                            "id",
                            "_row_id",
                        )
                        if state_row.get(key) not in (None, "")
                    ), None)
                    if str(state_id) in updated_ids:
                        state_row[reason_field] = ""
    if recipe_id in {"124154692", "124154895"}:
        table_id = "31777" if recipe_id == "124154692" else "35019"
        updated_by_field = "60f204f5_30e0_45df_a049_2965b01857e7"
        for call in calls:
            if call.get("tool") not in {
                "workato_db_table.add_record",
                "workato_db_table.update_record",
            }:
                continue
            if str((call.get("args") or {}).get("table_id")) != table_id:
                continue
            record = (call.get("args") or {}).get("record")
            if isinstance(record, dict):
                record.pop(updated_by_field, None)
        initial_rows = (
            (((variant_input.get("seed") or {}).get("workato_db_table") or {})
             .get("tables") or {}).get(table_id)
            or []
        )
        initial_by_id = {
            str(row.get("11fbe9a6_a16d_4d7e_86ea_afe42ec03005")): row
            for row in initial_rows
            if isinstance(row, dict)
            and row.get("11fbe9a6_a16d_4d7e_86ea_afe42ec03005") not in (None, "")
        }
        final_rows = (
            snapshot.setdefault("workato_db_table", {})
            .setdefault("tables", {})
            .get(table_id) or []
        )
        for row in final_rows:
            if not isinstance(row, dict):
                continue
            initial = initial_by_id.get(str(
                row.get("11fbe9a6_a16d_4d7e_86ea_afe42ec03005")
            ))
            if isinstance(initial, dict) and updated_by_field in initial:
                row[updated_by_field] = initial[updated_by_field]
            else:
                row.pop(updated_by_field, None)
    return calls, snapshot


def _runtime_reference_rebindings(
    gold: dict[str, Any],
    seed: dict[str, Any],
) -> dict[str, str]:
    """Map live-reference values in stored gold to this isolated episode.

    The mapping is joined strictly by private seed token (for example
    ``$ACCT_ID``), never by guessing ID shapes or model-visible text. This
    keeps correct trigger/result bindings scoreable when the live reference
    run and deterministic evaluator provision different connector IDs.
    """

    prior_by_token: dict[str, str] = {}
    for call in (gold.get("details") or {}).get("seed_harness_tool_calls") or []:
        if not isinstance(call, dict):
            continue
        result = call.get("result") or {}
        state = result.get("state") or {}
        refs = state.get("refs") or {}
        for token, value in refs.items() if isinstance(refs, dict) else []:
            if str(token).startswith("$") and value not in (None, ""):
                prior_by_token[str(token)] = str(value)

    current_by_token: dict[str, str] = {}
    for key, value in seed.items():
        if not str(key).endswith("_ref_tokens") or not isinstance(value, dict):
            continue
        for token, resolved in value.items():
            if str(token).startswith("$") and resolved not in (None, ""):
                current_by_token[str(token)] = str(resolved)

    replacements: dict[str, str] = {}
    for token in sorted(set(prior_by_token) & set(current_by_token)):
        before = prior_by_token[token]
        after = current_by_token[token]
        existing = replacements.get(before)
        if existing is not None and existing != after:
            raise RuntimeError(
                "one stored live reference maps to multiple current values: "
                f"{token}"
            )
        if before != after:
            replacements[before] = after
    return replacements


def _replace_runtime_reference_values(
    value: Any,
    replacements: dict[str, str],
) -> Any:
    """Recursively replace private provisioned values in scorer-side gold."""

    ordered = sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    )
    if isinstance(value, dict):
        return {
            key: _replace_runtime_reference_values(item, replacements)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_runtime_reference_values(item, replacements)
            for item in value
        ]
    if isinstance(value, str):
        for before, after in ordered:
            value = value.replace(before, after)
    return value


def _public_output_boolean_argument_paths(
    public_output_schema: dict[str, Any] | None,
) -> set[tuple[str, ...]]:
    """Shared with the public scorer; see metrics.outcome for the contract."""

    from metrics.outcome import public_output_boolean_argument_paths

    return public_output_boolean_argument_paths(public_output_schema)


@cache
def _declared_argument_slots(
    recipe_id: str,
    tool: str,
    comparison: str,
) -> tuple[str, ...]:
    """Return argument slots delegated to one audited semantic comparator.

    The task-description quality gate records recipe-specific equivalence
    classes in a single registry. Runtime scoring must consume the same
    declarations; otherwise a publication-approved encoding can still be
    rejected by an older literal/query comparator.
    """

    if not recipe_id or not SCORING_CONTRACT_REGISTRY.is_file():
        return ()
    registry = json.loads(SCORING_CONTRACT_REGISTRY.read_text(encoding="utf-8"))
    recipes = registry.get("recipes") or {}
    recipe_contract = recipes.get(str(recipe_id)) or {}
    equivalences = recipe_contract.get("slot_equivalences") or {}
    prefix = f"{tool}.arguments."
    slots = []
    for path, declaration in equivalences.items():
        if (
            str(path).startswith(prefix)
            and isinstance(declaration, dict)
            and declaration.get("comparison") == comparison
        ):
            slot = str(path)[len(prefix):]
            # The v1 registry defines direct argument slots. Fail closed for
            # an unsupported nested declaration instead of silently widening
            # comparison beyond the reviewed contract.
            if slot and "." not in slot:
                slots.append(slot)
    return tuple(sorted(set(slots)))


def _call_result_count(call: dict[str, Any]) -> int | None:
    result = call.get("result")
    if not isinstance(result, dict) or result.get("ok") is not True:
        return None
    for key in ("count", "list_size", "totalSize"):
        value = result.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    for key in ("records", "rows", "entries"):
        value = result.get(key)
        if isinstance(value, list):
            return len(value)
    return None


def _declared_result_semantics_match(
    expected_call: dict[str, Any],
    actual_call: dict[str, Any],
) -> bool:
    """Compare the observable selected-result evidence named by registry v1.

    Equal cardinality alone is not enough: two queries can return one wholly
    different record.  When both connector results expose row collections,
    compare their semantic row multisets.  Count-only results retain the
    conservative cardinality fallback.
    """

    def result_rows(call: dict[str, Any]) -> list[Any] | None:
        result = call.get("result")
        if not isinstance(result, dict) or result.get("ok") is not True:
            return None
        for key in ("records", "rows", "entries", "items"):
            value = result.get(key)
            if isinstance(value, list):
                return value
        metadata = {
            "count",
            "list_size",
            "totalSize",
            "ok",
            "query",
            "filters",
            "limit",
            "offset",
            "parameters",
            "sql",
            "sobject",
        }
        candidates = [
            value
            for key, value in result.items()
            if key not in metadata and isinstance(value, list)
        ]
        return candidates[0] if len(candidates) == 1 else None

    def canonical_result_value(value: Any, *, salesforce: bool) -> Any:
        if isinstance(value, list):
            return [
                canonical_result_value(item, salesforce=salesforce)
                for item in value
            ]
        if not isinstance(value, dict):
            return value
        # Salesforce stamps simulator-created records at execution time.  The
        # selected business record (including Id and business fields) is the
        # semantic evidence; these audit timestamps are not part of query
        # selection.  Preserve every other field so equal counts with a
        # different record still fail.
        volatile = {
            "CreatedDate",
            "LastModifiedDate",
            "SystemModstamp",
        } if salesforce else set()
        return {
            str(key): canonical_result_value(item, salesforce=salesforce)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in volatile
        }

    def row_multiset(rows: list[Any], *, salesforce: bool) -> Counter[str]:
        return Counter(
            json.dumps(
                canonical_result_value(row, salesforce=salesforce),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for row in rows
        )

    expected_count = _call_result_count(expected_call)
    actual_count = _call_result_count(actual_call)
    if expected_count is None or actual_count != expected_count:
        return False
    expected_rows = result_rows(expected_call)
    actual_rows = result_rows(actual_call)
    if expected_rows is None or actual_rows is None:
        return True
    salesforce = str(expected_call.get("tool") or "").startswith("salesforce.")
    return row_multiset(actual_rows, salesforce=salesforce) == row_multiset(
        expected_rows, salesforce=salesforce
    )


def _declared_execution_semantics_match(
    tool: str,
    expected_snapshot: dict[str, Any] | None,
    actual_snapshot: dict[str, Any] | None,
) -> bool:
    """Compare the backend state named by an execution-equivalence contract."""

    if not isinstance(expected_snapshot, dict) or not isinstance(actual_snapshot, dict):
        return False
    family = str(tool or "").split(".", 1)[0]
    if family == "snowflake":
        expected = (expected_snapshot.get("snowflake") or {}).get("tables")
        actual = (actual_snapshot.get("snowflake") or {}).get("tables")
        return isinstance(expected, dict) and actual == expected
    # No other execution-equivalence family is declared in registry v1. Fail
    # closed instead of treating unrelated whole-workspace equality as proof.
    return False


def _declared_statement_semantics_match(
    tool: str,
    expected_call: dict[str, Any],
    actual_call: dict[str, Any],
    expected_snapshot: dict[str, Any] | None,
    actual_snapshot: dict[str, Any] | None,
) -> bool:
    """Select result or state equivalence from the gold SQL statement kind.

    A recipe can legitimately use ``run_custom_sql`` for both SELECT and
    mutating statements.  A recipe-level slot declaration must therefore not
    weaken reads to state-only comparison or writes to result-only comparison.
    """

    expected_sql = str((expected_call.get("args") or {}).get("sql") or "")
    if re.match(r"^\s*(?:SELECT|WITH)\b", expected_sql, flags=re.IGNORECASE):
        return _declared_result_semantics_match(expected_call, actual_call)
    return _declared_execution_semantics_match(
        tool,
        expected_snapshot,
        actual_snapshot,
    )


def _representation_exact_equal(tool: str, actual: Any, expected: Any) -> bool:
    """Compare JSON arguments after representation-only canonicalization.

    The shared boundary canonicalizes object serialization and query lexical
    representation while preserving every structural token and JSON type. It
    also removes only tool-contract-declared transport injection. It never
    applies result/state equivalence, numeric coercion, or recipe-specific
    slot equivalence.
    """

    from task_description._internal.shared.exact_trace_normalization import (
        exact_arguments_equal,
    )

    return exact_arguments_equal(tool, actual, expected)


_QUERY_SEMANTIC_ARGUMENTS: dict[str, frozenset[str]] = {
    "salesforce.search_records": frozenset({"query", "filters", "limit"}),
    "snowflake.search_rows_sql": frozenset(
        {"sql", "parameters", "limit", "offset"}
    ),
    "snowflake.run_custom_sql": frozenset({"sql", "parameters"}),
}


def _query_connector_semantics_match(
    tool: str,
    expected_call: dict[str, Any],
    actual_call: dict[str, Any],
    expected_snapshot: dict[str, Any] | None,
    actual_snapshot: dict[str, Any] | None,
) -> bool:
    """Compare connector queries by their observable result or state.

    Query text is an implementation detail of the Salesforce and Snowflake
    connectors.  Non-query arguments (for example the Salesforce object) stay
    canonical-exact.  Read queries must return the same row multiset; mutating
    custom SQL must leave the same Snowflake table state.
    """

    semantic_keys = _QUERY_SEMANTIC_ARGUMENTS.get(tool)
    if semantic_keys is None:
        return False
    expected_args = expected_call.get("args") or {}
    actual_args = actual_call.get("args") or {}
    if not isinstance(expected_args, dict) or not isinstance(actual_args, dict):
        return False
    query_key = "query" if tool == "salesforce.search_records" else "sql"
    if query_key not in expected_args or query_key not in actual_args:
        return False
    expected_non_query = {
        key: value for key, value in expected_args.items() if key not in semantic_keys
    }
    actual_non_query = {
        key: value for key, value in actual_args.items() if key not in semantic_keys
    }
    if not _representation_exact_equal(
        tool,
        actual_non_query,
        expected_non_query,
    ):
        return False
    if tool in {"salesforce.search_records", "snowflake.search_rows_sql"}:
        return _declared_result_semantics_match(expected_call, actual_call)
    return _declared_statement_semantics_match(
        tool,
        expected_call,
        actual_call,
        expected_snapshot,
        actual_snapshot,
    )


def _runtime_orchestration_components(
    gold_calls: list[dict[str, Any]],
    agent_calls: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    *,
    evaluation_time: str,
    recipe_id: str = "",
    gold_snapshot: dict[str, Any] | None = None,
    agent_snapshot: dict[str, Any] | None = None,
    expected_failure_tool: str | None = None,
    boolean_paths: set[tuple[str, ...]] | None = None,
    required_order_edges: list[tuple[int, int]] | None = None,
    tool_specs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score observable orchestration axes against the authoritative trace.

    Primary correctness keeps tool identity/count/order and non-query
    connector arguments exact. Salesforce SOQL and Snowflake SQL surfaces are
    compared by observable result semantics for reads and final backend state
    for writes. Dependency-DAG order, extra-read tolerance, and other typed
    argument rewrites remain diagnostics only.
    """

    from benchmark.argument_semantics import (
        compare_argument_full,
        compare_argument_subset,
    )

    ignored_primary_tools = _STRUCTURAL_RETURN_TOOLS
    indexed_gold_calls = [
        (index, call)
        for index, call in enumerate(gold_calls)
        if str(call.get("tool") or "") not in ignored_primary_tools
    ]
    indexed_agent_calls = [
        (index, call)
        for index, call in enumerate(agent_calls)
        if str(call.get("tool") or "") not in ignored_primary_tools
    ]
    scored_gold_calls = [call for _index, call in indexed_gold_calls]
    scored_agent_calls = [call for _index, call in indexed_agent_calls]
    expected_tools = [str(call.get("tool") or "") for call in scored_gold_calls]
    actual_tools = [str(call.get("tool") or "") for call in scored_agent_calls]
    exact_selection_ok = Counter(expected_tools) == Counter(actual_tools)
    required_multiset_ok = not (Counter(expected_tools) - Counter(actual_tools))
    failed_tool_attempts = [
        step
        for step in steps
        if isinstance(step, dict)
        and isinstance(step.get("action"), dict)
        and step.get("action", {}).get("tool") not in {
            None, "", "finish", "submit_answer", "stop"
        }
        and str(step.get("action", {}).get("tool") or "")
        not in ignored_primary_tools
        and "error" in step
    ]
    failed_read_attempts = [
        step
        for step in failed_tool_attempts
        if _tool_effect_class(
            str(step.get("action", {}).get("tool") or ""), tool_specs
        )
        == "read"
    ]
    unexpected_failed_attempts = [
        step
        for step in failed_tool_attempts
        if str(step.get("action", {}).get("tool") or "")
        != str(expected_failure_tool or "")
        and _tool_effect_class(
            str(step.get("action", {}).get("tool") or ""), tool_specs
        )
        != "read"
    ]
    unexpected_failed_attempts_exact = [
        step
        for step in failed_tool_attempts
        if str(step.get("action", {}).get("tool") or "")
        != str(expected_failure_tool or "")
    ]

    def compare_pair(
        gold_index: int,
        agent_index: int,
    ) -> dict[str, Any]:
        expected = scored_gold_calls[gold_index]
        actual = scored_agent_calls[agent_index]
        expected_tool = str(expected.get("tool") or "")
        actual_tool = str(actual.get("tool") or "")
        if expected_tool != actual_tool:
            return {
                "index": gold_index,
                "gold_index": indexed_gold_calls[gold_index][0],
                "agent_index": indexed_agent_calls[agent_index][0],
                "tool": actual_tool,
                "required_ok": False,
                "required_raw_ok": False,
                "required_mode": "tool_mismatch",
                "ok": False,
                "raw_ok": False,
                "mode": "tool_mismatch",
            }
        expected_args = expected.get("args") or {}
        actual_args = actual.get("args") or {}
        required = compare_argument_subset(
            expected_tool,
            actual_args,
            expected_args,
            evaluation_time=evaluation_time,
            boolean_paths=boolean_paths,
        )
        full = compare_argument_full(
            expected_tool,
            actual_args,
            expected_args,
            evaluation_time=evaluation_time,
            boolean_paths=boolean_paths,
        )
        result_semantic_slots = _declared_argument_slots(
            recipe_id,
            expected_tool,
            "result_semantics",
        )
        execution_semantic_slots = _declared_argument_slots(
            recipe_id,
            expected_tool,
            "execution_equivalence",
        )
        statement_semantic_slots = _declared_argument_slots(
            recipe_id,
            expected_tool,
            "statement_semantics",
        )
        declared_slots = tuple(sorted(
            set(result_semantic_slots)
            | set(execution_semantic_slots)
            | set(statement_semantic_slots)
        ))
        if declared_slots:
            original_required_semantic_ok = bool(required["semantic_ok"])
            original_full_semantic_ok = bool(full["semantic_ok"])
            remaining_expected = {
                key: value
                for key, value in expected_args.items()
                if key not in declared_slots
            }
            remaining_actual = {
                key: value
                for key, value in actual_args.items()
                if key not in declared_slots
            }
            remaining_required = compare_argument_subset(
                expected_tool,
                remaining_actual,
                remaining_expected,
                evaluation_time=evaluation_time,
                boolean_paths=boolean_paths,
            )
            remaining_full = compare_argument_full(
                expected_tool,
                remaining_actual,
                remaining_expected,
                evaluation_time=evaluation_time,
                boolean_paths=boolean_paths,
            )
            declared_semantics_ok = (
                not result_semantic_slots
                or _declared_result_semantics_match(expected, actual)
            ) and (
                not execution_semantic_slots
                or _declared_execution_semantics_match(
                    expected_tool,
                    gold_snapshot,
                    agent_snapshot,
                )
            ) and (
                not statement_semantic_slots
                or _declared_statement_semantics_match(
                    expected_tool,
                    expected,
                    actual,
                    gold_snapshot,
                    agent_snapshot,
                )
            )
            declared_required_ok = bool(
                declared_semantics_ok and remaining_required["semantic_ok"]
            )
            declared_full_ok = bool(
                declared_semantics_ok and remaining_full["semantic_ok"]
            )
            # A declared result/state equivalence is an alternative legal
            # encoding path, never an extra hurdle for a call whose arguments
            # already match the public/gold semantics directly. This also
            # keeps exact scripted controls invariant to volatile connector
            # metadata such as record creation timestamps.
            required["semantic_ok"] = bool(
                original_required_semantic_ok or declared_required_ok
            )
            full["semantic_ok"] = bool(
                original_full_semantic_ok or declared_full_ok
            )
            mode_labels = []
            if result_semantic_slots:
                mode_labels.append(
                    "result:" + ",".join(result_semantic_slots)
                )
            if execution_semantic_slots:
                mode_labels.append(
                    "execution:" + ",".join(execution_semantic_slots)
                )
            if statement_semantic_slots:
                mode_labels.append(
                    "statement:" + ",".join(statement_semantic_slots)
                )
            slot_label = ";".join(mode_labels)
            if not original_required_semantic_ok:
                required["mode"] = (
                    f"declared_semantics[{slot_label}]"
                    if declared_required_ok
                    else "mismatch"
                )
            if not original_full_semantic_ok:
                full["mode"] = (
                    f"declared_semantics[{slot_label}]"
                    if declared_full_ok
                    else "mismatch"
                )
        canonical_exact_ok = _representation_exact_equal(
            expected_tool,
            actual_args,
            expected_args,
        )
        query_semantic_ok = _query_connector_semantics_match(
            expected_tool,
            expected,
            actual,
            gold_snapshot,
            agent_snapshot,
        )
        primary_ok = bool(canonical_exact_ok or query_semantic_ok)
        query_semantic_tool = expected_tool in _QUERY_SEMANTIC_ARGUMENTS
        required_primary_ok = (
            primary_ok if query_semantic_tool else bool(required["raw_ok"])
        )
        required_primary_mode = (
            (
                "canonical_exact"
                if canonical_exact_ok
                else "query_result_or_state_semantics"
                if query_semantic_ok
                else "mismatch"
            )
            if query_semantic_tool
            else "raw_subset"
            if required["raw_ok"]
            else "mismatch"
        )
        semantic_required_ok = bool(
            required["semantic_ok"] or query_semantic_ok
        )
        semantic_full_ok = bool(full["semantic_ok"] or query_semantic_ok)
        semantic_mode = (
            full["mode"]
            if full["semantic_ok"]
            else "query_result_or_state_semantics"
            if query_semantic_ok
            else full["mode"]
        )
        return {
            "index": gold_index,
            "gold_index": indexed_gold_calls[gold_index][0],
            "agent_index": indexed_agent_calls[agent_index][0],
            "tool": expected_tool,
            # Query-bearing connectors use result/state equivalence as their
            # primary query comparison. All other argument rewrites remain
            # diagnostics.
            "required_ok": required_primary_ok,
            "required_raw_ok": bool(required["raw_ok"]),
            "required_mode": required_primary_mode,
            "ok": primary_ok,
            "raw_ok": canonical_exact_ok,
            "mode": (
                "canonical_exact"
                if canonical_exact_ok
                else "query_result_or_state_semantics"
                if query_semantic_ok
                else "mismatch"
            ),
            "query_semantic_ok": query_semantic_ok,
            "semantic_required_ok": semantic_required_ok,
            "semantic_required_mode": (
                required["mode"]
                if required["semantic_ok"]
                else "query_result_or_state_semantics"
                if query_semantic_ok
                else required["mode"]
            ),
            "semantic_ok": semantic_full_ok,
            "semantic_mode": semantic_mode,
            "declared_result_semantic_slots": list(result_semantic_slots),
            "declared_execution_semantic_slots": list(
                execution_semantic_slots
            ),
            "declared_statement_semantic_slots": list(
                statement_semantic_slots
            ),
        }

    pair_checks: dict[tuple[int, int], dict[str, Any]] = {}
    gold_by_tool: dict[str, list[int]] = {}
    agent_by_tool: dict[str, list[int]] = {}
    for index, tool in enumerate(expected_tools):
        gold_by_tool.setdefault(tool, []).append(index)
    for index, tool in enumerate(actual_tools):
        agent_by_tool.setdefault(tool, []).append(index)

    matched_gold_to_agent: dict[int, int] = {}
    for tool, gold_indices in gold_by_tool.items():
        agent_indices = agent_by_tool.get(tool, [])
        adjacency: dict[int, list[int]] = {}
        for gold_index in gold_indices:
            candidates: list[tuple[tuple[int, int, int, int], int]] = []
            for agent_index in agent_indices:
                check = compare_pair(gold_index, agent_index)
                pair_checks[(gold_index, agent_index)] = check
                if check["required_ok"]:
                    rank = (
                        -int(check["ok"]),
                        -int(check["required_raw_ok"]),
                        abs(gold_index - agent_index),
                        agent_index,
                    )
                    candidates.append((rank, agent_index))
            adjacency[gold_index] = [
                agent_index for _rank, agent_index in sorted(candidates)
            ]

        matched_agent_to_gold: dict[int, int] = {}

        def augment(gold_index: int, seen: set[int]) -> bool:
            for agent_index in adjacency.get(gold_index, []):
                if agent_index in seen:
                    continue
                seen.add(agent_index)
                prior = matched_agent_to_gold.get(agent_index)
                if prior is None or augment(prior, seen):
                    matched_agent_to_gold[agent_index] = gold_index
                    return True
            return False

        for gold_index in sorted(
            gold_indices,
            key=lambda value: (len(adjacency.get(value, [])), value),
        ):
            augment(gold_index, set())
        for agent_index, gold_index in matched_agent_to_gold.items():
            matched_gold_to_agent[gold_index] = agent_index

        # Preserve a detailed failed argument comparison when the required
        # multiset exists but no semantically passing assignment does.
        unused_agents = [
            index
            for index in agent_indices
            if index not in matched_agent_to_gold
        ]
        for gold_index in gold_indices:
            if gold_index in matched_gold_to_agent or not unused_agents:
                continue
            agent_index = min(
                unused_agents,
                key=lambda value: (abs(gold_index - value), value),
            )
            unused_agents.remove(agent_index)
            matched_gold_to_agent[gold_index] = agent_index

    argument_checks: list[dict[str, Any]] = []
    for gold_index in range(len(scored_gold_calls)):
        agent_index = matched_gold_to_agent.get(gold_index)
        if agent_index is None:
            argument_checks.append({
                "index": gold_index,
                "gold_index": indexed_gold_calls[gold_index][0],
                "agent_index": None,
                "tool": expected_tools[gold_index],
                "required_ok": False,
                "required_raw_ok": False,
                "required_mode": "missing_required_call",
                "ok": False,
                "raw_ok": False,
                "mode": "missing_required_call",
                "declared_result_semantic_slots": [],
                "declared_execution_semantic_slots": [],
                "declared_statement_semantic_slots": [],
            })
            continue
        argument_checks.append(
            pair_checks.get((gold_index, agent_index))
            or compare_pair(gold_index, agent_index)
        )

    assigned_agent_indices = set(matched_gold_to_agent.values())
    extra_agent_indices = [
        index
        for index in range(len(scored_agent_calls))
        if index not in assigned_agent_indices
    ]
    extra_read_indices = [
        index
        for index in extra_agent_indices
        if _tool_effect_class(actual_tools[index], tool_specs) == "read"
    ]
    extra_write_indices = [
        index for index in extra_agent_indices if index not in extra_read_indices
    ]
    # Exact tool identity and count are primary.  Extra reads/writes and a
    # missing gold call all fail; the relaxed multiset signal remains below as
    # a diagnostic.
    selection_ok = exact_selection_ok

    original_gold_to_scored = {
        original_index: scored_index
        for scored_index, (original_index, _call) in enumerate(indexed_gold_calls)
    }
    if required_order_edges is None:
        scored_order_edges = [
            (before, after)
            for before in range(len(scored_gold_calls))
            for after in range(before + 1, len(scored_gold_calls))
        ]
        order_mode = "exact_fallback"
    else:
        scored_order_edges = sorted({
            (
                original_gold_to_scored[before],
                original_gold_to_scored[after],
            )
            for before, after in required_order_edges
            if before in original_gold_to_scored
            and after in original_gold_to_scored
        })
        order_mode = "dependency_dag"
    order_violations = [
        {
            "before_gold_index": indexed_gold_calls[before][0],
            "after_gold_index": indexed_gold_calls[after][0],
            "before_agent_index": (
                indexed_agent_calls[matched_gold_to_agent[before]][0]
                if before in matched_gold_to_agent
                else None
            ),
            "after_agent_index": (
                indexed_agent_calls[matched_gold_to_agent[after]][0]
                if after in matched_gold_to_agent
                else None
            ),
        }
        for before, after in scored_order_edges
        if before not in matched_gold_to_agent
        or after not in matched_gold_to_agent
        or matched_gold_to_agent[before] >= matched_gold_to_agent[after]
    ]
    dependency_order_ok = (
        len(matched_gold_to_agent) == len(scored_gold_calls)
        and not order_violations
    )
    order_ok = actual_tools == expected_tools
    required_in_agent_order = [
        gold_index
        for gold_index, _agent_index in sorted(
            matched_gold_to_agent.items(), key=lambda item: item[1]
        )
    ]
    exact_required_order_ok = required_in_agent_order == list(
        range(len(scored_gold_calls))
    )
    execution_ok = (
        selection_ok
        and order_ok
        and not unexpected_failed_attempts_exact
    )

    arguments_checked = len(matched_gold_to_agent) == len(scored_gold_calls)
    required_arguments_ok = (
        arguments_checked
        and len(argument_checks) == len(scored_gold_calls)
        and all(check["required_ok"] for check in argument_checks)
    )
    required_raw_arguments_ok = (
        arguments_checked
        and len(argument_checks) == len(scored_gold_calls)
        and all(check["required_raw_ok"] for check in argument_checks)
    )
    arguments_ok = (
        arguments_checked
        and len(argument_checks) == len(scored_gold_calls)
        and all(check["ok"] for check in argument_checks)
    )
    raw_arguments_ok = (
        arguments_checked
        and len(argument_checks) == len(scored_gold_calls)
        and all(check["raw_ok"] for check in argument_checks)
    )
    # For one active variant, the exact call sequence is the observable branch
    # and loop path. Static condition expressions remain recipe-level fidelity.
    condition_path_ok = actual_tools == expected_tools
    count = len(argument_checks)
    efficiency_denominator = max(len(scored_gold_calls), 1)
    orchestration_action_count_ratio = (
        len(scored_agent_calls) / efficiency_denominator
    )
    return {
        "tool_selection_checked": True,
        "tool_selection_pass": selection_ok,
        "tool_selection_check_count": 1,
        "tool_selection_passed_check_count": int(selection_ok),
        "tool_selection_exact_pass": exact_selection_ok,
        "tool_selection_semantic_pass": (
            required_multiset_ok and not extra_write_indices
        ),
        "tool_selection_required_multiset_pass": required_multiset_ok,
        "tool_selection_extra_read_count": len(extra_read_indices),
        "tool_selection_extra_write_count": len(extra_write_indices),
        "tool_selection_extra_read_tools": [
            actual_tools[index] for index in extra_read_indices
        ],
        "tool_selection_extra_write_tools": [
            actual_tools[index] for index in extra_write_indices
        ],
        "tool_order_checked": True,
        "tool_order_pass": order_ok,
        "tool_order_check_count": 1,
        "tool_order_passed_check_count": int(order_ok),
        "tool_order_mode": "canonical_exact",
        "tool_order_exact_pass": exact_required_order_ok,
        "tool_trace_exact_pass": actual_tools == expected_tools,
        "tool_order_dependency_mode": order_mode,
        "tool_order_dependency_pass": dependency_order_ok,
        "tool_order_dependency_edge_count": len(scored_order_edges),
        "tool_order_violations": order_violations,
        "tool_execution_success_checked": True,
        "tool_execution_success_pass": execution_ok,
        "tool_execution_success_check_count": max(len(scored_gold_calls), 1),
        "tool_execution_success_passed_check_count": (
            max(len(scored_gold_calls), 1)
            if execution_ok
            else max(0, len(scored_gold_calls) - len(unexpected_failed_attempts))
        ),
        "tool_argument_full_checked": arguments_checked,
        "tool_argument_full_pass": arguments_ok if arguments_checked else None,
        "tool_argument_full_check_count": count,
        "tool_argument_full_passed_check_count": sum(
            int(check["ok"]) for check in argument_checks
        ),
        "tool_argument_full_raw_checked": arguments_checked,
        "tool_argument_full_raw_pass": raw_arguments_ok if arguments_checked else None,
        "tool_argument_full_raw_check_count": count,
        "tool_argument_full_raw_passed_check_count": sum(
            int(check["raw_ok"]) for check in argument_checks
        ),
        "tool_argument_required_checked": arguments_checked,
        "tool_argument_required_pass": (
            required_arguments_ok if arguments_checked else None
        ),
        "tool_argument_required_check_count": count,
        "tool_argument_required_passed_check_count": sum(
            int(check["required_ok"]) for check in argument_checks
        ),
        "tool_argument_required_raw_checked": arguments_checked,
        "tool_argument_required_raw_pass": (
            required_raw_arguments_ok if arguments_checked else None
        ),
        "tool_argument_required_raw_check_count": count,
        "tool_argument_required_raw_passed_check_count": sum(
            int(check["required_raw_ok"]) for check in argument_checks
        ),
        "tool_argument_full_semantic_pass": (
            all(check.get("semantic_ok") is True for check in argument_checks)
            if arguments_checked
            else None
        ),
        "tool_argument_required_semantic_pass": (
            all(
                check.get("semantic_required_ok") is True
                for check in argument_checks
            )
            if arguments_checked
            else None
        ),
        "condition_path_checked": True,
        "condition_path_pass": condition_path_ok,
        "condition_path_check_count": 1,
        "condition_path_passed_check_count": int(condition_path_ok),
        "tool_argument_full_details": argument_checks,
        "failed_tool_attempt_count": len(failed_tool_attempts),
        "failed_read_attempt_count": len(failed_read_attempts),
        "unexpected_failed_tool_attempt_count": len(unexpected_failed_attempts),
        "unexpected_failed_tool_attempt_exact_count": len(
            unexpected_failed_attempts_exact
        ),
        # Efficiency remains diagnostic after exact trace correctness has
        # already rejected any extra action.
        "orchestration_action_count_ratio": round(
            orchestration_action_count_ratio, 4
        ),
        "orchestration_efficiency_within_2x": (
            len(scored_agent_calls) <= 2 * efficiency_denominator
        ),
    }


def _primary_strict_verdict(
    task_source: str,
    *,
    legacy_strict_pass: bool,
    canonical_trace_pass: bool,
) -> bool:
    """Select the authoritative strict verdict for the task source."""

    return (
        bool(canonical_trace_pass)
        if task_source == "task_description"
        else bool(legacy_strict_pass)
    )


def _attach_task_description_forced_error(
    seed: dict[str, Any],
    recipe_id: str,
) -> None:
    """Map a private raw-step fault to the corresponding public tool call.

    Gold replay raises ``force_action_error`` before a raw Workato action.
    Task-description agents execute canonical public tools instead, so the
    evaluator must privately translate that raw step id without exposing the
    fault or its target in the prompt.  A stable identity selector wins over
    occurrence order when one tool appears multiple times in the workflow.
    """

    forced = seed.get("force_action_error")
    if not isinstance(forced, dict):
        return
    if isinstance(seed.get("force_tool_error"), dict):
        return
    source_as = str(forced.get("step_as") or "")
    workflow = _task_description_workflow(recipe_id)
    nodes = [
        item for item in workflow.get("nodes") or [] if isinstance(item, dict)
    ]
    target = next(
        (item for item in nodes if str(item.get("source_as") or "") == source_as),
        None,
    )
    tool = str((target or {}).get("benchmark_tool") or "")
    if not tool:
        raise RuntimeError(
            f"cannot map forced raw step {source_as!r} for recipe {recipe_id} "
            "to a model-visible tool"
        )
    same_tool_nodes = [
        item for item in nodes if str(item.get("benchmark_tool") or "") == tool
    ]
    occurrence = next(
        (
            index
            for index, item in enumerate(same_tool_nodes, 1)
            if str(item.get("source_as") or "") == source_as
        ),
        None,
    )
    if occurrence is None:
        raise RuntimeError(
            f"forced raw step {source_as!r} is absent from the {tool} sequence"
        )
    mapped: dict[str, Any] = {
        "tool": tool,
        "error": str(forced.get("error") or "simulated connector failure"),
        "occurrence_index": occurrence,
    }
    configured = target.get("configured_arguments") or {}
    selector = {
        public_key: configured[raw_key]
        for raw_key, public_key in _FORCED_ERROR_SELECTOR_KEYS.items()
        if raw_key in configured
        and configured[raw_key] not in (None, "")
        and not str(configured[raw_key]).startswith(("=", "#{"))
    }
    if selector:
        other_selectors = []
        for item in same_tool_nodes:
            if item is target:
                continue
            other = item.get("configured_arguments") or {}
            other_selectors.append(
                {
                    public_key: other[raw_key]
                    for raw_key, public_key in _FORCED_ERROR_SELECTOR_KEYS.items()
                    if raw_key in other
                    and other[raw_key] not in (None, "")
                    and not str(other[raw_key]).startswith(("=", "#{"))
                }
            )
        if selector not in other_selectors:
            mapped["args_contains"] = selector
    seed["force_tool_error"] = mapped


def attempted_tool_names(steps: list[dict[str, Any]]) -> list[str]:
    """Return every parsed non-control tool attempt, successful or not."""

    return [
        name
        for step in steps
        if (
            name := str((step.get("action") or {}).get("tool") or "")
        )
        and name not in _CONTROL_ACTIONS
    ]


def _value_checked(expect: dict[str, Any], n_expected_tools: int) -> bool:
    """True only when EVERY expected call carries a value-asserting
    expectation object (zero-call variants are trivially value-checked)."""
    items = expect.get("tool_expectations") or []
    if len(items) != n_expected_tools:
        return False
    return all(isinstance(item, dict) and any(key in item for key in _VALUE_KEYS)
               for item in items)


def _ensure_isolation(eval_root: Path) -> None:
    if "benchmark.config" in sys.modules:
        import benchmark.config as config
        if Path(config.OUTPUT_DIR) == GT_ROOT:
            raise RuntimeError("benchmark.config imported before isolation; "
                               "start run_eval in a fresh process")
        return
    # never clobber an explicit caller-provided isolation dir (tests set one)
    os.environ.setdefault("BENCHMARK_OUTPUT_DIR", str(eval_root / "_state_root"))


def load_brief(recipe_id: str, brief_dir: Path | None = None) -> dict[str, Any]:
    path = (brief_dir or BRIEF_DIR) / f"{recipe_id}.json"
    if not path.exists():
        raise RuntimeError(f"missing goal-only brief: {path}")
    brief = json.loads(path.read_text())
    if not isinstance(brief, dict):
        raise RuntimeError(f"brief must be a JSON object: {path}")
    return brief


_TASK_DESCRIPTIONS: dict[str, dict[str, Any]] | None = None


def _hydrate_accepted_task_description(
    row: dict[str, Any],
) -> dict[str, Any]:
    """Join a compact accepted-corpus row to its hash-bound Stage-8 package.

    The generation corpus intentionally stores description/provenance once in
    its accepted index and keeps the large 64-tool contract in the canonical
    per-recipe publication.  Evaluation must consume both.  Flat standalone
    exports remain supported by returning rows that already contain a public
    tool surface unchanged.
    """

    if row.get("public_tool_surface"):
        return row
    recipe_id = str(row.get("recipe_id") or "")
    publication_path = TASK_DESCRIPTION_PUBLICATION_DIR / f"{recipe_id}.json"
    if not publication_path.is_file():
        # A minimal test/standalone row can deliberately omit the broader
        # package when only description_brief is under test.
        if row.get("schema_version") != "agentorch-accepted-task-description-v1":
            return row
        raise RuntimeError(
            f"accepted task description {recipe_id} has no Stage-8 publication: "
            f"{publication_path}"
        )
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    package = publication.get("public_planning_package")
    if not isinstance(package, dict):
        raise RuntimeError(f"invalid Stage-8 publication: {publication_path}")
    mismatches: list[str] = []
    if str(publication.get("recipe_id") or "") != recipe_id:
        mismatches.append("publication recipe_id")
    if str(package.get("recipe_id") or "") != recipe_id:
        mismatches.append("package recipe_id")
    if package.get("task_description") != row.get("task_description"):
        mismatches.append("task_description")
    if package.get("task_description_hash") != row.get("task_description_hash"):
        mismatches.append("task_description_hash")
    current_context_hash = row.get("current_public_context_hash")
    if current_context_hash and package.get("public_context_hash") != current_context_hash:
        mismatches.append("current_public_context_hash")
    accepted_taskspec_hash = row.get("accepted_taskspec_hash")
    if accepted_taskspec_hash and (
        (publication.get("lineage") or {}).get("accepted_taskspec_hash")
        != accepted_taskspec_hash
    ):
        mismatches.append("accepted_taskspec_hash")
    if mismatches:
        raise RuntimeError(
            f"accepted task description {recipe_id} does not match its "
            f"Stage-8 publication: {', '.join(mismatches)}"
        )
    critic = publication.get("critic")
    if not isinstance(critic, dict):
        raise RuntimeError(f"publication {recipe_id} has no critic verdict")
    return {
        **row,
        **package,
        "critic": critic,
        "lineage": publication.get("lineage") or row.get("lineage") or {},
        "publication_hash": publication.get("publication_hash"),
    }


def load_task_description(recipe_id: str) -> dict[str, Any]:
    """Load one critic-approved portable task description by recipe id."""

    global _TASK_DESCRIPTIONS
    if TASK_DESCRIPTION_PACKAGE_DIR is not None:
        package_path = (
            TASK_DESCRIPTION_PACKAGE_DIR / str(recipe_id) / "PUBLIC_PACKAGE.json"
        )
        if not package_path.is_file():
            raise RuntimeError(
                f"missing public task-description package: {package_path}"
            )
        row = json.loads(package_path.read_text(encoding="utf-8"))
        if not isinstance(row, dict):
            raise RuntimeError(f"invalid public task-description package: {package_path}")
    else:
        row = None
    if _TASK_DESCRIPTIONS is None:
        if row is not None:
            _TASK_DESCRIPTIONS = {}
        elif not TASK_DESCRIPTION_FILE.is_file():
            raise RuntimeError(
                f"missing task-description export: {TASK_DESCRIPTION_FILE}"
            )
        else:
            rows: dict[str, dict[str, Any]] = {}
            for line_number, line in enumerate(
                TASK_DESCRIPTION_FILE.read_text(encoding="utf-8").splitlines(), 1
            ):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict) or not value.get("recipe_id"):
                    raise RuntimeError(
                        f"invalid task-description row {line_number}: "
                        f"{TASK_DESCRIPTION_FILE}"
                    )
                row_id = str(value["recipe_id"])
                if row_id in rows:
                    raise RuntimeError(f"duplicate task-description recipe {row_id}")
                rows[row_id] = _hydrate_accepted_task_description(value)
            _TASK_DESCRIPTIONS = rows
    if row is None:
        row = _TASK_DESCRIPTIONS.get(str(recipe_id))
    if row is None:
        raise RuntimeError(f"missing task description for recipe {recipe_id}")
    task = row.get("task_description")
    critic = row.get("critic") or {}
    if (
        not isinstance(task, str)
        or not task.strip()
        or task != task.strip()
        or critic.get("accepted") is not True
        or critic.get("structured_output_valid") is not True
    ):
        raise RuntimeError(
            f"task description for recipe {recipe_id} is not current and accepted"
        )
    import hashlib
    if row.get("task_description_hash") != hashlib.sha256(
        task.encode("utf-8")
    ).hexdigest():
        raise RuntimeError(f"task-description hash mismatch for recipe {recipe_id}")
    return row


def description_brief(recipe_id: str) -> dict[str, Any]:
    """Wrap the portable description in the runner's structured brief shape."""

    row = load_task_description(recipe_id)
    return {
        "objective": row["task_description"],
        "input_contract": [
            "The TRIGGER EVENT is the complete caller/event payload available "
            "for this run.",
            "The ENVIRONMENT and SCHEMA cards describe available state without "
            "revealing hidden row values.",
        ],
        "completion_criteria": [
            "Achieve every business effect and caller-visible response stated "
            "in the task description.",
            "Stop after the required final state or terminal response is complete.",
        ],
        "constraints": [
            "Choose tools from the broad workspace catalog; many are distractors.",
            "Ground every identifier and value in the task, trigger, schema, or "
            "a prior tool observation.",
            "Avoid speculative reads, unrelated mutations, and duplicate messages.",
        ],
        "task_description_lineage": {
            "hash": row["task_description_hash"],
            "critic_model": (row.get("critic") or {}).get("model"),
        },
    }


def description_tool_families(recipe_id: str) -> set[str]:
    """Return the variant-blind software scope published with a TaskSpec."""

    surface = load_task_description(recipe_id).get("public_tool_surface") or []
    names = {
        str(card.get("name") or "")
        for card in surface
        if isinstance(card, dict)
    }
    families = {name.split(".", 1)[0] for name in names if "." in name}
    if not families:
        raise RuntimeError(f"task description {recipe_id} has no public tool surface")
    return families


def description_schema_card(recipe_id: str) -> str:
    """Render only the public, variant-invariant package context."""

    row = load_task_description(recipe_id)
    payload = {
        "input_schema": row.get("public_input_schema") or {},
        "execution_context_schema": row.get("public_execution_context_schema") or {},
        "control_actions": row.get("public_control_actions") or [],
        "workspace_resources": row.get("public_workspace_cards") or [],
        "communication_templates": row.get("public_communication_templates") or [],
    }
    return "PUBLIC WORKFLOW CONTEXT:\n" + json.dumps(payload, indent=1, sort_keys=True)


def initial_plan_context(
    recipe_id: str,
    llm,
    eval_root: Path,
    *,
    model_id: str,
    enriched_tool_docs: bool,
    runtime_input: dict[str, Any] | None = None,
    variant: int | None = None,
) -> dict[str, Any]:
    """Build the exact prompt, validation context, and cache key for a plan.

    Without ``runtime_input`` this is the variant-blind Global View request
    (one plan per recipe, cached under ``plans/``). With ``runtime_input`` and
    ``variant`` it is the GLOBAL+INPUT request for one runtime variant: the
    identical tool surface, workspace context, validation schema and decoding,
    plus that variant's concrete public runtime input in the prompt, cached
    under ``plans_global_input/<model>/<recipe>/variant_XX.json``.
    """

    from task.workflow_plan import (
        GLOBAL_INPUT_PLANNER_PROMPT,
        PLAN_SCHEMA,
        PLANNER_PROMPT_VERSION,
        planner_prompts,
        stable_hash,
    )

    if (runtime_input is None) != (variant is None):
        raise ValueError("runtime_input and variant must be given together")
    planner_prompt_version = (
        PLANNER_PROMPT_VERSION if runtime_input is None else GLOBAL_INPUT_PLANNER_PROMPT
    )

    row = load_task_description(recipe_id)
    tool_specs = deepcopy(row.get("public_tool_surface") or [])
    if enriched_tool_docs:
        from task.tool_catalog import enrich_tool_specs
        tool_specs = enrich_tool_specs(tool_specs)
    allowed_tools = {
        str(item.get("name") or "")
        for item in tool_specs
        if isinstance(item, dict) and item.get("name")
    }
    if not allowed_tools:
        raise RuntimeError(f"task description {recipe_id} has no planner tools")
    workspace_context = {
        "execution_context_schema": row.get("public_execution_context_schema") or {},
        "workspace_resources": row.get("public_workspace_cards") or [],
        "communication_templates": row.get("public_communication_templates") or [],
    }
    validation_input_schema = deepcopy(row.get("public_input_schema") or {})
    validation_input_schema.setdefault("type", "object")
    validation_input_schema.setdefault("properties", {})["execution_context"] = deepcopy(
        row.get("public_execution_context_schema") or {"type": "object"}
    )
    system, user = planner_prompts(
        objective=row["task_description"],
        # The frozen compiler sees schemas, never variant values.  Publish the
        # execution context inside the same root schema used by input_ref
        # validation so values such as execution_context.recipe_url are
        # constructible without guessing that they belong to an error object.
        input_schema=validation_input_schema,
        output_schema=row.get("public_output_schema") or {},
        tool_specs=tool_specs,
        workspace_context=workspace_context,
        runtime_input=runtime_input,
    )
    decoding = {
        key: getattr(llm, key)
        for key in (
            "temperature", "thinking", "effort", "max_tokens", "revision", "do_sample"
        )
        if hasattr(llm, key)
    }
    cache_key_payload = {
        "schema": PLAN_SCHEMA,
        "planner_prompt": planner_prompt_version,
        "model": model_id,
        "decoding": decoding,
        "system_hash": stable_hash(system),
        "user_hash": stable_hash(user),
        "public_package_hash": row.get("public_package_hash"),
        "enriched_tool_docs": enriched_tool_docs,
    }
    if runtime_input is not None:
        cache_key_payload["variant"] = int(variant)
        cache_key_payload["runtime_input_hash"] = stable_hash(runtime_input)
    cache_key = stable_hash(cache_key_payload)
    safe_model = model_id.replace("/", "__").replace(":", "_")
    if runtime_input is None:
        cache_path = eval_root / "plans" / safe_model / recipe_id / "initial_plan.json"
    else:
        cache_path = (
            eval_root / "plans_global_input" / safe_model / recipe_id
            / f"variant_{int(variant):02d}.json"
        )
    return {
        "recipe_id": recipe_id,
        "variant": variant,
        "planner_prompt_version": planner_prompt_version,
        "tool_specs": tool_specs,
        "allowed_tools": allowed_tools,
        "workspace_context": workspace_context,
        "validation_input_schema": validation_input_schema,
        "system": system,
        "user": user,
        "cache_key": cache_key,
        "cache_key_payload": cache_key_payload,
        "cache_path": cache_path,
    }


def prepare_initial_plan(
    recipe_id: str,
    llm,
    eval_root: Path,
    *,
    model_id: str,
    enriched_tool_docs: bool,
    raw_override: str | None = None,
    planner_tokens_override: int | None = None,
) -> dict[str, Any]:
    """Generate or reuse exactly one variant-blind initial plan per recipe."""

    from task.agents import parse_plan
    from task.workflow_plan import (
        PLAN_SCHEMA,
        PLANNER_PROMPT_VERSION,
        PlanValidationError,
        normalize_plan,
        plan_hash,
        stable_hash,
    )

    context = initial_plan_context(
        recipe_id,
        llm,
        eval_root,
        model_id=model_id,
        enriched_tool_docs=enriched_tool_docs,
    )
    tool_specs = context["tool_specs"]
    allowed_tools = context["allowed_tools"]
    workspace_context = context["workspace_context"]
    validation_input_schema = context["validation_input_schema"]
    system = context["system"]
    user = context["user"]
    cache_key = context["cache_key"]
    cache_key_payload = context["cache_key_payload"]
    cache_path = context["cache_path"]
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("cache_key") == cache_key:
            if cached.get("status") == "invalid_plan":
                # A cache written by an older validator can hold a raw
                # response that the current execution contract accepts.
                # Deterministically re-adjudicate from the stored response
                # instead of resampling the model — the mirror image of the
                # stale-cache reclassification below.
                raw_text = cached.get("raw_response")
                reparsed = (
                    parse_plan(raw_text, repair_missing_closers=True)
                    if isinstance(raw_text, str)
                    else None
                )
                revalidated = None
                if isinstance(reparsed, list):
                    try:
                        revalidated = normalize_plan(
                            reparsed,
                            allowed_tools,
                            tool_specs=tool_specs,
                            input_schema=validation_input_schema,
                            workspace_context=workspace_context,
                        )
                    except PlanValidationError:
                        revalidated = None
                if revalidated is not None:
                    cached.update({
                        "status": "ok",
                        "plan": revalidated,
                        "plan_hash": plan_hash(revalidated),
                        "cache_reused": True,
                        "validation_reclassified": True,
                        "syntax_normalized_from_raw": True,
                    })
                    cached.pop("error", None)
                    cache_path.write_text(
                        json.dumps(cached, indent=2, sort_keys=True, default=str)
                        + "\n",
                        encoding="utf-8",
                    )
                    return cached
                cached["cache_reused"] = True
                return cached
            cached_plan = cached.get("plan")
            recovered_from_raw = False
            if not isinstance(cached_plan, list) and isinstance(
                cached.get("raw_response"), str
            ):
                cached_plan = parse_plan(
                    cached["raw_response"], repair_missing_closers=True
                )
                recovered_from_raw = isinstance(cached_plan, list)
            if isinstance(cached_plan, list):
                try:
                    validated = normalize_plan(
                        cached_plan,
                        allowed_tools,
                        tool_specs=tool_specs,
                        input_schema=validation_input_schema,
                        workspace_context=workspace_context,
                    )
                except PlanValidationError as exc:
                    if isinstance(cached.get("plan"), list):
                        # A cache produced by an older validator can contain a
                        # plan that was accepted at generation time but is no
                        # longer valid under the current execution contract.
                        # Preserve the sampled response and deterministically
                        # reclassify it instead of aborting the whole run or
                        # resampling the model.
                        cached.update({
                            "status": "invalid_plan",
                            "error": str(exc),
                            "plan": None,
                            "plan_hash": None,
                            "cache_reused": True,
                            "validation_reclassified": True,
                        })
                        cache_path.write_text(
                            json.dumps(cached, indent=2, sort_keys=True, default=str)
                            + "\n",
                            encoding="utf-8",
                        )
                        return cached
                else:
                    if (
                        not recovered_from_raw
                        and (
                            validated != cached["plan"]
                            or plan_hash(validated) != cached.get("plan_hash")
                        )
                    ):
                        raw_plan = (
                            parse_plan(
                                cached["raw_response"], repair_missing_closers=True
                            )
                            if isinstance(cached.get("raw_response"), str)
                            else None
                        )
                        raw_validated = (
                            normalize_plan(
                                raw_plan,
                                allowed_tools,
                                tool_specs=tool_specs,
                                input_schema=validation_input_schema,
                                workspace_context=workspace_context,
                            )
                            if isinstance(raw_plan, list)
                            else None
                        )
                        if raw_validated != validated:
                            raise RuntimeError(
                                f"corrupt frozen-plan cache: {cache_path}"
                            )
                        recovered_from_raw = True
                    cached.update({
                        "status": "ok",
                        "plan": validated,
                        "plan_hash": plan_hash(validated),
                        "cache_reused": True,
                        "syntax_normalized_from_raw": recovered_from_raw,
                    })
                    cached.pop("error", None)
                    if recovered_from_raw:
                        cache_path.write_text(
                            json.dumps(cached, indent=2, sort_keys=True, default=str)
                            + "\n",
                            encoding="utf-8",
                        )
                    return cached

    calls_before = int(getattr(llm, "calls", 0) or 0)
    tokens_before = int(getattr(llm, "total_tokens", 0) or 0)
    raw = (
        raw_override
        if raw_override is not None
        else llm.complete(system, [{"role": "user", "content": user}])
    )
    parsed = parse_plan(raw)
    json_syntax_repaired = False
    if parsed is None:
        parsed = parse_plan(raw, repair_missing_closers=True)
        json_syntax_repaired = parsed is not None
    artifact: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "planner_prompt": PLANNER_PROMPT_VERSION,
        "recipe_id": recipe_id,
        "model": model_id,
        "cache_key": cache_key,
        "cache_key_payload": cache_key_payload,
        "planner_input": {
            "system_hash": stable_hash(system),
            "user_hash": stable_hash(user),
            "contains_runtime_input": False,
        },
        "raw_response": raw,
        "planner_calls": (
            1
            if raw_override is not None
            else int(getattr(llm, "calls", 0) or 0) - calls_before
        ),
        "planner_tokens": (
            planner_tokens_override
            if planner_tokens_override is not None
            else int(getattr(llm, "total_tokens", 0) or 0) - tokens_before
        ),
        "cache_reused": False,
        "json_syntax_repaired": json_syntax_repaired,
    }
    try:
        if parsed is None:
            raise PlanValidationError("model response does not contain a plan array")
        normalized = normalize_plan(
            parsed,
            allowed_tools,
            tool_specs=tool_specs,
            input_schema=validation_input_schema,
            workspace_context=workspace_context,
        )
        artifact["plan"] = normalized
        artifact["plan_hash"] = plan_hash(normalized)
        artifact["status"] = "ok"
    except PlanValidationError as exc:
        artifact["status"] = "invalid_plan"
        artifact["error"] = str(exc)
        artifact["plan"] = None
        artifact["plan_hash"] = None
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return artifact


def prepare_variant_plan(
    recipe_id: str,
    variant: int,
    llm,
    eval_root: Path,
    *,
    model_id: str,
    enriched_tool_docs: bool,
    runtime_input: dict[str, Any],
) -> dict[str, Any]:
    """GLOBAL+INPUT: one one-shot plan for ONE runtime variant.

    Mirrors ``prepare_initial_plan`` (same parser, validator, decoding, single
    LLM call, invalid plans recorded as ``invalid_plan``) with two
    differences: the prompt carries the variant's concrete public runtime
    input, and the artifact is cached per variant so nothing is shared across
    variants. A transport failure of the single planning call is cached as an
    ``invalid_plan`` too, so a resumed lane never re-runs a deterministic
    context overflow.
    """

    from task.agents import parse_plan
    from task.llm_client import LLMError
    from task.workflow_plan import (
        PLAN_SCHEMA,
        PlanValidationError,
        normalize_plan,
        plan_hash,
        stable_hash,
    )

    context = initial_plan_context(
        recipe_id,
        llm,
        eval_root,
        model_id=model_id,
        enriched_tool_docs=enriched_tool_docs,
        runtime_input=runtime_input,
        variant=variant,
    )
    cache_path = context["cache_path"]
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cached = None
        if isinstance(cached, dict) and cached.get("cache_key") == context["cache_key"]:
            cached["cache_reused"] = True
            return cached

    system = context["system"]
    user = context["user"]
    messages = [{"role": "user", "content": user}]
    prompt_tokens = None
    tokens_before = int(getattr(llm, "total_tokens", 0) or 0)

    def _per_call_costs() -> tuple[int, int | None, str]:
        """(completion tokens, prompt tokens, source) for THIS call.

        Clients that run concurrently expose per-thread counters for the
        last call; the shared-total delta is only valid for serial clients.
        """
        nonlocal prompt_tokens
        out = getattr(llm, "last_call_completion_tokens", None)
        inp = getattr(llm, "last_call_prompt_tokens", None)
        if isinstance(inp, int):
            prompt_tokens = inp
        if isinstance(out, int):
            return out, prompt_tokens, "per_call"
        if prompt_tokens is None:
            counter = getattr(llm, "prompt_token_count", None)
            if callable(counter):
                try:
                    prompt_tokens = int(counter(system, messages))
                except Exception:
                    prompt_tokens = None
        return (
            int(getattr(llm, "total_tokens", 0) or 0) - tokens_before,
            prompt_tokens,
            "client_delta",
        )
    artifact: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "planner_prompt": context["planner_prompt_version"],
        "recipe_id": recipe_id,
        "variant": int(variant),
        "model": model_id,
        "cache_key": context["cache_key"],
        "cache_key_payload": context["cache_key_payload"],
        "planner_input": {
            "system_hash": stable_hash(system),
            "user_hash": stable_hash(user),
            "contains_runtime_input": True,
            "runtime_input_hash": stable_hash(runtime_input),
            "prompt_chars": len(system) + len(user),
            "prompt_tokens": None,
        },
        "runtime_input": deepcopy(runtime_input),
        "cache_reused": False,
    }
    try:
        raw = llm.complete(system, messages)
    except LLMError as exc:
        completion_tokens, prompt_tokens, source = _per_call_costs()
        artifact["planner_input"]["prompt_tokens"] = prompt_tokens
        artifact.update({
            "raw_response": None,
            "planner_calls": 1,
            "planner_tokens": completion_tokens,
            "planner_tokens_source": source,
            "json_syntax_repaired": False,
            "status": "invalid_plan",
            "error": f"planning call failed: {exc}",
            "plan": None,
            "plan_hash": None,
        })
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        return artifact
    completion_tokens, prompt_tokens, source = _per_call_costs()
    artifact["planner_input"]["prompt_tokens"] = prompt_tokens
    parsed = parse_plan(raw)
    json_syntax_repaired = False
    if parsed is None:
        parsed = parse_plan(raw, repair_missing_closers=True)
        json_syntax_repaired = parsed is not None
    artifact.update({
        "raw_response": raw,
        "planner_calls": 1,
        "planner_tokens": completion_tokens,
        "planner_tokens_source": source,
        "json_syntax_repaired": json_syntax_repaired,
    })
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
        artifact["plan"] = normalized
        artifact["plan_hash"] = plan_hash(normalized)
        artifact["status"] = "ok"
    except PlanValidationError as exc:
        artifact["status"] = "invalid_plan"
        artifact["error"] = str(exc)
        artifact["plan"] = None
        artifact["plan_hash"] = None
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return artifact


def prepare_initial_plans_batched(
    recipe_ids: list[str],
    llm,
    eval_root: Path,
    *,
    model_id: str,
    enriched_tool_docs: bool,
) -> dict[str, dict[str, Any]]:
    """Prepare missing frozen plans in one native vLLM scheduler batch."""

    prepared: dict[str, dict[str, Any]] = {}
    pending: list[tuple[str, dict[str, Any]]] = []
    for recipe_id in recipe_ids:
        context = initial_plan_context(
            recipe_id,
            llm,
            eval_root,
            model_id=model_id,
            enriched_tool_docs=enriched_tool_docs,
        )
        cache_path = context["cache_path"]
        cache_matches = False
        if cache_path.is_file():
            try:
                cache_matches = (
                    json.loads(cache_path.read_text(encoding="utf-8")).get("cache_key")
                    == context["cache_key"]
                )
            except (OSError, ValueError):
                cache_matches = False
        if cache_matches:
            prepared[recipe_id] = prepare_initial_plan(
                recipe_id,
                llm,
                eval_root,
                model_id=model_id,
                enriched_tool_docs=enriched_tool_docs,
            )
        else:
            pending.append((recipe_id, context))

    if not pending:
        return prepared
    batch_size = max(
        1, int(getattr(llm, "initial_plan_batch_size", len(pending)) or len(pending))
    )
    for offset in range(0, len(pending), batch_size):
        chunk = pending[offset:offset + batch_size]
        requests = [
            (context["system"], [{"role": "user", "content": context["user"]}])
            for _, context in chunk
        ]
        try:
            # Indexed batching keeps one failed request (context overflow,
            # empty completion) from discarding its batch peers' plans and
            # forcing the slow serial-regeneration fallback below.
            if hasattr(llm, "complete_many_indexed"):
                raw_responses = llm.complete_many_indexed(requests)
            else:
                raw_responses = llm.complete_many(requests)
            if len(raw_responses) != len(chunk):
                raise RuntimeError(
                    "batched planner returned a different number of responses "
                    "than prompts"
                )
        except Exception:
            # API batches are deliberately small. If one transport request
            # exhausts retries, retry only this chunk serially so completed
            # prior chunks remain checkpointed and one 529 cannot discard the
            # whole corpus run.
            for recipe_id, _ in chunk:
                try:
                    prepared[recipe_id] = prepare_initial_plan(
                        recipe_id,
                        llm,
                        eval_root,
                        model_id=model_id,
                        enriched_tool_docs=enriched_tool_docs,
                    )
                except Exception as exc:
                    print(
                        f"[plan-transport] recipe {recipe_id}: "
                        f"{type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )
                    prepared[recipe_id] = {
                        "status": "invalid_plan",
                        "recipe_id": recipe_id,
                        "model": model_id,
                        "plan": None,
                        "plan_hash": None,
                        "error": f"initial planning failed: {exc}",
                    }
            continue
        token_counts = list(getattr(llm, "last_completion_token_counts", []))
        if len(token_counts) != len(chunk):
            token_counts = [None] * len(chunk)
        for (recipe_id, _), raw, token_count in zip(
            chunk, raw_responses, token_counts, strict=True
        ):
            if isinstance(raw, Exception):
                print(
                    f"[plan-transport] recipe {recipe_id}: "
                    f"{type(raw).__name__}: {raw}",
                    file=sys.stderr,
                )
                prepared[recipe_id] = {
                    "status": "invalid_plan",
                    "recipe_id": recipe_id,
                    "model": model_id,
                    "plan": None,
                    "plan_hash": None,
                    "error": f"initial planning failed: {raw}",
                }
                continue
            prepared[recipe_id] = prepare_initial_plan(
                recipe_id,
                llm,
                eval_root,
                model_id=model_id,
                enriched_tool_docs=enriched_tool_docs,
                raw_override=raw,
                planner_tokens_override=token_count,
            )
    return prepared


def prepare_incremental_plan(
    recipe_id: str,
    llm,
    eval_root: Path,
    *,
    model_id: str,
    enriched_tool_docs: bool,
    max_editor_turns: int = 64,
) -> dict[str, Any]:
    """Compile one variant-blind plan through an append-only editor."""

    from task.agents import parse_incremental_plan_action
    from task.workflow_plan import (
        INCREMENTAL_PLANNER_PROMPT,
        PLAN_SCHEMA,
        PlanValidationError,
        append_incremental_plan_node,
        normalize_plan,
        plan_hash,
        planner_prompts,
        stable_hash,
    )

    row = load_task_description(recipe_id)
    tool_specs = deepcopy(row.get("public_tool_surface") or [])
    if enriched_tool_docs:
        from task.tool_catalog import enrich_tool_specs
        tool_specs = enrich_tool_specs(tool_specs)
    allowed_tools = {
        str(item.get("name") or "")
        for item in tool_specs
        if isinstance(item, dict) and item.get("name")
    }
    if not allowed_tools:
        raise RuntimeError(f"task description {recipe_id} has no planner tools")
    workspace_context = {
        "execution_context_schema": row.get("public_execution_context_schema") or {},
        "workspace_resources": row.get("public_workspace_cards") or [],
        "communication_templates": row.get("public_communication_templates") or [],
    }
    validation_input_schema = deepcopy(row.get("public_input_schema") or {})
    validation_input_schema.setdefault("type", "object")
    validation_input_schema.setdefault("properties", {})["execution_context"] = deepcopy(
        row.get("public_execution_context_schema") or {"type": "object"}
    )
    system, user = planner_prompts(
        objective=row["task_description"],
        input_schema=validation_input_schema,
        output_schema=row.get("public_output_schema") or {},
        tool_specs=tool_specs,
        workspace_context=workspace_context,
        incremental=True,
    )
    decoding = {
        key: getattr(llm, key)
        for key in (
            "temperature", "thinking", "effort", "max_tokens", "revision", "do_sample"
        )
        if hasattr(llm, key)
    }
    cache_key_payload = {
        "schema": PLAN_SCHEMA,
        "planner_prompt": INCREMENTAL_PLANNER_PROMPT,
        "model": model_id,
        "decoding": decoding,
        "system_hash": stable_hash(system),
        "user_hash": stable_hash(user),
        "public_package_hash": row.get("public_package_hash"),
        "enriched_tool_docs": enriched_tool_docs,
        "max_editor_turns": max_editor_turns,
    }
    cache_key = stable_hash(cache_key_payload)
    safe_model = model_id.replace("/", "__").replace(":", "_")
    cache_path = (
        eval_root
        / "incremental_plans"
        / safe_model
        / recipe_id
        / "initial_plan.json"
    )
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if (
            cached.get("cache_key") == cache_key
            and cached.get("status") == "invalid_plan"
        ):
            cached["cache_reused"] = True
            return cached
        if cached.get("cache_key") == cache_key and isinstance(cached.get("plan"), list):
            try:
                validated = normalize_plan(
                    cached["plan"],
                    allowed_tools,
                    tool_specs=tool_specs,
                    input_schema=validation_input_schema,
                    workspace_context=workspace_context,
                )
            except PlanValidationError as exc:
                raise RuntimeError(f"corrupt incremental-plan cache: {cache_path}") from exc
            syntax_normalized = validated != cached["plan"]
            if syntax_normalized:
                recovered_draft: list[dict[str, Any]] = []
                try:
                    for step in cached.get("planner_steps") or []:
                        action = step.get("action") if isinstance(step, dict) else None
                        if (
                            step.get("accepted") is True
                            and isinstance(action, dict)
                            and action.get("type") == "append_node"
                        ):
                            recovered_draft, _ = append_incremental_plan_node(
                                recovered_draft,
                                action["parent"],
                                action["node"],
                                allowed_tools,
                            )
                    recovered = normalize_plan(
                        recovered_draft,
                        allowed_tools,
                        tool_specs=tool_specs,
                        input_schema=validation_input_schema,
                        workspace_context=workspace_context,
                    )
                except (KeyError, TypeError, PlanValidationError) as exc:
                    raise RuntimeError(
                        f"corrupt incremental-plan cache: {cache_path}"
                    ) from exc
                if recovered != validated:
                    raise RuntimeError(f"corrupt incremental-plan cache: {cache_path}")
            elif plan_hash(validated) != cached.get("plan_hash"):
                raise RuntimeError(f"corrupt incremental-plan cache: {cache_path}")
            cached.update({
                "status": "ok",
                "plan": validated,
                "plan_hash": plan_hash(validated),
                "cache_reused": True,
                "syntax_normalized_from_editor_transcript": syntax_normalized,
            })
            if syntax_normalized:
                cache_path.write_text(
                    json.dumps(cached, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8",
                )
            return cached

    calls_before = int(getattr(llm, "calls", 0) or 0)
    tokens_before = int(getattr(llm, "total_tokens", 0) or 0)
    messages: list[dict[str, str]] = [{"role": "user", "content": user}]
    draft: list[dict[str, Any]] = []
    planner_steps: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] | None = None
    final_error = "model did not finish the plan within the editor-turn limit"

    for turn in range(1, max_editor_turns + 1):
        try:
            raw = llm.complete(system, messages)
        except Exception as exc:
            # A doomed session's conversation grows every turn (rejected op
            # + feedback) until the prompt exceeds the pinned input limit;
            # the resulting LLMError must still produce a CACHED artifact.
            # Propagating instead left only an in-memory invalid_plan, so a
            # preempted-and-resumed lane re-ran the same doomed sessions
            # forever (hours each, serially — the local-view treadmill).
            final_error = (
                f"editor session aborted at turn {turn}: "
                f"{type(exc).__name__}: {exc}"
            )
            planner_steps.append({
                "turn": turn,
                "raw_response": None,
                "action": None,
                "accepted": False,
                "error": final_error,
            })
            break
        messages.append({"role": "assistant", "content": raw})
        action = parse_incremental_plan_action(raw)
        step: dict[str, Any] = {"turn": turn, "raw_response": raw, "action": action}
        if action is None:
            final_error = "unparseable incremental editor action"
            step.update({"accepted": False, "error": final_error})
            planner_steps.append(step)
            feedback = (
                "EDITOR OBSERVATION: rejected. Return exactly one append_node or "
                "finish_plan JSON operation. No node was added."
            )
        elif action["type"] == "invalid_action":
            final_error = action["error"]
            step.update({"accepted": False, "error": final_error})
            planner_steps.append(step)
            feedback = f"EDITOR OBSERVATION: rejected. {action['error']}"
        elif action["type"] == "append_node":
            try:
                candidate_draft, draft_id = append_incremental_plan_node(
                    draft,
                    action["parent"],
                    action["node"],
                    allowed_tools,
                )
                try:
                    normalize_plan(
                        candidate_draft,
                        allowed_tools,
                        tool_specs=tool_specs,
                        input_schema=validation_input_schema,
                        workspace_context=workspace_context,
                    )
                except PlanValidationError as semantic_exc:
                    # A partial draft may legitimately contain only control or
                    # transform nodes. Every other semantic error belongs to
                    # the just-proposed node and is returned while that node is
                    # still editable, instead of surfacing only after an
                    # immutable bad prefix has been accepted.
                    if str(semantic_exc) != "plan must contain at least one call node":
                        raise semantic_exc
            except PlanValidationError as exc:
                final_error = str(exc)
                step.update({"accepted": False, "error": final_error})
                planner_steps.append(step)
                feedback = f"EDITOR OBSERVATION: rejected: {final_error}. No node was added."
            else:
                draft = candidate_draft
                step.update({
                    "accepted": True,
                    "draft_id": draft_id,
                    "parent": action["parent"],
                })
                planner_steps.append(step)
                feedback = (
                    f"EDITOR OBSERVATION: accepted as {draft_id} under "
                    f"{action['parent']}. Append one next node or finish the plan."
                )
        else:
            try:
                normalized = normalize_plan(
                    draft,
                    allowed_tools,
                    tool_specs=tool_specs,
                    input_schema=validation_input_schema,
                    workspace_context=workspace_context,
                )
            except PlanValidationError as exc:
                final_error = str(exc)
                step.update({"accepted": False, "error": final_error})
                planner_steps.append(step)
                feedback = (
                    f"EDITOR OBSERVATION: finish rejected: {final_error}. "
                    "Append missing work if the immutable prefix permits it, then finish."
                )
            else:
                step.update({"accepted": True})
                planner_steps.append(step)
                break
        messages.append({
            "role": "user",
            "content": feedback + "\n\nCURRENT DRAFT:\n" + json.dumps(
                {"plan": draft}, indent=1, sort_keys=True
            ),
        })

    artifact: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "planner_prompt": INCREMENTAL_PLANNER_PROMPT,
        "recipe_id": recipe_id,
        "model": model_id,
        "cache_key": cache_key,
        "cache_key_payload": cache_key_payload,
        "planner_input": {
            "system_hash": stable_hash(system),
            "user_hash": stable_hash(user),
            "contains_runtime_input": False,
        },
        "planner_steps": planner_steps,
        "planner_calls": int(getattr(llm, "calls", 0) or 0) - calls_before,
        "planner_tokens": int(getattr(llm, "total_tokens", 0) or 0) - tokens_before,
        "cache_reused": False,
        "accepted_node_count": sum(
            step.get("accepted") is True
            and isinstance(step.get("action"), dict)
            and step["action"].get("type") == "append_node"
            for step in planner_steps
        ),
    }
    if normalized is None:
        artifact.update({
            "status": "invalid_plan",
            "error": final_error,
            "plan": None,
            "plan_hash": None,
            "unfinished_draft": draft,
        })
    else:
        artifact.update({
            "status": "ok",
            "plan": normalized,
            "plan_hash": plan_hash(normalized),
        })
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return artifact


def task_visible_constants(
    brief: dict[str, Any],
    expect: dict[str, Any],
    task_source: str,
) -> set[str]:
    """Return expected values intentionally stated in an approved task.

    The runtime leak gate exists to catch a prompt builder copying hidden
    expectation values into generated scaffolding.  A hash-bound task
    description is itself the benchmark input, however, and must be allowed
    to state fixed business literals that an operator could not infer (for
    example a Salesforce object API name or an exact Slack message).  Limit
    this exception to values already present in the objective; values copied
    into constraints, contracts, or other generated fields remain leaks.
    """

    if task_source != "task_description":
        return set()
    from task.prompt import brief_leaks

    return set(brief_leaks(str(brief.get("objective") or ""), expect))


def load_contract(recipe_id: str, contract_dir: Path | None = None) -> dict[str, Any]:
    path = (contract_dir or CONTRACT_DIR) / f"{recipe_id}.json"
    if not path.exists():
        raise RuntimeError(f"missing output contract: {path}")
    contract = json.loads(path.read_text())
    if not isinstance(contract, dict):
        raise RuntimeError(f"contract must be a JSON object: {path}")
    return contract


def _final_snapshot(registry, families: set[str]) -> dict[str, Any]:
    """Snapshot every state-carrying backend in the task's tool surface.
    Backend participation is decided by FAMILIES (gold usage + seeded
    sections), never by catching errors: a snapshot failure on a
    participating backend is a real harness failure and raises."""
    snapshot: dict[str, Any] = {}
    for tool in _MOCK_SNAPSHOT_TOOLS:
        result = registry.call(tool, {})
        for key, value in result.items():
            if key != "ok":
                snapshot[key] = value
    for family, tool in _LIVE_SNAPSHOT_TOOLS.items():
        if family not in families:
            continue
        result = registry.call(tool, {})
        for key, value in result.items():
            if key != "ok":
                snapshot[key] = value
    if "google_sheets" in families:
        sheets = registry.call(_SHEETS_SNAPSHOT_TOOL, {})
        snapshot["google_sheets"] = {k: v for k, v in sheets.items() if k != "ok"}
    return snapshot


def _cleanup_live(registry, families: set[str]) -> None:
    """Delete benchmark-owned live state created for this eval run. Required
    cleanup is fail-fast: a cleanup error or leftover raises instead of being
    hidden (benchmark cleanup policy 'Cleanup principle'). Gating is by
    family membership, not exception swallowing."""
    for family, tool in _LIVE_CLEANUP_TOOLS.items():
        if family not in families:
            continue
        result = registry.call(tool, {})
        if not result.get("ok"):
            raise RuntimeError(f"live cleanup left residue: {tool} -> {result}")


def _replan_protocol_counters(steps: list[Any]) -> dict[str, int]:
    """Attribution counters for the replan review protocol (v2 adds repair
    turns, the patch op and resolver-error reviews; all zero under v1)."""
    rejected = [s for s in steps if isinstance(s, dict) and "replan_rejected" in s]
    accepted = [
        s["replan_accepted"] for s in steps
        if isinstance(s, dict) and isinstance(s.get("replan_accepted"), dict)
    ]
    reviews = [
        s["replan_review"] for s in steps
        if isinstance(s, dict) and isinstance(s.get("replan_review"), dict)
    ]
    return {
        "replan_rejected_count": len(rejected),
        "replan_repair_offered_count": sum(
            1 for s in rejected if s.get("repair_offered") is True
        ),
        "replan_repair_accepted_count": sum(
            1 for e in accepted if e.get("attempt") == 2
        ),
        "replan_patch_accepted_count": sum(
            1 for e in accepted if e.get("kind") == "patch"
        ),
        "replan_resolver_review_count": sum(
            1 for s in rejected + accepted + reviews
            if s.get("trigger") == "resolution_error"
        ),
        "replan_resolver_accepted_count": sum(
            1 for e in accepted if e.get("trigger") == "resolution_error"
        ),
    }


def run_one(recipe_id: str, variant: int, mode: str, llm,
            brief_dir: Path | None = None,
            eval_root: Path = EVAL_ROOT_DEFAULT,
            task_source: str = "legacy_brief",
            tool_surface: str = "recipe",
            enriched_tool_docs: bool = True,
            initial_plan_artifact: dict[str, Any] | None = None,
            max_replans: int = 2,
            replan_protocol: str = "v1") -> dict[str, Any]:
    _ensure_isolation(eval_root)
    from benchmark.seed_recipe import load_variant_input, seed_recipe
    from benchmark.run_recipe import build_context

    task_id = f"{recipe_id}__v{variant:02d}"
    row: dict[str, Any] = {"task_id": task_id, "recipe_id": recipe_id,
                           "variant": variant, "mode": mode, "model": llm.model}
    # GLOBAL+INPUT plans per variant, after the public runtime input has been
    # projected below; a caller-supplied artifact (scripted control) is used
    # as-is. Every other frozen-plan mode arrives with its recipe-level plan.
    per_variant_plan = mode == "global_input" and initial_plan_artifact is None
    if per_variant_plan and task_source != "task_description":
        row.update({"status": "infra_error",
                    "error": "global_input requires --task-source task_description"})
        return row
    if mode in {"plan_execute", "global_input", "replan", "incremental_workflow"} and (
        not per_variant_plan
    ) and (
        not isinstance(initial_plan_artifact, dict)
        or initial_plan_artifact.get("status") != "ok"
        or not isinstance(initial_plan_artifact.get("plan"), list)
    ):
        row.update({
            "status": "plan_error",
            "error": (
                (initial_plan_artifact or {}).get("error")
                or "missing valid recipe-level frozen plan"
            ),
            "initial_plan_hash": (initial_plan_artifact or {}).get("plan_hash"),
        })
        return row
    try:
        if task_source == "task_description":
            brief = description_brief(recipe_id)
        elif task_source == "legacy_brief":
            brief = load_brief(recipe_id, brief_dir)
        else:
            raise RuntimeError(f"unknown task source: {task_source}")
        contract = (
            load_task_description(recipe_id).get("public_output_schema") or {}
            if task_source == "task_description"
            else load_contract(recipe_id)
        )
        variant_input = load_variant_input(recipe_id, variant, None)
        raw_expect = variant_input.get("expect")
        if not isinstance(raw_expect, dict):
            raise RuntimeError(f"{task_id}: variant input has no expect block")
        gold_path = GT_ROOT / recipe_id / f"variant_{variant:02d}" / "output.json"
        if not gold_path.exists():
            raise RuntimeError(f"{task_id}: missing ground truth {gold_path}")
        gold = json.loads(gold_path.read_text())
        gold_calls = gold["tool_calls"]
        gold_snapshot = (gold.get("details") or {}).get("final_snapshot") or {}
        gold_structural_return = (
            _gold_structural_return(gold, recipe_id)
            if task_source == "task_description"
            else {"present": False, "value": None}
        )
        seed = seed_recipe(recipe_id, variant_input)
        visible_variant = deepcopy(seed.get("variant_input") or variant_input)
        # Live seeders resolve benchmark-local public input tokens (for
        # example a Salesforce $ACCOUNT_ID) after provisioning. The evaluated
        # model must receive that resolved caller payload, never the private
        # fixture token from the source variant file.
        if isinstance(seed.get("trigger"), dict):
            seed = deepcopy(seed)
            visible_variant["trigger_input"] = deepcopy(seed["trigger"])
            seed["variant_input"] = visible_variant
        if task_source == "task_description":
            reference_rebindings = _runtime_reference_rebindings(gold, seed)
            if reference_rebindings:
                gold_calls = _replace_runtime_reference_values(
                    gold_calls, reference_rebindings
                )
                gold_snapshot = _replace_runtime_reference_values(
                    gold_snapshot, reference_rebindings
                )
                gold_structural_return = _replace_runtime_reference_values(
                    gold_structural_return, reference_rebindings
                )
                rebind_control = getattr(llm, "rebind_runtime_values", None)
                if callable(rebind_control):
                    rebind_control(reference_rebindings)
            gold_calls, gold_snapshot = _task_description_public_gold_projection(
                recipe_id,
                visible_variant,
                gold_calls,
                gold_snapshot,
            )
            # The TaskSpec advertises a canonical execution-context schema;
            # provide its matching runtime projection.  In particular,
            # referenced top-level job_context fields become the model-visible
            # execution_context while private seed/expect/fault data is removed.
            visible_variant = _public_task_description_runtime_input(
                recipe_id,
                visible_variant,
            )
            seed = deepcopy(seed)
            seed["variant_input"] = deepcopy(visible_variant)
        if per_variant_plan:
            # The planner sees exactly the object the deterministic executor
            # binds input_ref against (trigger_input + execution_context) and
            # nothing seeded, expected, or observed. One LLM call, no
            # execution, no feedback, frozen before the first tool call.
            planner_input = {
                key: deepcopy(visible_variant[key])
                for key in ("trigger_input", "execution_context")
                if key in visible_variant
            }
            try:
                initial_plan_artifact = prepare_variant_plan(
                    recipe_id,
                    variant,
                    llm,
                    eval_root,
                    model_id=str(getattr(llm, "model", "") or ""),
                    enriched_tool_docs=enriched_tool_docs,
                    runtime_input=planner_input,
                )
            except Exception as exc:  # transport failure outside the LLM call
                initial_plan_artifact = {
                    "status": "invalid_plan",
                    "plan": None,
                    "plan_hash": None,
                    "error": f"initial planning failed: {exc}",
                }
            artifact = initial_plan_artifact
            row.update({
                "planner_calls": int(artifact.get("planner_calls", 0) or 0),
                "planner_tokens": int(artifact.get("planner_tokens", 0) or 0),
                "planner_prompt_tokens": (artifact.get("planner_input") or {}).get(
                    "prompt_tokens"
                ),
                "planner_prompt_chars": (artifact.get("planner_input") or {}).get(
                    "prompt_chars"
                ),
                "plan_cache_reused": bool(artifact.get("cache_reused", False)),
                "planning_status": artifact.get("status"),
            })
            if (
                artifact.get("status") != "ok"
                or not isinstance(artifact.get("plan"), list)
            ):
                row.update({
                    "status": "plan_error",
                    "error": artifact.get("error") or "missing valid variant-level frozen plan",
                    "initial_plan_hash": artifact.get("plan_hash"),
                })
                return row
        # Live seeders resolve benchmark-local reference tokens such as
        # $STUDENT_ID only after provisioning records.  Strict scoring and
        # the prompt leak gate must use that resolved expectation object;
        # comparing a real call against the pre-seed placeholders produces a
        # false negative even for an exact gold replay.
        # Most static seeders leave expectations in the variant input; live
        # seeders additionally return a resolved copy after provisioning.
        seeded_expect = seed.get("expect")
        expect = seeded_expect if isinstance(seeded_expect, dict) else raw_expect
        if task_source == "task_description":
            _attach_task_description_forced_error(seed, recipe_id)
        ctx = build_context(seed)
        ctx.tools.configure_forced_error(seed.get("force_tool_error"))
    except (RuntimeError, KeyError, ValueError, FileNotFoundError) as exc:
        row.update({"status": "infra_error", "error": str(exc),
                    "error_traceback": traceback.format_exc()[-1500:]})
        return row
    families: set[str] | None = None
    try:
        families = (
            description_tool_families(recipe_id)
            if task_source == "task_description"
            else _tool_families(recipe_id, seed)
        )
        return _score_run(recipe_id, mode, llm, row, task_id, brief, contract,
                          visible_variant, expect, gold_calls, gold_snapshot,
                          seed, ctx, families, task_source, tool_surface,
                          enriched_tool_docs, initial_plan_artifact,
                          max_replans, gold_structural_return,
                          replan_protocol=replan_protocol)
    finally:
        # Live state seeded for this run must not leak even when the agent
        # run or scoring fails; _score_run snapshots before cleanup runs. If
        # family derivation itself failed, fall back to the seeded sections.
        if families is None:
            families = {fam for section, fam in _SEED_SECTION_FAMILIES.items()
                        if seed.get(section)}
        _cleanup_live(ctx.tools, families)


def _score_run(recipe_id: str, mode: str, llm, row: dict[str, Any],
               task_id: str, brief: dict[str, Any], contract: dict[str, Any],
               variant_input: dict[str, Any], expect: dict[str, Any],
               gold_calls: list[dict[str, Any]], gold_snapshot: dict[str, Any],
               seed: dict[str, Any], ctx, families: set[str],
               task_source: str, tool_surface: str,
               enriched_tool_docs: bool,
               initial_plan_artifact: dict[str, Any] | None,
               max_replans: int,
               gold_structural_return: dict[str, Any],
               replan_protocol: str = "v1") -> dict[str, Any]:
    from metrics.planning import score_one
    from metrics.plan_fidelity import evaluate_for_mode
    from metrics.strict import compute_action_budget, evaluate, expected_tools
    from metrics.outcome import evaluate_outcome
    from task.runner import AgentRunner
    # Task-description runs consume the variant-invariant public planning
    # package. Legacy runs retain their raw-recipe-derived schema card.
    if task_source == "task_description":
        schema_text = description_schema_card(recipe_id)
    else:
        from benchmark.recipe_store import load_raw_recipe
        from task.schema_card import schema_card_text
        try:
            schema_text = schema_card_text(load_raw_recipe(recipe_id), seed)
        except (RuntimeError, KeyError, ValueError, FileNotFoundError) as exc:
            row.update({"status": "infra_error", "error": str(exc),
                        "error_traceback": traceback.format_exc()[-1500:]})
            return row

    if mode == "agent_sdk":
        import task.agent_sdk_runner as agent_sdk_runner
        runner = agent_sdk_runner.AgentSDKRunner(llm.model)
    else:
        runner = AgentRunner(llm, mode, replan_protocol=replan_protocol)
    from task.prompt import output_contract_text
    from task.solvability import classify
    constants = set(classify(variant_input)["constants"])
    visible_constants = task_visible_constants(brief, expect, task_source)
    constants.update(visible_constants)
    contract_text = output_contract_text(contract)
    # Primary (1.0x) budget decouples the agent's room to orient from the gold
    # trace's efficiency; enforcement runs at 2.0x so budget sensitivity
    # (pass@1.0x/1.5x/2.0x) falls out of a single run via actions_used.
    base_budget = compute_action_budget(expect, len(families))
    max_actions = 2 * base_budget
    if tool_surface == "broad":
        runner_tool_families = None
    elif tool_surface == "recipe":
        runner_tool_families = families
    else:
        row.update({"status": "infra_error",
                    "error": f"unknown tool surface: {tool_surface}"})
        return row
    evaluation_time = datetime.now(timezone.utc).isoformat()
    public_tool_specs: list[dict[str, Any]] | None = None
    public_input_schema: dict[str, Any] | None = None
    public_workspace_context: dict[str, Any] | None = None
    if task_source == "task_description":
        description_row = load_task_description(recipe_id)
        public_tool_specs = deepcopy(description_row.get("public_tool_surface") or [])
        public_input_schema = deepcopy(description_row.get("public_input_schema") or {})
        public_input_schema.setdefault("type", "object")
        public_input_schema.setdefault("properties", {})[
            "execution_context"
        ] = deepcopy(
            description_row.get("public_execution_context_schema")
            or {"type": "object"}
        )
        public_workspace_context = {
            "execution_context_schema": deepcopy(
                description_row.get("public_execution_context_schema") or {}
            ),
            "workspace_resources": deepcopy(
                description_row.get("public_workspace_cards") or []
            ),
            "communication_templates": deepcopy(
                description_row.get("public_communication_templates") or []
            ),
        }
    try:
        result = runner.run(brief, seed, ctx.tools, expect, max_actions,
                            schema_text=schema_text,
                            allowed_brief_values=constants,
                            tool_families=runner_tool_families,
                            public_tool_specs=public_tool_specs,
                            public_input_schema=public_input_schema,
                            public_workspace_context=public_workspace_context,
                            contract_text=contract_text,
                            enriched_tool_docs=enriched_tool_docs,
                            initial_plan=(initial_plan_artifact or {}).get("plan"),
                            max_replans=max_replans)
    except RuntimeError as exc:  # prompt leak or registry construction issue
        row.update({"status": "infra_error", "error": str(exc),
                    "error_traceback": traceback.format_exc()[-1500:]})
        return row
    if result.stop_reason.startswith("llm_error"):
        row.update({"status": "llm_error", "error": result.stop_reason,
                    "run": result.to_dict()})
        return row

    try:
        if mode == "react":
            plan_fidelity = evaluate_for_mode(mode)
        else:
            reference_path = TASK_DESCRIPTION_GROUNDTRUTH_DIR / f"{recipe_id}.json"
            reference_bundle = json.loads(reference_path.read_text(encoding="utf-8"))
            plan_fidelity = evaluate_for_mode(
                mode,
                reference_bundle,
                (initial_plan_artifact or {}).get("plan"),
            )
    except (OSError, ValueError, TypeError) as exc:
        row.update({
            "status": "infra_error",
            "error": f"plan-fidelity scoring failed: {exc}",
            "run": result.to_dict(),
        })
        return row
    plan_fidelity_flat = {
        key: value
        for key, value in plan_fidelity.items()
        if key.startswith("plan_")
    }

    final_snapshot = _final_snapshot(ctx.tools, families)
    try:
        verdict = evaluate(
            expect,
            result.trajectory,
            final_snapshot,
            evaluation_time=evaluation_time,
        )
    except RuntimeError as exc:
        row.update({"status": "infra_error", "error": f"scoring failed: {exc}",
                    "run": result.to_dict()})
        return row
    business_gold_calls = (
        _task_description_outcome_calls(
            recipe_id,
            _task_description_business_calls(gold_calls),
            str(getattr(ctx.env, "slack_channel_override", "") or ""),
        )
        if task_source == "task_description"
        else gold_calls
    )
    business_agent_calls = (
        _task_description_outcome_calls(
            recipe_id,
            _task_description_business_calls(result.trajectory),
            str(getattr(ctx.env, "slack_channel_override", "") or ""),
        )
        if task_source == "task_description"
        else result.trajectory
    )
    outcome_gold_calls = deepcopy(business_gold_calls)
    outcome_agent_calls = deepcopy(business_agent_calls)
    if task_source == "task_description":
        if gold_structural_return.get("present") is True:
            outcome_gold_calls.append(
                _synthetic_return_call(gold_structural_return.get("value"))
            )
        # Symbolic Global/Local plans execute a public return control node;
        # ReAct directly invokes one of the raw catalog forms. Canonicalize
        # both into the same semantic output without counting either as a
        # business tool-selection decision.
        if result.stop_reason == "return":
            outcome_agent_calls.append(_synthetic_return_call(result.final_answer))
        for call in result.trajectory:
            if str(call.get("tool") or "") not in _STRUCTURAL_RETURN_TOOLS:
                continue
            args = call.get("args") or {}
            if isinstance(args, dict) and "result" in args:
                outcome_agent_calls.append(_synthetic_return_call(args["result"]))
    output_boolean_paths = (
        _public_output_boolean_argument_paths(contract)
        if task_source == "task_description"
        else set()
    )
    terminal_boolean_paths = (
        {"workato_api_platform.return_response": output_boolean_paths}
        if output_boolean_paths
        else None
    )
    outcome = evaluate_outcome(
        outcome_gold_calls,
        gold_snapshot,
        outcome_agent_calls,
        final_snapshot,
        terminal_boolean_paths=terminal_boolean_paths,
    )
    all_specs = (
        public_tool_specs
        if public_tool_specs is not None
        else [
            spec for spec in ctx.tools.exposed_specs()
            if not spec["name"].startswith("harness.")
            and (
                runner_tool_families is None
                or spec["name"].split(".", 1)[0] in runner_tool_families
            )
        ]
    )
    runtime_order_spec = (
        _task_description_runtime_order_spec(
            recipe_id,
            task_id,
            business_gold_calls,
            all_specs,
        )
        if task_source == "task_description"
        else None
    )
    runtime_orchestration = _runtime_orchestration_components(
        business_gold_calls,
        business_agent_calls,
        result.steps,
        evaluation_time=evaluation_time,
        recipe_id=recipe_id,
        gold_snapshot=gold_snapshot,
        agent_snapshot=final_snapshot,
        expected_failure_tool=str(
            (seed.get("force_tool_error") or {}).get("tool") or ""
        ),
        boolean_paths=output_boolean_paths,
        required_order_edges=(
            [
                (
                    int(edge["before_gold_index"]),
                    int(edge["after_gold_index"]),
                )
                for edge in runtime_order_spec["dependency_edges"]
            ]
            if runtime_order_spec is not None
            else None
        ),
        tool_specs=all_specs,
    )
    if runtime_order_spec is not None:
        runtime_orchestration.update({
            "tool_order_dependency_spec_hash": runtime_order_spec["spec_hash"],
            "tool_order_multiple_topological_orders": runtime_order_spec[
                "multiple_topological_orders"
            ],
            "tool_order_mapped_gold_call_count": runtime_order_spec[
                "mapped_call_count"
            ],
            "tool_order_public_temporal_requirement_count": len(
                runtime_order_spec["public_temporal_requirement_ids"]
            ),
        })
    orchestration_trace_pass = all(
        runtime_orchestration[key] is True
        for key in (
            "tool_selection_pass",
            "tool_order_pass",
            "tool_execution_success_pass",
            "tool_argument_full_pass",
            "condition_path_pass",
        )
    )
    side_effect_checks = [
        check
        for check in outcome["checks"]
        if check.get("name") != "terminal_outputs_match"
    ]
    side_effect_pass = all(bool(check.get("ok")) for check in side_effect_checks)
    if outcome["transient_event_checked"]:
        side_effect_pass = side_effect_pass and bool(outcome["transient_event_pass"])
    # The exact canonical trace is the primary orchestration score.  Outcome
    # and state checks can veto an apparently faithful trace, but normalized
    # terminal/result equivalence can never rescue a different trace.
    canonical_trace_pass = bool(
        orchestration_trace_pass
        and outcome["terminal_exact_pass"]
        and side_effect_pass
    )
    # Task-description evaluation has a richer gold execution than the legacy
    # serialized ``expect`` subset. Use that execution-backed comparison as
    # the public strict verdict so SQL/SOQL semantics are not subsequently
    # vetoed by the legacy raw-string fixture check. Raw-recipe evaluation
    # keeps its historical strict verifier.
    primary_strict_pass = _primary_strict_verdict(
        task_source,
        legacy_strict_pass=bool(verdict["strict_pass"]),
        canonical_trace_pass=canonical_trace_pass,
    )
    planning = score_one(task_id, gold_calls, result.trajectory,
                         primary_strict_pass, result.failed_calls,
                         result.stop_reason)
    actions_used = len(result.trajectory)
    exposed_names = {spec["name"] for spec in all_specs}
    gold_names = {str(call.get("tool") or "") for call in business_gold_calls}
    successful_names = [
        str(call.get("tool") or "") for call in business_agent_calls
    ]
    attempted_names = [
        name
        for name in attempted_tool_names(result.steps)
        if name not in _STRUCTURAL_RETURN_TOOLS
    ]
    gold_tool_coverage = (
        len(gold_names.intersection(attempted_names)) / len(gold_names)
        if gold_names else 1.0
    )
    useful_action_rate = (
        sum(name in gold_names for name in attempted_names) / len(attempted_names)
        if attempted_names else 1.0
    )
    successful_gold_tool_coverage = (
        len(gold_names.intersection(successful_names)) / len(gold_names)
        if gold_names else 1.0
    )
    successful_useful_action_rate = (
        sum(name in gold_names for name in successful_names) / len(successful_names)
        if successful_names else 1.0
    )
    import math as _math
    row.update({"status": "ok", "strict_pass": primary_strict_pass,
                "legacy_fixture_strict_pass": bool(verdict["strict_pass"]),
                "outcome_pass": outcome["outcome_pass"],
                "outcome_semantic_pass": outcome["outcome_semantic_pass"],
                "canonical_trace_pass": canonical_trace_pass,
                "orchestration_trace_pass": orchestration_trace_pass,
                "side_effect_pass": side_effect_pass,
                "outcome_and_strict_pass": bool(
                    outcome["outcome_pass"] and primary_strict_pass
                ),
                **verdict["component_metrics"],
                **runtime_orchestration,
                "state_accuracy": outcome["state_accuracy"],
                "outcome_checks": outcome["checks"],
                "terminal_exact_pass": outcome["terminal_exact_pass"],
                "terminal_normalized_pass": outcome["terminal_normalized_pass"],
                "terminal_similarity_score": outcome["terminal_similarity_score"],
                "terminal_diff_reason": outcome["terminal_diff_reason"],
                "transient_event_checked": outcome["transient_event_checked"],
                "transient_event_pass": outcome["transient_event_pass"],
                "transient_event_expected_count": outcome[
                    "transient_event_expected_count"
                ],
                "transient_event_actual_count": outcome[
                    "transient_event_actual_count"
                ],
                "base_budget": base_budget,
                "max_actions": max_actions,
                "actions_used": actions_used,
                # Budget sensitivity from one 2.0x-capped run: pass@k means the
                # outcome passed AND fit within k× the primary budget.
                "outcome_pass_at_1x": bool(outcome["outcome_pass"]) and actions_used <= base_budget,
                "outcome_pass_at_1_5x": bool(outcome["outcome_pass"]) and actions_used <= _math.ceil(1.5 * base_budget),
                "outcome_pass_at_2x": bool(outcome["outcome_pass"]),
                "tool_families": sorted(families),
                "task_source": task_source,
                "tool_surface": tool_surface,
                "enriched_tool_docs": enriched_tool_docs,
                "task_visible_constant_count": len(visible_constants),
                "evaluation_time": evaluation_time,
                "initial_plan_hash": result.initial_plan_hash,
                "initial_plan_cache_key": (
                    (initial_plan_artifact or {}).get("cache_key")
                ),
                "protocol_violations": result.protocol_violations,
                "replan_count": result.replan_count,
                "replan_protocol": replan_protocol,
                **_replan_protocol_counters(result.steps),
                "replan_review_count": sum(
                    1
                    for step in result.steps
                    if isinstance(step, dict)
                    and any(
                        key in step
                        for key in (
                            "replan_review",
                            "replan_accepted",
                            "replan_rejected",
                        )
                    )
                ),
                "plan_fidelity_applicable": plan_fidelity["applicable"],
                **plan_fidelity_flat,
                "tools_exposed_count": len(exposed_names),
                "gold_distinct_tools": len(gold_names),
                "distractor_tools_count": len(exposed_names - gold_names),
                # Selection diagnostics count every parsed attempt, including
                # unknown names and registered calls whose arguments/backend
                # validation failed. The successful-only views are retained
                # separately for runtime-trajectory analysis.
                "gold_tool_coverage": round(gold_tool_coverage, 4),
                "useful_action_rate": round(useful_action_rate, 4),
                "extraneous_actions": sum(name not in gold_names for name in attempted_names),
                "successful_gold_tool_coverage": round(
                    successful_gold_tool_coverage, 4
                ),
                "successful_useful_action_rate": round(
                    successful_useful_action_rate, 4
                ),
                "successful_extraneous_actions": sum(
                    name not in gold_names for name in successful_names
                ),
                "value_checked": _value_checked(expect, len(expected_tools(expect))),
                "checks": verdict["checks"], **{k: v for k, v in planning.items()
                                                if k != "task_id"},
                "final_answer": result.final_answer, "run": result.to_dict()})
    # Row-level primary metrics (doc/metric.md): computed from the component
    # verdicts above so the leaderboard aggregation and the per-row record
    # can never disagree.
    from metrics.aggregate import primary_metrics_for_row
    row.update(primary_metrics_for_row(row))
    # Per-task inspection bundle: exactly what the agent saw (input), what it
    # did (output), and what the recipe did (groundtruth). Captured at run
    # time so later brief/corpus edits can never desynchronize the record.
    from task.prompt import environment_card
    row["_artifact"] = {
        "task_id": task_id,
        "model": llm.model,
        "mode": mode,
        "input": {
            "brief": brief,
            "output_contract": contract_text,
            "trigger_input": (variant_input.get("trigger_input") or {}),
            "environment_card": environment_card(seed),
            "schema_card": schema_text,
            "tool_families": sorted(families),
            "task_source": task_source,
            "tool_surface": tool_surface,
            "enriched_tool_docs": enriched_tool_docs,
            "task_visible_constant_count": len(visible_constants),
            "evaluation_time": evaluation_time,
            "tools_exposed": sorted(exposed_names),
            "tools_exposed_count": len(exposed_names),
            "gold_distinct_tools": len(gold_names),
            "distractor_tools_count": len(exposed_names - gold_names),
            "base_budget": base_budget,
            "max_actions": max_actions,
            "initial_plan_hash": result.initial_plan_hash,
            "initial_plan_cache_key": (
                (initial_plan_artifact or {}).get("cache_key")
            ),
        },
        "output": {
            "trajectory": result.trajectory,
            "final_snapshot": final_snapshot,
            "steps": result.steps,
            "plan": result.plan,
            "plan_versions": result.plan_versions,
            "replan_count": result.replan_count,
            "replan_events": result.replan_events,
            "protocol_violations": result.protocol_violations,
            "final_answer": result.final_answer,
            "stop_reason": result.stop_reason,
            "failed_calls": result.failed_calls,
            "plan_fidelity": plan_fidelity,
            "runtime_orchestration": runtime_orchestration,
        },
        "groundtruth": {
            "gold_tool_calls": gold_calls,
            "gold_final_snapshot": gold_snapshot,
            "gold_structural_return": gold_structural_return,
            "expect": expect,
        },
        "verdict": {
            "outcome_pass": outcome["outcome_pass"],
            "outcome_semantic_pass": outcome["outcome_semantic_pass"],
            "canonical_trace_pass": canonical_trace_pass,
            "orchestration_trace_pass": orchestration_trace_pass,
            "side_effect_pass": side_effect_pass,
            "strict_pass": primary_strict_pass,
            "legacy_fixture_strict_pass": bool(verdict["strict_pass"]),
            "outcome_and_strict_pass": bool(
                outcome["outcome_pass"] and primary_strict_pass
            ),
            **verdict["component_metrics"],
            **runtime_orchestration,
            "terminal_exact_pass": outcome["terminal_exact_pass"],
            "terminal_normalized_pass": outcome["terminal_normalized_pass"],
            "terminal_similarity_score": outcome["terminal_similarity_score"],
            "terminal_diff_reason": outcome["terminal_diff_reason"],
            "transient_event_checked": outcome["transient_event_checked"],
            "transient_event_pass": outcome["transient_event_pass"],
            "transient_event_expected_count": outcome[
                "transient_event_expected_count"
            ],
            "transient_event_actual_count": outcome[
                "transient_event_actual_count"
            ],
            "failed_outcome_checks": [c for c in outcome["checks"] if not c["ok"]],
            "plan_fidelity_applicable": plan_fidelity["applicable"],
            **plan_fidelity_flat,
        },
    }
    return row


def main(argv: list[str]) -> int:
    global TASK_DESCRIPTION_FILE, _TASK_DESCRIPTIONS

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-opus-4-8")
    from task.agents import DEFAULT_AGENT_MODES

    default_modes = ",".join(DEFAULT_AGENT_MODES)
    parser.add_argument(
        "--modes",
        default=default_modes,
        help=f"comma-separated agent strategies (default: {default_modes})",
    )
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument(
        "--variants",
        default="0",
        choices=["0", "nonzero", "all"],
        help=(
            "run development variant 0, fresh nonzero variants only, or all variants"
        ),
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true",
                        help="skip tasks already recorded in results.jsonl and append")
    parser.add_argument("--runs", type=int, default=1,
                        help="repeat each task k times; leaderboard CIs use a "
                             "per-task cluster bootstrap")
    parser.add_argument(
        "--max-replans",
        type=int,
        default=2,
        help="maximum accepted suffix replans per Replan variant (default: 2)",
    )
    parser.add_argument(
        "--replan-protocol",
        choices=("v1", "v2"),
        default="v1",
        help="replan review-turn protocol: v1 = canonical single-shot "
             "fail-closed review; v2 = + one repair turn on rejection, the "
             "single-node patch op, resolver-error reviews and a workspace "
             "resource hint on error observations (default: v1)",
    )
    parser.add_argument(
        "--task-source",
        choices=("legacy_brief", "task_description"),
        default="legacy_brief",
        help="agent objective source; orchestration runs use task_description",
    )
    parser.add_argument(
        "--tool-surface",
        choices=("recipe", "broad"),
        default="recipe",
        help="recipe families only, or every agent-visible workspace tool",
    )
    parser.add_argument(
        "--enriched-tool-docs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "include operation, side-effect, and when-to-use guidance in the "
            "shared public tool contracts (default: enabled)"
        ),
    )
    parser.add_argument("--scripted-selftest", action="store_true",
                        help="replay gold trajectories via ScriptedLLM (no API)")
    args = parser.parse_args(argv)

    if (
        args.pilot
        and args.task_source == "task_description"
        and "BENCHMARK_TASK_DESCRIPTION_FILE" not in os.environ
    ):
        TASK_DESCRIPTION_FILE = (
            TASK_DESCRIPTION_PILOT_MANIFEST.parent
            / "exports"
            / "pilot_tasks.jsonl"
        )
        _TASK_DESCRIPTIONS = None

    # BENCHMARK_EVAL_ROOT redirects the whole eval output tree (results,
    # artifacts, default state root) so sharded runs against one endpoint
    # never append to the same results.jsonl.
    eval_root = (Path(os.environ["BENCHMARK_EVAL_ROOT"])
                 if os.environ.get("BENCHMARK_EVAL_ROOT") else EVAL_ROOT_DEFAULT)
    _ensure_isolation(eval_root)
    from task.agents import AGENT_MODES
    from task.llm_client import build_client
    from task.select_recipes import pilot_ids
    from metrics.aggregate import leaderboard

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    unknown = [m for m in modes if m not in AGENT_MODES]
    if unknown:
        raise SystemExit(f"unknown agent mode(s): {unknown}; choices: {sorted(AGENT_MODES)}")
    if args.scripted_selftest and "agent_sdk" in modes:
        raise SystemExit("agent_sdk mode has no scripted selftest (SDK owns the loop)")

    if args.ids:
        ids = args.ids
    elif args.pilot:
        if args.task_source == "task_description":
            pilot_manifest = json.loads(
                TASK_DESCRIPTION_PILOT_MANIFEST.read_text(encoding="utf-8")
            )
            ids = [
                str(recipe_id)
                for recipe_id in pilot_manifest.get("recipe_ids") or []
                if str(recipe_id)
            ]
            if not ids:
                raise SystemExit(
                    "task-description pilot manifest has no recipe IDs: "
                    f"{TASK_DESCRIPTION_PILOT_MANIFEST}"
                )
        else:
            ids = pilot_ids(GT_ROOT)
    else:
        raise SystemExit("select recipes with --ids or --pilot")
    if args.limit:
        ids = ids[: args.limit]

    shared_llm = None
    if not args.scripted_selftest and any(mode != "agent_sdk" for mode in modes):
        # Local transformer clients load many GiB of weights. Construct once
        # per process, then reuse it across tasks and strategies.
        shared_llm = build_client(args.model)

    open_loop_modes = {"plan_execute", "replan"}.intersection(modes)
    frozen_plan_modes = {
        "plan_execute", "replan", "incremental_workflow"
    }.intersection(modes)
    # GLOBAL+INPUT plans inside run_one, once per variant; it only needs a
    # recipe-level artifact under the scripted control.
    per_variant_plan_modes = {"global_input"}.intersection(modes)
    if per_variant_plan_modes and args.task_source != "task_description":
        raise SystemExit("global_input requires --task-source task_description")
    initial_plans_by_mode: dict[str, dict[str, dict[str, Any]]] = {
        mode: {} for mode in frozen_plan_modes | per_variant_plan_modes
    }
    calls_before_initial_planning = int(
        getattr(shared_llm, "calls", 0) or 0
    )
    tokens_before_initial_planning = int(
        getattr(shared_llm, "total_tokens", 0) or 0
    )
    batched_open_loop_plans: dict[str, dict[str, Any]] = {}
    if (
        frozen_plan_modes
        and open_loop_modes
        and not args.scripted_selftest
        and getattr(shared_llm, "batch_initial_plans", False)
    ):
        assert shared_llm is not None
        batched_open_loop_plans = prepare_initial_plans_batched(
            ids,
            shared_llm,
            eval_root,
            model_id=args.model,
            enriched_tool_docs=args.enriched_tool_docs,
        )
    if frozen_plan_modes or (per_variant_plan_modes and args.scripted_selftest):
        if args.task_source != "task_description":
            raise SystemExit(
                "recipe-level frozen plans require --task-source task_description"
            )
        planner_concurrency = max(
            1, int(os.environ.get("VLLM_PLANNER_CONCURRENCY", "1") or "1")
        )
        if (
            "incremental_workflow" in frozen_plan_modes
            and planner_concurrency > 1
            and not args.scripted_selftest
        ):
            # Editor sessions are independent per recipe but the planning
            # loop below is serial; doomed sessions run 1-3 h each and a
            # low-compliance lane would take weeks. Warm the disk cache
            # concurrently (the engine batches concurrent requests exactly
            # as in react mode); the serial loop then reuses every cached
            # artifact, so ordering, prints, and semantics are unchanged.
            # A warmer failure is harmless — the loop re-runs that recipe.
            from concurrent.futures import ThreadPoolExecutor
            assert shared_llm is not None
            def _warm(recipe_id: str) -> None:
                try:
                    prepare_incremental_plan(
                        recipe_id,
                        shared_llm,
                        eval_root,
                        model_id=args.model,
                        enriched_tool_docs=args.enriched_tool_docs,
                    )
                except Exception as exc:
                    print(
                        f"[incremental-warm] recipe {recipe_id}: "
                        f"{type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )
            with ThreadPoolExecutor(max_workers=planner_concurrency) as pool:
                list(pool.map(_warm, ids))
        for recipe_id in ids:
            if args.scripted_selftest:
                artifact = _scripted_initial_plan_artifact(recipe_id, args.model)
                for mode in frozen_plan_modes | per_variant_plan_modes:
                    initial_plans_by_mode[mode][recipe_id] = artifact
                print(json.dumps({
                    "recipe_id": recipe_id,
                    "planning_mode": "scripted_control",
                    "initial_plan_status": artifact.get("status"),
                    "initial_plan_hash": artifact.get("plan_hash"),
                    "cache_reused": artifact.get("cache_reused", False),
                }))
                continue
            if open_loop_modes:
                assert shared_llm is not None
                if batched_open_loop_plans:
                    artifact = batched_open_loop_plans[recipe_id]
                else:
                    try:
                        artifact = prepare_initial_plan(
                            recipe_id,
                            shared_llm,
                            eval_root,
                            model_id=args.model,
                            enriched_tool_docs=args.enriched_tool_docs,
                        )
                    except Exception as exc:
                        print(
                            f"[plan-transport] recipe {recipe_id}: "
                            f"{type(exc).__name__}: {exc}",
                            file=sys.stderr,
                        )
                        traceback.print_exc(file=sys.stderr)
                        artifact = {
                            "status": "invalid_plan",
                            "recipe_id": recipe_id,
                            "model": args.model,
                            "plan": None,
                            "plan_hash": None,
                            "error": f"initial planning failed: {exc}",
                        }
                for mode in open_loop_modes:
                    initial_plans_by_mode[mode][recipe_id] = artifact
                print(json.dumps({
                    "recipe_id": recipe_id,
                    "planning_mode": "open_loop",
                    "initial_plan_status": artifact.get("status"),
                    "initial_plan_hash": artifact.get("plan_hash"),
                    "cache_reused": artifact.get("cache_reused", False),
                }))
            if "incremental_workflow" in frozen_plan_modes:
                assert shared_llm is not None
                try:
                    artifact = prepare_incremental_plan(
                        recipe_id,
                        shared_llm,
                        eval_root,
                        model_id=args.model,
                        enriched_tool_docs=args.enriched_tool_docs,
                    )
                except Exception as exc:
                    artifact = {
                        "status": "invalid_plan",
                        "recipe_id": recipe_id,
                        "model": args.model,
                        "plan": None,
                        "plan_hash": None,
                        "error": f"incremental planning failed: {exc}",
                    }
                initial_plans_by_mode["incremental_workflow"][recipe_id] = artifact
                print(json.dumps({
                    "recipe_id": recipe_id,
                    "planning_mode": "incremental_workflow",
                    "initial_plan_status": artifact.get("status"),
                    "initial_plan_hash": artifact.get("plan_hash"),
                    "planner_calls": artifact.get("planner_calls", 0),
                    "cache_reused": artifact.get("cache_reused", False),
                }))
    calls_after_initial_planning = int(
        getattr(shared_llm, "calls", 0) or 0
    )
    tokens_after_initial_planning = int(
        getattr(shared_llm, "total_tokens", 0) or 0
    )

    for mode in modes:
        mode_initial_plans = initial_plans_by_mode.get(mode, {})
        calls_before_mode = int(getattr(shared_llm, "calls", 0) or 0)
        tokens_before_mode = int(getattr(shared_llm, "total_tokens", 0) or 0)
        run_dir = eval_root / args.model.replace("/", "__") / mode
        run_dir.mkdir(parents=True, exist_ok=True)
        results_path = run_dir / "results.jsonl"
        traj_path = run_dir / "trajectories.jsonl"
        rows: list[dict[str, Any]] = []
        done: set[tuple[str, int]] = set()
        file_mode = "w"
        if args.resume and results_path.exists():
            for line in results_path.read_text().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                rows.append(row)
                done.add((row["task_id"], int(row.get("run_index") or 0)))
            file_mode = "a"
            print(f"[resume] {mode}: {len(done)} tasks already recorded")
        pending_tasks = [
            (recipe_id, variant, run_index)
            for recipe_id in ids
            for variant in _selected_variants(recipe_id, args.variants)
            for run_index in range(max(args.runs, 1))
            if (f"{recipe_id}__v{variant:02d}", run_index) not in done
        ]

        def evaluate_task(task: tuple[str, int, int]) -> dict[str, Any]:
            recipe_id, variant, run_index = task
            if args.scripted_selftest:
                llm = _scripted_from_gold(
                    recipe_id,
                    variant,
                    mode,
                    mode_initial_plans.get(recipe_id),
                )
            elif mode == "agent_sdk":
                from types import SimpleNamespace
                llm = SimpleNamespace(model=args.model)
            else:
                llm = shared_llm
            row = run_one(
                recipe_id,
                variant,
                mode,
                llm,
                eval_root=eval_root,
                task_source=args.task_source,
                tool_surface=args.tool_surface,
                enriched_tool_docs=args.enriched_tool_docs,
                initial_plan_artifact=mode_initial_plans.get(recipe_id),
                max_replans=args.max_replans,
                replan_protocol=args.replan_protocol,
            )
            row["run_index"] = run_index
            return row

        # ReAct turns and GLOBAL+INPUT per-variant planning calls are both
        # independent per variant, so both join the engine's shared batch.
        parallel_react = bool(
            mode in {"react", "global_input"}
            and getattr(shared_llm, "concurrent_batching", False)
            and pending_tasks
        )
        executor = None
        if parallel_react:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            executor = ThreadPoolExecutor(
                max_workers=int(os.environ.get("VLLM_REACT_CONCURRENCY", "16")),
                thread_name_prefix="react-eval",
            )
            futures = [executor.submit(evaluate_task, task) for task in pending_tasks]
            evaluated_rows = (future.result() for future in as_completed(futures))
        else:
            evaluated_rows = map(evaluate_task, pending_tasks)
        with results_path.open(file_mode) as results_fh, traj_path.open(file_mode) as traj_fh:
            try:
                for row in evaluated_rows:
                    run_index = int(row["run_index"])
                    run_payload = row.pop("run", None)
                    artifact = row.pop("_artifact", None)
                    if artifact is not None:
                        artifacts_dir = run_dir / "artifacts"
                        artifacts_dir.mkdir(exist_ok=True)
                        name = f"{row['task_id']}" + (f"_r{run_index}" if args.runs > 1 else "")
                        (artifacts_dir / f"{name}.json").write_text(
                            json.dumps(artifact, indent=1, sort_keys=True, default=str) + "\n")
                    rows.append(row)
                    results_fh.write(json.dumps(row, default=str) + "\n")
                    results_fh.flush()
                    if run_payload is not None:
                        traj_fh.write(json.dumps(
                            {"task_id": row["task_id"], **run_payload}, default=str) + "\n")
                        traj_fh.flush()
                    print(json.dumps({"task_id": row["task_id"], "mode": mode,
                                      "status": row.get("status"),
                                      "strict": row.get("strict_pass")}))
            finally:
                if executor is not None:
                    executor.shutdown(wait=True, cancel_futures=True)
        board = leaderboard(rows)
        board["meta"] = {
            "model": args.model,
            "mode": mode,
            # Record the effective client setting. Newest Anthropic models
            # require API-default sampling and therefore expose None here.
            "temperature_requested": (
                None
                if args.scripted_selftest
                else getattr(shared_llm, "temperature", 0.0)
            ),
            "scripted_selftest": bool(args.scripted_selftest),
            "variants": args.variants,
            "runs_per_task": max(args.runs, 1),
            "n_recipes": len(ids),
            "task_source": args.task_source,
            "tool_surface": args.tool_surface,
            "enriched_tool_docs": args.enriched_tool_docs,
            "cross_variant_frozen_plan": mode in {
                "plan_execute", "replan", "incremental_workflow"
            },
            "per_variant_frozen_plan": mode == "global_input",
            "max_replans": args.max_replans if mode == "replan" else 0,
            "replan_protocol": args.replan_protocol if mode == "replan" else None,
            "initial_plan_hashes": (
                {
                    recipe_id: mode_initial_plans[recipe_id].get("plan_hash")
                    for recipe_id in ids
                }
                if mode in {"plan_execute", "replan", "incremental_workflow"}
                or (mode == "global_input" and args.scripted_selftest)
                else {}
            ),
        }
        if mode == "global_input":
            # Efficiency is reported separately (doc/global_input.md §10): one
            # planning call per variant instead of one per recipe.
            def _sum(key: str) -> int:
                return sum(int(r.get(key) or 0) for r in rows)
            board["meta"]["variant_planning"] = {
                "planning_calls": _sum("planner_calls"),
                "planning_completion_tokens": _sum("planner_tokens"),
                "planning_prompt_tokens": (
                    _sum("planner_prompt_tokens")
                    if any(r.get("planner_prompt_tokens") is not None for r in rows)
                    else None
                ),
                "planning_prompt_chars": _sum("planner_prompt_chars"),
                "planning_failures": sum(
                    1 for r in rows if r.get("status") == "plan_error"
                ),
                "plans_cache_reused": sum(
                    1 for r in rows if r.get("plan_cache_reused")
                ),
                "variants": len(rows),
            }
        if shared_llm is not None:
            total_calls = int(getattr(shared_llm, "calls", 0) or 0)
            board["meta"]["model_runtime"] = {
                key: getattr(shared_llm, key)
                for key in (
                    "backend",
                    "revision",
                    "dtype",
                    "max_new_tokens",
                    "react_max_new_tokens",
                    "react_soft_max_new_tokens",
                    "max_input_tokens",
                    "context_extension",
                    "do_sample",
                    "temperature",
                    "thinking",
                    "effort",
                    "max_tokens",
                    "codex_version",
                    "calls",
                    "total_tokens",
                    "prompt_cache",
                    "api_usage",
                )
                if hasattr(shared_llm, key)
            }
            board["meta"]["initial_plan_artifact_calls"] = sum(
                int(artifact.get("planner_calls", 0) or 0)
                for artifact in mode_initial_plans.values()
            )
            board["meta"]["initial_plan_generation_calls_this_process"] = (
                calls_after_initial_planning - calls_before_initial_planning
            )
            board["meta"]["initial_plan_generation_tokens_this_process"] = (
                tokens_after_initial_planning - tokens_before_initial_planning
            )
            board["meta"]["runtime_llm_calls_this_process"] = (
                total_calls - calls_before_mode
            )
            board["meta"]["runtime_llm_calls_this_mode"] = (
                total_calls - calls_before_mode
            )
            board["meta"]["runtime_llm_tokens_this_mode"] = (
                int(getattr(shared_llm, "total_tokens", 0) or 0)
                - tokens_before_mode
            )
        if mode == "agent_sdk":
            import importlib.metadata
            import subprocess
            try:
                sdk_version = importlib.metadata.version("claude-agent-sdk")
            except Exception:
                sdk_version = "unknown"
            try:
                cli_version = subprocess.run(
                    ["claude", "--version"], capture_output=True,
                    text=True, timeout=30).stdout.strip() or "unknown"
            except Exception:
                cli_version = "unknown"
            board["meta"]["harness"] = {
                "claude_agent_sdk": sdk_version,
                "claude_cli": cli_version,
                "options": {"system_prompt": "benchmark-override",
                            "tools": [], "permission_mode": "bypassPermissions",
                            "setting_sources": [], "strict_mcp_config": True,
                            "disallowed_tools": "all Claude Code built-ins (belt-and-suspenders; tools=[] is primary)",
                            "max_turns": "max_actions + 4",
                            "thinking": "SDK default (adaptive)"},
            }
        (run_dir / "leaderboard.json").write_text(json.dumps(board, indent=2) + "\n")
        print(f"LEADERBOARD {args.model}/{mode}:", json.dumps(board))
    return 0


def _variant_list(recipe_id: str) -> list[int]:
    dirs = sorted(
        path
        for path in (RECIPE_DATA_DIR / recipe_id).glob("variant_*")
        if path.is_dir()
    )
    return [int(d.name.split("_")[1]) for d in dirs]


def _selected_variants(recipe_id: str, selection: str) -> list[int]:
    """Keep development variant 0 separate from fresh generalization cases."""

    if selection == "0":
        return [0]
    variants = _variant_list(recipe_id)
    if selection == "nonzero":
        return [variant for variant in variants if variant != 0]
    if selection == "all":
        return variants
    raise ValueError(f"unknown variant selection: {selection}")


def _scripted_initial_plan_artifact(
    recipe_id: str, model: str = "scripted"
) -> dict[str, Any]:
    """Private scripted control: translate the compiler plan to the protocol."""

    from task.workflow_plan import normalize_plan, plan_hash

    path = TASK_DESCRIPTION_GROUNDTRUTH_DIR / f"{recipe_id}.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    source = (bundle.get("workflow_plan") or {}).get("workflow") or []

    error_bindings: dict[str, str] = {}
    loop_bindings: dict[str, str] = {}
    return_error_bindings: dict[str, str] = {}

    def index(
        values: list[dict[str, Any]], enclosing_try_error: str | None = None
    ) -> None:
        for node in values:
            node_id = str(node.get("id") or "node")
            if node.get("kind") == "try":
                error_bindings[node_id] = f"{node_id}_error"
            if node.get("kind") == "foreach":
                loop_bindings[node_id] = f"{node_id}_item"
            if node.get("kind") == "return" and enclosing_try_error is not None:
                # A return node has no output datapill. One legacy compiler
                # artifact nevertheless points at its success return from the
                # enclosing catch to obtain the caught error message. Preserve
                # that intended catch binding deterministically.
                return_error_bindings[node_id] = enclosing_try_error
            for region in ("then", "else", "body", "catch"):
                if isinstance(node.get(region), list):
                    child_error = enclosing_try_error
                    if node.get("kind") == "try" and region == "body":
                        child_error = error_bindings[node_id]
                    index(node[region], child_error)

    index(source)

    def rewrite(value: Any, current_item_bind: str | None) -> Any:
        if isinstance(value, list):
            return {"expression": {
                "op": "array",
                "items": [rewrite(item, current_item_bind) for item in value],
            }}
        if not isinstance(value, dict):
            return {"literal": value}
        if len(value) == 1 and "literal" in value:
            return deepcopy(value)
        if len(value) == 1 and "input_ref" in value:
            return deepcopy(value)
        if len(value) == 1 and isinstance(value.get("output_ref"), dict):
            payload = value["output_ref"]
            source_node = str(payload.get("node") or payload.get("binding") or "")
            path = list(payload.get("path") or [])
            marker = next((
                index
                for index, part in enumerate(path)
                if part in {"current_item", "<current_item>"}
            ), None)
            if marker is not None and current_item_bind is not None:
                return {"loop_ref": {
                    "binding": current_item_bind,
                    "path": path[marker + 1 :],
                }}
            if source_node in loop_bindings:
                return {"loop_ref": {
                    "binding": loop_bindings[source_node],
                    "path": path,
                }}
            if source_node in return_error_bindings:
                error_path = ["message"] if path[-1:] == ["error_message"] else path
                return {"error_ref": {
                    "binding": return_error_bindings[source_node],
                    "path": error_path,
                }}
            return {"output_ref": {
                "binding": source_node,
                "path": path,
            }}
        if len(value) == 1 and isinstance(value.get("error_ref"), dict):
            payload = dict(value["error_ref"])
            source_node = str(
                payload.get("source_node")
                or payload.get("node")
                or payload.get("binding")
                or ""
            )
            if source_node in error_bindings:
                payload["binding"] = error_bindings[source_node]
            elif source_node:
                payload["binding"] = source_node
            payload.pop("source_node", None)
            payload.pop("node", None)
            return {"error_ref": payload}
        if len(value) == 1 and isinstance(value.get("loop_ref"), dict):
            payload = dict(value["loop_ref"])
            source_node = str(
                payload.get("source_node")
                or payload.get("node")
                or payload.get("binding")
                or ""
            )
            if source_node in loop_bindings:
                payload["binding"] = loop_bindings[source_node]
            elif source_node:
                payload["binding"] = source_node
            payload.pop("source_node", None)
            payload.pop("node", None)
            return {"loop_ref": payload}
        if len(value) == 1 and isinstance(value.get("expression"), dict):
            expression = value["expression"]
            converted: dict[str, Any] = {"op": expression.get("op")}
            for key in ("args", "items", "parts"):
                if key in expression:
                    converted[key] = [
                        rewrite(item, current_item_bind)
                        for item in expression.get(key) or []
                    ]
            if "fields" in expression:
                converted["fields"] = {
                    str(key): rewrite(item, current_item_bind)
                    for key, item in (expression.get("fields") or {}).items()
                }
            for key in ("value", "condition"):
                if key in expression:
                    converted[key] = rewrite(
                        expression.get(key), current_item_bind
                    )
            for key in ("item_bind", "path", "direction"):
                if key in expression:
                    converted[key] = deepcopy(expression[key])
            return {"expression": converted}
        return {"expression": {
            "op": "object",
            "fields": {
                str(key): rewrite(item, current_item_bind)
                for key, item in value.items()
            },
        }}

    def rewrite_condition(value: Any, current_item_bind: str | None) -> Any:
        """Translate the compiler's compound condition card to a boolean AST."""

        expression = value.get("expression") if isinstance(value, dict) else None
        fields = expression.get("fields") if isinstance(expression, dict) else None
        if not (
            isinstance(fields, dict)
            and expression.get("op") == "object"
            and isinstance(fields.get("conditions"), dict)
        ):
            return rewrite(value, current_item_bind)

        def literal(raw: Any) -> Any:
            return raw.get("literal") if isinstance(raw, dict) else None

        conditions_expression = fields["conditions"].get("expression") or {}
        leaves: list[dict[str, Any]] = []
        for raw_leaf in conditions_expression.get("items") or []:
            leaf_expression = (
                raw_leaf.get("expression") if isinstance(raw_leaf, dict) else None
            ) or {}
            leaf_fields = leaf_expression.get("fields") or {}
            operand = str(literal(leaf_fields.get("operand")) or "")
            lhs = rewrite(leaf_fields.get("lhs"), current_item_bind)
            rhs = rewrite(leaf_fields.get("rhs"), current_item_bind)
            binary = {
                "equals_to": "eq",
                "not_equals_to": "ne",
                "greater_than": "gt",
                "less_than": "lt",
            }
            if operand in binary:
                leaves.append({"expression": {
                    "op": binary[operand], "args": [lhs, rhs],
                }})
                continue
            if operand in {"present", "blank"}:
                leaves.append({"expression": {
                    "op": "is_present" if operand == "present" else "is_blank",
                    "args": [lhs],
                }})
                continue
            if operand in {"is_true", "is_not_true"}:
                leaves.append({"expression": {
                    "op": "eq" if operand == "is_true" else "ne",
                    "args": [lhs, {"literal": True}],
                }})
                continue
            method_by_operand = {
                "contains": "include?",
                "not_contains": "include?",
                "starts_with": "starts_with?",
                "ends_with": "ends_with?",
                "not_ends_with": "ends_with?",
            }
            method = method_by_operand.get(operand)
            if method is None:
                raise RuntimeError(f"unsupported canonical condition operand: {operand}")
            method_call: dict[str, Any] = {"expression": {
                "op": "call_method",
                "args": [lhs, {"literal": method}, rhs],
            }}
            if operand.startswith("not_"):
                method_call = {"expression": {"op": "not", "args": [method_call]}}
            leaves.append(method_call)

        connective = str(literal(fields.get("operand")) or "and")
        if connective not in {"and", "or"}:
            raise RuntimeError(f"unsupported canonical condition connective: {connective}")
        if not leaves:
            return {"literal": connective == "and"}
        if len(leaves) == 1:
            return leaves[0]
        return {"expression": {"op": connective, "args": leaves}}

    def translate(
        values: list[dict[str, Any]], current_item_bind: str | None = None
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for node in values:
            kind = node.get("kind")
            node_id = str(node.get("id") or "node")
            if kind == "call":
                out.append({
                    "kind": "call",
                    "tool": node["tool"],
                    "arguments": {
                        str(key): rewrite(value, current_item_bind)
                        for key, value in (node.get("arguments") or {}).items()
                    },
                    "bind": node_id,
                    "purpose": f"Execute canonical {node['tool']} workflow step",
                })
            elif kind == "if":
                out.append({
                    "kind": "if",
                    "condition": rewrite_condition(
                        node.get("condition") or {}, current_item_bind
                    ),
                    "then": translate(node.get("then") or [], current_item_bind),
                    "else": translate(node.get("else") or [], current_item_bind),
                })
            elif kind == "foreach":
                item_bind = loop_bindings[node_id]
                out.append({
                    "kind": "foreach",
                    "items": rewrite(node.get("items") or {}, current_item_bind),
                    "item_bind": item_bind,
                    "body": translate(node.get("body") or [], item_bind),
                })
            elif kind == "repeat":
                out.append({
                    "kind": "repeat",
                    "body": translate(node.get("body") or [], current_item_bind),
                    "until": rewrite_condition(
                        node.get("until") or {}, current_item_bind
                    ),
                })
            elif kind == "try":
                out.append({
                    "kind": "try",
                    "error_bind": error_bindings[node_id],
                    "body": translate(node.get("body") or [], current_item_bind),
                    "catch": translate(node.get("catch") or [], current_item_bind),
                })
            elif kind == "stop":
                out.append({
                    "kind": "stop",
                    "arguments": {
                        str(key): rewrite(value, current_item_bind)
                        for key, value in (node.get("arguments") or {}).items()
                    },
                })
            elif kind == "return":
                out.append({
                    "kind": "return",
                    "value": rewrite(node.get("value"), current_item_bind),
                })
            else:
                raise RuntimeError(f"unsupported canonical plan node kind: {kind}")
        return out

    surface = load_task_description(recipe_id).get("public_tool_surface") or []
    allowed = {
        str(item.get("name") or "")
        for item in surface
        if isinstance(item, dict) and item.get("name")
    }
    plan = normalize_plan(translate(source), allowed)
    return {
        "status": "ok",
        "recipe_id": recipe_id,
        "model": model,
        "plan": plan,
        "plan_hash": plan_hash(plan),
        "cache_key": f"scripted:{recipe_id}",
        "cache_reused": False,
    }


def _scripted_from_gold(
    recipe_id: str,
    variant: int,
    mode: str = "react",
    initial_plan_artifact: dict[str, Any] | None = None,
):
    from task.agents import get_agent
    from task.llm_client import ScriptedLLM
    gold_path = GT_ROOT / recipe_id / f"variant_{variant:02d}" / "output.json"
    gold = json.loads(gold_path.read_text())
    if get_agent(mode).request_initial_plan:
        bundle = json.loads(
            (TASK_DESCRIPTION_GROUNDTRUTH_DIR / f"{recipe_id}.json").read_text(
                encoding="utf-8"
            )
        )
        variant_id = f"{variant:02d}"
        private_variant = next(
            item
            for item in bundle.get("variants") or []
            if str(item.get("variant_id")) == variant_id
        )
        events = [
            item
            for item in (private_variant.get("active_trace") or {}).get("events") or []
            if item.get("event_type") == "tool_call"
        ]
        refs = [
            "p" + str(item.get("plan_node_ref") or "").removeprefix("n")
            for item in events
        ]
        # Gold public calls and ActiveTrace tool-call events are aligned by
        # construction. If a legacy fixture omits a reference, fail loudly.
        if len(refs) != len(gold["tool_calls"]):
            raise RuntimeError(
                f"scripted plan refs do not align for {recipe_id} variant {variant_id}"
            )
        replies = [
            json.dumps({
                "type": "act",
                "plan_node_id": ref,
                "tool": call["tool"],
                "args": call["args"],
            })
            for ref, call in zip(refs, gold["tool_calls"])
        ]
        variant_source = json.loads(
            (
                RECIPE_DATA_DIR
                / recipe_id
                / f"variant_{variant:02d}"
                / "input.json"
            ).read_text(encoding="utf-8")
        )
        forced_source = variant_source.get("force_action_error")
        if isinstance(forced_source, dict):
            mapped_seed = {"force_action_error": forced_source}
            _attach_task_description_forced_error(mapped_seed, recipe_id)
            forced = mapped_seed["force_tool_error"]
            workflow_node = next(
                node
                for node in _task_description_workflow(recipe_id).get("nodes") or []
                if str(node.get("source_as") or "")
                == str(forced_source.get("step_as") or "")
            )
            source_ref = str(
                workflow_node.get("source_ref")
                or workflow_node.get("node_id")
                or ""
            )
            source_mapping = bundle.get("private_source_mapping") or {}
            canonical_node = next(
                node_id
                for node_id, mapped_ref in source_mapping.items()
                if str(mapped_ref) == source_ref
            )
            failed_reply = json.dumps({
                "type": "act",
                "plan_node_id": "p" + canonical_node.removeprefix("n"),
                "tool": forced["tool"],
                "args": forced.get("args_contains") or {},
            })
            # Canonical exception traces begin at the catch because failed
            # connector attempts are absent from successful call logs. The
            # scripted executor must nevertheless make that attempt so the
            # frozen-plan guard observes the try-body failure.
            replies.insert(0, failed_reply)
        replies.append(json.dumps({"type": "finish"}))
    else:
        replies = [json.dumps({"tool": c["tool"], "args": c["args"]})
                   for c in gold["tool_calls"]]
        replies.append(json.dumps({"tool": "finish", "args": {}}))
    return ScriptedLLM(replies)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

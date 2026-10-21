"""Agent-facing usage cards for the simulator's exact tool contracts.

The executable registry remains authoritative for names and JSON schemas.
Workato's recipe-skills material informs the high-level usage language where
available, but never overrides a simulator schema (some skill documents mark
individual recipe-authoring shapes as provisional).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


TERMINAL_TOOLS = {
    "workato_api_platform.return_response",
    "workato_genie.workflow_return_result",
    "workato_recipe_function.return_result",
    "workato_service.send_reply",
}

READ_PREFIXES = (
    "get_",
    "list_",
    "query_",
    "search_",
)
WRITE_PREFIXES = (
    "add_",
    "create_",
    "delete_",
    "insert_",
    "rerun_",
    "start_",
    "stop_",
    "truncate",
    "update_",
    "upsert_",
)
COMMUNICATION_PREFIXES = (
    "open_",
    "post_",
    "publish_",
)

SOURCE_NOTES = {
    "salesforce": (
        "Connector selection concepts cross-checked against "
        "workato-recipe-skills/skills/salesforce-recipes; the simulator "
        "schema below is the executable contract."
    ),
    "slack": (
        "Native Slack versus interactive Workbot usage cross-checked against "
        "workato-recipe-skills/skills/slack-recipes; the simulator schema "
        "below is the executable contract."
    ),
    "slack_bot": (
        "Interactive Workbot usage cross-checked against "
        "workato-recipe-skills/skills/slack-recipes; the simulator schema "
        "below is the executable contract."
    ),
    "workato_db_table": (
        "Data-table read/write concepts cross-checked against "
        "workato-recipe-skills/skills/datatable-recipes; table and column "
        "identifiers must follow the simulator schema/environment cards."
    ),
}


def _operation(name: str) -> str:
    if name in TERMINAL_TOOLS:
        return "terminal"
    action = name.split(".", 1)[-1]
    if action.startswith(READ_PREFIXES):
        return "read"
    if action.startswith(COMMUNICATION_PREFIXES):
        return "communication"
    if action.startswith(WRITE_PREFIXES):
        return "mutation"
    if action in {"call_service", "call_service_async", "wait_for_interval"}:
        return "operation"
    return "transform"


def _usage(name: str, operation: str) -> str:
    action = name.split(".", 1)[-1]
    if operation == "terminal":
        return (
            "Use only when the caller or parent workflow must receive its "
            "final response. Complete prerequisite reads and mutations first; "
            "a successful terminal call can end the run."
        )
    if action.startswith(("search_", "query_", "get_", "list_")):
        return (
            "Use for a targeted read when an identifier, existing value, or "
            "current state is needed by a later decision or mutation. Avoid "
            "speculative reads whose result is already in the prompt."
        )
    if action.startswith("upsert_"):
        return (
            "Use when the task requires create-or-update behavior keyed by the "
            "match fields in the schema. Supply only grounded identifiers and "
            "values."
        )
    if action.startswith("update_"):
        return (
            "Use to change an existing target after its identifier and new "
            "values are known. This is a side effect; do not use it as a read."
        )
    if action.startswith(("add_", "create_", "insert_")):
        return (
            "Use to create new state only when the task requires it and after "
            "checking for duplicates when the task or schema calls for that."
        )
    if action.startswith(("delete_", "truncate")):
        return (
            "Destructive operation. Use only when deletion is explicitly "
            "required and the target is unambiguous."
        )
    if operation == "communication":
        return (
            "Produces a user-visible message, publication, view, or dialog. "
            "Resolve the destination and content first; avoid duplicate sends."
        )
    if action in {"call_service", "call_service_async"}:
        return (
            "Invoke a configured child service only when its result or side "
            "effect is required. The synchronous form returns a seeded reply; "
            "the asynchronous form returns only an acknowledgement."
        )
    if action == "wait_for_interval":
        return "Advance the simulated clock only when the task explicitly requires waiting."
    return (
        "Use for the named deterministic transformation or workflow-runtime "
        "operation when its output is needed by a later step."
    )


def enrich_tool_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Return one portable usage card while preserving the exact schema."""

    result = deepcopy(spec)
    name = str(result.get("name") or "")
    family = name.split(".", 1)[0]
    operation = _operation(name)
    side_effect = operation in {"mutation", "communication", "terminal", "operation"}
    original = str(result.get("description") or "").strip()
    guidance = _usage(name, operation)
    source_note = SOURCE_NOTES.get(
        family,
        "The simulator registry description and JSON schema are the executable contract.",
    )
    result["description"] = " ".join(
        part for part in (original, guidance, source_note) if part
    )
    result["usage"] = {
        "connector_family": family,
        "operation": operation,
        "side_effect": side_effect,
        "when_to_use": guidance,
    }
    return result


def enrich_tool_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_tool_spec(spec) for spec in specs]

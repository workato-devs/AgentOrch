"""Canonical, fail-closed model visibility for runtime execution context."""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from typing import Any

from .recipe_semantics import references


# These are Workato runtime facts, not arbitrary fields copied from a seed.
# A field is exposed only when it is both listed here and referenced by the
# canonical workflow IR.  Keep recipe parameters separately allowlisted: a
# recipe's settings bag may also contain credentials or evaluator fixtures.
PUBLIC_JOB_CONTEXT_FIELDS = frozenset(
    {
        "job_created_at",
        "job_id",
        "job_url",
        "recipe_id",
        "recipe_name",
        "recipe_url",
        "repeated_job",
        "started_at",
        "user_id",
        "user_name",
    }
)
PUBLIC_JOB_CONTEXT_PARAMETER_FIELDS = frozenset(
    {
        "event_date",
        "event_kit_gsheet_id",
        "marketo_id",
    }
)
PUBLIC_RUNTIME_INPUT_FIELDS = ("trigger_input", "runtime_input")


def _has_slack_bot_trigger(workflow_a: dict[str, Any] | None) -> bool:
    for node in (workflow_a or {}).get("nodes") or []:
        if not isinstance(node, dict) or node.get("kind") != "trigger":
            continue
        action = str(
            node.get("recipe_action")
            or node.get("tool_name")
            or node.get("benchmark_tool")
            or ""
        )
        if action.startswith("slack_bot."):
            return True
    return False


def _uses_runtime_clock(workflow_a: dict[str, Any] | None) -> bool:
    for node in (workflow_a or {}).get("nodes") or []:
        if not isinstance(node, dict):
            continue
        semantic_text = json.dumps(
            {
                "arguments": node.get("arguments"),
                "configured_arguments": node.get("configured_arguments"),
                "condition": node.get("condition"),
            },
            sort_keys=True,
        )
        if re.search(
            r"(?:\bnow\b|\btoday\b|\bcurrent_(?:date|time|timestamp)\s*\()",
            semantic_text,
            flags=re.IGNORECASE,
        ):
            return True
    return False


def _safe_workspace_configuration_name(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
    sensitive_markers = {
        "api_key",
        "auth",
        "bearer",
        "client_secret",
        "credential",
        "password",
        "private_key",
        "secret",
        "token",
    }
    return not any(marker in normalized for marker in sensitive_markers)


def _referenced_workspace_properties(
    workflow_a: dict[str, Any] | None,
) -> set[tuple[str, str]]:
    referenced: set[tuple[str, str]] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
            return
        if isinstance(value, list):
            for child in value:
                visit(child)
            return
        if not isinstance(value, str):
            return
        for match in re.finditer(r"_dp\('([^']+)'\)", value):
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            scope = str(payload.get("pill_type") or "")
            name = str(payload.get("property_name") or "").strip()
            if (
                scope in {"account_property", "project_property"}
                and name
                and _safe_workspace_configuration_name(name)
            ):
                referenced.add((scope, name))

    visit((workflow_a or {}).get("nodes") or [])
    return referenced


class PublicExecutionContextError(ValueError):
    """The IR asks for execution context that is not safe to publish."""


def _job_context_reference_paths(
    workflow_a: dict[str, Any] | None,
) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    for reference in references(workflow_a or {}):
        is_job_context_pill = reference.get("pill_type") == "job_context"
        is_job_context_data_path = (
            reference.get("dialect") == "data_path"
            and reference.get("provider") == "workato"
            and reference.get("line") == "job_context"
        )
        if not (is_job_context_pill or is_job_context_data_path):
            continue
        path = tuple(
            str(item)
            for item in reference.get("path") or []
            if isinstance(item, (str, int))
        )
        if path:
            paths.add(path)
    return paths


def _validate_reference_paths(paths: set[tuple[str, ...]]) -> None:
    unsupported = sorted(
        path
        for path in paths
        if not (
            (len(path) == 1 and path[0] in PUBLIC_JOB_CONTEXT_FIELDS)
            or (
                len(path) == 2
                and path[0] == "parameters"
                and path[1] in PUBLIC_JOB_CONTEXT_PARAMETER_FIELDS
            )
        )
    )
    if unsupported:
        rendered = ", ".join(".".join(path) for path in unsupported)
        raise PublicExecutionContextError(
            "workflow references non-public job_context fields: " + rendered
        )


def _public_scalar(value: Any, path: tuple[str, ...]) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return deepcopy(value)
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise PublicExecutionContextError(
        "public execution-context field must be a JSON scalar: "
        + ".".join(path)
    )


def canonical_public_execution_context(
    variant_input: dict[str, Any],
    workflow_a: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return only referenced, explicitly safe top-level job context.

    ``seed.job_context`` is intentionally never considered.  Seed sections
    are private simulator fixtures; a runtime value that a model needs must be
    represented canonically by top-level ``job_context`` in the input variant.
    """

    paths = _job_context_reference_paths(workflow_a)
    _validate_reference_paths(paths)
    public: dict[str, Any] = {}
    source = variant_input.get("job_context")
    if isinstance(source, dict):
        for path in sorted(paths):
            if len(path) == 1:
                field = path[0]
                if field in source:
                    public[field] = _public_scalar(source[field], path)
                continue
            parameters = source.get("parameters")
            field = path[1]
            if isinstance(parameters, dict) and field in parameters:
                public.setdefault("parameters", {})[field] = _public_scalar(
                    parameters[field],
                    path,
                )
    if "now" in variant_input:
        public["now"] = _public_scalar(variant_input["now"], ("now",))
    if _has_slack_bot_trigger(workflow_a):
        trigger = variant_input.get("trigger_input")
        if isinstance(trigger, dict):
            channel = trigger.get("channel")
            message_ts = trigger.get("message_ts", trigger.get("ts"))
            parameters = (
                trigger.get("parameters")
                if isinstance(trigger.get("parameters"), dict)
                else {}
            )
            invoking_user = trigger.get("user", parameters.get("user"))
            invoking_message: dict[str, Any] = {}
            if channel not in (None, ""):
                invoking_message["channel"] = _public_scalar(
                    channel, ("invoking_message", "channel")
                )
            if message_ts not in (None, ""):
                invoking_message["message_ts"] = _public_scalar(
                    message_ts, ("invoking_message", "message_ts")
                )
            if invoking_user not in (None, ""):
                invoking_message["user"] = _public_scalar(
                    invoking_user, ("invoking_message", "user")
                )
            if invoking_message:
                public["invoking_message"] = invoking_message
    workspace_configuration: dict[str, dict[str, Any]] = {}
    for scope, name in sorted(_referenced_workspace_properties(workflow_a)):
        container_name = (
            "account_properties"
            if scope == "account_property"
            else "project_properties"
        )
        source_container = variant_input.get(container_name)
        if isinstance(source_container, dict) and name in source_container:
            workspace_configuration.setdefault(container_name, {})[name] = (
                _public_scalar(
                    source_container[name],
                    ("workspace_configuration", container_name, name),
                )
            )
    if workspace_configuration:
        public["workspace_configuration"] = workspace_configuration
    return public


def public_execution_context_schema(
    workflow_a: dict[str, Any] | None,
) -> dict[str, Any]:
    """Describe safe job-context fields referenced by canonical A.

    This is recipe-level and value-free, so it may be published before any
    runtime variant is selected. Concrete values remain in the per-variant
    ``execution_context`` payload produced below.
    """

    paths = _job_context_reference_paths(workflow_a)
    _validate_reference_paths(paths)
    properties: dict[str, Any] = {}
    if _uses_runtime_clock(workflow_a):
        properties["now"] = {
            "title": "Current Time",
            "description": (
                "The benchmark-supplied current timestamp for this run when the "
                "workflow depends on current date or time."
            ),
            "type": ["string", "number", "null"],
        }
    if _has_slack_bot_trigger(workflow_a):
        properties["invoking_message"] = {
            "title": "Invoking Slack Message",
            "description": (
                "Runtime identity of the Slack message/conversation that "
                "invoked the bot command, when present."
            ),
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "message_ts": {"type": "string"},
                "user": {"type": "string"},
            },
            "additionalProperties": False,
        }
    referenced_configuration = _referenced_workspace_properties(workflow_a)
    if referenced_configuration:
        configuration_properties: dict[str, Any] = {}
        for scope, name in sorted(referenced_configuration):
            container_name = (
                "account_properties"
                if scope == "account_property"
                else "project_properties"
            )
            container = configuration_properties.setdefault(
                container_name,
                {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            )
            container["properties"][name] = {
                "title": name,
                "type": ["string", "number", "boolean", "null"],
            }
        properties["workspace_configuration"] = {
            "title": "Workspace Configuration",
            "description": (
                "Non-secret workspace configuration referenced by this "
                "workflow. Values are supplied at runtime and may vary "
                "between runs."
            ),
            "type": "object",
            "properties": configuration_properties,
            "additionalProperties": False,
        }
    for path in sorted(paths):
        if len(path) == 1:
            properties[path[0]] = {
                "title": path[0].replace("_", " ").title(),
                "type": ["string", "number", "boolean", "null"],
            }
            continue
        parameters = properties.setdefault(
            "parameters",
            {"title": "Parameters", "type": "object", "properties": {}},
        )
        parameters["properties"][path[1]] = {
            "title": path[1].replace("_", " ").title(),
            "type": ["string", "number", "boolean", "null"],
        }
    return {"type": "object", "properties": properties}


def canonical_public_runtime_input(
    variant_input: dict[str, Any],
    workflow_a: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the one public runtime payload used by every pipeline stage."""

    public = {
        key: deepcopy(variant_input[key])
        for key in PUBLIC_RUNTIME_INPUT_FIELDS
        if key in variant_input
    }
    execution_context = canonical_public_execution_context(
        variant_input,
        workflow_a,
    )
    if execution_context:
        public["execution_context"] = execution_context
    return public


def private_execution_context(
    variant_input: dict[str, Any],
    workflow_a: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return unexposed top-level job context for the hidden Stage 8 shard."""

    source = variant_input.get("job_context")
    if not isinstance(source, dict):
        return {}
    private = deepcopy(source)
    public = canonical_public_execution_context(variant_input, workflow_a)
    for field in public:
        if field == "parameters":
            parameters = private.get("parameters")
            if isinstance(parameters, dict):
                for parameter in public["parameters"]:
                    parameters.pop(parameter, None)
                if not parameters:
                    private.pop("parameters", None)
        else:
            private.pop(field, None)
    return private

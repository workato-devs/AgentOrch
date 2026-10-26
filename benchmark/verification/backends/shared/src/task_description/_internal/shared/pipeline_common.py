from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..paths import DEFAULT_ARTIFACT_ROOT, PROJECT_ROOT


DEFAULT_INPUT_ROOT = PROJECT_ROOT / "dataset" / "input_recipes"

STAGE_DIRECTORIES = {
    0: "00_source_packages",
    1: "01_canonical_ir",
    2: "02_annotations",
    3: "03_task_plans",
    4: "04_candidates",
    5: "05_workflowllm_samples",
    6: "06_semantic_validation",
    7: "07_variant_validation",
    8: "08_final",
}

# These actions terminate the current recipe by their own execution semantics.
# Communication-like names are deliberately not enough: in particular,
# workato_service.send_reply is non-terminal unless an explicit stop or the end
# of the enclosing control-flow path follows it.
INHERENTLY_TERMINAL_TOOLS = {
    "workato_api_platform.return_response",
    "workato_genie.workflow_return_result",
    "workato_recipe_function.return_result",
}
# Backwards-compatible name for existing artifact consumers.
TERMINAL_TOOLS = INHERENTLY_TERMINAL_TOOLS

INTERNAL_COMPUTE_TOOL_PREFIXES = (
    "clock.",
    "json_parser.",
    "logger.",
    "workato_list.",
    "workato_smart_list.",
    "workato_variable.",
)


def tool_is_inherently_terminal(tool: str) -> bool:
    return tool in INHERENTLY_TERMINAL_TOOLS

RAW_RECIPE_RE = re.compile(
    r"Complete raw recipe:\s*```json\s*(?P<json>\{.*\})\s*```",
    flags=re.S,
)


class PipelineError(RuntimeError):
    """Raised when an artifact or source package violates a pipeline invariant."""


def stable_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def stable_json_hash(value: Any) -> str:
    return hashlib.sha256(stable_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PipelineError(f"missing JSON artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PipelineError(f"invalid JSON artifact {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    """Atomically persist a human-readable JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_structured_failure_artifact(
    output_path: Path,
    exc: Exception,
) -> Path | None:
    failure = getattr(exc, "structured_generation_failure", None)
    if not isinstance(failure, dict):
        return None
    timestamp = dt.datetime.now(dt.timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    path = (
        output_path.parent
        / "failures"
        / f"{output_path.stem}_{timestamp}.json"
    )
    write_json(
        path,
        {
            **failure,
            "rejected": True,
            "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
    )
    return path


def load_raw_recipe(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PipelineError(f"missing raw recipe: {path}") from exc
    match = RAW_RECIPE_RE.search(text)
    if not match:
        raise PipelineError(
            f"{path} does not contain a 'Complete raw recipe' JSON block"
        )
    try:
        raw = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        raise PipelineError(f"invalid embedded recipe JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PipelineError(f"embedded recipe in {path} must be a JSON object")
    return raw


def walk_raw_nodes(node: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(node, dict):
        return
    yield node
    for child in node.get("block") or []:
        yield from walk_raw_nodes(child)


def nested_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [
            text
            for item in value.values()
            for text in nested_strings(item)
        ]
    if isinstance(value, list):
        return [
            text
            for item in value
            for text in nested_strings(item)
        ]
    return [value] if isinstance(value, str) else []


def action_tool(node: dict[str, Any]) -> str:
    provider = str(node.get("provider") or "")
    name = str(node.get("name") or "")
    return f"{provider}.{name}" if provider and name else ""


def discover_recipe_ids(input_root: Path) -> list[str]:
    ids = [
        path.name
        for path in input_root.iterdir()
        if path.is_dir()
        and path.name.isdigit()
        and (path / "raw_recipe.md").is_file()
    ]
    return sorted(ids, key=lambda item: (len(item), item))


def select_recipe_ids(
    input_root: Path,
    requested: Iterable[str] | None,
    limit: int = 0,
) -> list[str]:
    available = discover_recipe_ids(input_root)
    requested_list = [str(item) for item in (requested or [])]
    if requested_list:
        available_set = set(available)
        missing = [item for item in requested_list if item not in available_set]
        if missing:
            raise PipelineError(f"recipe IDs not found under {input_root}: {missing}")
        ids = list(dict.fromkeys(requested_list))
    else:
        ids = available
    return ids[:limit] if limit else ids


def stage_directory(artifact_root: Path, stage: int) -> Path:
    try:
        name = STAGE_DIRECTORIES[stage]
    except KeyError as exc:
        raise PipelineError(f"unknown pipeline stage: {stage}") from exc
    return artifact_root / name


def stage_artifact_path(artifact_root: Path, stage: int, recipe_id: str) -> Path:
    return stage_directory(artifact_root, stage) / f"{recipe_id}.json"


def load_stage_artifact(
    artifact_root: Path,
    stage: int,
    recipe_id: str,
) -> dict[str, Any]:
    value = read_json(stage_artifact_path(artifact_root, stage, recipe_id))
    if not isinstance(value, dict):
        raise PipelineError(
            f"stage {stage} artifact for {recipe_id} must be a JSON object"
        )
    if str(value.get("recipe_id") or "") != str(recipe_id):
        raise PipelineError(
            f"stage {stage} artifact ID mismatch for {recipe_id}: "
            f"{value.get('recipe_id')!r}"
        )
    return value


def add_common_stage_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input-root",
        type=Path,
        default=DEFAULT_INPUT_ROOT,
        help="directory containing <recipe_id>/raw_recipe.md bundles",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help="root directory for all persisted stage artifacts",
    )
    parser.add_argument(
        "--recipe-id",
        action="append",
        dest="recipe_ids",
        help="process only this recipe ID; repeat for multiple IDs",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="maximum recipes to process after selection; 0 means all",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing artifact instead of skipping it",
    )


def artifact_should_run(path: Path, overwrite: bool) -> bool:
    return overwrite or not path.exists()


def print_stage_summary(
    stage: int,
    written: int,
    skipped: int,
    failed: list[dict[str, str]],
) -> None:
    print(
        json.dumps(
            {
                "stage": stage,
                "stage_directory": STAGE_DIRECTORIES[stage],
                "written": written,
                "skipped": skipped,
                "failed": failed,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def normalize_variant_id(path: Path) -> str:
    name = path.name
    return name.removeprefix("variant_") if name.startswith("variant_") else name


def selected_variant_dirs(input_root: Path, recipe_id: str) -> list[Path]:
    """Return explicitly selected variants, or every variant when unpinned."""

    recipe_root = input_root / recipe_id
    available = {
        normalize_variant_id(path): path
        for path in recipe_root.glob("variant_*")
        if path.is_dir() and (path / "input.json").is_file()
    }
    selection_path = recipe_root / "variant_selection.json"
    if not selection_path.is_file():
        return [available[key] for key in sorted(available)]
    selection = read_json(selection_path)
    included = [
        str(value)
        for value in selection.get("included_variant_ids") or []
    ]
    if not included or len(included) != len(set(included)):
        raise PipelineError(
            f"{selection_path} must select unique variant IDs"
        )
    missing = sorted(set(included) - set(available))
    if missing:
        raise PipelineError(
            f"{selection_path} selects missing variants {missing}"
        )
    return [available[key] for key in included]


def json_schema_from_workato_fields(fields: Any) -> dict[str, Any]:
    if not isinstance(fields, list):
        return {}
    properties: dict[str, Any] = {}
    required: list[str] = []
    type_map = {
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        "date_time": "string",
        "date": "string",
        "string": "string",
    }
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "")
        if not name:
            continue
        workato_type = str(field.get("type") or "string")
        schema: dict[str, Any] = {
            "type": type_map.get(workato_type, "string"),
        }
        label = field.get("label")
        if label:
            schema["title"] = str(label)
        if workato_type in {"date", "date_time"}:
            schema["format"] = "date-time" if workato_type == "date_time" else "date"
        if workato_type == "object" and isinstance(field.get("properties"), list):
            nested = json_schema_from_workato_fields(field["properties"])
            schema.update(nested)
        if workato_type == "array":
            schema["items"] = {"type": "object"}
            if isinstance(field.get("properties"), list):
                schema["items"].update(
                    json_schema_from_workato_fields(field["properties"])
                )
        properties[name] = schema
        if field.get("optional") is False:
            required.append(name)
    result: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def public_input_schema(raw: dict[str, Any]) -> dict[str, Any]:
    raw_input = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    request = raw_input.get("request") if isinstance(raw_input.get("request"), dict) else {}
    encoded_schema = request.get("schema")
    if isinstance(encoded_schema, str) and encoded_schema.strip():
        try:
            decoded = json.loads(encoded_schema)
        except json.JSONDecodeError:
            decoded = None
        schema = json_schema_from_workato_fields(decoded)
        if schema.get("properties"):
            return schema

    extended = raw.get("extended_output_schema")
    schema = json_schema_from_workato_fields(extended)
    if schema.get("properties"):
        return schema

    if isinstance(raw_input, dict) and raw_input:
        return {
            "type": "object",
            "properties": {
                str(key): {"type": _json_type(value)}
                for key, value in raw_input.items()
            },
        }
    return {"type": "object", "properties": {}}


def _json_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def tool_side_effect_class(tool: str) -> str:
    name = tool.rsplit(".", 1)[-1]
    if tool in INHERENTLY_TERMINAL_TOOLS:
        return "terminal"
    if any(
        token in name
        for token in (
            "post",
            "send",
            "reply",
            "publish",
            "return",
            "open_bot",
        )
    ):
        return "communication"
    if any(
        token in name
        for token in (
            "add",
            "create",
            "update",
            "upsert",
            "delete",
            "truncate",
            "insert",
            "start_recipe",
            "stop_recipe",
            "rerun",
        )
    ):
        return "write"
    if any(
        token in name
        for token in (
            "get",
            "search",
            "list",
            "lookup",
            "query",
            "parse",
        )
    ):
        return "read"
    return "compute"


def tool_is_observable(tool: str) -> bool:
    if tool.startswith(INTERNAL_COMPUTE_TOOL_PREFIXES):
        return False
    return tool_side_effect_class(tool) in {
        "terminal",
        "communication",
        "write",
    }

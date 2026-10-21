from __future__ import annotations

import hashlib
import json
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..paths import PACKAGE_ROOT


VENDOR_ROOT = PACKAGE_ROOT / "vendor"
LABS_ROOT = VENDOR_ROOT / "workato-labs"
RECIPE_SKILLS_ROOT = VENDOR_ROOT / "workato-recipe-skills"

LABS_URL = "https://github.com/workato-devs/labs"
RECIPE_SKILLS_URL = "https://github.com/workato-devs/recipe-skills"

CONNECTOR_SKILLS = {
    "asana": "asana-recipes",
    "gmail": "gmail-recipes",
    "jira": "jira-recipes",
    "salesforce": "salesforce-recipes",
    "slack": "slack-recipes",
    "slack_bot": "slack-recipes",
    "stripe": "stripe-recipes",
    "workato_db_table": "datatable-recipes",
}

ACTION_REFERENCES = {
    "salesforce.search_sobjects": [
        "skills/salesforce-recipes/SKILL.md",
        "skills/salesforce-recipes/patterns/search-sobjects.md",
        "skills/salesforce-recipes/lint-rules.json",
    ],
    "workato_api_platform.return_response": [
        "skills/workato-recipes/SKILL.md",
        "skills/workato-recipes/triggers/api-endpoint.md",
    ],
    "logger.log_message": [
        "skills/workato-recipes/control-flow/if-else.md",
        "skills/workato-recipes/control-flow/try-catch.md",
    ],
}

ACTION_FACTS = {
    "salesforce.search_sobjects": [
        "The action finds Salesforce records by exact field-match criteria.",
        "sobject_name selects the Salesforce object; other configured field "
        "inputs are combined with AND logic.",
        "Use filters for exact field matches and set the required query input "
        "to an empty string. Use a non-empty query only for predicates that "
        "filters cannot represent; never restate the same predicate in both.",
        "field_list selects returned fields and the output is an array under "
        "the configured SObject name.",
    ],
    "workato_api_platform.return_response": [
        "The action returns the configured API response to the caller.",
        "A successful return_response is inherently recipe-terminal.",
        "The response input is exactly the caller-visible JSON body. Put the "
        "HTTP status only in http_status_code, and do not add response-name "
        "or content-type metadata as fields inside response unless Q names "
        "those fields as part of the JSON body.",
        "Its response schema and configured response body must be preserved.",
    ],
    "logger.log_message": [
        "The public repository contains logger examples but no dedicated "
        "logger connector action reference.",
        "The configured message remains authoritative for this recipe action.",
    ],
}

ACTION_SUPPORT_LEVEL = {
    "salesforce.search_sobjects": "action_specific",
    "workato_api_platform.return_response": "action_specific",
    "logger.log_message": "examples_only",
}


@lru_cache(maxsize=None)
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=None)
def _git_revision(path: Path) -> str | None:
    if not path.is_dir():
        return None
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    revision = completed.stdout.strip()
    return revision if completed.returncode == 0 and revision else None


def repository_provenance() -> dict[str, Any]:
    return {
        "hub": {
            "repository": LABS_URL,
            "local_path": str(LABS_ROOT),
            "revision": _git_revision(LABS_ROOT),
            "role": (
                "Workato public labs hub that points recipe development to "
                "the Workato Developer Skills repository"
            ),
        },
        "connector_documentation": {
            "repository": RECIPE_SKILLS_URL,
            "local_path": str(RECIPE_SKILLS_ROOT),
            "revision": _git_revision(RECIPE_SKILLS_ROOT),
            "role": (
                "versioned Workato recipe and connector guidance consumed by "
                "the pipeline"
            ),
        },
    }


def _source_record(relative_path: str) -> dict[str, Any] | None:
    path = RECIPE_SKILLS_ROOT / relative_path
    if not path.is_file():
        return None
    revision = _git_revision(RECIPE_SKILLS_ROOT)
    url = (
        f"{RECIPE_SKILLS_URL}/blob/{revision}/{relative_path}"
        if revision
        else f"{RECIPE_SKILLS_URL}/blob/main/{relative_path}"
    )
    return {
        "local_path": str(path),
        "repository_path": relative_path,
        "url": url,
        "sha256": _sha256(path),
    }


def _connector_sources(provider: str) -> list[str]:
    skill = CONNECTOR_SKILLS.get(provider)
    if not skill:
        return []
    paths = [f"skills/{skill}/SKILL.md", f"skills/{skill}/lint-rules.json"]
    return [
        path
        for path in paths
        if (RECIPE_SKILLS_ROOT / path).is_file()
    ]


def _lint_action_status(provider: str, action: str) -> bool | None:
    skill = CONNECTOR_SKILLS.get(provider)
    if not skill:
        return None
    path = RECIPE_SKILLS_ROOT / "skills" / skill / "lint-rules.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    actions = payload.get("valid_action_names")
    if not isinstance(actions, list):
        return None
    return action in {str(item) for item in actions}


@lru_cache(maxsize=None)
def public_tool_documentation(tool: str) -> dict[str, Any]:
    provider, _, action = tool.partition(".")
    relative_sources = list(
        dict.fromkeys(
            [
                *ACTION_REFERENCES.get(tool, []),
                *_connector_sources(provider),
            ]
        )
    )
    source_records = [
        record
        for relative_path in relative_sources
        if (record := _source_record(relative_path)) is not None
    ]
    exact_action_documented = (
        ACTION_SUPPORT_LEVEL.get(tool) == "action_specific"
    )
    connector_documented = provider in CONNECTOR_SKILLS
    if tool in ACTION_SUPPORT_LEVEL:
        support_level = ACTION_SUPPORT_LEVEL[tool]
    elif connector_documented:
        support_level = "connector_level"
    else:
        support_level = "not_present_in_public_recipe_skills"
    facts = ACTION_FACTS.get(tool, [])
    if not facts and connector_documented:
        facts = [
            "Connector-level Workato guidance and the connector lint catalog "
            "are available; the raw recipe configuration remains authoritative "
            "for action-specific business semantics."
        ]
    return {
        "support_level": support_level,
        "exact_action_documented": exact_action_documented,
        "connector_documented": connector_documented,
        "action_name_recognized_by_lint_catalog": _lint_action_status(
            provider, action
        ),
        "sources": source_records,
        "authoritative_facts": facts,
        "absence_note": (
            None
            if source_records
            else (
                "No dedicated entry for this legacy/internal action was found "
                "in the vendored Workato recipe-skills repository. Preserve the "
                "raw recipe input, embedded schemas, and simulator tool surface."
            )
        ),
    }


def configured_action_schemas(
    raw: dict[str, Any],
    tool: str,
    walk_nodes: Any,
    action_tool: Any,
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for node in walk_nodes(raw):
        if node.get("keyword") != "action" or action_tool(node) != tool:
            continue
        occurrences.append(
            {
                "number": node.get("number"),
                "as": node.get("as"),
                "configured_input": (
                    node.get("input")
                    if isinstance(node.get("input"), dict)
                    else {}
                ),
                "dynamic_pick_list_selection": (
                    node.get("dynamicPickListSelection")
                    if isinstance(node.get("dynamicPickListSelection"), dict)
                    else {}
                ),
                "extended_input_schema": node.get("extended_input_schema") or [],
                "extended_output_schema": node.get("extended_output_schema") or [],
            }
        )
    return occurrences

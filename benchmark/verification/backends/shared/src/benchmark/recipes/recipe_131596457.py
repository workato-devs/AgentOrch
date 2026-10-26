from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131596457
from .salesforce_recipe_utils import (
    collect_actions,
    copy_expect,
    replace_tokens,
    run_salesforce_recipe,
    salesforce_refs,
    seed_salesforce_state,
)


RECIPE_ID = "131596457"
SEED_TYPE = "genie_salesforce_opportunity_team_member_lookup_variant"
TRACK = "live_salesforce_genie_opportunity_team_lookup"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
EXPECTED_ACTIONS = [
    ("workato_variable", "declare_variable"),
    ("salesforce", "search_sobjects_soql"),
    ("workato_variable", "update_variables"),
    ("salesforce", "search_sobjects_soql_v2"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_runtime.update_variables",
    "salesforce.search_records",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = [
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "salesforce.search_records",
    "workato_genie.workflow_return_result",
]


def validate_131596457(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    declare_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if "OpportunityID" not in str(declare_input):
        raise RuntimeError(f"recipe {RECIPE_ID} OpportunityID variable mapping changed")
    name_search_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if name_search_input.get("sobject_name") != "Opportunity" or "OpportunityName" not in str(name_search_input.get("query") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Opportunity name fallback search changed")
    team_search_input = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    team_query = str(team_search_input.get("query") or "")
    if "FROM OpportunityTeamMember" not in team_query or "OpportunityId" not in team_query:
        raise RuntimeError(f"recipe {RECIPE_ID} OpportunityTeamMember query changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_131596457(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131596457(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    refs = salesforce_refs(provision)
    trigger = replace_tokens(trigger_input(ctx), refs)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    # Both Genie parameters are optional in the raw schema, but the recipe is
    # meaningless without at least one: a blank OpportunityID takes the IF#3
    # name-fallback branch (search_sobjects_soql by OpportunityName), so that
    # branch requires a non-blank OpportunityName instead.
    if not isinstance(parameters, dict) or (
        parameters.get("OpportunityID") in (None, "")
        and parameters.get("OpportunityName") in (None, "")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input requires parameters.OpportunityID or parameters.OpportunityName"
        )
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": replace_tokens(copy_expect(data), refs),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_131596457(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_131596457(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_131596457,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]

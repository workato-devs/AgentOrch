from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_128375319
from .salesforce_recipe_utils import collect_actions, copy_expect, replace_tokens, run_salesforce_recipe, salesforce_refs, seed_salesforce_state


RECIPE_ID = "128375319"
SEED_TYPE = "genie_salesforce_opportunity_team_lookup_variant"
TRACK = "live_salesforce_genie_lookup"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
EXPECTED_ACTIONS = [
    ("salesforce", "search_sobjects"),
    ("salesforce", "search_sobjects_soql_v2"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = ["salesforce.search_records", "salesforce.search_records", "workato_genie.workflow_return_result"]
ALLOWED_TOOLS = ["salesforce.search_records", "workato_genie.workflow_return_result"]


def validate_128375319(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    query_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if "FROM OpportunityTeamMember" not in str(query_input.get("query") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} OpportunityTeamMember SOQL changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def _seed_salesforce_with_existing_users(data: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    """Provision seed.salesforce in two phases when existing_users are declared.

    The harness registers salesforce.existing_users as read-only rows but does
    NOT expose their live ids as $-ref tokens inside a single provision call
    (owned records are created in the same pass, before any module code can see
    the resolved User). An OpportunityTeamMember row needs a REAL UserId at
    create time, so:

      phase A: provision only the existing_users declaration and resolve the
               read-only User (fail-fast when the org has no match);
      phase B: replace $USER_ID / $USER_EMAIL tokens in the remaining section
               and provision the owned records;
      merge:   carry phase A's read_only_records into phase B's run state and
               snapshot so the recipe's live User search and the trigger/expect
               token replacement see the full read-only row set.

    Cleanup semantics are unchanged: only phase B creates owned records, and
    the merged state keeps exactly those under owned_records. Variants without
    existing_users take the single-call path untouched.
    """
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    section = seed_in.get("salesforce")
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    existing_users = section.get("existing_users")
    if not existing_users:
        return seed_salesforce_state(RECIPE_ID, data, ctx)
    if not isinstance(existing_users, list):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.existing_users must be a list")
    users_provision = ctx.tools.call(
        "harness.salesforce.seed_records",
        {"salesforce": {"existing_users": deepcopy(existing_users)}},
    )
    if not users_provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} existing_users provisioning failed: {users_provision}")
    user_refs = salesforce_refs(users_provision)
    if not user_refs.get("$USER_ID"):
        raise RuntimeError(f"recipe {RECIPE_ID} existing_users resolved no read-only User id")
    rest = {key: deepcopy(value) for key, value in section.items() if key != "existing_users"}
    records_provision = ctx.tools.call(
        "harness.salesforce.seed_records",
        {"salesforce": replace_tokens(rest, user_refs)},
    )
    if not records_provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {records_provision}")
    state = deepcopy(records_provision["state"])
    users_state = users_provision.get("state") if isinstance(users_provision.get("state"), dict) else {}
    state["read_only_records"] = [deepcopy(row) for row in users_state.get("read_only_records") or []] + list(
        state.get("read_only_records") or []
    )
    snapshot = deepcopy(records_provision.get("snapshot") or {})
    users_snapshot_records = (
        ((users_provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or []
    )
    salesforce_snapshot = snapshot.setdefault("salesforce", {})
    salesforce_snapshot["records"] = list(salesforce_snapshot.get("records") or []) + [
        deepcopy(row) for row in users_snapshot_records
    ]
    return {"ok": True, "state": state, "snapshot": snapshot}


def seed_128375319(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128375319(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = _seed_salesforce_with_existing_users(data, ctx)
    refs = salesforce_refs(provision)
    trigger = replace_tokens(trigger_input(ctx), refs)
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else None
    if not isinstance(context, dict) or not context.get("user_email"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing context.user_email")
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


def run_128375319(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_128375319(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_128375319,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]

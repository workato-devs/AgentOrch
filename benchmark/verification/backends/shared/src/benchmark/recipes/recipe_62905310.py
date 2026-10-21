from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_62905310
from .salesforce_recipe_utils import (
    collect_actions,
    copy_expect,
    replace_tokens,
    run_salesforce_recipe,
    salesforce_refs,
    seed_salesforce_state,
)


RECIPE_ID = "62905310"
SEED_TYPE = "salesforce_platform_event_embedded_opportunity_guard_variant"
TRACK = "live_salesforce_platform_event_embedded_opportunity"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_platform_event"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "search_sobjects"),
    ("salesforce", "search_sobjects_soql"),
    ("salesforce", "upsert_sobject"),
    ("salesforce", "update_sobject"),
    ("salesforce", "update_sobject"),
    ("salesforce", "search_sobjects"),
    ("salesforce", "composite_update_sobject"),
    ("workato_variable", "declare_variable"),
    ("salesforce", "search_sobjects"),
    ("salesforce", "update_sobject"),
    ("salesforce", "update_sobject"),
    ("workato_variable", "declare_variable"),
    ("salesforce", "search_sobjects"),
    ("salesforce", "create_custom_object"),
    ("salesforce", "update_sobject"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.upsert_record",
    "salesforce.update_record",
    "workato_runtime.declare_variable",
    "salesforce.create_record",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.upsert_record",
    "salesforce.update_record",
    "salesforce.create_record",
]


def validate_62905310(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    raw_input = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(raw_input.get("event_name") or "") != "Embedded_Opportunity__e":
        raise RuntimeError(f"recipe {RECIPE_ID} platform event changed")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    first_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if first_input.get("sobject_name") != "Opportunity" or "Opportunity_ID__c" not in str(first_input):
        raise RuntimeError(f"recipe {RECIPE_ID} embedded Opportunity lookup changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_62905310(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_62905310(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    refs = salesforce_refs(provision)
    # Per-ref live-id tokens ($<REF>_ID, recipe_122139155 precedent) so the
    # branch-coverage variants can pin exact seeded-record ids in trigger and
    # expect blocks. Ref tokens override the sobject-derived defaults, matching
    # the harness's own in-seed substitution order.
    refs.update(_seed_ref_tokens(data, provision))
    trigger = replace_tokens(trigger_input(ctx), refs)
    if not trigger.get("Opportunity_ID__c"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing Opportunity_ID__c")
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


def run_62905310(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    result = run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_62905310(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_62905310,
    )
    id_map = (seed.get("salesforce_live") or {}).get("user_id_map") or {}
    if id_map:
        # Expose the declared translation to the verifier and re-verify so
        # the named read-back check lands in the verification ARTIFACT (the
        # exception clause requires the assertion in verification, not just
        # a runtime fail-fast).
        details = result.setdefault("details", {})
        details["user_id_map"] = dict(id_map)
        _attest_owner_translation(seed, result)
        result["verifier"] = verify_62905310(result)
        result["ok"] = bool(result.get("ok")) and bool(result["verifier"].get("ok"))
    return result


def _attest_owner_translation(seed: dict[str, Any], result: dict[str, Any]) -> None:
    """Foreign-ID translation attestation (benmark_rules foreign-ID
    exception): when the seed declares a user_id_map, the live read-back must
    show the MAPPED owner on some created record and the raw source-org
    literal on none — the translation is evidenced, never hidden."""
    id_map = (seed.get("salesforce_live") or {}).get("user_id_map") or {}
    if not id_map:
        return
    details = result.get("details") or {}
    snapshot = (details.get("final_snapshot") or {}).get("salesforce") or {}
    by_id = {
        str(record.get("id")): (record.get("fields") or {})
        for record in snapshot.get("records") or []
        if isinstance(record, dict)
    }
    # Records whose CREATE args carried a mapped foreign owner are the ones
    # the exception clause covers: each must read back with the mapped live
    # target, and the raw literal must appear on no live record.
    attested: list[dict[str, str]] = []
    for call in result.get("tool_calls") or []:
        args_fields = ((call.get("args") or {}).get("fields")
                       if isinstance(call.get("args"), dict) else None) or {}
        foreign = str(args_fields.get("OwnerId") or "")
        if foreign not in id_map:
            continue
        created_id = str((call.get("result") or {}).get("id") or "")
        live_owner = str((by_id.get(created_id) or {}).get("OwnerId") or "")
        if live_owner != str(id_map[foreign]):
            raise RuntimeError(
                f"recipe {RECIPE_ID}: created record {created_id} reads back "
                f"OwnerId {live_owner!r}, expected mapped {id_map[foreign]!r}"
            )
        attested.append({"record": created_id, "foreign": foreign,
                         "live_owner": live_owner})
    leaked = sorted(
        record_id for record_id, fields in by_id.items()
        if str(fields.get("OwnerId") or "") in id_map
    )
    if leaked:
        raise RuntimeError(
            f"recipe {RECIPE_ID}: foreign OwnerId leaked into live records {leaked}"
        )
    if not attested:
        raise RuntimeError(
            f"recipe {RECIPE_ID}: user_id_map declared but no create call used "
            "a mapped OwnerId — remove the map or fix the variant"
        )
    details["owner_translation_attested"] = attested


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]


def _seed_ref_tokens(data: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    """$<REF>_ID tokens for every seeded record carrying a ref name, zipped
    seed-order to provisioned snapshot order (recipe_122139155 precedent).
    Fail-fast on any seed/snapshot mismatch — a silent partial map would let a
    variant pin the wrong live id."""
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    seed_section = seed_in.get("salesforce") if isinstance(seed_in.get("salesforce"), dict) else {}
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    owned = [
        record for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and not record.get("read_only")
    ]
    if len(owned) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned)} provisioned"
        )
    refs: dict[str, str] = {}
    for seed_record, live in zip(seed_records, owned):
        ref = str(seed_record.get("ref") or "").strip()
        live_id = str(live.get("id") or "")
        if ref and not live_id:
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record for ref {ref!r} has no live id")
        if ref:
            refs[f"${ref.upper()}_ID"] = live_id
    return refs

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_125223317


RECIPE_ID = "125223317"
SEED_TYPE = "salesforce_campaign_activity_dup_notes_backfill_variant"
TRACK = "live_salesforce_campaign_activity_dup_notes_backfill"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "updated_custom_object"
TRIGGER_AS = "d808c1bc"
CA_SOBJECT = "Campaign_Activity__c"
SEARCH_AS = "0e6d3a4e"
UPDATE_AS = "978585f0"
FILTER_CAMPAIGN_FRAGMENT = "7011N000000xp4nQAA"
# Schema-in-seed contract: Campaign_Activity__c ALREADY EXISTS in the
# benchmark org (114149061 / 88707765 precedent; object + Campaign__c/
# Email__c/Notes__c verified live via tooling 2026-07-07). All three are
# TEXT custom fields -- ensure_custom_field only re-grants FLS, it never
# re-creates them. No mdapi deploy involved.
REQUIRED_SCHEMA = [
    {"sobject": CA_SOBJECT, "field": "Campaign__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Email__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Notes__c", "sf_type": "Text"},
]
TRIGGER_KEYS = ("Campaign__c", "Email__c", "Notes__c", "CreatedDate")
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SAME_DAY_RE = re.compile(r"^\$SAME_DAY_AS:([A-Za-z0-9_]+)$")
_CREATED_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+0000$")

# salesforce.updated_custom_object on Campaign_Activity__c (as d808c1bc,
# since 2024-01-01). The trigger payload is SEED-AUTHORED (never polled --
# 122911418 precedent); it dereferences exactly Campaign__c / Email__c
# (search filters), Notes__c (update value) and CreatedDate (day-equality).
#
# TRIGGER FILTER (2 AND conditions):
#   1. Campaign__c contains '7011N000000xp4nQAA'  (org-foreign campaign id
#      living INSIDE a benchmark-authored Text value)
#   2. Notes__c present
# Body:
#   2  salesforce.search_sobjects 0e6d3a4e (LIVE): Campaign_Activity__c,
#      non-metadata input keys map to EQUALITY filters (Campaign__c =
#      trigger.Campaign__c AND Email__c = trigger.Email__c), field_list
#      Id/OwnerId/CreatedDate/Notes__c/Email__c/Campaign__c is metadata-only
#      (ignored by the adapter), limit 150. Result carries records + the
#      sobject-named list + list_size.
#   IF 3 (list_size greater_than '1'):
#     FOREACH 4 (as d8fe011c over 0e6d3a4e.Campaign_Activity__c, simple):
#       IF 5 (foreach.Notes__c blank):
#         IF 6 ('=foreach.CreatedDate.to_date' equals_to
#               '=trigger.CreatedDate.to_date'  -- DAY equality, time-of-day
#               truncated on both sides):
#           7  salesforce.update_sobject 978585f0 (LIVE):
#              id = foreach.Id, Notes__c = trigger.Notes__c
#
# DETERMINISM: live CreatedDate is an UNSEEDABLE audit field. The same-day
# variant authors trigger.CreatedDate as the token '$SAME_DAY_AS:<REF>'; the
# seeder reads the referenced record's LIVE CreatedDate back from the
# provision snapshot and derives a same-UTC-day timestamp at a DIFFERENT
# clock time (proving .to_date truncation, not string equality). Because
# CreatedDate is immutable once seeded, the derived comparison is stable at
# any later run time -- no midnight coupling. Different-day variants pin a
# fixed past timestamp instead.
#
# Branch mapping (per benmark_rules):
# - variant_00 dup_backfilled_same_day: filter true; trigger-record + blank-
#   notes dup share Campaign+Email (list_size 2 > 1); dup CreatedDate is
#   same-day as the derived trigger.CreatedDate -> ONE update writes
#   trigger.Notes__c onto the dup; the trigger-record row is skipped at IF 5
#   (its Notes are present); an off-email decoy proves the Email__c filter.
# - variant_01 dup_blank_but_older_day: IF 6 false (fixed past
#   trigger.CreatedDate) -> no update.
# - variant_02 dup_notes_present_skip: IF 5 false (dup already carries
#   Notes) -> no update.
# - variant_03 no_duplicates: IF 3 false (only the trigger record matches;
#   off-campaign and off-email decoys prove BOTH equality filters).
# - variant_04 trigger_filter_skip: blank trigger.Notes__c fails filter
#   condition 2 -> zero actions, nothing seeded live.
#
# Backends: salesforce LIVE. Cleanup deletes all owned Campaign_Activity__c
# records in a finally block (the recipe updates a benchmark-owned record).

_STRUCTURE_PINS_JSON = r"""[{"as": "d808c1bc", "filter": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"d808c1bc\",\"path\":[\"Campaign__c\"]}')}", "operand": "contains", "rhs": "7011N000000xp4nQAA"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"d808c1bc\",\"path\":[\"Notes__c\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "input": {"field_list": "Id\nOwnerId\nWorked_By__c\nCampaign__c\nName\nNotes__c\nSDR_Notes__c\nManager_Notes__c\nLead__c\nContact__c\nCreatedDate\nLastActivityDate\nEmail__c", "since": "<anon>2024-01-01T00:00:00-08:00</anon>", "sobject_name": "Campaign_Activity__c"}, "keyword": "trigger", "name": "updated_custom_object", "number": 1, "provider": "salesforce", "skip": false}, {"as": "0e6d3a4e", "input": {"Campaign__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"d808c1bc\",\"path\":[\"Campaign__c\"]}')}", "Email__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"d808c1bc\",\"path\":[\"Email__c\"]}')}", "field_list": "Id\nOwnerId\nCreatedDate\nNotes__c\nEmail__c\nCampaign__c", "limit": "150", "sobject_name": "Campaign_Activity__c"}, "keyword": "action", "name": "search_sobjects", "number": 2, "provider": "salesforce", "skip": false}, {"as": null, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"0e6d3a4e\",\"path\":[\"list_size\"]}')}", "operand": "greater_than", "rhs": "1"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 3, "provider": null, "skip": false}, {"as": "d8fe011c", "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"0e6d3a4e\",\"path\":[\"Campaign_Activity__c\"]}')}"}, "keyword": "foreach", "name": null, "number": 4, "provider": null, "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"0e6d3a4e\",\"path\":[\"Campaign_Activity__c\"]}')}"}, {"as": null, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d8fe011c\",\"path\":[\"Notes__c\"]}')}", "operand": "blank", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 5, "provider": null, "skip": false}, {"as": null, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d8fe011c\",\"path\":[\"CreatedDate\"]}').to_date", "operand": "equals_to", "rhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"d808c1bc\",\"path\":[\"CreatedDate\"]}').to_date"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 6, "provider": null, "skip": false}, {"as": "978585f0", "input": {"Notes__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"d808c1bc\",\"path\":[\"Notes__c\"]}')}", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d8fe011c\",\"path\":[\"Id\"]}')}", "sobject_name": "Campaign_Activity__c"}, "keyword": "action", "name": "update_sobject", "number": 7, "provider": "salesforce", "skip": false}]"""

STRUCTURE_PINS: list[dict] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.update_record",
]
EXPECT_KEYS = (
    "case",
    "trigger_filter_matched",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "final_notes",
)


def _structure(node: dict[str, Any]) -> list[dict[str, Any]]:
    pin: dict[str, Any] = {
        "keyword": node.get("keyword"),
        "number": node.get("number"),
        "as": node.get("as"),
        "provider": node.get("provider"),
        "name": node.get("name"),
        "skip": bool(node.get("skip")),
        "input": node.get("input") or {},
    }
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_125223317(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("sobject_name") or "") != CA_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sobject changed")
    if not isinstance(raw.get("filter"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter missing")
    if FILTER_CAMPAIGN_FRAGMENT not in json.dumps(raw.get("filter")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger filter campaign fragment changed "
            f"(expected contains {FILTER_CAMPAIGN_FRAGMENT!r})"
        )
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "trigger_sobject": CA_SOBJECT,
        "actions": [
            {
                "number": pin["number"],
                "provider": pin["provider"],
                "name": pin["name"],
                "as": pin["as"],
            }
            for pin in actions
        ],
    }


def seed_125223317(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125223317(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    _require_expect_shape(expect)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    salesforce_section = seed_in.get("salesforce")
    filter_matched = expect.get("trigger_filter_matched")
    if filter_matched and salesforce_section is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter-matched variants search live records: "
            "seed.salesforce is required"
        )
    if not filter_matched and salesforce_section is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the filter-skip variant runs zero actions; "
            "it must not provision live records"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
    }
    if salesforce_section is not None:
        _require_salesforce_section(salesforce_section, trigger)
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(salesforce_section)}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(salesforce_section, provision)
        trigger = _derive_same_day_created_date(trigger, salesforce_section, provision)
        trigger = _replace_value(trigger, refs)
        expect = _replace_value(deepcopy(expect), refs)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    else:
        expect = deepcopy(expect)
    _require_resolved(trigger)
    _require_resolved(expect)
    out["trigger"] = trigger
    out["expect"] = expect
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_125223317(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125223317(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("salesforce_live"), dict)
    if expect.get("trigger_filter_matched") and not live:
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter-matched variants require live salesforce state"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, live)
    finally:
        if live:
            # Required cleanup: the run updates a benchmark-owned live record.
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
            details["cleanup_response"] = cleanup_response
    if live and not (cleanup_response or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_125223317(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if tuple(sorted(trigger.keys())) != tuple(sorted(TRIGGER_KEYS)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly {sorted(TRIGGER_KEYS)} "
            f"(the dereferenced field_list subset); got {sorted(trigger.keys())}"
        )
    for key in ("Campaign__c", "Email__c"):
        if not isinstance(trigger.get(key), str) or not trigger[key].strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger.{key} must be a non-empty string")
    if not isinstance(trigger.get("Notes__c"), str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger.Notes__c must be a string ('' exercises the "
            "filter-skip branch)"
        )
    created = trigger.get("CreatedDate")
    if not isinstance(created, str) or not (
        _CREATED_DATE_RE.fullmatch(created) or _SAME_DAY_RE.fullmatch(created)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger.CreatedDate must be a fixed "
            "'YYYY-MM-DDTHH:MM:SS.mmm+0000' timestamp or the '$SAME_DAY_AS:<REF>' "
            f"seeder-derivation token: {created!r}"
        )


def _require_salesforce_section(section: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
    unexpected = sorted(set(section) - {"schema", "records"})
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected} "
            "(equality-filter search + update need no strict/expansion flags)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)} (FLS re-ensure on the pre-existing live fields)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    for record in records:
        if not isinstance(record, dict) or str(record.get("sobject") or "") != CA_SOBJECT:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must all be {CA_SOBJECT}: {record}"
            )
        if not str(record.get("ref") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs a 'ref': {record}")
        fields = record.get("fields")
        if not isinstance(fields, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seeded record needs explicit fields: {record}")
        for key in ("Name", "Campaign__c", "Email__c"):
            if not str(fields.get(key) or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} {CA_SOBJECT} seed must set {key}: {record}")
        extra = sorted(set(fields) - {"Name", "Campaign__c", "Email__c", "Notes__c"})
        if extra:
            raise RuntimeError(f"recipe {RECIPE_ID} seed fields out of contract: {extra}")
        if "Notes__c" in fields:
            if not isinstance(fields["Notes__c"], str) or not fields["Notes__c"].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} a seeded Notes__c must be non-empty (Salesforce "
                    "create silently drops empty strings -- blank-notes records must use "
                    f"read_fields ['Notes__c'] instead): {record}"
                )
            if record.get("read_fields") is not None:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} records with seeded Notes__c must not also declare "
                    f"read_fields: {record}"
                )
        elif record.get("read_fields") != ["Notes__c"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} blank-notes records must declare read_fields "
                f"['Notes__c'] so the live null read-back drives the IF-5 blank check: {record}"
            )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if not isinstance(expect.get("trigger_filter_matched"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.trigger_filter_matched must be a bool")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    final_notes = expect.get("final_notes")
    if not isinstance(final_notes, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_notes must map every seeded record's id token "
            "to its expected final Notes__c ({} on the filter-skip variant)"
        )
    if expect["trigger_filter_matched"]:
        if tools[:1] != ["salesforce.search_records"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-matched variants always run the search first"
            )
        if not final_notes:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-matched variants must pin final_notes for every "
                "seeded record"
            )
    else:
        if tools or expect.get("executed_action_count") != 0 or final_notes:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the filter-skip variant runs zero actions and seeds "
                "nothing: tools [], executed_action_count 0, final_notes {}"
            )


def _derive_same_day_created_date(
    trigger: dict[str, Any],
    seed_section: dict[str, Any],
    provision: dict[str, Any],
) -> dict[str, Any]:
    created = str(trigger.get("CreatedDate") or "")
    match = _SAME_DAY_RE.fullmatch(created)
    if not match:
        return trigger
    ref = match.group(1).lower()
    seed_records = [row for row in seed_section.get("records") or [] if isinstance(row, dict)]
    index = next(
        (idx for idx, row in enumerate(seed_records) if str(row.get("ref") or "").lower() == ref),
        None,
    )
    if index is None:
        raise RuntimeError(f"recipe {RECIPE_ID} $SAME_DAY_AS references unknown ref {ref!r}")
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    records = [row for row in salesforce_snapshot.get("records") or [] if isinstance(row, dict)]
    if index >= len(records):
        raise RuntimeError(f"recipe {RECIPE_ID} provision snapshot missing record {index}")
    fields = records[index].get("fields") if isinstance(records[index].get("fields"), dict) else {}
    live_created = str(fields.get("CreatedDate") or "")
    if not _CREATED_DATE_RE.fullmatch(live_created):
        raise RuntimeError(
            f"recipe {RECIPE_ID} live CreatedDate read-back has an unexpected shape: "
            f"{live_created!r} (audit-field derivation needs 'YYYY-MM-DDTHH:MM:SS.mmm+0000')"
        )
    # Same UTC day, guaranteed-different clock time: .to_date truncation is
    # what makes IF-6 true, never full-timestamp equality. CreatedDate is
    # immutable, so this derivation stays valid on any later run.
    day = live_created[:10]
    hour = int(live_created[11:13])
    derived = f"{day}T{'18:30:00.000+0000' if hour < 12 else '06:30:00.000+0000'}"
    if derived == live_created:
        raise RuntimeError(f"recipe {RECIPE_ID} same-day derivation collided with the live value")
    out = dict(trigger)
    out["CreatedDate"] = derived
    return out


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_ids)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = live_ids[idx]
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {_replace_str(key, refs): _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        return _replace_str(value, refs)
    return value


def _replace_str(value: str, refs: dict[str, str]) -> str:
    out = value
    for token, replacement in refs.items():
        out = out.replace(token, replacement)
    return out


def _require_resolved(value: Any) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(
            f"recipe {RECIPE_ID} unresolved seed tokens remain: {sorted(set(leftover))}"
        )


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return ctx.tools.call("harness.salesforce.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_96969599


RECIPE_ID = "96969599"
SEED_TYPE = "salesforce_slack_dynamic_account_menu_variant"
TRACK = "live_salesforce_slack_dynamic_account_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "1a17b594"
LOGGER_AS = "3aea41e4"
SEARCH_URL_AS = "ff34358d"
SEARCH_PREFIX_AS = "3cc8cfc8"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# slack_bot.dynamic_menu 'Select Account' (as 1a17b594; parameters
# account_name/contact_id are declared but never dereferenced). Body:
#   IF 2 (trigger typeahead.value contains 'https'):
#     3  logger.log_message 3aea41e4:
#        =typeahead.value.split("Account/").last.gsub(/\/view/,"").strip
#        (lightning URL -> bare record id; trailing whitespace stripped)
#     4  salesforce.search_sobjects_soql_v2 ff34358d (LIVE, limit 30):
#        SELECT Id,Name,Owner.Name FROM Account
#        WHERE Id = '#{logger.message}' ORDER BY Name ASC
#     5  slack_bot.generate_menu_options dcf3a3c2:
#        options ____source = records, label '#{Name} (#{Owner.Name})',
#        value Id
#   ELSE 6:
#     7  salesforce.search_sobjects_soql_v2 3cc8cfc8 (LIVE, limit 30):
#        SELECT Id,Name,Owner.Name FROM Account
#        WHERE Name LIKE '#{typeahead.value}%' ORDER BY Name ASC
#        (LIKE is PREFIX-ANCHORED like live SOQL -- engine f9d83a51:
#        'Acme%' must NOT match 'Big Acme'; case-insensitive)
#     8  slack_bot.generate_menu_options 6d379c93 (same mapping)
#
# Branch mapping (per benmark_rules):
# - variant_00 url_id_lookup   : IF true; parsed id hits one owned Account ->
#   one option (trailing space in the URL proves .strip).
# - variant_01 url_no_match    : IF true; well-formed foreign id -> [] options
#   (seeded decoys prove the emptiness is the Id filter).
# - variant_02 prefix_search   : ELSE; 'Acm' -> two prefix matches returned in
#   ORDER BY Name ASC (seeded in reverse order to prove the sort); the seeded
#   contains-not-prefix decoy ('Big Acme...') proves LIKE anchoring.
# - variant_03 prefix_no_match : ELSE; 'qqq' -> [] options against the same
#   style of seeded pool.
#
# Backends: salesforce LIVE. Owner.Name is a live-org join: every seeded
# Account declares read_fields ['OwnerId'] and the seed enables
# relationship_expansion so search read-back attaches Owner={Id,Name} from
# the live User record (the org integration user -- run-dependent, threaded
# into expects as $USER_NAME via the current_user seed section).
# slack_bot.generate_menu_options is a payload echo (no live Slack post).
# Cleanup deletes all owned Accounts in a finally block (read-only recipe,
# but owned records must not leak).

_STRUCTURE_PINS_JSON = r"""[{"as": "1a17b594", "input": {"dynamic_menu_name": "Select Account", "parameters": "[\n  {\n    \"name\": \"account_name\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"control_type\": \"text\",\n    \"label\": \"Account name\"\n  },\n  {\n    \"name\": \"contact_id\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"control_type\": \"text\",\n    \"label\": \"Contact ID\"\n  }\n]"}, "keyword": "trigger", "name": "dynamic_menu", "number": 1, "provider": "slack_bot", "skip": false}, {"as": null, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"1a17b594\",\"path\":[\"typeahead\", \"value\"]}')}", "operand": "contains", "rhs": "https"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 2, "provider": null, "skip": false}, {"as": "3aea41e4", "input": {"message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"1a17b594\",\"path\":[\"typeahead\",\"value\"]}').split(\"Account/\").last.gsub(/\\/view/,\"\").strip", "user_logs_enabled": "false"}, "keyword": "action", "name": "log_message", "number": 3, "provider": "logger", "skip": false}, {"as": "ff34358d", "input": {"limit": "30", "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"},{\"properties\":[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"}],\"label\":\"Owner\",\"type\":\"object\",\"name\":\"Owner\"}]", "query": "SELECT Id,Name,Owner.Name FROM Account WHERE Id = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"3aea41e4\",\"path\":[\"message\"]}')}' ORDER BY Name ASC"}, "keyword": "action", "name": "search_sobjects_soql_v2", "number": 4, "provider": "salesforce", "skip": false}, {"as": "dcf3a3c2", "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ff34358d\",\"path\":[\"records\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ff34358d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ff34358d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Owner\", \"Name\"]}')})", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ff34358d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"}}, "keyword": "action", "name": "generate_menu_options", "number": 5, "provider": "slack_bot", "skip": false}, {"as": null, "input": {}, "keyword": "else", "name": null, "number": 6, "provider": null, "skip": false}, {"as": "3cc8cfc8", "input": {"limit": "30", "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"},{\"properties\":[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"}],\"label\":\"Owner\",\"type\":\"object\",\"name\":\"Owner\"}]", "query": "SELECT Id,Name,Owner.Name FROM Account WHERE Name LIKE '#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"1a17b594\",\"path\":[\"typeahead\", \"value\"]}')}%' ORDER BY Name ASC"}, "keyword": "action", "name": "search_sobjects_soql_v2", "number": 7, "provider": "salesforce", "skip": false}, {"as": "6d379c93", "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"3cc8cfc8\",\"path\":[\"records\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"3cc8cfc8\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"3cc8cfc8\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Owner\", \"Name\"]}')})", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"3cc8cfc8\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"}}, "keyword": "action", "name": "generate_menu_options", "number": 8, "provider": "slack_bot", "skip": false}]"""

STRUCTURE_PINS: list[dict] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.log_message",
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
EXPECT_KEYS = (
    "case",
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "logger_message",
    "resolved_query",
    "menu_options",
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


def validate_96969599(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
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


def seed_96969599(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_96969599(raw)
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
    _require_salesforce_section(seed_in.get("salesforce"))
    expect = data.get("expect")
    _require_expect_shape(expect, trigger)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
    trigger = _replace_value(trigger, refs)
    _require_resolved(trigger)
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_resolved(resolved_expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        # Expected SOQL text / option values are this run's live Account ids
        # and the live integration user's Name ($USER_NAME), threaded via
        # $REF tokens (106603524 / 110005007 precedent).
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_96969599(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_96969599(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    live_state = seed["salesforce_live"]
    if not live_state.get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(anchored LIKE / Id equality / ORDER BY are strict-only)"
        )
    if not live_state.get("expand_relationships"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires relationship_expansion in the live state "
            "(the Owner.Name label join resolves via expanded parents)"
        )
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
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
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup: owned Account seeds must not leak into later runs
        # (the recipe itself only reads).
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_96969599(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"typeahead"} or not isinstance(trigger.get("typeahead"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'typeahead': {{'value': ...}}}} "
            "(the only dereferenced trigger output)"
        )
    typeahead = trigger["typeahead"]
    if set(typeahead) != {"value"} or not isinstance(typeahead.get("value"), str) or not typeahead["value"].strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger typeahead must carry exactly a non-empty string 'value'"
        )


def _require_salesforce_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(anchored LIKE / Id equality / ORDER BY Name ASC are strict-only)"
        )
    if section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(Owner.Name in the option label walks the expanded live User parent)"
        )
    if section.get("current_user") != {"sobject": "User"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.current_user must be {{'sobject': 'User'}} "
            "(the owner of benchmark-created Accounts; pins $USER_NAME in expects)"
        )
    if "schema" in section:
        raise RuntimeError(
            f"recipe {RECIPE_ID} touches only standard Account fields; "
            "seed.salesforce.schema must be absent"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    for record in records:
        if not isinstance(record, dict) or str(record.get("sobject") or "") != "Account":
            raise RuntimeError(f"recipe {RECIPE_ID} seeded records must all be Accounts: {record}")
        if not str(record.get("ref") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded Account needs a 'ref': {record}")
        fields = record.get("fields")
        if not isinstance(fields, dict) or set(fields) != {"Name"} or not str(fields.get("Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Account carries exactly a non-empty Name: {record}"
            )
        if record.get("read_fields") != ["OwnerId"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Account must declare read_fields ['OwnerId'] "
                "(the live owner id feeds the Owner.Name relationship expansion): "
                f"{record}"
            )


def _require_expect_shape(expect: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    if tools != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every reachable path runs exactly one search + one "
            f"generate_menu_options: expect.tools must equal {ALLOWED_TOOLS}"
        )
    if not isinstance(expect.get("menu_options"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.menu_options must pin the exact rendered options "
            "([] on the no-match branches)"
        )
    if not isinstance(expect.get("resolved_query"), str) or not expect["resolved_query"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} expect.resolved_query must pin the resolved SOQL text")
    contains_https = "https" in str(trigger["typeahead"]["value"])
    branch = expect.get("branch")
    if branch == "url":
        if not contains_https:
            raise RuntimeError(
                f"recipe {RECIPE_ID} branch 'url' requires a typeahead containing 'https'"
            )
        if expect.get("executed_action_count") != 3:
            raise RuntimeError(f"recipe {RECIPE_ID} the url branch runs 3 actions (logger+search+menu)")
        if not isinstance(expect.get("logger_message"), str) or not expect["logger_message"].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} url variants must pin expect.logger_message (the parsed id)"
            )
    elif branch == "prefix":
        if contains_https:
            raise RuntimeError(
                f"recipe {RECIPE_ID} branch 'prefix' requires a typeahead NOT containing 'https'"
            )
        if expect.get("executed_action_count") != 2:
            raise RuntimeError(f"recipe {RECIPE_ID} the prefix branch runs 2 actions (search+menu)")
        if expect.get("logger_message") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} prefix variants never run the logger: logger_message must be null"
            )
    else:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be 'url' or 'prefix': {branch!r}")


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    snapshot_records = [row for row in salesforce_snapshot.get("records") or [] if isinstance(row, dict)]
    owned = [row for row in snapshot_records if not row.get("read_only")]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(owned) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        record_id = str(owned[idx].get("id") or "")
        if not record_id:
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record {idx} has no id")
        refs[f"${ref.upper()}_ID"] = record_id
    users = [
        row for row in snapshot_records
        if row.get("read_only") and str(row.get("sobject") or "") == "User"
    ]
    if len(users) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected exactly the current_user read-only User row "
            f"in the provision snapshot; got {len(users)}"
        )
    user_fields = users[0].get("fields") if isinstance(users[0].get("fields"), dict) else {}
    user_name = str(user_fields.get("Name") or "")
    if not user_name:
        raise RuntimeError(f"recipe {RECIPE_ID} current user has no Name to pin option labels")
    refs["$USER_ID"] = str(users[0].get("id") or "")
    refs["$USER_NAME"] = user_name
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_resolved(value: Any) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(
            f"recipe {RECIPE_ID} unresolved seed tokens remain: {sorted(set(leftover))}"
        )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.salesforce.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118905064


RECIPE_ID = "118905064"
SEED_TYPE = "slack_dynamic_menu_repgenie_fields_variant"
TRACK = "live_salesforce_slack_dynamic_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "b8aa6233"
MENU_NAME = "[RepGenie] Fields"
LOOKUP_TABLE_ID = "4026533"
TRIGGER_PARAM_KEYS = {"api_name", "object_name"}
# menu_branch -> (search step number, search as, menu step number, menu as)
BRANCH_STEPS = {
    "lookup": ("3", "7fb98fac", "4", "e89c104c"),
    "contact": ("7", "b1582dc0", "8", "586380ee"),
    "object": ("10", "1ecaa00b", "11", "0dc00721"),
}
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# slack_bot.dynamic_menu '[RepGenie] Fields' (as b8aa6233; optional trigger
# parameters api_name / object_name plus the typeahead box):
#   IF 2 (parameters.api_name present):
#     3  lookup_table.search_entries 7fb98fac on table 4026533
#        '[Rep Genie] Picklist Lookups' by col1 = api_name (Workato-internal
#        mock, seeded per variant)
#     4  slack_bot.generate_menu_options e89c104c over the entries
#        (label = entry.col2, value = entry.col3; use_option_groups false ->
#        plain flattened options, no option_groups key)
#   ELSIF 5 (parameters.object_name present):
#     IF 6 (object_name == 'Contact'):
#       7  salesforce.search_sobjects_soql_v2 b1582dc0 (LIVE):
#          SELECT Id, Name, Email FROM Contact WHERE Name like
#          '%<typeahead.value>%' AND IsDeleted = false (limit 150)
#       8  generate_menu_options 586380ee (label '#{Name} (#{Email})',
#          value Id)
#     ELSE 9:
#       10 salesforce.search_sobjects_soql_v2 1ecaa00b (LIVE, dynamic FROM
#          #{parameters.object_name}): SELECT Id, Name FROM <object> WHERE
#          Name like '%<typeahead.value>%' AND IsDeleted = false (limit 150)
#       11 generate_menu_options 0dc00721 (label Name, value Id)
#   neither parameter present -> the whole body is skipped: a legal
#   zero-action dynamic-menu job.
#
# Branch mapping (per benmark_rules):
# - variant_00 lookup  : api_name present -> lookup search (2 matching rows +
#   1 decoy col1) -> menu from col2/col3.
# - variant_01 contact : object_name='Contact' -> live Contact SOQL matches
#   the two seeded 'Bench 118905064 Zx *' contacts (LastName-only seeds:
#   the live Contact Name renders as the LastName), excludes the Kappa decoy
#   -> menu 'Name (Email)' / Id.
# - variant_02 object  : object_name='Account' -> ELSE arm, dynamic FROM ->
#   the two seeded Zx accounts match, Kappa decoy excluded -> menu Name / Id.
# - variant_03 none    : parameters {} -> IF 2 false ('=_dp' present on a
#   missing key -> MISSING -> false) and ELSIF 5 false -> zero actions.
#
# Backends: lookup_table 4026533 is a Workato-internal per-variant mock (read
# only here -> the snapshot must be identical before/after). Salesforce runs
# LIVE against benchmark-owned records; seed.salesforce.strict_soql_conditions
# MUST be true ('IsDeleted = false' is an unquoted-boolean leaf that only the
# strict evaluator understands - lenient mode would silently drop it) and
# every record MUST declare read_fields ['IsDeleted'] so the live read-back
# carries the derived-false column the strict leaf compares against.
# generate_menu_options is a controlled echo (Workato menu payload return, no
# Slack channel write) and the recipe never writes Salesforce -> the only
# cleanup obligation is deleting this run's seeded records (finally block).
# Live record ids are threaded into expect via $<REF>_ID tokens
# (64106452 / 118168683 precedent). No try/catch exists in the raw recipe, so
# force_action_error is rejected: a forced failure would fail the whole job
# instead of exercising a recipe branch.

_STRUCTURE_PINS_JSON = r'''[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "b8aa6233",
  "provider": "slack_bot",
  "name": "dynamic_menu",
  "skip": false,
  "input": {
   "dynamic_menu_name": "[RepGenie] Fields",
   "parameters": "[\n  {\n    \"name\": \"api_name\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"control_type\": \"text\",\n    \"label\": \"Api name\"\n  },\n  {\n    \"name\": \"object_name\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"control_type\": \"text\",\n    \"label\": \"Object name\"\n  }\n]"
  }
 },
 {
  "keyword": "if",
  "number": 2,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b8aa6233\",\"path\":[\"parameters\",\"api_name\"]}')",
     "operand": "present"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "7fb98fac",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "4026533",
   "parameters": {
    "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b8aa6233\",\"path\":[\"parameters\", \"api_name\"]}')}"
   }
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "e89c104c",
  "provider": "slack_bot",
  "name": "generate_menu_options",
  "skip": false,
  "input": {
   "options": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"7fb98fac\",\"path\":[\"entries\"]}')}",
    "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"7fb98fac\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"7fb98fac\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col3\"]}')}"
   },
   "use_option_groups": "false"
  }
 },
 {
  "keyword": "elsif",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b8aa6233\",\"path\":[\"parameters\",\"object_name\"]}')",
     "operand": "present"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "if",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b8aa6233\",\"path\":[\"parameters\", \"object_name\"]}')}",
     "operand": "equals_to",
     "rhs": "Contact"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "b1582dc0",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "150",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"},{\"control_type\":\"text\",\"label\":\"Email\",\"type\":\"string\",\"name\":\"Email\"}]",
   "query": "SELECT Id, Name, Email FROM Contact WHERE Name like '%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b8aa6233\",\"path\":[\"typeahead\", \"value\"]}')}%' AND IsDeleted = false"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "586380ee",
  "provider": "slack_bot",
  "name": "generate_menu_options",
  "skip": false,
  "input": {
   "options": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b1582dc0\",\"path\":[\"records\"]}')}",
    "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b1582dc0\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b1582dc0\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Email\"]}')})",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b1582dc0\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
   },
   "use_option_groups": "false"
  }
 },
 {
  "keyword": "else",
  "number": 9,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "1ecaa00b",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "150",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"}]",
   "query": "SELECT Id, Name FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b8aa6233\",\"path\":[\"parameters\", \"object_name\"]}')} WHERE Name like '%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b8aa6233\",\"path\":[\"typeahead\", \"value\"]}')}%' AND IsDeleted = false"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "0dc00721",
  "provider": "slack_bot",
  "name": "generate_menu_options",
  "skip": false,
  "input": {
   "options": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1ecaa00b\",\"path\":[\"records\"]}')}",
    "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1ecaa00b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1ecaa00b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
   },
   "use_option_groups": "false"
  }
 }
]'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
EXPECT_KEYS = ("menu_branch", "executed_action_count", "tools", "tool_expectations")
OPTIONAL_EXPECT_KEYS = {"menu_options", "case"}


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
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_118905064(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_cfg.get("dynamic_menu_name") or "") != MENU_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} dynamic menu name changed")
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


def seed_118905064(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118905064(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"lookup_table", "salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    branch = _require_expect_shape(data.get("expect"))
    _require_branch_consistency(branch, trigger, seed_in)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
    }
    refs: dict[str, str] = {}
    if branch == "lookup":
        _require_lookup_section(seed_in.get("lookup_table"), trigger)
        out["lookup_table"] = deepcopy(seed_in["lookup_table"])
    elif branch in {"contact", "object"}:
        _require_salesforce_section(seed_in.get("salesforce"), branch, trigger)
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    expect = _replace_value(deepcopy(data["expect"]), refs)
    _require_no_tokens(trigger, "trigger")
    _require_no_tokens(expect, "expect")
    out["trigger"] = trigger
    out["expect"] = expect
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_118905064(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118905064(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    branch = str(expect.get("menu_branch") or "")
    if branch in {"contact", "object"}:
        if not isinstance(seed.get("salesforce_live"), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
        if not seed["salesforce_live"].get("strict_soql_conditions"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
                "(the 'IsDeleted = false' unquoted-boolean leaf is strict-only)"
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
        details["initial_snapshot"] = _snapshot(ctx, seed)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, seed)
    finally:
        # Required cleanup: delete this run's live-seeded records. The recipe
        # itself is read-only on Salesforce; the lookup mock is per-variant
        # seeded state, so no other cleanup obligation exists.
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
            details["cleanup_response"] = cleanup_response
    if cleanup_response is not None and not cleanup_response.get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118905064(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters", "typeahead"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly "
            "{'parameters': {...}, 'typeahead': {'value': <str>}} (the dynamic-menu payload)"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters must be an object")
    extra = sorted(set(parameters) - TRIGGER_PARAM_KEYS)
    if extra:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has undeclared fields: {extra}")
    typeahead = trigger.get("typeahead")
    if not isinstance(typeahead, dict) or set(typeahead) != {"value"} or not isinstance(
        typeahead.get("value"), str
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger typeahead must be exactly {{'value': <str>}}"
        )


def _require_expect_shape(expect: Any) -> str:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    branch = expect.get("menu_branch")
    if branch not in {"lookup", "contact", "object", "none"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.menu_branch must be lookup|contact|object|none: {branch!r}"
        )
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if branch == "none":
        if tools or expect.get("executed_action_count") != 0 or "menu_options" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the none branch runs zero actions: expect.tools must be [] "
                "and executed_action_count 0, with no menu_options"
            )
    else:
        if not isinstance(expect.get("menu_options"), list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} menu branches must pin the exact ordered expect.menu_options list"
            )
        expected_search = {
            "lookup": "lookup_table.search_entries",
            "contact": "salesforce.search_records",
            "object": "salesforce.search_records",
        }[branch]
        if tools != [expected_search, "slack_bot.generate_menu_options"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} branch {branch!r} must expect exactly "
                f"[{expected_search!r}, 'slack_bot.generate_menu_options']"
            )
        if expect.get("executed_action_count") != 2:
            raise RuntimeError(f"recipe {RECIPE_ID} menu branches execute exactly two actions")
    return str(branch)


def _require_branch_consistency(branch: str, trigger: dict[str, Any], seed_in: dict[str, Any]) -> None:
    parameters = trigger["parameters"]
    api_name = parameters.get("api_name")
    object_name = parameters.get("object_name")
    sections = sorted(seed_in)
    if branch == "lookup":
        if not isinstance(api_name, str) or not api_name.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} lookup branch requires a non-empty api_name")
        if sections != ["lookup_table"]:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup branch seeds exactly the lookup_table section")
    elif branch in {"contact", "object"}:
        if "api_name" in parameters:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} branch requires api_name ABSENT (IF 2 wins otherwise)"
            )
        if not isinstance(object_name, str) or not object_name.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} {branch} branch requires a non-empty object_name")
        if branch == "contact" and object_name != "Contact":
            raise RuntimeError(f"recipe {RECIPE_ID} contact branch requires object_name == 'Contact'")
        if branch == "object" and object_name == "Contact":
            raise RuntimeError(f"recipe {RECIPE_ID} object branch requires object_name != 'Contact'")
        if not str(trigger["typeahead"].get("value") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} branch requires a non-empty typeahead.value "
                "(the SOQL LIKE pattern)"
            )
        if sections != ["salesforce"]:
            raise RuntimeError(f"recipe {RECIPE_ID} {branch} branch seeds exactly the salesforce section")
    else:  # none
        if parameters != {}:
            raise RuntimeError(f"recipe {RECIPE_ID} none branch requires parameters == {{}}")
        if sections:
            raise RuntimeError(f"recipe {RECIPE_ID} none branch touches no backend: seed must be empty")


def _require_lookup_section(section: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID}"
        )
    rows = section["tables"][LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} must be a non-empty list")
    api_name = str(trigger["parameters"].get("api_name") or "")
    matches = 0
    decoys = 0
    for row in rows:
        if not isinstance(row, dict) or not set(row) <= {"col1", "col2", "col3"}:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup rows must only use col1..col3: {row!r}")
        if not str(row.get("col1") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every lookup row needs a non-empty col1 search key")
        if str(row.get("col1")) == api_name:
            matches += 1
        else:
            decoys += 1
    if matches < 1 or decoys < 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} lookup branch must seed >=1 col1={api_name!r} row AND >=1 "
            f"non-matching decoy row (got {matches} matches / {decoys} decoys)"
        )


def _require_salesforce_section(section: Any, branch: str, trigger: dict[str, Any]) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(the 'IsDeleted = false' leaf is strict-only; lenient would silently drop it)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    expected_sobject = "Contact" if branch == "contact" else str(
        trigger["parameters"].get("object_name") or ""
    )
    typeahead = str(trigger["typeahead"].get("value") or "")
    matches = 0
    decoys = 0
    for record in records:
        if not isinstance(record, dict) or not str(record.get("ref") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}")
        if str(record.get("sobject") or "") != expected_sobject:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} branch records must all be {expected_sobject}: {record}"
            )
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}")
        read_fields = record.get("read_fields")
        if not isinstance(read_fields, list) or "IsDeleted" not in read_fields:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every record needs read_fields including 'IsDeleted' "
                f"(derived false on create; the strict leaf compares it): {record}"
            )
        if branch == "contact":
            name = str(fields.get("LastName") or "")
            if not name or not str(fields.get("Email") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} contact records need LastName (the rendered live Name) "
                    f"and Email (the menu label interpolates both): {record}"
                )
            if "FirstName" in fields:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seed LastName-only contacts so the live Name is "
                    f"deterministic: {record}"
                )
        else:
            name = str(fields.get("Name") or "")
            if not name:
                raise RuntimeError(f"recipe {RECIPE_ID} {branch} records need a Name: {record}")
        if typeahead in name:
            matches += 1
        else:
            decoys += 1
    if matches < 1 or decoys < 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} branch must seed >=1 record whose name contains the "
            f"typeahead {typeahead!r} AND >=1 non-matching decoy (got {matches}/{decoys})"
        )


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
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("lookup_table"), dict):
        snap = ctx.tools.call("harness.lookup_table.snapshot", {})
        out["lookup_table"] = snap.get("lookup_table")
    if isinstance(seed.get("salesforce_live"), dict):
        snap = ctx.tools.call("harness.salesforce.snapshot", {})
        out["salesforce"] = snap.get("salesforce")
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118168683


RECIPE_ID = "118168683"
SEED_TYPE = "slack_dynamic_menu_salesforce_typeahead_variant"
TRACK = "live_salesforce_slack_dynamic_menu_sf_data_list"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "d0dbce8e"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")


_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "d0dbce8e",
  "input": {
   "dynamic_menu_name": "sfDataList",
   "parameters": "[\n\n]"
  },
  "keyword": "trigger",
  "name": "dynamic_menu",
  "number": 1,
  "provider": "slack_bot",
  "skip": false
 },
 {
  "as": null,
  "input": {},
  "keyword": "try",
  "name": null,
  "number": 2,
  "provider": null,
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"d0dbce8e\",\"path\":[\"typeahead\", \"name\"]}')}",
     "operand": "equals_to",
     "rhs": "User"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 3,
  "provider": null,
  "skip": false
 },
 {
  "as": "146dcac6",
  "input": {
   "limit": "2000",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"}]",
   "query": "select id, name from user where name like '#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"d0dbce8e\",\"path\":[\"typeahead\", \"value\"]}')}%'"
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 4,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "8a836e8a",
  "input": {
   "option_groups": [
    {
     "label": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"146dcac6\",\"path\":[\"records\"]}')",
     "options": [
      {
       "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"146dcac6\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
       "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"146dcac6\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
      }
     ]
    }
   ],
   "use_option_groups": "true"
  },
  "keyword": "action",
  "name": "generate_menu_options",
  "number": 5,
  "provider": "slack_bot",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"d0dbce8e\",\"path\":[\"typeahead\", \"name\"]}')}",
     "operand": "equals_to",
     "rhs": "Account"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 6,
  "provider": null,
  "skip": false
 },
 {
  "as": "2284ebd6",
  "input": {
   "limit": "2000",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"}]",
   "query": "select id, name from account where name like '#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"d0dbce8e\",\"path\":[\"typeahead\", \"value\"]}')}%'"
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 7,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "6c4a1f08",
  "input": {
   "option_groups": [
    {
     "label": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2284ebd6\",\"path\":[\"records\"]}')",
     "options": [
      {
       "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2284ebd6\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
       "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2284ebd6\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
      }
     ]
    }
   ],
   "use_option_groups": "true"
  },
  "keyword": "action",
  "name": "generate_menu_options",
  "number": 8,
  "provider": "slack_bot",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"d0dbce8e\",\"path\":[\"typeahead\", \"name\"]}')}",
     "operand": "equals_to",
     "rhs": "Contact"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 9,
  "provider": null,
  "skip": false
 },
 {
  "as": "7942ec9f",
  "input": {
   "limit": "2000",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"}]",
   "query": "select id, name from contact where name like '#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"d0dbce8e\",\"path\":[\"typeahead\", \"value\"]}')}%'"
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 10,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "54230477",
  "input": {
   "option_groups": [
    {
     "label": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7942ec9f\",\"path\":[\"records\"]}')",
     "options": [
      {
       "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7942ec9f\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
       "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7942ec9f\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
      }
     ]
    }
   ],
   "use_option_groups": "true"
  },
  "keyword": "action",
  "name": "generate_menu_options",
  "number": 11,
  "provider": "slack_bot",
  "skip": false
 },
 {
  "as": "5968e436",
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  },
  "keyword": "catch",
  "name": null,
  "number": 12,
  "provider": null,
  "skip": false
 },
 {
  "as": "52c21140",
  "input": {
   "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"5968e436\",\"path\":[\"type\"]}')} : #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"5968e436\",\"path\":[\"message\"]}')}",
   "user_logs_enabled": "false"
  },
  "keyword": "action",
  "name": "log_message",
  "number": 13,
  "provider": "logger",
  "skip": false
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
MENU_BRANCHES = {"user", "account", "contact", "none", "empty", "catch"}


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
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_118168683(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger line id changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: "
            f"{len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} "
                f"(step {expected.get('number')}) changed:\n"
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


def seed_118168683(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118168683(raw)
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
    branch = _require_expect_shape(data)
    refs: dict[str, str] = {}
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track"),
        "raw_validation": validation,
    }
    sf_section = seed_in.get("salesforce")
    if sf_section is not None:
        _require_salesforce_section(sf_section, branch)
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_section})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(sf_section, provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    elif branch in {"user", "account", "contact"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} menu branch {branch!r} requires seed.salesforce "
            "(matching records / current_user); refusing an empty-backend menu variant"
        )
    trigger = _replace_value(trigger, refs)
    _require_no_tokens(trigger, "trigger")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out["trigger"] = trigger
    out["expect"] = resolved_expect
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_118168683(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118168683(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    if isinstance(seed.get("salesforce_live"), dict) and not (cleanup_response or {}).get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118168683(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"typeahead"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the typeahead object; got {sorted(trigger)}"
        )
    typeahead = trigger.get("typeahead")
    if not isinstance(typeahead, dict) or set(typeahead) != {"name", "value"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger typeahead must be {{'name', 'value'}}; got {typeahead!r}"
        )
    for key in ("name", "value"):
        value = typeahead.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger typeahead.{key} must be a non-empty string")


def _require_expect_shape(data: dict[str, Any]) -> str:
    expect = data.get("expect")
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    if not isinstance(expect.get("tools"), list) or not isinstance(expect.get("tool_expectations"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect must pin tools and tool_expectations lists")
    branch = expect.get("menu_branch")
    if branch not in MENU_BRANCHES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.menu_branch must be one of {sorted(MENU_BRANCHES)}; got {branch!r}"
        )
    force = data.get("force_action_error")
    if branch == "catch":
        for key in ("logger_message", "catch_type", "catch_error"):
            if not str(expect.get(key) or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} catch variant must pin expect.{key}")
        if not isinstance(force, dict) or str(force.get("step_as") or "") != "2284ebd6":
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variant requires force_action_error.step_as='2284ebd6'; got {force!r}"
            )
    else:
        if force is not None:
            raise RuntimeError(f"recipe {RECIPE_ID} only the catch variant may force an action error")
        if branch != "none" and not isinstance(expect.get("menu_options"), list):
            raise RuntimeError(f"recipe {RECIPE_ID} menu branch {branch!r} must pin expect.menu_options")
    return str(branch)


def _require_salesforce_section(section: Any, branch: str) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
    unexpected = sorted(set(section) - {"strict_soql_conditions", "current_user", "records"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true")
    current_user = section.get("current_user")
    if branch == "user":
        if current_user != {"sobject": "User"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} user branch requires seed.salesforce.current_user "
                f"== {{'sobject': 'User'}}; got {current_user!r}"
            )
    elif current_user is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} only the user branch registers the current user")
    records = section.get("records")
    if records is not None:
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
        for record in records:
            if not isinstance(record, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} seed record must be an object: {record!r}")
            if str(record.get("sobject") or "") not in {"Account", "Contact"}:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seed record sobject must be Account or Contact: {record!r}"
                )
            if not str(record.get("ref") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} seed record must declare a ref: {record!r}")
            fields = record.get("fields")
            if not isinstance(fields, dict) or not fields:
                raise RuntimeError(f"recipe {RECIPE_ID} seed record must declare fields: {record!r}")


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    records = [record for record in salesforce_snapshot.get("records") or [] if isinstance(record, dict)]
    owned = [record for record in records if not record.get("read_only")]
    read_only_users = [
        record for record in records
        if record.get("read_only") and str(record.get("sobject") or "").lower() == "user"
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(owned) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        live_id = str(owned[idx].get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        refs[f"${ref.upper()}_ID"] = live_id
    if isinstance(seed_section.get("current_user"), dict):
        if len(read_only_users) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expected exactly one read-only current-user row; "
                f"got {len(read_only_users)}"
            )
        user_id = str(read_only_users[0].get("id") or "")
        user_fields = read_only_users[0].get("fields") if isinstance(read_only_users[0].get("fields"), dict) else {}
        user_name = str(user_fields.get("Name") or "")
        if not _SF_ID_RE.fullmatch(user_id):
            raise RuntimeError(f"recipe {RECIPE_ID} current-user id looks invalid: {user_id!r}")
        if not user_name.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} current-user row has no Name")
        refs["$CURRENT_USER_ID"] = user_id
        refs["$CURRENT_USER_NAME"] = user_name
    elif read_only_users:
        raise RuntimeError(f"recipe {RECIPE_ID} unexpected read-only user rows: {read_only_users}")
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
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("salesforce_live"), dict):
        return ctx.tools.call("harness.salesforce.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

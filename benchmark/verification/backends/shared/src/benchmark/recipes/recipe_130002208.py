from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130002208


RECIPE_ID = "130002208"
SEED_TYPE = "pubsub_snowflake_employee_app_update_variant"
TRACK = "live_snowflake_pubsub_row_update"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "subscribe_to_topic"
TRIGGER_AS = "7d81917f"
TOPIC_ID = "39340"
DECLARE_AS = "eafdad03"
UPDATE_AS = "04a6799d"
CATCH_AS = "3c87292f"
STOP_AS = "e994dc18"
SNOWFLAKE_TABLE = "PUBLIC.EMPLOYEE_APP"
# The 8 pub_sub-updatable columns, in the raw update node input order.
MESSAGE_COLUMNS = (
    "admin_access",
    "app_user_id",
    "deprovision_date",
    "last_active",
    "modified_at",
    "provision_date",
    "status",
    "username",
)
# Full physical schema from the update node extended_input_schema (seeded
# verbatim so the WHERE identifiers and every SET column exist live).
TABLE_COLUMNS = {
    "admin_access": "boolean",
    "app_id": "string",
    "app_user_id": "string",
    "created_at": "timestamp_ntz",
    "deprovision_date": "timestamp_ntz",
    "employee_id": "number",
    "external_user": "boolean",
    "last_active": "timestamp_ntz",
    "modified_at": "timestamp_ntz",
    "provision_date": "timestamp_ntz",
    "secondary_account": "number",
    "service_account": "boolean",
    "status": "string",
    "username": "string",
}
TIMESTAMP_COLUMNS = {
    "created_at",
    "deprovision_date",
    "last_active",
    "modified_at",
    "provision_date",
}
BOOLEAN_COLUMNS = {"admin_access", "external_user", "service_account"}
NUMBER_COLUMNS = {"employee_id", "secondary_account"}

# workato_pub_sub.subscribe_to_topic (as 7d81917f, topic 39340 '[APPS] Update
# Row on Snowflake') -- the trigger message carries where_condition (verbatim
# SQL WHERE) and a columns hash. Body (all inside TRY step 2):
#   3  workato_variable.declare_variable eafdad03 'Check if key exist to
#      determine if null value is intended': key_exist.<col> =
#      =_dp(message.columns).keys.include?("<col>") x8 -- Hash#keys +
#      Array#include? KEY-presence (distinct from value presence; batch07
#      engine fix, re-probed green on this tree).
#   4  snowflake.update_rows 04a6799d (LIVE): table PUBLIC.EMPLOYEE_APP,
#      where = #{message.where_condition} VERBATIM; each of the 8 columns is
#      the 3-way no-paren right-associative ternary
#        value.present? ? value : key_exist.<col>.is_true? ? null : skip
#      -> value present: SET value; key present with null/'': SET NULL
#      (explicit-NULL SET reaches Snowflake -- batch07 snowflake_live fix,
#      re-probed: None survives to the SET list and binds as SQL NULL);
#      key absent: column omitted (SKIP).
#   CATCH 5 (3c87292f, max_retry 0) -> STOP 6 (e994dc18, stop_with_error
#      'true', stop_reason = catch.message pill). Engine stop rows trace
#      {stopped: true} without evaluating stop_reason (batch04/05 semantics);
#      the catch payload pins the groundtruth instead.
#
# Branch mapping (branch is DERIVED from the variant input, never trusted):
# - variant_00 update: 3 string columns present -> SET those, skip the rest;
#   where matches exactly one seeded row; rows_updated 1; decoy row untouched.
# - variant_01 update: app_user_id value + status null + deprovision_date
#   null + modified_at ISO-T timestamp value -> the explicit-NULL arm wipes a
#   varchar AND a timestamp_ntz column while a value SET lands in the same
#   statement (the recipe's whole point: null-intended vs absent).
# - variant_02 update: single username SET; every other column ABSENT ->
#   key_exist false x7 -> skipped -> seeded STATUS/PROVISION_DATE/... survive.
# - variant_03 zero_match: where targets an unseeded app_id -> rows_updated 0,
#   table byte-identical. tool_expectations is [] BY DESIGN: the shared
#   verifier's snowflake.update_rows check hard-requires a where-matching row
#   in the final snapshot (its _strict_snowflake_update_checks), which
#   cannot express a zero-match update -- the fragment pins args verbatim,
#   rows_updated 0 and snapshot equality instead.
# - variant_04 catch_stop: force_action_error on 04a6799d -> CATCH -> STOP
#   with stop_with_error; trace = declare + stop row; no snowflake call; the
#   catch payload {type, message} is pinned.
#
# Engine-vs-Ruby edge kept OUT of contract: the engine's .present? keeps
# boolean false (probed), while Ruby false.present? is false (Rails would take
# the NULL arm). Variant inputs REJECT boolean false in message.columns so no
# variant depends on the divergent edge; true is accepted (both agree).
#
# Backends: snowflake LIVE (seed = create-or-replace under the LITERAL
# 2-part name PUBLIC.EMPLOYEE_APP -> env schema PUBLIC; cleanup DROPS it in
# the runner's finally). The where strings are single-equality
# "app_id = '<value>'" (unquoted identifier passes
# _rewrite_where_identifiers untouched; single-equality keeps the shared
# verifier's where parser exact). No CURRENT_*/sysdate anywhere -> no
# seed.snowflake_live.current_time. workato_pub_sub trigger and
# workato_variable are Workato-internal (mock/in-process).

_RAW_PIN_JSON = r"""{"as": "7d81917f", "block": [{"as": "", "block": [{"as": "eafdad03", "block": [], "input": {"variables": {"data": {"key_exist": {"admin_access": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"admin_access\")", "app_user_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"app_user_id\")", "deprovision_date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"deprovision_date\")", "last_active": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"last_active\")", "modified_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"modified_at\")", "provision_date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"provision_date\")", "status": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"status\")", "username": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\"]}').keys.include?(\"username\")"}}, "schema": "[{\"properties\":[{\"control_type\":\"checkbox\",\"label\":\"App user ID Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"app_user_id\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"App user ID\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"app_user_id\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]},{\"control_type\":\"checkbox\",\"label\":\"Admin Access Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"admin_access\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"Admin Access\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"admin_access\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]},{\"control_type\":\"checkbox\",\"label\":\"Provision date Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"provision_date\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"Provision date\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"provision_date\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]},{\"control_type\":\"checkbox\",\"label\":\"Deprovision date Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"deprovision_date\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"Deprovision date\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"deprovision_date\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]},{\"control_type\":\"checkbox\",\"label\":\"Modified at Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"modified_at\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"Modified at\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"modified_at\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]},{\"control_type\":\"checkbox\",\"label\":\"Status Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"status\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"Status\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"status\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]},{\"control_type\":\"checkbox\",\"label\":\"Username Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"username\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"Username\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"username\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]},{\"control_type\":\"checkbox\",\"label\":\"Last Active Key Exist\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"last_active\",\"optional\":true,\"type\":\"boolean\",\"toggle_hint\":\"Select from option list\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"toggle_field\":{\"label\":\"last_active\",\"control_type\":\"text\",\"toggle_hint\":\"Select from option list\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"last_active\",\"optional\":true,\"type\":\"boolean\",\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\",\"key_exist\"]},\"parent\":[\"variables\",\"data\",\"key_exist\"]}],\"label\":\"Key Exist\",\"name\":\"key_exist\",\"type\":\"object\",\"optional\":true,\"details\":{\"real_name\":\"Key Exist\"},\"initially_expanded\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "04a6799d", "block": [], "input": {"columns": {"admin_access": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"admin_access\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"admin_access\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"admin_access\"]}').is_true? ? null : skip", "app_user_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"app_user_id\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"app_user_id\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"app_user_id\"]}').is_true? ? null : skip", "deprovision_date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"deprovision_date\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"deprovision_date\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"deprovision_date\"]}').is_true? ? null : skip", "last_active": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"last_active\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"last_active\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"last_active\"]}').is_true? ? null : skip", "modified_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"modified_at\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"modified_at\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"modified_at\"]}').is_true? ? null : skip", "provision_date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"provision_date\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"provision_date\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"provision_date\"]}').is_true? ? null : skip", "status": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"status\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"status\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"status\"]}').is_true? ? null : skip", "username": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"username\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\",\"columns\",\"username\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eafdad03\",\"path\":[\"key_exist\",\"username\"]}').is_true? ? null : skip"}, "table": "PUBLIC.EMPLOYEE_APP", "where": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"7d81917f\",\"path\":[\"message\", \"where_condition\"]}')}"}, "keyword": "action", "name": "update_rows", "number": 4, "provider": "snowflake", "skip": false}, {"as": "3c87292f", "block": [{"as": "e994dc18", "block": [], "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"3c87292f\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 6, "provider": "", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 5, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"since_offset": "0", "topic_id": "39340"}, "keyword": "trigger", "name": "subscribe_to_topic", "number": 1, "provider": "workato_pub_sub", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_AS, "workato_variable", "declare_variable"),
    (UPDATE_AS, "snowflake", "update_rows"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.update_rows",
]
ALLOWED_TOOLS: list[str] = ["snowflake.update_rows"]
BRANCHES = ("update", "zero_match", "catch_stop")
REQUIRED_EXPECT_KEYS = (
    "case",
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "key_exist",
    "update_args",
    "rows_updated",
    "final_rows",
    "catch",
)
OPTIONAL_EXPECT_KEYS = ("final_table", "stopped")
# Corpus lint: targeting keys + value keys allowed on tool_expectations items.
_EXPECTATION_TARGET_KEYS = {"tool", "table_id", "lookup_table_id", "match_fields", "channel"}
_EXPECTATION_VALUE_KEYS = {
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
}
_WHERE_RE = re.compile(r"^app_id = '([A-Za-z0-9_-]+)'$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}$")


def validate_130002208(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("topic_id") or "") != TOPIC_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} pub_sub topic changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone pieces (the tree pin holds the bytes;
    # these name the trap when one changes).
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    declare = nodes.get(DECLARE_AS) or {}
    key_exist = (((declare.get("input") or {}).get("variables") or {}).get("data") or {}).get(
        "key_exist"
    ) or {}
    if sorted(key_exist.keys()) != sorted(MESSAGE_COLUMNS):
        raise RuntimeError(f"recipe {RECIPE_ID} declare no longer covers the 8 key_exist columns")
    for column, formula in key_exist.items():
        if f'.keys.include?("{column}")' not in str(formula) or '"message","columns"' not in str(
            formula
        ).replace(" ", ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} key_exist.{column} is no longer the Hash#keys "
                f"membership formula: {formula!r}"
            )
    update = nodes.get(UPDATE_AS) or {}
    update_input = update.get("input") or {}
    if str(update_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} update table changed")
    if "where_condition" not in str(update_input.get("where") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} update where no longer binds message.where_condition")
    columns_input = update_input.get("columns") or {}
    if tuple(columns_input.keys()) != MESSAGE_COLUMNS:
        raise RuntimeError(f"recipe {RECIPE_ID} update columns changed: {tuple(columns_input.keys())}")
    for column, formula in columns_input.items():
        text = str(formula)
        if (
            ".present? ?" not in text
            or ".is_true? ? null : skip" not in text
            or f'"key_exist","{column}"' not in text.replace(" ", "")
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} update column {column} lost the 3-way "
                f"value/null/skip ternary: {formula!r}"
            )
    stop = nodes.get(STOP_AS) or {}
    stop_input = stop.get("input") or {}
    if str(stop_input.get("stop_with_error") or "") != "true" or CATCH_AS not in str(
        stop_input.get("stop_reason") or ""
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch stop node changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "topic_id": TOPIC_ID,
        "snowflake_table": SNOWFLAKE_TABLE,
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_130002208(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130002208(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    message = _require_trigger_shape(trigger)
    force = data.get("force_action_error")
    if force is not None and (
        not isinstance(force, dict)
        or str(force.get("step_as") or "") != UPDATE_AS
        or not str(force.get("error") or "").strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must be exactly "
            f"{{'step_as': {UPDATE_AS!r}, 'error': <non-empty text>}} (the catch is "
            f"reachable ONLY through the update step): {force!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    rows = _require_snowflake_section(seed_in["snowflake_live"])
    derived = _derive_ground_truth(message, rows, force)
    _require_expect_shape(data.get("expect"), derived)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130002208(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130002208(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("trigger"), dict) or not seed["trigger"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the trigger message")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # The seeded EMPLOYEE_APP table is benchmark-owned live state: drop it
        # even when execution fails (fail-fast cleanup, 103520604 pattern).
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_130002208(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> dict[str, Any]:
    if sorted(trigger.keys()) != ["message"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'message': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    message = trigger["message"]
    if not isinstance(message, dict) or sorted(message.keys()) != ["columns", "where_condition"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger message must carry exactly where_condition "
            f"and columns (both are dereferenced): {message!r}"
        )
    where = message["where_condition"]
    if not isinstance(where, str) or not _WHERE_RE.fullmatch(where):
        raise RuntimeError(
            f"recipe {RECIPE_ID} where_condition must be the single-equality "
            f"\"app_id = '<value>'\" form (unquoted identifier passes the live "
            f"where rewrite untouched AND the shared verifier where parser is "
            f"single-equality); got {where!r}"
        )
    if re.search(r"current_(?:date|timestamp)|sysdate", where, flags=re.I):
        raise RuntimeError(
            f"recipe {RECIPE_ID} where_condition must not use CURRENT_*/sysdate "
            f"(no current_time is seeded)"
        )
    columns = message["columns"]
    if not isinstance(columns, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} message.columns must be an object")
    unknown = sorted(set(columns.keys()) - set(MESSAGE_COLUMNS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} message.columns has unknown keys: {unknown}")
    for column, value in columns.items():
        if value is False:
            raise RuntimeError(
                f"recipe {RECIPE_ID} message.columns.{column} must not be boolean false: "
                f"the engine keeps false through .present? while Ruby false.present? is "
                f"false (Rails would take the NULL arm) -- out of contract by design"
            )
        if column == "admin_access":
            if value not in (None, "", True):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} message.columns.admin_access must be true or "
                    f"null/''; got {value!r}"
                )
            continue
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} message.columns.{column} must be a string or null; "
                f"got {value!r}"
            )
        if column in TIMESTAMP_COLUMNS and not _TS_RE.fullmatch(value):
            raise RuntimeError(
                f"recipe {RECIPE_ID} message.columns.{column} must be "
                f"YYYY-MM-DD[ T]HH:MM:SS (it lands in a TIMESTAMP_NTZ SET); got {value!r}"
            )
    return message


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            f"(no CURRENT_* anywhere -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [SNOWFLAKE_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SNOWFLAKE_TABLE!r} (the LITERAL 2-part name the update targets)"
        )
    spec = tables[SNOWFLAKE_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake table spec must be exactly "
            f"{{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != TABLE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} EMPLOYEE_APP columns must be exactly the raw schema "
            f"set {TABLE_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} EMPLOYEE_APP rows must be a non-empty list (the update "
            f"needs live rows to prove touched vs untouched)"
        )
    app_ids: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(TABLE_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} EMPLOYEE_APP row {idx} must fill exactly the "
                f"declared columns: {row!r}"
            )
        for column in TABLE_COLUMNS:
            value = row[column]
            if column in BOOLEAN_COLUMNS:
                if not isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} row {idx}.{column} must be a boolean; got {value!r}"
                    )
            elif column in NUMBER_COLUMNS:
                if not isinstance(value, int) or isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} row {idx}.{column} must be an int; got {value!r}"
                    )
            elif column in TIMESTAMP_COLUMNS:
                if not isinstance(value, str) or not _TS_RE.fullmatch(value):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} row {idx}.{column} must be "
                        f"YYYY-MM-DD[ T]HH:MM:SS; got {value!r}"
                    )
            else:
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} row {idx}.{column} must be a non-empty "
                        f"string; got {value!r}"
                    )
        app_ids.append(str(row["app_id"]))
    if len(set(app_ids)) != len(app_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded app_id values must be distinct (the where "
            f"targets app_id; groundtruth matching is keyed on it)"
        )
    return [dict(row) for row in rows]


def _derive_ground_truth(
    message: dict[str, Any],
    rows: list[dict[str, Any]],
    force: Any,
) -> dict[str, Any]:
    """Recompute the run's observable groundtruth from the variant input alone
    (engine-formula semantics mirrored; expect must match or the seed fails)."""
    columns = message["columns"]
    key_exist = {name: name in columns for name in MESSAGE_COLUMNS}
    update_columns: dict[str, Any] = {}
    for name in MESSAGE_COLUMNS:
        if name not in columns:
            continue  # key absent -> skip arm -> column omitted
        value = columns[name]
        update_columns[name] = None if value in (None, "") else value
    where_value = _WHERE_RE.fullmatch(str(message["where_condition"])).group(1)
    matching = [row for row in rows if str(row["app_id"]) == where_value]
    if force is not None:
        branch = "catch_stop"
    elif matching:
        branch = "update"
    else:
        branch = "zero_match"
    if branch == "update" and not update_columns:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update variants must carry at least one message "
            f"column (an all-skip SET has no live meaning)"
        )
    final_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized = {
            column: _normalize_cell(column, row[column]) for column in sorted(TABLE_COLUMNS)
        }
        if branch == "update" and str(row["app_id"]) == where_value:
            for column, value in update_columns.items():
                normalized[column] = None if value is None else _normalize_cell(column, value)
        final_rows.append(normalized)
    final_rows.sort(key=lambda row: str(row["app_id"]))
    return {
        "branch": branch,
        "key_exist": key_exist,
        "update_columns": update_columns,
        "where": str(message["where_condition"]),
        "rows_updated": len(matching),
        "final_rows": final_rows,
        "forced_error": str((force or {}).get("error") or "") if isinstance(force, dict) else "",
    }


def _normalize_cell(column: str, value: Any) -> Any:
    if column in TIMESTAMP_COLUMNS and isinstance(value, str):
        # Snowflake TIMESTAMP_NTZ reads back as datetime.isoformat() ('T').
        return value.replace(" ", "T")
    return value


def _require_expect_shape(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS) - set(OPTIONAL_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    if branch != derived["branch"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the variant input "
            f"(derived {derived['branch']!r})"
        )
    if branch == "catch_stop":
        checks = (
            expect.get("executed_action_count") == 1,
            expect.get("tools") == [],
            expect.get("tool_expectations") == [],
            expect.get("update_args") is None,
            expect.get("rows_updated") is None,
            expect.get("stopped") is True,
            expect.get("catch")
            == {
                "type": "RawRecipeExecutionError",
                "message": derived["forced_error"],
                "adapter": "snowflake",
                "action": "update_rows",
                "line_number": 4,
            },
        )
    else:
        expected_update_args = {
            "table": SNOWFLAKE_TABLE,
            "where": derived["where"],
            "columns": derived["update_columns"],
        }
        checks = (
            expect.get("executed_action_count") == 2,
            expect.get("tools") == ["snowflake.update_rows"],
            expect.get("update_args") == expected_update_args,
            expect.get("rows_updated") == derived["rows_updated"],
            "stopped" not in expect or expect.get("stopped") is False,
            expect.get("catch") is None,
        )
    if not all(checks) or expect.get("key_exist") != derived["key_exist"] or expect.get(
        "final_rows"
    ) != derived["final_rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth (branch {derived['branch']!r}): {expect!r}"
        )
    if "final_table" in expect:
        expected_final_table = {
            "backend": "snowflake",
            "table_id": SNOWFLAKE_TABLE,
            "row_count": len(derived["final_rows"]),
            "rows": derived["final_rows"],
        }
        if expect.get("final_table") != expected_final_table:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.final_table must be the canonical exact "
                f"alias of the derived table state: {expected_final_table!r}"
            )
    _require_tool_expectations(expect, derived)


def _require_tool_expectations(expect: dict[str, Any], derived: dict[str, Any]) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a list")
    branch = derived["branch"]
    if branch in ("catch_stop", "zero_match"):
        if items != []:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} variants must carry an EMPTY "
                f"tool_expectations list: catch runs no external tool, and the shared "
                f"verifier's update check cannot express a zero-match where (the "
                f"fragment pins those branches)"
            )
        return
    if len(items) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update variants must pin exactly the one live "
            f"snowflake.update_rows call"
        )
    item = items[0]
    if not isinstance(item, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must be an object")
    unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] has non-corpus keys: {unknown}")
    if not any(key in item for key in _EXPECTATION_VALUE_KEYS):
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] pins no ground-truth value")
    if item.get("tool") != "snowflake.update_rows" or item.get("args_contains") != {
        "table": SNOWFLAKE_TABLE,
        "where": derived["where"],
        "columns": derived["update_columns"],
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim update args "
            f"(table + where + the derived value/NULL/skip columns): {item!r}"
        )


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if not out["skip"]:
        out["input"] = node.get("input")
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        out["filter"] = node["filter"]
    out["block"] = [
        _normalize_tree(child) for child in node.get("block") or [] if isinstance(child, dict)
    ]
    return out


def _first_tree_mismatch(actual: Any, expected: Any, path: str = "root") -> str:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                return f"{path}.{key}: missing in raw recipe"
            if key not in expected:
                return f"{path}.{key}: unexpected in raw recipe"
            found = _first_tree_mismatch(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for idx, (act, exp) in enumerate(zip(actual, expected)):
            found = _first_tree_mismatch(act, exp, f"{path}[{idx}]")
            if found:
                return found
        return ""
    if actual != expected:
        return f"{path}: {json.dumps(actual, default=str)[:200]} != {json.dumps(expected, default=str)[:200]}"
    return ""


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

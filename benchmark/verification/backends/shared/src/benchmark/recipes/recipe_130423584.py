from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130423584


RECIPE_ID = "130423584"
SEED_TYPE = "workato_ai_usage_daily_snowflake_upsert_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "e6c72845"
TOKEN_DECLARE_AS = "21a36e04"
LIST_DECLARE_AS = "6eb62ac7"
GET_RECORDS_AS = "1823734b"
INSERT_BATCH_AS = "9c5c969f"
UPDATE_TOKEN_AS = "ef95fc6a"
UPSERT_AS = "418ea7e9"
DB_TABLE_ID = "56478"
SNOWFLAKE_TABLE = "PUBLIC.WORKATO_AI_USAGE"
COMPLETED_FIELD = "4652b125_31c7_41a7_a518_440147b84c0e"
DB_STRING_FIELDS = (
    "c16bf317_ae46_44e2_b912_400da66ff1f3",  # Recipe ID
    "ab7f7770_adca_4e99_8c15_f07bbe493362",  # Job ID
    "67461374_ee4b_44c8_8fd3_ef62602d6792",  # Access Profile Name
    "4b3212e0_2c2e_4bc7_85c2_26086ee4f9ac",  # Connector
    "081b5c41_77a6_4534_ae1a_cc032e2551f3",  # Business Owner Email
    "316a6259_8ba4_4338_b18b_fdf6a2d49b0b",  # Use Case
    "b39400af_67e9_4297_b189_a5b989e06d07",  # Connector Action
    "ccf286bd_24c7_4ccf_b186_e1055091ce84",  # Endpoint
)
DB_INT_FIELDS = (
    "930baaff_e3c2_4f1e_9ce7_7d9c2fdeddb2",  # Prompt Tokens
    "c8980714_114d_41b9_8a28_701c048e02a5",  # Completion Tokens
    "6b305309_5ab8_49da_8687_4bab3044fc0f",  # Total Tokens
)
JOB_ID_FIELD = "ab7f7770_adca_4e99_8c15_f07bbe493362"
DB_ROW_FIELDS = DB_STRING_FIELDS + DB_INT_FIELDS + (COMPLETED_FIELD,)
SNOWFLAKE_COLUMNS = {
    "job_id": "string",
    "recipe_id": "number",
    "access_profile_name": "string",
    "connector": "string",
    "business_owner_email": "string",
    "use_case": "string",
    "connector_action": "string",
    "endpoint": "string",
    "prompt_tokens": "number",
    "completion_tokens": "number",
    "total_tokens": "number",
    "completed_at": "timestamp_ntz",
}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "e6c72845", "skip": false, "input": {"time_unit": "days", "timezone": "America/Los_Angeles", "trigger_at": "00:00:00.000", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "21a36e04", "skip": false, "input": {"variables": {"schema": "[{\"name\":\"Token\",\"type\":\"string\",\"optional\":true,\"label\":\"Token\",\"details\":{\"real_name\":\"Token\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_list", "as": "6eb62ac7", "skip": false, "input": {"list_item_schema_json": "[{\"name\":\"recipe_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Recipe ID\"},{\"name\":\"job_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Job ID\"},{\"name\":\"access_profile_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Access profile name\"},{\"name\":\"connector\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Connector\"},{\"name\":\"business_owner_email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Business owner email\"},{\"name\":\"use_case\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Use case\"},{\"name\":\"connector_action\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Connector action\"},{\"name\":\"endpoint\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Endpoint\"},{\"name\":\"prompt_tokens\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Prompt tokens\",\"parse_output\":\"integer_conversion\",\"render_input\":\"integer_conversion\"},{\"name\":\"completion_tokens\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Completion tokens\",\"parse_output\":\"integer_conversion\",\"render_input\":\"integer_conversion\"},{\"name\":\"total_tokens\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Total tokens\",\"parse_output\":\"integer_conversion\",\"render_input\":\"integer_conversion\"},{\"name\":\"completed_at\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date_time\",\"label\":\"Completed at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\"}]", "name": "workato_ai_usage"}, "block": []}, {"number": 4, "keyword": "repeat", "provider": "", "name": "", "as": "7252ab80", "skip": false, "input": {}, "block": [{"number": 5, "keyword": "action", "provider": "workato_db_table", "name": "get_records", "as": "1823734b", "skip": false, "input": {"081b5c41-77a6-4534-ae1a-cc032e2551f3": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "316a6259-8ba4-4338-b18b-fdf6a2d49b0b": "string", "4652b125-31c7-41a7-a518-440147b84c0e": "date_time", "4b3212e0-2c2e-4bc7-85c2-26086ee4f9ac": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "67461374-ee4b-44c8-8fd3-ef62602d6792": "string", "6b305309-5ab8-49da-8687-4bab3044fc0f": "integer", "930baaff-e3c2-4f1e-9ce7-7d9c2fdeddb2": "integer", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "ab7f7770-adca-4e99-8c15-f07bbe493362": "string", "b39400af-67e9-4297-b189-a5b989e06d07": "string", "c16bf317-ae46-44e2-b912-400da66ff1f3": "string", "c8980714-114d-41b9-8a28-701c048e02a5": "integer", "ccf286bd-24c7-4ccf-b186-e1055091ce84": "string", "filters": [{"field_id": "4652b125-31c7-41a7-a518-440147b84c0e", "op_date_time": "gte", "value_date_time": "=(_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}') -1.days).beginning_of_day"}, {"field_id": "4652b125-31c7-41a7-a518-440147b84c0e", "op_date_time": "lt", "value_date_time": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').beginning_of_day"}], "limit": "1000", "order_by_field_id": "4652b125-31c7-41a7-a518-440147b84c0e", "order_direction": "asc", "table_id": "56478"}, "block": []}, {"number": 6, "keyword": "action", "provider": "workato_variable", "name": "insert_to_list_batch", "as": "9c5c969f", "skip": false, "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\"]}')}", "access_profile_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"67461374_ee4b_44c8_8fd3_ef62602d6792\"]}')}", "business_owner_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"081b5c41_77a6_4534_ae1a_cc032e2551f3\"]}')}", "completed_at": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"4652b125_31c7_41a7_a518_440147b84c0e\"]}')}", "completion_tokens": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"c8980714_114d_41b9_8a28_701c048e02a5\"]}')}", "connector": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"4b3212e0_2c2e_4bc7_85c2_26086ee4f9ac\"]}')}", "connector_action": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"b39400af_67e9_4297_b189_a5b989e06d07\"]}')}", "endpoint": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ccf286bd_24c7_4ccf_b186_e1055091ce84\"]}')}", "job_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ab7f7770_adca_4e99_8c15_f07bbe493362\"]}')}", "prompt_tokens": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"930baaff_e3c2_4f1e_9ce7_7d9c2fdeddb2\"]}')}", "recipe_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"c16bf317_ae46_44e2_b912_400da66ff1f3\"]}')}", "total_tokens": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"6b305309_5ab8_49da_8687_4bab3044fc0f\"]}')}", "use_case": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"316a6259_8ba4_4338_b18b_fdf6a2d49b0b\"]}')}"}, "location": "end", "name": "5f3d3717-d75c-48a2-8496-e2c9cad9142b:6eb62ac7"}, "block": []}, {"number": 7, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "ef95fc6a", "skip": false, "input": {"Token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1823734b\",\"path\":[\"continuation_token\"]}').presence or nil", "input_mode": "structured", "name": "f7da2ffd-9a4d-4c3a-9e4d-6b8f3b6ef7be:21a36e04:Token"}, "block": []}, {"number": 8, "keyword": "while_condition", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"21a36e04\",\"path\":[\"Token\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "block": []}]}, {"number": 9, "keyword": "action", "provider": "snowflake", "name": "upsert_rows_batch", "as": "418ea7e9", "skip": false, "input": {"key_columns": "JOB_ID", "rows": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\"]}')}", "access_profile_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"access_profile_name\"]}')}", "business_owner_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"business_owner_email\"]}')}", "completed_at": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"completed_at\"]}')}", "completion_tokens": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"completion_tokens\"]}')}", "connector": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"connector\"]}')}", "connector_action": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"connector_action\"]}')}", "endpoint": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"endpoint\"]}')}", "job_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"job_id\"]}')}", "prompt_tokens": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"prompt_tokens\"]}')}", "recipe_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"recipe_id\"]}')}", "total_tokens": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"total_tokens\"]}')}", "use_case": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6eb62ac7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"use_case\"]}')}"}, "table": "PUBLIC.WORKATO_AI_USAGE"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (TOKEN_DECLARE_AS, "workato_variable", "declare_variable"),
    (LIST_DECLARE_AS, "workato_variable", "declare_list"),
    (GET_RECORDS_AS, "workato_db_table", "get_records"),
    (INSERT_BATCH_AS, "workato_variable", "insert_to_list_batch"),
    (UPDATE_TOKEN_AS, "workato_variable", "update_variables"),
    (UPSERT_AS, "snowflake", "upsert_rows_batch"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "workato_db_table.get_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "snowflake.upsert_rows_batch",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "snowflake.upsert_rows_batch",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "upsert_created",
    "upsert_updated",
    "final_snowflake_tables",
    "workato_db_final_count",
    "cleanup_tables",
)
_NAIVE_ISO_RE_FIELDS = "%Y-%m-%dT%H:%M:%S"


def validate_130423584(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_130423584(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130423584(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler "
            f"tick; the recipe reads job_context, never the trigger): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    job_context = data.get("job_context")
    _require_job_context(job_context)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live", "workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live and "
            f"workato_db_table sections; got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    _require_db_section(seed_in["workato_db_table"])
    _require_snowflake_section(seed_in["snowflake_live"])
    expect = data.get("expect")
    _require_expect_shape(expect)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "job_context": deepcopy(job_context),
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130423584(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130423584(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if "continuation_tokens" in seed["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} must never seed continuation_tokens (the recipe does not "
            "wire Token back into get_records; a seeded token loops forever)"
        )
    if not isinstance(seed.get("job_context"), dict) or not seed["job_context"].get("job_created_at"):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context.job_created_at")
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
        # PUBLIC.WORKATO_AI_USAGE is a benchmark-owned live table: drop it
        # even when execution fails. The datatable is an in-process mock.
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
    result["verifier"] = verify_130423584(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_job_context(job_context: Any) -> None:
    if not isinstance(job_context, dict) or sorted(job_context.keys()) != ["job_created_at"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin job_context as exactly "
            f"{{'job_created_at': ...}} (both date filters read it): {job_context!r}"
        )
    value = str(job_context["job_created_at"] or "")
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != datetime.timedelta(0):
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must be pinned in UTC (+00:00) so the "
            f"beginning_of_day window bounds and the offset-free seed timestamps agree: {value!r}"
        )


def _require_db_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}; "
            "continuation_tokens are FORBIDDEN (the recipe never passes Token back into "
            "get_records, so a seeded token would re-serve page 1 forever)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DB_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{DB_TABLE_ID!r}"
        )
    rows = tables[DB_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {DB_TABLE_ID} must seed a non-empty rows list (the "
            "empty-window variant seeds out-of-window rows, never an empty table)"
        )
    if len(rows) >= 1000:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {DB_TABLE_ID} must stay under the recipe's 1000-row "
            "page limit (the mock ignores limit, so the seed must make it irrelevant)"
        )
    completed_values: list[str] = []
    job_ids: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(DB_ROW_FIELDS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {DB_TABLE_ID} row {idx} must carry exactly the 12 "
                f"uuid column fields: {row!r}"
            )
        for field in DB_STRING_FIELDS:
            if not isinstance(row[field], str) or not row[field].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {DB_TABLE_ID} row {idx} field {field} must be "
                    "a non-empty string"
                )
        for field in DB_INT_FIELDS:
            if isinstance(row[field], bool) or not isinstance(row[field], int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {DB_TABLE_ID} row {idx} field {field} must be "
                    "an integer"
                )
        completed = str(row[COMPLETED_FIELD] or "")
        try:
            datetime.datetime.strptime(completed, _NAIVE_ISO_RE_FIELDS)
        except ValueError as exc:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {DB_TABLE_ID} row {idx} Completed At must be "
                f"offset-free ISO 'YYYY-MM-DDTHH:MM:SS' (byte-stable through the mock filter, "
                f"the upsert args and the TIMESTAMP_NTZ read-back): {completed!r}"
            ) from exc
        completed_values.append(completed)
        job_ids.append(str(row[JOB_ID_FIELD]))
    if completed_values != sorted(completed_values):
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {DB_TABLE_ID} rows must be pre-sorted ascending by "
            "Completed At (the mock ignores order_by; the seed must make it irrelevant)"
        )
    if len(set(job_ids)) != len(job_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {DB_TABLE_ID} Job IDs must be unique (JOB_ID is the "
            "upsert key; duplicate seeds would make row-level groundtruth ambiguous)"
        )


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the upsert path never rewrites current time)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [SNOWFLAKE_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SNOWFLAKE_TABLE!r} (2-part name -> SNOWFLAKE_DATABASE.PUBLIC)"
        )
    spec = tables[SNOWFLAKE_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake table spec must be {{'columns','rows'}}")
    if spec["columns"] != SNOWFLAKE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake columns must be exactly {SNOWFLAKE_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake rows must be a list (may be empty)")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SNOWFLAKE_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake row {idx} must fill every declared column: {row!r}"
            )
        for column, kind in SNOWFLAKE_COLUMNS.items():
            value = row[column]
            if kind == "number" and (isinstance(value, bool) or not isinstance(value, int)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake row {idx} {column} must be an integer"
                )
            if kind == "string" and (not isinstance(value, str) or not value.strip()):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake row {idx} {column} must be a non-empty string"
                )
        completed = str(row["completed_at"] or "")
        try:
            datetime.datetime.strptime(completed, _NAIVE_ISO_RE_FIELDS)
        except ValueError as exc:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake row {idx} completed_at must be offset-free ISO "
                f"'YYYY-MM-DDTHH:MM:SS' (TIMESTAMP_NTZ read-back is byte-identical): {completed!r}"
            ) from exc


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("executed_action_count") != 6:
        raise RuntimeError(
            f"recipe {RECIPE_ID} always executes exactly 6 actions (single while iteration "
            f"because the mock emits no continuation token): {expect.get('executed_action_count')!r}"
        )
    if expect.get("tools") != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {ALLOWED_TOOLS} (linear path, "
            f"one loop iteration): {expect.get('tools')!r}"
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
    merged: dict[str, Any] = {}
    for tool in ("harness.snowflake.snapshot", "harness.workato_db_table.snapshot"):
        for key, value in ctx.tools.call(tool, {}).items():
            if key != "ok":
                merged[key] = value
    return merged


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

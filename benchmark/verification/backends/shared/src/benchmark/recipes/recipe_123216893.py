from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_123216893


RECIPE_ID = "123216893"
SEED_TYPE = "psm_enhancements_snowflake_sync_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "e31aafaf"
SQL_STEP_AS = "2a246498"
FOREACH_AS = "38f87cc5"
UPSERT_AS = "747954b2"
CATCH_AS = "9e9e7b09"
STOP_AS = "6b5e3996"
DB_TABLE_ID = "33563"
PRIMARY_FIELD_ID = "4fd3d64a-5fa4-4a8f-b5db-22a214b39b9f"
ISSUES_TABLE = "bi_db.atlassian.jsm_psm_issues"
SLA_TABLE = "bi_db.atlassian.jsm_psm_issues_sla"
RAW_SQL = (
    "with \n\nbreach_times as (\n    select key, sla_name, breached, breachtime, "
    "row_number() over (partition by key order by breachtime desc) as rn\n    "
    "from bi_db.atlassian.jsm_psm_issues_sla\n    where sla_name = 'PM_TRIAGE_SLA'\n"
    "    order by key\n),\n\nbreach_time as (\n    select *\n    from breach_times\n"
    "    where rn = 1\n)\n\nselect \nj.ticket_url, \nj.key,\nj.summary, \n"
    "j.description,\nj.product_area,\nj.pe_team,\nj.target_project,\n"
    "j.product_manager,\nj.status,\nj.created,\nj.updated, \n"
    "j.source_of_enhancement_request,\nj.customer_company,\n"
    "b.breached as pm_triage_breach,\nb.breachtime as pm_triage_breach_time\n"
    "from bi_db.atlassian.jsm_psm_issues j\nleft join breach_time b on b.key = j.key\n"
    "where j.issuetype = 'Enhancement'"
)

# Mock table 33563 'PSM Enhancements Data' record fields (underscored ids).
FIELD_KEY = "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f"
FIELD_TICKET_URL = "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8"
FIELD_SUMMARY = "75551508_f290_41de_88fd_d77306bebea5"
FIELD_DESCRIPTION = "d3779dbf_043c_4826_8c8e_d83c2e46b8fb"
FIELD_PRODUCT_AREA = "347bdaaf_5194_4363_a3e0_2a1e04f8aca2"
FIELD_PE_TEAM = "e8bf2d92_807a_477b_9c2a_de56a876b993"
FIELD_TARGET_PROJECT = "1b9473c2_54ae_47f3_9576_c3ec76f3bd6d"
FIELD_PRODUCT_MANAGER = "d71da57a_cf54_48ca_89a5_51e4ea1bd675"
FIELD_STATUS = "a08c09e7_53d4_46dc_9bc7_a308696dc6c1"
FIELD_CREATED = "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b"
FIELD_UPDATED = "68cbd891_51dd_4e33_92fa_8651d7e09441"
FIELD_SOURCE = "b57087c4_57c9_4d82_a27e_af9969896e53"
FIELD_CUSTOMER = "5a7eb53b_e407_41fd_a227_8f93e6a9c023"
FIELD_BREACH = "f7651665_4dd2_413d_a704_f81972a4c1d4"
FIELD_BREACH_TIME = "b2ae037d_640f_4c56_aeee_17d61b531080"
DB_RECORD_FIELDS = (
    FIELD_KEY,
    FIELD_TICKET_URL,
    FIELD_SUMMARY,
    FIELD_DESCRIPTION,
    FIELD_PRODUCT_AREA,
    FIELD_PE_TEAM,
    FIELD_TARGET_PROJECT,
    FIELD_PRODUCT_MANAGER,
    FIELD_STATUS,
    FIELD_CREATED,
    FIELD_UPDATED,
    FIELD_SOURCE,
    FIELD_CUSTOMER,
    FIELD_BREACH,
    FIELD_BREACH_TIME,
)

ISSUES_COLUMNS = {
    "TICKET_URL": "string",
    "KEY": "string",
    "SUMMARY": "string",
    "DESCRIPTION": "string",
    "PRODUCT_AREA": "string",
    "PE_TEAM": "string",
    "TARGET_PROJECT": "string",
    "PRODUCT_MANAGER": "string",
    "STATUS": "string",
    "CREATED": "timestamp",
    "UPDATED": "timestamp",
    "SOURCE_OF_ENHANCEMENT_REQUEST": "string",
    "CUSTOMER_COMPANY": "string",
    "ISSUETYPE": "string",
}
SLA_COLUMNS = {
    "KEY": "string",
    "SLA_NAME": "string",
    "BREACHED": "boolean",
    "BREACHTIME": "timestamp",
}

# clock.scheduled_event (as e31aafaf, daily 00:00) -- payload-less trigger
# (seed.trigger MUST be exactly {}). Body = one TRY (step 2):
#   3  snowflake.run_custom_sql 2a246498 (LIVE Snowflake): static CTE --
#      breach_times = jsm_psm_issues_sla WHERE sla_name='PM_TRIAGE_SLA' with
#      row_number() OVER (PARTITION BY key ORDER BY breachtime DESC) -> rn=1
#      keeps the LATEST breach row per key; final SELECT = 13 j.* columns +
#      b.breached pm_triage_breach + b.breachtime pm_triage_breach_time FROM
#      jsm_psm_issues j LEFT JOIN breach_time b ON b.key = j.key WHERE
#      j.issuetype = 'Enhancement'. The 3-part bi_db.atlassian.* names map to
#      <BENCH_DB>.ATLASSIAN.* live.
#   4  FOREACH 38f87cc5 over rows (repeat_mode simple; 0..N iterations) ->
#   5  workato_db_table.upsert_record 747954b2 (MOCK table 33563 'PSM
#      Enhancements Data', primary key = 4fd3d64a-... 'key'): 10 #{pill}
#      fields (typed passthrough -- pm_triage_breach lands the JSON boolean),
#      created/updated/pm_triage_breach_time via =pill formula mode (live
#      TIMESTAMP_NTZ read-back isoformat strings, null passes through), and
#      description via the ternary
#        =pill.present? ? pill.gsub('"', "'")[0,9999] : null
#      (single/mixed-quote gsub args + two-arg slice -- the two engine gaps
#      fixed for this recipe; blank description takes the null arm).
#   6  CATCH 9e9e7b09 (max_retry_count 3 -- the engine executes try/catch as
#      a single attempt, observably identical for a deterministic forced
#      error) -> 7 STOP 6b5e3996 stop_with_error true, reason
#      '#{catch.type}: #{catch.message} (Retry count: #{catch.retry_count})'.
#      ENGINE SEMANTICS PINNED: the stop trace row carries stopped:true only;
#      stop_reason is not resolved into the trace, and the catch payload has
#      only {type, message}.
#
# Branch mapping (all reachable paths covered):
# - variant_00 upsert_mixed: 3 Enhancement rows -> 3 upserts (PSM-1 UPDATE of
#   a pre-seeded stale mock row created:false; PSM-3 + PSM-4 INSERTs
#   created:true); PSM-2 'Bug' decoy excluded by the WHERE; PSM-1 has TWO
#   PM_TRIAGE_SLA rows (rn=1 picks the LATEST breachtime -> breached true)
#   plus an OTHER_SLA decoy that would win rn=1 if the sla_name filter broke;
#   PSM-4 has NO sla row -> LEFT JOIN nulls -> breach fields null (dropped
#   from the stored mock row); PSM-1/PSM-3 descriptions carry double quotes
#   -> gsub swaps them to single quotes.
# - variant_01 blank_description_null_arm: description '' -> present? false
#   -> ternary null arm -> description None in the upsert args and ABSENT
#   from the stored row. 1 insert.
# - variant_02 zero_rows: no Enhancement rows -> SQL 0 rows -> foreach runs 0
#   iterations -> no upserts; the pre-seeded mock row must be byte-identical
#   after the run.
# - variant_03 catch_stop: seed.force_action_error on 2a246498 (static SQL --
#   no trigger-controllable live failure) -> the error raises BEFORE the tool
#   call (NO snowflake row in the trace) -> CATCH -> STOP with error. 0
#   executed actions.
#
# ROW-ORDER NOTE (live lane): the final SELECT has no ORDER BY; expects pin
# the seed insertion order ([PSM-1, PSM-3, PSM-4]), which the triage live
# probe observed for these single-micro-partition seed tables. The live lane
# must confirm order stability before registering.
#
# Backends: Snowflake LIVE (harness.snowflake_live.seed_tables
# create-or-replace; dropped in the runner's finally -- READ-ONLY here, live
# snapshot equality verifier-pinned); workato_db_table 33563 MOCK
# (Workato-internal, per-variant seeded state). No current_time seed needed:
# the SQL never references current date/time.

_RAW_PIN_JSON = r"""{"as": "e31aafaf", "block": [{"as": "", "block": [{"as": "2a246498", "block": [], "input": {"output_schema": "[{\"control_type\":\"text\",\"label\":\"Ticket URL\",\"type\":\"string\",\"name\":\"ticket_url\"},{\"control_type\":\"text\",\"label\":\"Key\",\"type\":\"string\",\"name\":\"key\"},{\"control_type\":\"text\",\"label\":\"Summary\",\"type\":\"string\",\"name\":\"summary\"},{\"control_type\":\"text\",\"label\":\"Description\",\"type\":\"string\",\"name\":\"description\"},{\"control_type\":\"text\",\"label\":\"Product area\",\"type\":\"string\",\"name\":\"product_area\"},{\"control_type\":\"text\",\"label\":\"Pe team\",\"type\":\"string\",\"name\":\"pe_team\"},{\"control_type\":\"text\",\"label\":\"Target project\",\"type\":\"string\",\"name\":\"target_project\"},{\"control_type\":\"text\",\"label\":\"Product manager\",\"type\":\"string\",\"name\":\"product_manager\"},{\"control_type\":\"text\",\"label\":\"Status\",\"type\":\"string\",\"name\":\"status\"},{\"control_type\":\"text\",\"label\":\"Created\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"created\"},{\"control_type\":\"text\",\"label\":\"Updated\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"updated\"},{\"control_type\":\"text\",\"label\":\"Source of enhancement request\",\"type\":\"string\",\"name\":\"source_of_enhancement_request\"},{\"control_type\":\"text\",\"label\":\"Customer company\",\"type\":\"string\",\"name\":\"customer_company\"},{\"control_type\":\"text\",\"label\":\"Pm triage breach\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Pm triage breach\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"pm_triage_breach\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"pm_triage_breach\"},{\"control_type\":\"text\",\"label\":\"Pm triage breach time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"pm_triage_breach_time\"}]", "sql": "with \n\nbreach_times as (\n    select key, sla_name, breached, breachtime, row_number() over (partition by key order by breachtime desc) as rn\n    from bi_db.atlassian.jsm_psm_issues_sla\n    where sla_name = 'PM_TRIAGE_SLA'\n    order by key\n),\n\nbreach_time as (\n    select *\n    from breach_times\n    where rn = 1\n)\n\nselect \nj.ticket_url, \nj.key,\nj.summary, \nj.description,\nj.product_area,\nj.pe_team,\nj.target_project,\nj.product_manager,\nj.status,\nj.created,\nj.updated, \nj.source_of_enhancement_request,\nj.customer_company,\nb.breached as pm_triage_breach,\nb.breachtime as pm_triage_breach_time\nfrom bi_db.atlassian.jsm_psm_issues j\nleft join breach_time b on b.key = j.key\nwhere j.issuetype = 'Enhancement'", "update_only": "false"}, "keyword": "action", "name": "run_custom_sql", "number": 3, "provider": "snowflake", "skip": false}, {"as": "38f87cc5", "block": [{"as": "747954b2", "block": [], "input": {"parameters": {"1b9473c2_54ae_47f3_9576_c3ec76f3bd6d": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"target_project\"]}')}", "347bdaaf_5194_4363_a3e0_2a1e04f8aca2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"product_area\"]}')}", "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"ticket_url\"]}')}", "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"key\"]}')}", "5a7eb53b_e407_41fd_a227_8f93e6a9c023": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"customer_company\"]}')}", "68cbd891_51dd_4e33_92fa_8651d7e09441": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"updated\"]}')", "75551508_f290_41de_88fd_d77306bebea5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"summary\"]}')}", "a08c09e7_53d4_46dc_9bc7_a308696dc6c1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"status\"]}')}", "b2ae037d_640f_4c56_aeee_17d61b531080": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"pm_triage_breach_time\"]}')", "b57087c4_57c9_4d82_a27e_af9969896e53": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"source_of_enhancement_request\"]}')}", "d3779dbf_043c_4826_8c8e_d83c2e46b8fb": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"description\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"description\"]}').gsub('\"', \"'\")[0,9999] : null", "d71da57a_cf54_48ca_89a5_51e4ea1bd675": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"product_manager\"]}')}", "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"created\"]}')", "e8bf2d92_807a_477b_9c2a_de56a876b993": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"pe_team\"]}')}", "f7651665_4dd2_413d_a704_f81972a4c1d4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"38f87cc5\",\"path\":[\"pm_triage_breach\"]}')}"}, "primary_field_id": "4fd3d64a-5fa4-4a8f-b5db-22a214b39b9f", "table_id": "33563"}, "keyword": "action", "name": "upsert_record", "number": 5, "provider": "workato_db_table", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"2a246498\",\"path\":[\"rows\"]}')}"}, "keyword": "foreach", "name": "", "number": 4, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"2a246498\",\"path\":[\"rows\"]}')}"}, {"as": "9e9e7b09", "block": [{"as": "6b5e3996", "block": [], "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"9e9e7b09\",\"path\":[\"type\"]}')}: #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"9e9e7b09\",\"path\":[\"message\"]}')} (Retry count: #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"9e9e7b09\",\"path\":[\"retry_count\"]}')})", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 7, "provider": "", "skip": false}], "input": {"max_retry_count": "3", "retry_interval": "5"}, "keyword": "catch", "name": "", "number": 6, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"time_unit": "days", "trigger_at": "00:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (UPSERT_AS, "workato_db_table", "upsert_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_db_table.upsert_record",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_db_table.upsert_record",
]
REQUIRED_EXPECT_KEYS = (
    "case",
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_rows_keys",
    "upsert_records",
    "upsert_created",
    "stopped",
    "initial_table_rows",
    "final_table_rows",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
BRANCHES = ("foreach_upserts", "zero_rows", "catch_stop")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def validate_123216893(raw: dict[str, Any]) -> dict[str, Any]:
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
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    # Semantic pins (the tree pin holds the bytes; these name the traps):
    # 1. the verbatim CTE/window SQL,
    if str((nodes[SQL_STEP_AS].get("input") or {}).get("sql")) != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed")
    # 2. the upsert target (mock table + dashed primary 'key' field),
    upsert_input = nodes[UPSERT_AS].get("input") or {}
    if (
        str(upsert_input.get("table_id")) != DB_TABLE_ID
        or str(upsert_input.get("primary_field_id")) != PRIMARY_FIELD_ID
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert target changed: {upsert_input!r}")
    if sorted((upsert_input.get("parameters") or {}).keys()) != sorted(DB_RECORD_FIELDS):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert record fields changed")
    # 3. the description ternary with single/mixed-quote gsub + [0,9999] slice
    #    (the two engine gaps this recipe needed),
    description_formula = str((upsert_input.get("parameters") or {}).get(FIELD_DESCRIPTION) or "")
    if ".gsub('\"', \"'\")[0,9999]" not in description_formula or ": null" not in description_formula:
        raise RuntimeError(
            f"recipe {RECIPE_ID} description ternary changed: {description_formula!r}"
        )
    # 4. the foreach source is the snowflake rows pill,
    foreach = next(node for node in _walk_nodes(raw) if node.get("keyword") == "foreach")
    if SQL_STEP_AS not in str(foreach.get("source") or "") or foreach.get("repeat_mode") != "simple":
        raise RuntimeError(f"recipe {RECIPE_ID} foreach source changed")
    # 5. the catch->stop wiring (stop_with_error true).
    stop = nodes[STOP_AS]
    if str((stop.get("input") or {}).get("stop_with_error")) != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} stop node changed")
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


def seed_123216893(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123216893(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less "
            f"scheduler tick): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live", "workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live + "
            f"workato_db_table sections: got "
            f"{sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    seeded_keys = _require_db_section(seed_in["workato_db_table"])
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(data.get("expect"), force, seed_in, seeded_keys)
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
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_123216893(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123216893(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live section")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be exactly {{}}")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
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
        # The seeded jsm tables are benchmark-owned create-or-replace live
        # state: drop them even when execution fails (cleanup principle). The
        # mock table is per-variant seeded state re-materialized from seed.json
        # on every run -- no cleanup needed.
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
    result["verifier"] = verify_123216893(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    unexpected = sorted(set(section.keys()) - {"tables"})
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live has unexpected keys: {unexpected} "
            f"(the SQL never uses current date/time, so current_time must not be seeded)"
        )
    if sorted(section["tables"]) != sorted([ISSUES_TABLE, SLA_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{ISSUES_TABLE!r} and {SLA_TABLE!r}"
        )
    issues = section["tables"][ISSUES_TABLE]
    sla = section["tables"][SLA_TABLE]
    for name, spec, columns in (
        (ISSUES_TABLE, issues, ISSUES_COLUMNS),
        (SLA_TABLE, sla, SLA_COLUMNS),
    ):
        if not isinstance(spec, dict) or spec.get("columns") != columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {name} columns must be exactly {columns} (every "
                f"SQL-referenced column needs a declared type; all-null seeds would drop "
                f"columns at CREATE)"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {name} rows must be a NON-EMPTY list (an empty live "
                f"table cannot pin the WHERE/JOIN semantics; use decoy rows for the "
                f"zero-Enhancement branch)"
            )
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(columns):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every {name} row must fill all declared columns "
                    f"(use '' not null -- type inference must never drop a column): {row!r}"
                )
    issue_keys = [str(row["KEY"]) for row in issues["rows"]]
    if len(set(issue_keys)) != len(issue_keys):
        raise RuntimeError(f"recipe {RECIPE_ID} issue KEY values must be unique")
    for row in issues["rows"]:
        for column in ("CREATED", "UPDATED"):
            if not _TIMESTAMP_RE.match(str(row[column])):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {column} must be a 'YYYY-MM-DD HH:MM:SS' literal "
                    f"(stable isoformat read-back): {row!r}"
                )
    triage_times: dict[str, list[str]] = {}
    for row in sla["rows"]:
        if not isinstance(row["BREACHED"], bool):
            raise RuntimeError(f"recipe {RECIPE_ID} BREACHED must be a JSON boolean: {row!r}")
        if not _TIMESTAMP_RE.match(str(row["BREACHTIME"])):
            raise RuntimeError(
                f"recipe {RECIPE_ID} BREACHTIME must be a 'YYYY-MM-DD HH:MM:SS' literal: {row!r}"
            )
        if str(row["SLA_NAME"]) == "PM_TRIAGE_SLA":
            triage_times.setdefault(str(row["KEY"]), []).append(str(row["BREACHTIME"]))
    for key, times in triage_times.items():
        if len(set(times)) != len(times):
            raise RuntimeError(
                f"recipe {RECIPE_ID} PM_TRIAGE_SLA breachtimes for {key} must be distinct "
                f"(row_number() ... ORDER BY breachtime DESC must be deterministic)"
            )


def _require_db_section(section: Any) -> list[str]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DB_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{DB_TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[DB_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {DB_TABLE_ID} rows must be a list")
    keys: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(DB_RECORD_FIELDS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown}")
        if not isinstance(row.get(FIELD_KEY), str) or not row[FIELD_KEY].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} needs a non-empty key ({FIELD_KEY}) "
                f"-- it is the upsert primary key"
            )
        keys.append(row[FIELD_KEY])
    if len(set(keys)) != len(keys):
        raise RuntimeError(f"recipe {RECIPE_ID} seeded key values must be unique (upsert primary)")
    return keys


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} "
            f"with an explicit error message (the static SQL has no trigger-controllable "
            f"live failure; the mock upsert cannot fail deterministically)"
        )


def _require_expect_shape(
    expect: Any, force: Any, seed_in: dict[str, Any], seeded_keys: list[str]
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    if (branch == "catch_stop") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch_stop branch and force_action_error must be "
            f"declared together"
        )
    sql_keys = expect.get("sql_rows_keys")
    records = expect.get("upsert_records")
    created = expect.get("upsert_created")
    if branch == "catch_stop":
        checks = (
            sql_keys is None,
            records == [],
            created == [],
            expect.get("stopped") is True,
            expect.get("executed_action_count") == 0,
            expect.get("tools") == [],
            expect.get("tool_expectations") == [],
            isinstance(expect.get("catch_message"), str)
            and expect["catch_message"] == force.get("error"),
        )
        if not all(checks):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch_stop expect block is incoherent: {expect!r}"
            )
    else:
        if not isinstance(sql_keys, list) or not isinstance(records, list) or not isinstance(created, list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.sql_rows_keys/upsert_records/upsert_created "
                f"must be lists on SQL branches"
            )
        if (branch == "zero_rows") != (len(sql_keys) == 0):
            raise RuntimeError(
                f"recipe {RECIPE_ID} zero_rows branch requires exactly 0 SQL rows "
                f"(and foreach_upserts at least 1): {expect!r}"
            )
        if len(records) != len(sql_keys) or len(created) != len(sql_keys):
            raise RuntimeError(
                f"recipe {RECIPE_ID} one upsert per SQL row: sql_rows_keys={sql_keys!r} "
                f"upsert_records={len(records)} upsert_created={len(created)}"
            )
        if expect.get("stopped") is not False or "catch_message" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} SQL branches never stop and never catch: {expect!r}"
            )
        if expect.get("executed_action_count") != 1 + len(sql_keys):
            raise RuntimeError(
                f"recipe {RECIPE_ID} executed_action_count must be 1 + upserts: {expect!r}"
            )
        expected_tools = ["snowflake.run_custom_sql"] + [
            "workato_db_table.upsert_record"
        ] * len(sql_keys)
        if expect.get("tools") != expected_tools:
            raise RuntimeError(f"recipe {RECIPE_ID} expect.tools must be {expected_tools}")
        items = expect.get("tool_expectations")
        if not isinstance(items, list) or len(items) != len(expected_tools):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations must carry one item per expected call"
            )
        issues_by_key = {
            str(row["KEY"]): row
            for row in seed_in["snowflake_live"]["tables"][ISSUES_TABLE]["rows"]
        }
        for key, record, flag in zip(sql_keys, records, created):
            if not isinstance(record, dict) or record.get(FIELD_KEY) != key:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} upsert record for {key!r} must carry the key "
                    f"field: {record!r}"
                )
            row = issues_by_key.get(str(key))
            if not isinstance(row, dict) or str(row.get("ISSUETYPE")) != "Enhancement":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sql_rows_keys entry {key!r} must be a seeded "
                    f"Enhancement issue"
                )
            if flag is not (key not in seeded_keys):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} created flag for {key!r} contradicts the seeded "
                    f"mock table (pre-seeded key -> update created:false)"
                )
        non_enhancement = [
            str(row["KEY"])
            for row in seed_in["snowflake_live"]["tables"][ISSUES_TABLE]["rows"]
            if str(row.get("ISSUETYPE")) != "Enhancement"
        ]
        if not non_enhancement:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every SQL-branch variant must seed at least one "
                f"non-Enhancement decoy row (the WHERE filter must be observable)"
            )
        enhancement_keys = [
            str(row["KEY"])
            for row in seed_in["snowflake_live"]["tables"][ISSUES_TABLE]["rows"]
            if str(row.get("ISSUETYPE")) == "Enhancement"
        ]
        if sorted(enhancement_keys) != sorted(str(key) for key in sql_keys):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sql_rows_keys must cover every seeded Enhancement "
                f"issue exactly once: seeded={enhancement_keys!r} expected={sql_keys!r}"
            )
    if not isinstance(expect.get("initial_table_rows"), list) or not isinstance(
        expect.get("final_table_rows"), list
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect must pin initial_table_rows/final_table_rows"
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
    merged: dict[str, Any] = {}
    for key, value in ctx.tools.call("harness.workato_db_table.snapshot", {}).items():
        if key != "ok":
            merged[key] = value
    for key, value in ctx.tools.call("harness.snowflake.snapshot", {}).items():
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

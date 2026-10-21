from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_112147962


RECIPE_ID = "112147962"
SEED_TYPE = "gsheets_sync_log_notify_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "36a295e0"
DECLARE_STRINGS_AS = "1b604b40"
DECLARE_MESSAGE_AS = "2827c38c"
UPSERT_AS = "de0e5465"
POST_SUCCESS_AS = "40e0f3b9"
POST_ERROR_AS = "55c7f4e5"
RETURN_AS = "7f4ad154"
DB_TABLE_ID = "18871"
PRIMARY_FIELD_ID = "ff4e9906-204e-4d1e-a77d-166e1da98025"
RAW_CHANNEL = "#api-interest-gsheets-sync-update"
FIELD_JOB_TYPE = "38cad50b_c7f6_4ddd_914c_83ce17ba24e5"
FIELD_SUCCESS = "74c3bd2b_6daf_4e66_87d0_34eb0a016521"
FIELD_ERROR = "7785bacb_64d3_4bbb_9025_8dfcbc65e722"
FIELD_JOB_CREATED = "85ded8e6_b7f2_482e_b84c_9598dcda6cf2"
FIELD_JOB_DATE = "914f28df_3166_4686_993c_7cf60f833c97"
FIELD_JOB_LINK = "ff4e9906_204e_4d1e_a77d_166e1da98025"
DB_RECORD_FIELDS = (
    FIELD_JOB_TYPE,
    FIELD_SUCCESS,
    FIELD_ERROR,
    FIELD_JOB_CREATED,
    FIELD_JOB_DATE,
    FIELD_JOB_LINK,
)

# workato_recipe_function.execute (as 36a295e0) -- dereferences parameters.
# {jobType, error, jobLink, jobDate, successful (boolean_conversion),
# rowsUpserted} plus job_context.job_created_at. Body:
#   2  declare_variable 1b604b40 (five formula strings, all probed green):
#        DateString  = ="started at _" + job_created_at.strftime(
#                      "%A, %d %B %Y,%k:%M:%S") + "_ " -- %A/%B day+month
#                      names; %k is the SPACE-PADDED hour (' 9' vs '14'),
#                      pinned by one single-digit-hour and one two-digit-hour
#                      variant; the seed timestamp's own wall time renders
#                      (no zone conversion)
#        JobString   = ="Sync job *" + jobType + "* "
#        RowsUpsertedString = rowsUpserted.present? ? ("with *" +
#                      rowsUpserted + "* Rows added") : ""
#        SuccessString = ="is *" + (successful ? "Successful" :
#                      "Not Successful") + "* " -- BARE-PILL Ruby truthiness.
#                      CRITICAL SEED RULE: parameters.successful must be a
#                      JSON BOOLEAN. The string 'false' is TRUTHY here
#                      ('is *Successful* ') while the IF-5 is_true operand is
#                      string-aware -- an incoherent non-Workato state the
#                      seeder rejects loudly (schema boolean_conversion).
#        jobDateString = jobDate.present? ? ("for Date _" + jobDate + "_ ")
#                      : ""
#   3  declare_variable 2827c38c: MessageString = JobString + DateString +
#      "\n" + SuccessString + jobDateString + RowsUpsertedString (real
#      newline via decoded escape)
#   4  workato_db_table.upsert_record de0e5465 (MOCK datatable 18871 'API
#      Interest GSheets Sync Log', primary jobLink ff4e9906-...): fields
#      jobType/successful/error/jobDate/jobLink from parameters +
#      jobCreatedDateTime = job_context.job_created_at verbatim. Absent
#      optional parameters land as null. Insert vs update both reachable
#      (update variant pre-seeds a row with the same jobLink).
#   IF 5 (parameters.successful is_true)
#   -> 6  slack_bot.post_bot_message 40e0f3b9 (LIVE): blocks section_with_
#         button (section_text=MessageString, url=jobLink) + divider ->
#         rendered text is MessageString ONLY (button/divider contribute no
#         lines); channel '#api-interest-gsheets-sync-update' routes to
#         SLACK_CHANNEL_OVERRIDE
#   ELSE 7
#   -> 8  slack_bot.post_bot_message 55c7f4e5 (LIVE): same + section
#         '*Error:* _#{parameters.error}_' -> text is MessageString + "\n" +
#         the error line
#   9  return_result 7f4ad154 (empty result {})
#
# Exactly one post per run; 5 executed actions on every path. Backends:
# slack LIVE (terminal observable posts -> no cleanup), workato_db_table
# MOCK (Workato-internal; per-variant seeded), workato_variable +
# workato_recipe_function mocks. job_context comes from the variant input.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "36a295e0", "skip": false, "input": {"parameters_schema_json": "[{\"control_type\":\"text\",\"label\":\"Job type\",\"name\":\"jobType\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Error\",\"name\":\"error\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Job link\",\"name\":\"jobLink\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"jobDate\",\"name\":\"jobDate\",\"type\":\"date_time\",\"optional\":true,\"hint\":\"job is for this particular date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"},{\"control_type\":\"checkbox\",\"label\":\"Successful\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"successful\",\"type\":\"boolean\",\"optional\":false,\"hint\":\"if the job is successful\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Successful\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"successful\",\"type\":\"boolean\",\"optional\":false,\"hint\":\"if the job is successful\"}},{\"name\":\"rowsUpserted\",\"type\":\"integer\",\"optional\":true,\"hint\":\"number of rows upserted by the recipe (if applicable)\",\"control_type\":\"integer\",\"label\":\"Rows upserted\",\"parse_output\":\"integer_conversion\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "1b604b40", "skip": false, "input": {"variables": {"data": {"DateString": "=\"started at _\" + (_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').strftime(\"%A, %d %B %Y,%k:%M:%S\")) + \"_ \"", "JobString": "=\"Sync job *\" + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\",\"jobType\"]}') + \"* \"", "RowsUpsertedString": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\",\"rowsUpserted\"]}').present?) ? (\"with *\" +_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\",\"rowsUpserted\"]}') + \"* Rows added\") : \"\"", "SuccessString": "=\"is *\" +(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\",\"successful\"]}') ? \"Successful\" : \"Not Successful\") + \"* \"", "jobDateString": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\",\"jobDate\"]}').present?) ? (\"for Date _\" + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\",\"jobDate\"]}') + \"_ \") : \"\""}, "schema": "[{\"control_type\":\"text\",\"label\":\"SuccessString\",\"name\":\"SuccessString\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"SuccessString\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"DateString\",\"name\":\"DateString\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"DateString\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"JobDateString\",\"name\":\"jobDateString\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"jobDateString\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"control_type\":\"text\",\"label\":\"RowsUpsertedString\",\"name\":\"RowsUpsertedString\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"RowsUpsertedString\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"name\":\"JobString\",\"type\":\"string\",\"optional\":true,\"label\":\"JobString\",\"details\":{\"real_name\":\"JobString\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "2827c38c", "skip": false, "input": {"variables": {"data": {"MessageString": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1b604b40\",\"path\":[\"JobString\"]}') + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1b604b40\",\"path\":[\"DateString\"]}') + \"\\n\" + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1b604b40\",\"path\":[\"SuccessString\"]}') + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1b604b40\",\"path\":[\"jobDateString\"]}') + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1b604b40\",\"path\":[\"RowsUpsertedString\"]}')"}, "schema": "[{\"name\":\"MessageString\",\"type\":\"string\",\"optional\":true,\"label\":\"MessageString\",\"details\":{\"real_name\":\"MessageString\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 4, "keyword": "action", "provider": "workato_db_table", "name": "upsert_record", "as": "de0e5465", "skip": false, "input": {"parameters": {"38cad50b_c7f6_4ddd_914c_83ce17ba24e5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"jobType\"]}')}", "74c3bd2b_6daf_4e66_87d0_34eb0a016521": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"successful\"]}')}", "7785bacb_64d3_4bbb_9025_8dfcbc65e722": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"error\"]}')}", "85ded8e6_b7f2_482e_b84c_9598dcda6cf2": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}')}", "914f28df_3166_4686_993c_7cf60f833c97": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"jobDate\"]}')}", "ff4e9906_204e_4d1e_a77d_166e1da98025": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"jobLink\"]}')}"}, "primary_field_id": "ff4e9906-204e-4d1e-a77d-166e1da98025", "table_id": "18871"}, "block": []}, {"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"successful\"]}')}", "operand": "is_true", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "40e0f3b9", "skip": false, "input": {"blocks": [{"block_type": "section_with_button_with_long_action", "button_title": "Go to job", "button_type": "url_button", "section_text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2827c38c\",\"path\":[\"MessageString\"]}')}", "style": "default", "url": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"jobLink\"]}')}"}, {"block_type": "divider", "button_type": "continue_flow"}], "channel": "#api-interest-gsheets-sync-update"}, "block": []}, {"number": 7, "keyword": "else", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 8, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "55c7f4e5", "skip": false, "input": {"blocks": [{"block_type": "section_with_button_with_long_action", "button_title": "Go to job", "button_type": "url_button", "section_text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2827c38c\",\"path\":[\"MessageString\"]}')}", "style": "default", "url": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"jobLink\"]}')}"}, {"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "*Error:* _#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"36a295e0\",\"path\":[\"parameters\", \"error\"]}')}_"}, {"block_type": "divider", "button_type": "continue_flow"}], "channel": "#api-interest-gsheets-sync-update"}, "block": []}]}]}, {"number": 9, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "7f4ad154", "skip": false, "input": {}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STRINGS_AS, "workato_variable", "declare_variable"),
    (DECLARE_MESSAGE_AS, "workato_variable", "declare_variable"),
    (UPSERT_AS, "workato_db_table", "upsert_record"),
    (POST_SUCCESS_AS, "slack_bot", "post_bot_message"),
    (POST_ERROR_AS, "slack_bot", "post_bot_message"),
    (RETURN_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_db_table.upsert_record",
    "slack.post_message",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.upsert_record",
    "slack.post_message",
    "workato_recipe_function.return_result",
]
REQUIRED_PARAM_KEYS = ("jobType", "jobLink", "successful")
OPTIONAL_PARAM_KEYS = ("error", "jobDate", "rowsUpserted")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "raw_executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "declared_strings",
    "message_string",
    "slack_posts",
    "return_value",
    "initial_table_rows",
    "final_table_rows",
)
KNOWN_BRANCHES = ("success_post", "error_post")


def validate_112147962(raw: dict[str, Any]) -> dict[str, Any]:
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
    # 1. the bare-pill truthiness ternary that makes the boolean seed rule
    #    load-bearing,
    success_formula = str(
        (((nodes[DECLARE_STRINGS_AS].get("input") or {}).get("variables") or {}).get("data") or {})
        .get("SuccessString")
        or ""
    )
    if '? "Successful" : "Not Successful"' not in success_formula:
        raise RuntimeError(
            f"recipe {RECIPE_ID} SuccessString ternary changed: {success_formula!r}"
        )
    # 2. the upsert target (mock table + jobLink primary),
    upsert_input = nodes[UPSERT_AS].get("input") or {}
    if (
        str(upsert_input.get("table_id")) != DB_TABLE_ID
        or str(upsert_input.get("primary_field_id")) != PRIMARY_FIELD_ID
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert target changed: {upsert_input!r}")
    # 3. both posts target the raw channel (routed to the override live) and
    #    only the ELSE post carries the error section.
    for step_as, block_count in ((POST_SUCCESS_AS, 2), (POST_ERROR_AS, 3)):
        post_input = nodes[step_as].get("input") or {}
        if str(post_input.get("channel")) != RAW_CHANNEL:
            raise RuntimeError(f"recipe {RECIPE_ID} post {step_as} channel changed")
        blocks = post_input.get("blocks") or []
        if len(blocks) != block_count:
            raise RuntimeError(f"recipe {RECIPE_ID} post {step_as} blocks changed: {blocks!r}")
    error_section = str((nodes[POST_ERROR_AS].get("input") or {}).get("blocks")[1].get("section_text") or "")
    if not error_section.startswith("*Error:* _"):
        raise RuntimeError(f"recipe {RECIPE_ID} error section changed: {error_section!r}")
    # 4. the IF keys on parameters.successful with is_true.
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    if len(if_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} IF layout changed")
    conditions = (if_nodes[0].get("input") or {}).get("conditions") or []
    if (
        len(conditions) != 1
        or str(conditions[0].get("operand")) != "is_true"
        or '"successful"' not in str(conditions[0].get("lhs"))
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF condition changed: {conditions!r}")
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


def seed_112147962(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_112147962(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    job_context = data.get("job_context")
    _require_job_context(job_context)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; got "
            f"{sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    _require_db_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    _require_expect_shape(expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "job_context": deepcopy(job_context),
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_112147962(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_112147962(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("job_context"), dict) or not seed["job_context"].get("job_created_at"):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context.job_created_at")
    _require_trigger_shape(seed.get("trigger") or {})
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "expected_channel": ctx.env.slack_channel_override,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_112147962(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger["parameters"]
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters must be an object")
    unknown = sorted(set(parameters.keys()) - set(REQUIRED_PARAM_KEYS) - set(OPTIONAL_PARAM_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has unknown keys: {unknown}")
    missing = [key for key in REQUIRED_PARAM_KEYS if key not in parameters]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters missing: {missing}")
    for key in ("jobType", "jobLink"):
        if not isinstance(parameters.get(key), str) or not parameters[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.{key} must be a non-empty string"
            )
    if not isinstance(parameters.get("successful"), bool):
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.successful MUST be a JSON boolean "
            f"(boolean_conversion schema). A string 'false' would be TRUTHY in the bare-pill "
            f"SuccessString ternary ('is *Successful* ') while the string-aware IF-5 is_true "
            f"takes the else branch -- an incoherent state real Workato cannot produce: "
            f"{parameters.get('successful')!r}"
        )
    if "error" in parameters and not isinstance(parameters["error"], str):
        raise RuntimeError(f"recipe {RECIPE_ID} parameters.error must be a string when present")
    if "jobDate" in parameters:
        value = parameters["jobDate"]
        if not isinstance(value, str):
            raise RuntimeError(f"recipe {RECIPE_ID} parameters.jobDate must be a string")
        datetime.date.fromisoformat(value)
    if "rowsUpserted" in parameters:
        value = parameters["rowsUpserted"]
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.rowsUpserted must be a JSON integer "
                f"(integer_conversion schema): {value!r}"
            )


def _require_job_context(job_context: Any) -> None:
    if not isinstance(job_context, dict) or sorted(job_context.keys()) != ["job_created_at"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin job_context as exactly "
            f"{{'job_created_at': ...}} (DateString and the upsert both read it): {job_context!r}"
        )
    value = str(job_context["job_created_at"] or "")
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must carry an explicit UTC offset (the "
            f"strftime renders its wall time verbatim): {value!r}"
        )


def _require_db_section(section: Any) -> None:
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
    job_links: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(DB_RECORD_FIELDS))
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown}"
            )
        if not isinstance(row.get(FIELD_JOB_LINK), str) or not row[FIELD_JOB_LINK].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} needs a non-empty jobLink "
                f"({FIELD_JOB_LINK}) -- it is the upsert primary key"
            )
        job_links.append(row[FIELD_JOB_LINK])
    if len(set(job_links)) != len(job_links):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded jobLink values must be unique (upsert primary key)"
        )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("executed_action_count") != len(ALLOWED_TOOLS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} exposes exactly {len(ALLOWED_TOOLS)} benchmark tool "
            f"actions: {expect.get('executed_action_count')!r}"
        )
    if expect.get("raw_executed_action_count") != 5:
        raise RuntimeError(
            f"recipe {RECIPE_ID} always executes exactly 5 raw actions (2 declares, "
            f"upsert, one post, return): {expect.get('raw_executed_action_count')!r}"
        )
    if expect.get("tools") != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {ALLOWED_TOOLS}: "
            f"{expect.get('tools')!r}"
        )
    if expect.get("branch") not in KNOWN_BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch unknown: {expect.get('branch')!r}")
    if expect.get("return_value") != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} return_result is empty; expect.return_value must be {{}}: "
            f"{expect.get('return_value')!r}"
        )
    posts = expect.get("slack_posts")
    if not isinstance(posts, list) or len(posts) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly one post fires per run; expect.slack_posts must pin "
            f"it as a single [step_as, text] entry: {posts!r}"
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
    return merged


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

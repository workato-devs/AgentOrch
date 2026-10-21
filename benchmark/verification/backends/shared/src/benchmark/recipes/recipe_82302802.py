from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_82302802


RECIPE_ID = "82302802"
SEED_TYPE = "recipe_function_staged_file_column_count_variant"
TRACK = "workato_recipe_function_staged_file_column_count"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
# Callable recipe function (trigger as cabb207b; parameters.database/.schema/
# .stage/.date_path/.file_format, all required strings). "Takes a staged S3
# file and return the number of columns". The whole body is wrapped in TRY
# (step 2):
#   snowflake.search_rows_sql (step 3, as cdea878c) -- LIVE Snowflake; reads a
#     STAGED FILE, not a table:
#       SELECT ARRAY_SIZE(SPLIT(T.$1, ',')) AS NUMBER_OF_COLUMNS
#       FROM @<database>.<schema>.<stage>/<date_path>
#       (FILE_FORMAT => '<database>.<schema>.<file_format>') AS T LIMIT 1
#     All five identifiers are interpolated verbatim from the trigger
#     parameters. The named FILE FORMAT must use FIELD_DELIMITER = NONE so
#     T.$1 is the whole line and the comma-split counts every column (the raw
#     step comment: "For this to work, file format needs to used a different
#     delimiter than what the file is using").
#   return_result (step 4, as 1c675dba): number_of_columns = rows[0] pill
#     .presence or 0, success "true".
# CATCH (step 5, as 2918c48b, max_retry_count=0, retry_interval=2):
#   return_result (step 6, as 9b578a55): error_message = catch message pill,
#     number_of_columns = same pill formula (snowflake step missing -> 0),
#     success "false".
# Snowflake runs LIVE. The stage, its named file format and the staged CSV
# are benchmark-owned objects provisioned by the seed
# (seed.snowflake_live.stages via harness.snowflake_live.seed_tables) and
# dropped by harness cleanup; the recipe-function return is a deterministic
# Workato-internal mock.
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("snowflake", "search_rows_sql", "cdea878c"),
    ("workato_recipe_function", "return_result", "1c675dba"),
    ("workato_recipe_function", "return_result", "9b578a55"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_recipe_function.return_result",
]
STAGE_SQL = 'SELECT\nARRAY_SIZE(SPLIT(T.$1, \',\')) AS NUMBER_OF_COLUMNS\n\nFROM @#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"cabb207b","path":["parameters", "database"]}\')}.#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"cabb207b","path":["parameters", "schema"]}\')}.#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"cabb207b","path":["parameters", "stage"]}\')}/#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"cabb207b","path":["parameters", "date_path"]}\')} \n(FILE_FORMAT => \'#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"cabb207b","path":["parameters", "database"]}\')}.#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"cabb207b","path":["parameters", "schema"]}\')}.#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"cabb207b","path":["parameters", "file_format"]}\')}\') AS T\n\nLIMIT 1'
STAGE_SQL_OUTPUT_SCHEMA = '[{"control_type":"integer","label":"Number of columns","parse_output":"integer_conversion","name":"number_of_columns","type":"integer","optional":false}]'
PARAMETERS_SCHEMA_JSON = '[{"name":"database","type":"string","optional":false,"control_type":"text"},{"name":"schema","type":"string","optional":false,"control_type":"text"},{"name":"stage","type":"string","optional":false,"control_type":"text"},{"name":"date_path","type":"string","optional":false,"control_type":"text"},{"name":"file_format","type":"string","optional":false,"control_type":"text"}]'
RESULT_SCHEMA_JSON = '[{"control_type":"integer","label":"Number of columns","parse_output":"integer_conversion","name":"number_of_columns","type":"integer","optional":true},{"name":"success","type":"boolean","optional":false,"control_type":"checkbox","label":"Success","render_input":{},"parse_output":{},"toggle_hint":"Select from option list","toggle_field":{"label":"Success","control_type":"text","toggle_hint":"Use custom value","name":"success","type":"boolean","optional":false}},{"name":"error_message","type":"string","optional":true,"control_type":"text","label":"Error message"}]'
NUMBER_OF_COLUMNS_FORMULA = '=_dp(\'{"pill_type":"output","provider":"snowflake","line":"cdea878c","path":["rows",{"path_element_type":"current_item"},"number_of_columns_1d38290b"]}\').presence or 0'
CATCH_MESSAGE_TEMPLATE = '#{_dp(\'{"pill_type":"output","provider":"catch","line":"2918c48b","path":["message"]}\')}'
OK_RESULT_MAPPING = {
    "number_of_columns": NUMBER_OF_COLUMNS_FORMULA,
    "success": "true",
}
CATCH_RESULT_MAPPING = {
    "error_message": CATCH_MESSAGE_TEMPLATE,
    "number_of_columns": NUMBER_OF_COLUMNS_FORMULA,
    "success": "false",
}
TRIGGER_PARAMETER_NAMES = ("database", "schema", "stage", "date_path", "file_format")


def validate_82302802(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_input_obj = raw.get("input") or {}
    if trigger_input_obj.get("parameters_schema_json") != PARAMETERS_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter schema changed")
    if trigger_input_obj.get("result_schema_json") != RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger result schema changed")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = _input(actions[0])
    if search_input.get("sql") != STAGE_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} staged-file SQL changed: {search_input.get('sql')!r}")
    if str(search_input.get("limit") or "") != "50000" or str(search_input.get("offset") or "") != "0":
        raise RuntimeError(f"recipe {RECIPE_ID} staged-file query limit/offset changed")
    if search_input.get("output_schema") != STAGE_SQL_OUTPUT_SCHEMA:
        raise RuntimeError(f"recipe {RECIPE_ID} staged-file query output schema changed")
    ok_return_input = _input(actions[1])
    if ok_return_input.get("result") != OK_RESULT_MAPPING:
        raise RuntimeError(f"recipe {RECIPE_ID} success return_result mapping changed: {ok_return_input}")
    catch_return_input = _input(actions[2])
    if catch_return_input.get("result") != CATCH_RESULT_MAPPING:
        raise RuntimeError(f"recipe {RECIPE_ID} catch return_result mapping changed: {catch_return_input}")
    tries = _collect_keyword(raw, "try")
    if len(tries) != 1 or tries[0].get("number") != 2:
        raise RuntimeError(f"recipe {RECIPE_ID} try block changed")
    catches = _collect_keyword(raw, "catch")
    if (
        len(catches) != 1
        or catches[0].get("as") != "2918c48b"
        or str(_input(catches[0]).get("max_retry_count") or "") != "0"
        or str(_input(catches[0]).get("retry_interval") or "") != "2"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed")
    for keyword in ("if", "elsif", "else", "foreach", "stop", "repeat"):
        if _collect_keyword(raw, keyword):
            raise RuntimeError(f"recipe {RECIPE_ID} unexpectedly contains a {keyword} block")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def seed_82302802(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_82302802(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    for name in TRIGGER_PARAMETER_NAMES:
        value = parameters.get(name)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger input requires non-empty string parameters.{name}"
            )
    if sorted(parameters) != sorted(TRIGGER_PARAMETER_NAMES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must be exactly {sorted(TRIGGER_PARAMETER_NAMES)}: "
            f"{sorted(parameters)}"
        )
    date_path = parameters["date_path"]
    if date_path.startswith("/") or date_path.endswith("/"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.date_path must be a bare stage prefix "
            f"(no leading/trailing slash): {date_path!r}"
        )
    if not ctx.env.snowflake_database:
        raise RuntimeError(f"recipe {RECIPE_ID} requires SNOWFLAKE_DATABASE in the benchmark env")
    if parameters["database"].upper() != ctx.env.snowflake_database.upper():
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.database must name the live benchmark database "
            f"{ctx.env.snowflake_database!r}: {parameters['database']!r}"
        )
    bench_schema = (ctx.env.snowflake_schema or "BENCH").upper()
    if parameters["schema"].upper() != bench_schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.schema must name the benchmark schema "
            f"{bench_schema!r}: {parameters['schema']!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section: {sorted(seed_in)}"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not isinstance(expect.get("result"), dict) or not isinstance(
        expect.get("catch"), bool
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant must declare expect.result (object) and expect.catch (boolean)"
        )
    snowflake_seed = seed_in["snowflake_live"]
    _require_stage_seed(snowflake_seed, parameters, expect_catch=bool(expect["catch"]))
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake stage seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_82302802(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_82302802(raw)
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} run requires the seeded snowflake_live state")
    initial_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    finally:
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
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
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_82302802(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_stage_seed(snowflake_seed: Any, parameters: dict[str, Any], *, expect_catch: bool) -> None:
    if not isinstance(snowflake_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires a seed.snowflake_live object")
    if snowflake_seed.get("tables") != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} reads no Snowflake tables; seed.snowflake_live.tables must be "
            f"explicitly empty: {snowflake_seed.get('tables')!r}"
        )
    stages = snowflake_seed.get("stages")
    if not isinstance(stages, dict) or list(stages) != [parameters["stage"]]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must provision exactly the stage named by parameters.stage "
            f"{parameters['stage']!r}: {sorted(stages) if isinstance(stages, dict) else stages!r}"
        )
    spec = stages[parameters["stage"]]
    if not isinstance(spec, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} stage spec must be an object")
    if spec.get("cleanup") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} stage is benchmark-owned and must declare cleanup: true"
        )
    file_format = spec.get("file_format")
    if not isinstance(file_format, dict) or not str(file_format.get("name") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} stage seed requires file_format.name")
    if str(file_format.get("type") or "").upper() != "CSV":
        raise RuntimeError(f"recipe {RECIPE_ID} stage file format must be TYPE CSV")
    options = file_format.get("options")
    if not isinstance(options, dict) or options.get("FIELD_DELIMITER") != "NONE":
        raise RuntimeError(
            f"recipe {RECIPE_ID} stage file format must set FIELD_DELIMITER = NONE so T.$1 is "
            f"the whole line (ARRAY_SIZE(SPLIT(T.$1, ',')) counts every column): {options!r}"
        )
    format_matches_trigger = str(file_format["name"]).upper() == parameters["file_format"].upper()
    if expect_catch and format_matches_trigger:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variant must name a file format that is NOT provisioned "
            f"(trigger parameters.file_format {parameters['file_format']!r} matches the seeded format)"
        )
    if not expect_catch and not format_matches_trigger:
        raise RuntimeError(
            f"recipe {RECIPE_ID} non-catch variant must provision the file format named by "
            f"parameters.file_format {parameters['file_format']!r}: {file_format['name']!r}"
        )
    files = spec.get("files")
    if not isinstance(files, list):
        raise RuntimeError(f"recipe {RECIPE_ID} stage seed requires an explicit files list")
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} stage file entries must be objects")
        path = entry.get("path")
        if not isinstance(path, str) or not path.strip() or path.startswith("/"):
            raise RuntimeError(f"recipe {RECIPE_ID} stage file entry requires a relative path: {path!r}")
        if not isinstance(entry.get("content"), str):
            raise RuntimeError(f"recipe {RECIPE_ID} stage file {path!r} requires explicit string content")


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
    return found


def _input(node: dict[str, Any]) -> dict[str, Any]:
    value = node.get("input")
    return value if isinstance(value, dict) else {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

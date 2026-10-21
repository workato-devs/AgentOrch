from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_129217932


RECIPE_ID = "129217932"
SEED_TYPE = "snowflake_stage_copy_retention_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "a19e917d"
DECLARE_AS = "4e603d35"
COPY_AS = "ea11a3ca"
DELETE_AS = "2f2a548f"

# clock.scheduled_event (as a19e917d, daily 00:00 Etc/UTC) -- payload-less
# (trigger_input must be exactly {}); job_context.job_created_at is the only
# trigger-adjacent deref.
#   2  workato_variable.declare_variable 4e603d35: Schema='SALESFORCE',
#      Table='EVENT_LOGS', file_format='SALESFORCECSVFORMAT',
#      s_3_stage='ACTIVITY_EVENT_LOGS', retention_period_months='3',
#      year_month = =_dp(job_created_at).utc.strftime("%Y/%m") (the .utc chain
#      method is a batch-08 engine fix -- an offset instant converts to UTC
#      BEFORE the month renders, e.g. 2026-08-01T05:30+09:00 -> '2026/07').
#   3  snowflake.run_custom_sql ea11a3ca (LIVE, FORMULA-MODE sql '="..."'):
#      COPY INTO SALESFORCE.EVENT_LOGS FROM (SELECT METADATA$FILENAME,
#      T.$1..T.$5 FROM @SALESFORCE.ACTIVITY_EVENT_LOGS (FILE_FORMAT =>
#      'SALESFORCE.SALESFORCECSVFORMAT') AS T)
#      PATTERN = 'Daily/.*/<year_month>/.*/.*\.csv'
#      -- table ref rewrites to the seeded BENCH table; the STAGE and FILE
#      FORMAT refs stay verbatim 2-part names resolved via the session
#      database (seeded by _replace_stage under the same 2-part rule,
#      registered 82302802 precedent). COPY dedupe is a non-issue per run:
#      create-or-replace table resets Snowflake load history every seed.
#   4  snowflake.run_custom_sql 2f2a548f (LIVE): DELETE FROM
#      SALESFORCE.EVENT_LOGS WHERE TO_TIMESTAMP(timestamp,
#      'YYYYMMDDHH24MISS.FF3') < (convert_timezone('UTC',
#      current_timestamp()) - INTERVAL '3 MONTHS')::timestamp_ntz --
#      current_timestamp() pins to seed.snowflake_live.current_time
#      (_rewrite_time); DELETE runs AFTER COPY, so an old-timestamped row
#      inside a loaded file is deleted in the same job (variant 02 pins that).
#
# Linear recipe, no block-level branching. Observable dimensions covered by
# variants: PATTERN subset selection (month path arms + extension arm +
# multi-segment wildcards), COPY zero/N files, DELETE zero/N rows (preseeded
# AND just-loaded carriers), and the year_month UTC rollover.
#
# Backends: Snowflake LIVE only (backend policy). The stage, its named file
# format, the staged CSVs and the EVENT_LOGS table are benchmark-owned
# objects provisioned by seed.snowflake_live (harness.snowflake_live
# .seed_tables) and dropped by cleanup in the runner's finally.
#
# DETERMINISM GUARDS (enforced at seed time):
# - seed.snowflake_live.current_time must equal job_context.job_created_at
#   byte-for-byte (one pinned instant drives BOTH year_month and the DELETE
#   cutoff).
# - every timestamp value (preseeded rows and staged CSV rows) must sit more
#   than RETENTION_MARGIN (2 days) away from the derived 3-month cutoff:
#   convert_timezone('UTC', <ntz literal>) interprets its source in the LIVE
#   SESSION timezone, so the cutoff may drift by up to ~8h from the UTC
#   reading -- the margin makes every variant's delete set identical under
#   any session timezone.
# - event_id values are globally unique across preseeded rows and ALL staged
#   CSV rows (loaded or not): final-state row matching is keyed on event_id,
#   and METADATA$FILENAME's stage-prefix form is matched by SUFFIX (the
#   relative-path form is asserted by the live lane, same suffix convention
#   as registered 82302802's staged_file_suffixes).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "a19e917d", "skip": false, "input": {"time_unit": "days", "timezone": "Etc/UTC", "trigger_at": "00:00:00.000", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "4e603d35", "skip": false, "input": {"variables": {"data": {"Schema": "SALESFORCE", "Table": "EVENT_LOGS", "file_format": "SALESFORCECSVFORMAT", "retention_period_months": "3", "s_3_stage": "ACTIVITY_EVENT_LOGS", "year_month": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').utc.strftime(\"%Y/%m\")"}, "schema": "[{\"control_type\":\"text\",\"label\":\"Table\",\"name\":\"Table\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Table\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"S3 Stage\",\"name\":\"s_3_stage\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"S3 Stage\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"File Format\",\"name\":\"file_format\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"File Format\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"Year Month\",\"name\":\"year_month\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Year Month\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"Schema\",\"name\":\"Schema\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Schema\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"Retention Period (Months)\",\"name\":\"retention_period_months\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Retention Period (Months)\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "ea11a3ca", "skip": false, "input": {"output_schema": "[{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"},{\"name\":\"rows_loaded\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Rows loaded\"}]", "sql": "=\"\nCOPY INTO #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"Schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"Table\"]}')} FROM (\n  SELECT\n  METADATA$FILENAME,\n  T.$1,\n  T.$2,\n  T.$3,\n  T.$4,\n  T.$5\n  \n  FROM @#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"Schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"s_3_stage\"]}')}\n  (FILE_FORMAT => '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"Schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"file_format\"]}')}') AS T\n)\n-- Load all files for all dates for a given Year Month. If a file has already been loaded, Snowflake will know to skip it\nPATTERN = 'Daily/.*/#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"year_month\"]}')}/.*/.*\\.csv'\n\"", "update_only": "false"}, "block": []}, {"number": 4, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "2f2a548f", "skip": false, "input": {"sql": "DELETE FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"Schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"Table\"]}')}\nWHERE\nTO_TIMESTAMP(timestamp, 'YYYYMMDDHH24MISS.FF3') < (convert_timezone('UTC', current_timestamp()) - INTERVAL '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4e603d35\",\"path\":[\"retention_period_months\"]}')} MONTHS')::timestamp_ntz", "update_only": "false"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_AS, "workato_variable", "declare_variable"),
    (COPY_AS, "snowflake", "run_custom_sql"),
    (DELETE_AS, "snowflake", "run_custom_sql"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
]
# Semantic constants derived FROM the byte-pinned tree (no transcription
# drift): the five static declare values and the two SQL bodies.
_DECLARE_DATA = _EXPECTED_TREE["block"][0]["input"]["variables"]["data"]
STATIC_VARIABLES = {
    key: value for key, value in _DECLARE_DATA.items() if key != "year_month"
}
_COPY_SQL_FORMULA = _EXPECTED_TREE["block"][1]["input"]["sql"]
_DELETE_SQL_TEMPLATE = _EXPECTED_TREE["block"][2]["input"]["sql"]
EVENT_LOGS_TABLE = f"{STATIC_VARIABLES['Schema']}.{STATIC_VARIABLES['Table']}"
STAGE_NAME = f"{STATIC_VARIABLES['Schema']}.{STATIC_VARIABLES['s_3_stage']}"
FILE_FORMAT_NAME = f"{STATIC_VARIABLES['Schema']}.{STATIC_VARIABLES['file_format']}"
# Table shape: COPY INTO ... FROM (SELECT METADATA$FILENAME, T.$1..T.$5)
# inserts POSITIONALLY -- the seeded column ORDER is load-bearing and must be
# exactly this (filename first, then the five CSV columns; 'timestamp' is the
# retention column the DELETE parses with YYYYMMDDHH24MISS.FF3).
EVENT_LOGS_COLUMNS: dict[str, str] = {
    "filename": "string",
    "event_id": "string",
    "event_type": "string",
    "user_id": "string",
    "timestamp": "string",
    "detail": "string",
}
CSV_COLUMNS = ("event_id", "event_type", "user_id", "timestamp", "detail")
RETENTION_MONTHS = 3
RETENTION_MARGIN = datetime.timedelta(days=2)
REQUIRED_EXPECT_KEYS = (
    "case",
    "variables",
    "copy_sql",
    "delete_sql",
    "copy_files",
    "deleted_row_count",
    "initial_rows",
    "final_rows",
    "sql_execution_equivalence",
    "executed_action_count",
    "tools",
    "tool_expectations",
)
# Corpus lint: allowed tool_expectations keys.
_EXPECTATION_TARGET_KEYS = {"tool"}
_EXPECTATION_VALUE_KEYS = {
    "args_contains", "result_count", "argument_equivalence"
}
SQL_EXECUTION_EQUIVALENCE = {
    "table": EVENT_LOGS_TABLE,
    "row_key": "event_id",
    "suffix_expected_field": "filename_suffix",
    "suffix_actual_field": "filename",
}
SQL_ARGUMENT_EQUIVALENCE = {
    "sql": "execution_equivalence",
    "evidence_pointer": "expect.final_rows",
}
_PILL_RE = re.compile(r"#\{_dp\('([^']+)'\)\}")
_TS_RE = re.compile(r"^\d{14}\.\d{3}$")


def validate_129217932(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Named traps on top of the byte pin.
    if not (_COPY_SQL_FORMULA.startswith('="') and _COPY_SQL_FORMULA.endswith('"')):
        raise RuntimeError(
            f"recipe {RECIPE_ID} COPY sql is no longer a formula-mode string literal"
        )
    if "COPY INTO" not in _COPY_SQL_FORMULA or "PATTERN = '" not in _COPY_SQL_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} COPY INTO ... PATTERN shape changed")
    if not _DELETE_SQL_TEMPLATE.startswith("DELETE FROM ") or "INTERVAL '" not in _DELETE_SQL_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} DELETE retention shape changed")
    if sorted(_DECLARE_DATA) != sorted([*STATIC_VARIABLES, "year_month"]):
        raise RuntimeError(f"recipe {RECIPE_ID} declare variable set changed")
    if ".utc.strftime" not in str(_DECLARE_DATA.get("year_month") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} year_month .utc chain formula changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for keyword in ("if", "elsif", "else", "foreach", "stop", "repeat", "try", "catch"):
        if any(node.get("keyword") == keyword for node in _walk_nodes(raw)):
            raise RuntimeError(f"recipe {RECIPE_ID} unexpectedly contains a {keyword} block")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "event_logs_table": EVENT_LOGS_TABLE,
        "stage_name": STAGE_NAME,
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


def seed_129217932(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129217932(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler "
            f"tick; only job_context.job_created_at is dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the whole run"
        )
    job_context = data.get("job_context")
    if (
        not isinstance(job_context, dict)
        or sorted(job_context) != ["job_created_at"]
        or not isinstance(job_context.get("job_created_at"), str)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant must pin job_context exactly as "
            f"{{'job_created_at': <ISO instant>}}: {job_context!r}"
        )
    job_created_at = job_context["job_created_at"]
    job_utc = _parse_instant(job_created_at)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section: "
            f"{sorted(seed_in) if isinstance(seed_in, dict) else seed_in!r}"
        )
    section = seed_in["snowflake_live"]
    preseed_rows, stage_files = _require_snowflake_section(section, job_created_at)
    derived = _derive_ground_truth(job_utc, preseed_rows, stage_files)
    _require_expect_shape(data.get("expect"), derived)
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    snowflake_state = deepcopy(provision["state"])
    # JSON object member order is not an interface guarantee, while COPY INTO
    # without an explicit target-column list is positional.  Persist the
    # physical table order separately so canonical JSON serialization cannot
    # silently alphabetize the simulated schema between seed and run.
    snowflake_state["table_column_order"] = {
        EVENT_LOGS_TABLE: list(EVENT_LOGS_COLUMNS)
    }
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "job_context": deepcopy(job_context),
        "expect": deepcopy(data["expect"]),
        "snowflake_live": snowflake_state,
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_129217932(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129217932(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} run requires the seeded snowflake_live state")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} run requires the pinned job_context")
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be the explicit payload-less {{}}")
    if str((seed["snowflake_live"] or {}).get("current_time") or "") != str(
        seed["job_context"].get("job_created_at") or ""
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded current_time diverged from job_created_at"
        )
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
        details["initial_snapshot"] = ctx.tools.call("harness.snowflake.snapshot", {})
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = ctx.tools.call("harness.snowflake.snapshot", {})
    finally:
        # Stage + file format + table are benchmark-owned live objects: drop
        # them even when execution fails.
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
    result["verifier"] = verify_129217932(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _parse_instant(value: str) -> datetime.datetime:
    text = str(value).strip()
    try:
        parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must be an ISO-8601 instant: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must carry an explicit offset or Z: {value!r}"
        )
    return parsed.astimezone(datetime.timezone.utc)


def _require_snowflake_section(
    section: Any, job_created_at: str
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not isinstance(section, dict) or sorted(section) != ["current_time", "stages", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            f"{{'current_time', 'stages', 'tables'}}: "
            f"{sorted(section) if isinstance(section, dict) else section!r}"
        )
    if section["current_time"] != job_created_at:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.current_time must equal "
            f"job_context.job_created_at byte-for-byte (one pinned instant drives the "
            f"year_month AND the DELETE cutoff): {section['current_time']!r} vs "
            f"{job_created_at!r}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables) != [EVENT_LOGS_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{EVENT_LOGS_TABLE!r}"
        )
    spec = tables[EVENT_LOGS_TABLE]
    if not isinstance(spec, dict) or sorted(spec) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns', 'rows'}}"
        )
    if list(spec["columns"].items() if isinstance(spec["columns"], dict) else []) != list(
        EVENT_LOGS_COLUMNS.items()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} EVENT_LOGS columns must be exactly {EVENT_LOGS_COLUMNS} "
            "IN THAT ORDER (COPY INTO inserts positionally)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} EVENT_LOGS rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or list(row) != list(EVENT_LOGS_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} preseeded row {idx} must fill exactly the declared "
                f"columns in order: {row!r}"
            )
        for column, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} preseeded row {idx}.{column} must be a non-empty "
                    f"string: {value!r}"
                )
        if not _TS_RE.fullmatch(row["timestamp"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} preseeded row {idx}.timestamp must match "
                f"YYYYMMDDHH24MISS.FF3 ({_TS_RE.pattern}): {row['timestamp']!r}"
            )
    stages = section["stages"]
    if not isinstance(stages, dict) or sorted(stages) != [STAGE_NAME]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.stages must declare exactly "
            f"{STAGE_NAME!r}"
        )
    stage = stages[STAGE_NAME]
    if not isinstance(stage, dict) or sorted(stage) != ["cleanup", "file_format", "files"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} stage spec must be exactly {{'cleanup', 'file_format', 'files'}}"
        )
    if stage["cleanup"] is not True:
        raise RuntimeError(f"recipe {RECIPE_ID} stage is benchmark-owned: cleanup must be true")
    file_format = stage["file_format"]
    if file_format != {
        "name": FILE_FORMAT_NAME,
        "type": "CSV",
        "options": {"FIELD_DELIMITER": ","},
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} stage file format must be exactly the named "
            f"{FILE_FORMAT_NAME!r} comma CSV: {file_format!r}"
        )
    files = stage["files"]
    if not isinstance(files, list) or not files:
        raise RuntimeError(
            f"recipe {RECIPE_ID} stage requires an explicit non-empty files list "
            "(a variant without matching files still seeds non-matching decoys)"
        )
    seen_paths: set[str] = set()
    out_files: list[dict[str, str]] = []
    for idx, entry in enumerate(files):
        if not isinstance(entry, dict) or sorted(entry) != ["content", "path"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stage file {idx} must be exactly {{'content', 'path'}}"
            )
        path = entry["path"]
        if (
            not isinstance(path, str)
            or not path.strip()
            or path.startswith("/")
            or path.endswith("/")
            or path in seen_paths
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} stage file {idx} requires a unique relative path: {path!r}"
            )
        seen_paths.add(path)
        content = entry["content"]
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} stage file {path!r} requires non-empty string content"
            )
        _parse_csv(path, content)  # fail fast on malformed content
        out_files.append({"path": path, "content": content})
    return [dict(row) for row in rows], out_files


def _parse_csv(path: str, content: str) -> list[dict[str, str]]:
    """Strict 5-column CSV mirror of the seeded file format (comma delimiter,
    no quoting): every staged file must parse -- a live pattern surprise then
    loads DEFINED rows instead of failing mid-COPY."""
    if "\r" in content or '"' in content or "'" in content or "\\" in content:
        raise RuntimeError(
            f"recipe {RECIPE_ID} staged file {path!r} must not contain quotes, "
            "backslashes or CR characters (no CSV quoting in the mirror parser)"
        )
    rows: list[dict[str, str]] = []
    for line_no, line in enumerate(content.split("\n")):
        if line == "":
            continue
        fields = line.split(",")
        if len(fields) != len(CSV_COLUMNS) or any(not field.strip() for field in fields):
            raise RuntimeError(
                f"recipe {RECIPE_ID} staged file {path!r} line {line_no} must carry exactly "
                f"{len(CSV_COLUMNS)} non-empty comma-separated fields: {line!r}"
            )
        row = dict(zip(CSV_COLUMNS, fields))
        if not _TS_RE.fullmatch(row["timestamp"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} staged file {path!r} line {line_no} timestamp must "
                f"match YYYYMMDDHH24MISS.FF3: {row['timestamp']!r}"
            )
        rows.append(row)
    if not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} staged file {path!r} carries no data lines")
    return rows


def _derive_ground_truth(
    job_utc: datetime.datetime,
    preseed_rows: list[dict[str, Any]],
    stage_files: list[dict[str, str]],
) -> dict[str, Any]:
    year_month = job_utc.strftime("%Y/%m")
    variables = {**STATIC_VARIABLES, "year_month": year_month}
    copy_sql = _resolve_sql(_COPY_SQL_FORMULA[2:-1], variables)
    delete_sql = _resolve_sql(_DELETE_SQL_TEMPLATE, variables)
    pattern_match = re.search(r"PATTERN = '([^']+)'", copy_sql)
    if not pattern_match:
        raise RuntimeError(f"recipe {RECIPE_ID} resolved COPY sql lost its PATTERN literal")
    pattern = re.compile(pattern_match.group(1))
    cutoff = _shift_months(job_utc.replace(tzinfo=None), -RETENTION_MONTHS)
    loaded: list[dict[str, str]] = []
    copy_files: list[dict[str, Any]] = []
    for entry in stage_files:
        rows = _parse_csv(entry["path"], entry["content"])
        if not pattern.fullmatch(entry["path"]):
            continue
        copy_files.append({"file_suffix": entry["path"], "rows_loaded": len(rows)})
        for row in rows:
            loaded.append({"filename": entry["path"], **row})
    copy_files.sort(key=lambda item: item["file_suffix"])
    event_ids = [row["event_id"] for row in preseed_rows] + [
        row["event_id"]
        for entry in stage_files
        for row in _parse_csv(entry["path"], entry["content"])
    ]
    if len(set(event_ids)) != len(event_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} event_id values must be globally unique across preseeded "
            f"rows and ALL staged CSV rows (final-state matching is keyed on event_id): "
            f"{sorted(event_ids)}"
        )
    deleted = 0
    final_rows: list[dict[str, str]] = []
    for row in [*preseed_rows, *loaded]:
        ts = _parse_retention_ts(row["timestamp"])
        if abs(ts - cutoff) <= RETENTION_MARGIN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} timestamp {row['timestamp']!r} sits within "
                f"{RETENTION_MARGIN} of the retention cutoff {cutoff.isoformat()!r}; the "
                "live session timezone may flip its delete outcome -- move it outside the "
                "margin"
            )
        if ts < cutoff:
            deleted += 1
        else:
            final_rows.append(
                {"filename_suffix": row["filename"], **{c: row[c] for c in CSV_COLUMNS}}
            )
    return {
        "variables": variables,
        "copy_sql": copy_sql,
        "delete_sql": delete_sql,
        "copy_files": copy_files,
        "deleted_row_count": deleted,
        "initial_rows": [dict(row) for row in preseed_rows],
        "final_rows": final_rows,
    }


def _resolve_sql(template: str, variables: dict[str, str]) -> str:
    def _sub(match: "re.Match[str]") -> str:
        pill = json.loads(match.group(1))
        path = pill.get("path") or []
        if (
            pill.get("pill_type") != "output"
            or pill.get("line") != DECLARE_AS
            or len(path) != 1
            or path[0] not in variables
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} unexpected SQL pill: {match.group(1)!r}")
        return str(variables[path[0]])

    return _PILL_RE.sub(_sub, template)


def _parse_retention_ts(value: str) -> datetime.datetime:
    return datetime.datetime.strptime(value[:14], "%Y%m%d%H%M%S")


def _shift_months(dt: datetime.datetime, months: int) -> datetime.datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    last_day = (next_month - datetime.timedelta(days=1)).day
    return dt.replace(year=year, month=month, day=min(dt.day, last_day))


def _require_expect_shape(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if not isinstance(expect.get("case"), str) or not expect["case"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must describe the variant branch")
    checks = (
        expect.get("variables") == derived["variables"],
        expect.get("copy_sql") == derived["copy_sql"],
        expect.get("delete_sql") == derived["delete_sql"],
        expect.get("copy_files") == derived["copy_files"],
        expect.get("deleted_row_count") == derived["deleted_row_count"],
        _same_multiset(expect.get("initial_rows"), derived["initial_rows"]),
        _same_multiset(expect.get("final_rows"), derived["final_rows"]),
        expect.get("sql_execution_equivalence") == SQL_EXECUTION_EQUIVALENCE,
        expect.get("executed_action_count") == 3,
        expect.get("tools") == ["snowflake.run_custom_sql", "snowflake.run_custom_sql"],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground truth "
            f"{derived!r}: {expect!r}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 2 or not all(
        isinstance(item, dict) for item in items
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin both snowflake calls"
        )
    for idx, item in enumerate(items):
        unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has non-corpus keys: {unknown}"
            )
        if item.get("tool") != "snowflake.run_custom_sql":
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be "
                f"'snowflake.run_custom_sql': {item.get('tool')!r}"
            )
        if item.get("argument_equivalence") != SQL_ARGUMENT_EQUIVALENCE:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must declare the "
                "hidden final-state SQL equivalence witness"
            )
    copy_item, delete_item = items
    if copy_item.get("args_contains") != {"sql": derived["copy_sql"], "parameters": {}}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the resolved COPY sql verbatim"
        )
    if derived["copy_files"]:
        if copy_item.get("result_count") != len(derived["copy_files"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[0].result_count must equal the "
                f"loaded-file count {len(derived['copy_files'])}"
            )
    elif copy_item.get("result_count") != 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].result_count must be 0 on a "
            "zero-file COPY"
        )
    if delete_item.get("args_contains") != {"sql": derived["delete_sql"], "parameters": {}}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1] must pin the resolved DELETE sql verbatim"
        )
    if delete_item.get("result_count") != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1].result_count must be 1 (a DELETE "
            "returns exactly one 'number of rows deleted' summary row)"
        )


def _same_multiset(actual: Any, expected: list[dict[str, Any]]) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    key = lambda row: json.dumps(row, sort_keys=True, default=str)
    actual_sorted = sorted((row for row in actual if isinstance(row, dict)), key=key)
    expected_sorted = sorted(expected, key=key)
    return actual_sorted == expected_sorted


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


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}

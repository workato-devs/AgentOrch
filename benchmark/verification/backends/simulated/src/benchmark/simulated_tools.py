from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import re
from typing import Any

from .capabilities import validate_tool_registry
from .config import Env, lookup_table_file, workato_db_table_file
from .lookup_table import LookupTableMock
from .simulated_connectors import (
    GoogleDriveSimulatedClient as GoogleDriveLiveClient,
    GoogleSheetsSimulatedClient as GoogleSheetsLiveClient,
    JiraSimulatedClient as JiraLiveClient,
    SalesforceSimulatedRun as SalesforceRun,
    SlackSimulatedClient as SlackLiveClient,
    SnowflakeSimulatedClient as SnowflakeLiveClient,
    provision_salesforce_records as provision_records,
)
from .tools import ToolRegistry
from .workato_db_table import (
    WORKATO_RECORD_ID_FIELD,
    WorkatoDbTableMock,
    public_record_id,
)


def simulated_env(env: Env) -> Env:
    """Fill connector routing fields without requiring real credentials."""

    return replace(
        env,
        slack_bot_token=env.slack_bot_token or "simulated",
        slack_channel_override=env.slack_channel_override or "C_SIMULATED",
        sheets_spreadsheet_id=env.sheets_spreadsheet_id or "simulated-spreadsheet",
        sheets_tab=env.sheets_tab or "Sheet1",
        snowflake_account=env.snowflake_account or "simulated",
        snowflake_user=env.snowflake_user or "simulated",
        snowflake_role=env.snowflake_role or "SIMULATED",
        snowflake_pat=env.snowflake_pat or "simulated",
        snowflake_warehouse=env.snowflake_warehouse or "SIMULATED",
        snowflake_database=env.snowflake_database or "BENCH",
        snowflake_schema=env.snowflake_schema or "PUBLIC",
    )


def _workato_db_row_matches(row: Any, filters: list[Any]) -> bool:
    if not isinstance(row, dict):
        return False
    for raw_filter in filters:
        if not isinstance(raw_filter, dict):
            raise RuntimeError("workato_db_table filter must be an object")
        field_id = str(raw_filter.get("field_id") or "")
        if not field_id:
            raise RuntimeError("workato_db_table filter missing field_id")
        op = str(raw_filter.get("op") or "eq")
        if op not in {"eq", "equals", "ne", "gte", "gt", "lte", "lt", "starts_with", "isnull", "isnotnull"}:
            raise RuntimeError(f"unsupported workato_db_table filter op: {op}")
        actual = (
            public_record_id(row)
            if field_id in {"record_id", WORKATO_RECORD_ID_FIELD}
            else row.get(field_id)
        )
        expected = raw_filter.get("value")
        if op in {"isnull", "isnotnull"}:
            # Presence checks; any accompanying value is ignored (Workato keeps
            # a stale value_default alongside isnull/isnotnull ops).
            is_null = actual is None or actual == ""
            if (op == "isnull") != is_null:
                return False
            continue
        if op == "starts_with":
            if not str(actual if actual is not None else "").startswith(str(expected if expected is not None else "")):
                return False
            continue
        if op in {"eq", "equals", "ne"} and isinstance(actual, dict):
            values = {str(actual.get("record_id") or ""), str(actual.get("display_name") or "")}
            matched = str(expected) in values
            if (op == "ne") == matched:
                return False
            continue
        comparison = _compare_workato_values(actual, expected)
        if op in {"eq", "equals"} and comparison != 0:
            return False
        if op == "ne" and comparison == 0:
            return False
        if op == "gte" and comparison < 0:
            return False
        if op == "gt" and comparison <= 0:
            return False
        if op == "lte" and comparison > 0:
            return False
        if op == "lt" and comparison >= 0:
            return False
    return True


def _compare_workato_values(actual: Any, expected: Any) -> int:
    left = _comparable_workato_value(actual)
    right = _comparable_workato_value(expected)
    if type(left) is not type(right):
        left = str(left)
        right = str(right)
    if left == right:
        return 0
    return 1 if left > right else -1


def _comparable_workato_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str) and value.startswith("<anon>") and value.endswith("</anon>"):
        value = value[len("<anon>"):-len("</anon>")]
    text = str(value)
    parsed = _parse_datetime(text)
    if parsed is not None:
        return parsed
    return text


def _parse_datetime(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        if len(text) == 10:
            try:
                return datetime.fromisoformat(text + "T00:00:00+00:00")
            except ValueError:
                return None
    return None


def _integer_arg(value: Any, field: str, *, default: int | None = None) -> int:
    """Parse a model-supplied integer as a recoverable connector error."""

    if value in (None, "") and default is not None:
        return default
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{field} must be an integer; got {value!r}") from exc


def _legacy_sheet_rows(section: dict[str, Any], preferred_tab: str) -> list[dict[str, Any]]:
    spreadsheets = section.get("spreadsheets")
    if not isinstance(spreadsheets, list) or not spreadsheets:
        return []
    first = spreadsheets[0]
    if not isinstance(first, dict):
        return []
    tabs = first.get("tabs")
    if not isinstance(tabs, dict):
        return []
    rows = tabs.get(preferred_tab)
    if not isinstance(rows, list):
        rows = next((value for value in tabs.values() if isinstance(value, list)), [])
    return [dict(row) for row in rows if isinstance(row, dict)]


def _fixture_arguments_match(expected: Any, actual: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(expected) == set(actual) and all(
            _fixture_arguments_match(value, actual[key])
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(expected) == len(actual)
            and all(
                _fixture_arguments_match(left, right)
                for left, right in zip(expected, actual)
            )
        )
    if isinstance(expected, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", expected.strip()):
        return str(actual).strip() == expected.strip()
    if isinstance(actual, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", actual.strip()):
        return str(expected).strip() == actual.strip()
    return expected == actual


def _fault_arguments_match(expected: Any, actual: Any) -> bool:
    """Recursive subset match for explicit action-fault selectors."""

    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _fault_arguments_match(value, actual[key])
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(
            _fault_arguments_match(left, right)
            for left, right in zip(expected, actual)
        )
    return expected == actual


def _strict_fixture_arguments_match(expected: Any, actual: Any) -> bool:
    """Type-strict recursive equality for answer-bearing fixtures."""

    if type(expected) is not type(actual):
        return False
    if isinstance(expected, dict):
        return set(expected) == set(actual) and all(
            _strict_fixture_arguments_match(value, actual[key])
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(expected) == len(actual) and all(
            _strict_fixture_arguments_match(left, right)
            for left, right in zip(expected, actual)
        )
    return expected == actual


def build_simulated_tools(env: Env, seed: dict[str, Any] | None = None) -> ToolRegistry:
    tools = ToolRegistry()
    seed_full = seed or {}
    variant_seed = (
        (seed_full.get("variant_input") or {}).get("seed")
        if isinstance(seed_full.get("variant_input"), dict)
        else {}
    )
    slack_seed = seed_full.get("slack")
    if not isinstance(slack_seed, dict) and isinstance(variant_seed, dict):
        slack_seed = variant_seed.get("slack")
    slack = SlackLiveClient(
        env.slack_bot_token,
        slack_seed if isinstance(slack_seed, dict) else None,
    )
    jira_client: JiraLiveClient | None = None
    snowflake_live_client: SnowflakeLiveClient | None = None
    seed_section = (seed or {}).get("workato_db_table")
    lookup_seed_section = (seed or {}).get("lookup_table")
    snowflake_seed_section = (seed or {}).get("snowflake")
    recipe_id = str((seed or {}).get("recipe_id") or "")
    variant = (seed or {}).get("variant_label")
    state_file = workato_db_table_file(recipe_id, variant) if recipe_id and seed_section is not None else None
    lookup_state_file = lookup_table_file(recipe_id, variant) if recipe_id and lookup_seed_section is not None else None
    datatable = WorkatoDbTableMock(seed_section, state_file)
    lookup = LookupTableMock(lookup_seed_section, lookup_state_file)
    salesforce_run: SalesforceRun | None = None
    salesforce_seed_invocations = 0
    sheets_client: GoogleSheetsLiveClient | None = None
    drive_client: GoogleDriveLiveClient | None = None
    runtime_lists: dict[str, list[Any]] = {}
    accumulated_list_items: list[Any] = []
    fixture_rows = [
        deepcopy(item)
        for item in seed_full.get("_simulated_read_fixtures") or []
        if isinstance(item, dict)
    ]
    consumed_fixture_indexes: set[int] = set()
    action_fault_rows = [
        deepcopy(item)
        for item in (
            seed_full.get("_simulated_action_faults")
            or seed_full.get("simulated_action_faults")
            or []
        )
        if isinstance(item, dict)
    ]
    consumed_action_fault_indexes: set[int] = set()
    action_fault_match_counts: dict[int, int] = {}
    no_fixture = object()

    def simulated_fixture_result(
        tool: str,
        args: dict[str, Any],
        *,
        strict: bool = False,
    ) -> Any:
        for index, item in enumerate(fixture_rows):
            if index in consumed_fixture_indexes:
                continue
            if (
                str(item.get("tool") or "") == tool
                and (
                    _strict_fixture_arguments_match(
                        item.get("args") or {},
                        args,
                    )
                    if strict
                    else _fixture_arguments_match(
                        item.get("args") or {},
                        args,
                    )
                )
            ):
                consumed_fixture_indexes.add(index)
                replacement = item.get("replace_snowflake_state")
                if isinstance(replacement, dict):
                    snowflake_live().seed_tables(replacement)
                table_replacements = item.get("replace_snowflake_tables")
                if isinstance(table_replacements, dict):
                    snowflake_live().replace_table_rows(table_replacements)
                return deepcopy(item.get("result") or {})
        return no_fixture

    def raise_simulated_action_fault(tool: str, args: dict[str, Any]) -> None:
        """Raise one explicitly seeded connector fault after argument resolution."""

        for index, item in enumerate(action_fault_rows):
            if index in consumed_action_fault_indexes:
                continue
            if (
                str(item.get("tool") or "") == tool
                and _fault_arguments_match(item.get("args") or {}, args)
            ):
                match_count = action_fault_match_counts.get(index, 0) + 1
                action_fault_match_counts[index] = match_count
                skip_matches = int(item.get("skip_matches") or 0)
                if match_count <= skip_matches:
                    continue
                consumed_action_fault_indexes.add(index)
                raise RuntimeError(
                    str(item.get("error") or "benchmark simulated action failure")
                )

    def salesforce() -> SalesforceRun:
        nonlocal salesforce_run
        if salesforce_run is None:
            state = (seed or {}).get("salesforce_live")
            if not isinstance(state, dict) or not state.get("run_id"):
                state = provision_records({})["state"]
            salesforce_run = SalesforceRun(state)
        return salesforce_run

    def google_sheets() -> GoogleSheetsLiveClient:
        nonlocal sheets_client
        if sheets_client is None:
            sheets_client = GoogleSheetsLiveClient(env.sheets_spreadsheet_id, env.sheets_tab)
            sheet_seed = (
                (seed or {}).get("google_sheets")
                or (seed or {}).get("sheets")
            )
            if isinstance(sheet_seed, dict):
                rows = sheet_seed.get("rows") or []
                headers = sheet_seed.get("headers")
                if isinstance(rows, list):
                    sheets_client.replace_rows(
                        rows,
                        [str(header) for header in headers]
                        if isinstance(headers, list)
                        else None,
                    )
        return sheets_client

    def google_drive() -> GoogleDriveLiveClient:
        nonlocal drive_client
        if drive_client is None:
            drive_client = GoogleDriveLiveClient()
        return drive_client

    def jira() -> JiraLiveClient:
        nonlocal jira_client
        if jira_client is None:
            jira_client = JiraLiveClient()
        return jira_client

    def snowflake_live() -> SnowflakeLiveClient:
        # Keep the live connector's seed shapes and action semantics, but hold
        # all Snowflake tables in this process.
        nonlocal snowflake_live_client
        if snowflake_live_client is None:
            live_section = (seed or {}).get("snowflake_live")
            if isinstance(live_section, dict):
                snowflake_live_client = SnowflakeLiveClient(env, live_section)
            elif isinstance(snowflake_seed_section, dict):
                client = SnowflakeLiveClient(env, {})
                client.seed_tables(snowflake_seed_section)
                snowflake_live_client = client
            else:
                snowflake_live_client = SnowflakeLiveClient(env, {})
        return snowflake_live_client

    def slack_post_message(args: dict[str, Any]) -> dict[str, Any]:
        blocks = args.get("blocks")
        if blocks is not None and not isinstance(blocks, list):
            raise RuntimeError("slack.post_message blocks must be a list")
        attachments = args.get("attachments")
        if attachments is not None and (
            not isinstance(attachments, list)
            or not all(isinstance(item, dict) for item in attachments)
        ):
            raise RuntimeError(
                "slack.post_message attachments must be an array of objects"
            )
        raw_channel = str(args.get("channel") or "")
        channel = (
            raw_channel
            if raw_channel.startswith("U")
            else str(env.slack_channel_override or raw_channel)
        )
        # Match RawRecipeExecutor.slack_post_message: public plans name the
        # logical configured destination, while the benchmark connector
        # records the isolated physical destination used for the run.
        args["channel"] = channel
        if args.get("ts") not in (None, ""):
            return slack.update_message(
                channel,
                str(args.get("ts") or ""),
                str(args.get("text") or ""),
                blocks,
                attachments=attachments,
            )
        return slack.post_message(
            channel,
            str(args.get("text") or ""),
            blocks,
            str(args.get("thread_ts") or ""),
            attachments,
        )

    def slack_post_reply(args: dict[str, Any]) -> dict[str, Any]:
        blocks = args.get("blocks")
        if blocks is not None and (
            not isinstance(blocks, list)
            or not all(isinstance(item, dict) for item in blocks)
        ):
            raise RuntimeError("slack.post_reply blocks must be an array of objects")
        if (
            not str(args.get("text") or "")
            and not blocks
            and not bool(args.get("delete_original"))
        ):
            raise RuntimeError("slack.post_reply requires text or blocks")
        return slack.post_reply(
            str(args.get("channel") or env.slack_channel_override or ""),
            str(args.get("text") or ""),
            str(args.get("thread_ts") or ""),
            blocks,
            user=str(args.get("user") or ""),
            ephemeral=bool(args.get("ephemeral")),
            replace_original=bool(args.get("replace_original")),
            delete_original=bool(args.get("delete_original")),
            original_ts=str(args.get("original_ts") or ""),
        )

    def slack_delete_message(args: dict[str, Any]) -> dict[str, Any]:
        return slack.delete_message(str(args.get("channel") or ""), str(args.get("ts") or ""))

    def slack_update_blocks_by_block_id(args: dict[str, Any]) -> dict[str, Any]:
        updates = args.get("blocks_to_update") or []
        if not isinstance(updates, list):
            raise RuntimeError("slack.update_blocks_by_block_id blocks_to_update must be a list")
        return slack.update_blocks_by_block_id(args.get("message_json"), updates)

    def slack_lookup_user_by_email(args: dict[str, Any]) -> dict[str, Any]:
        if args.get("email") not in (None, ""):
            return slack.lookup_user_by_email(str(args.get("email") or ""))
        return slack.lookup_user_by_id(str(args.get("id") or ""))

    def slack_open_modal(args: dict[str, Any]) -> dict[str, Any]:
        view = args.get("view") or {}
        if not isinstance(view, dict):
            raise RuntimeError("slack_bot.block_kit_modals view must be an object")
        return slack.open_modal(str(args.get("trigger_id") or ""), view)

    def slack_open_bot_app_home(args: dict[str, Any]) -> dict[str, Any]:
        view = args.get("view") or {}
        if not isinstance(view, dict):
            raise RuntimeError("slack_bot.open_bot_app_home view must be an object")
        return slack.publish_home(str(args.get("user_id") or ""), view)

    def slack_generate_menu_options(args: dict[str, Any]) -> dict[str, Any]:
        options = args.get("options") or []
        if not isinstance(options, list):
            raise RuntimeError("slack_bot.generate_menu_options options must be a list")
        if any(not isinstance(option, dict) for option in options):
            raise RuntimeError(
                "slack_bot.generate_menu_options options must contain objects"
            )
        normalized_options: list[dict[str, Any]] = []
        for option in options:
            label = option.get("label")
            value = option.get("value")
            if label is None or value is None or isinstance(label, (dict, list)) or isinstance(value, (dict, list)):
                raise RuntimeError(
                    "slack_bot.generate_menu_options label and value must be scalar"
                )
            # A pure output datapill preserves its scalar type. Text formulas
            # render labels as strings, while numeric menu values can remain
            # numeric (the imported recipes and Workato verifier rely on it).
            normalized_options.append({"label": str(label), "value": value})
        out: dict[str, Any] = {"ok": True, "options": normalized_options}
        option_groups = args.get("option_groups")
        if option_groups is not None:
            if not isinstance(option_groups, list):
                raise RuntimeError("slack_bot.generate_menu_options option_groups must be a list")
            out["option_groups"] = option_groups
        return out

    def jira_create_issue(args: dict[str, Any]) -> dict[str, Any]:
        return jira().create_issue(args)

    def jira_delete_issue(args: dict[str, Any]) -> dict[str, Any]:
        return jira().delete_issue(str(args.get("key") or args.get("id") or ""))

    def sheets_update_row(args: dict[str, Any]) -> dict[str, Any]:
        data = args.get("data") or {}
        if not isinstance(data, dict):
            raise RuntimeError("google_sheets.update_row_v4_new data must be an object")
        row_number = args.get("row_number")
        if row_number in (None, ""):
            raise RuntimeError("google_sheets.update_row_v4_new missing row_number")
        return google_sheets().update_row(
            _integer_arg(row_number, "google_sheets.update_row_v4_new row_number"),
            data,
        )

    def sheets_add_row(args: dict[str, Any]) -> dict[str, Any]:
        data = args.get("data") or {}
        if not isinstance(data, dict):
            raise RuntimeError("google_sheets.add_spreadsheet_row_v4 data must be an object")
        headers = args.get("headers")
        if headers is not None and not isinstance(headers, list):
            raise RuntimeError("google_sheets.add_spreadsheet_row_v4 headers must be a list")
        return google_sheets().append_row(data, [str(header) for header in headers] if headers else None)

    def sheets_seed_rows(args: dict[str, Any]) -> dict[str, Any]:
        section = args.get("sheets") or args.get("section") or {}
        if not isinstance(section, dict):
            raise RuntimeError("harness.google_sheets.seed_rows section must be an object")
        rows = section.get("rows")
        headers = section.get("headers")
        if rows is None:
            rows = _legacy_sheet_rows(section, env.sheets_tab)
        if not isinstance(rows, list):
            raise RuntimeError("harness.google_sheets.seed_rows rows must be a list")
        if headers is not None and not isinstance(headers, list):
            raise RuntimeError("harness.google_sheets.seed_rows headers must be a list")
        return google_sheets().replace_rows(rows, [str(header) for header in headers] if headers else None)

    def sheets_snapshot(_args: dict[str, Any]) -> dict[str, Any]:
        return google_sheets().snapshot()

    def sheets_get_rows(args: dict[str, Any]) -> dict[str, Any]:
        snapshot = google_sheets().snapshot()
        rows = snapshot.get("rows") if isinstance(snapshot.get("rows"), list) else []
        return {
            "ok": True,
            "spreadsheet": args.get("spreadsheet"),
            "sheet": args.get("sheet"),
            "range": args.get("range"),
            "rows": rows,
            "records": rows,
            "count": len(rows),
            "list_size": len(rows),
            "headers": snapshot.get("headers") if isinstance(snapshot.get("headers"), list) else [],
        }

    def sheets_search_rows(args: dict[str, Any]) -> dict[str, Any]:
        filters = args.get("data") or {}
        if not isinstance(filters, dict):
            raise RuntimeError("google_sheets.search_spreadsheet_rows_v4_new data must be an object")
        return google_sheets().search_rows(filters, args.get("count"))

    def drive_create_folder(args: dict[str, Any]) -> dict[str, Any]:
        drive_seed = (seed or {}).get("google_drive")
        parent_override = ""
        if isinstance(drive_seed, dict):
            parent_override = str(drive_seed.get("parent_folder_id") or "")
        return google_drive().create_folder(
            parent_override or str(args.get("parent_id") or args.get("folderId") or args.get("folder_id") or ""),
            str(args.get("name") or ""),
        )

    def drive_delete_file(args: dict[str, Any]) -> dict[str, Any]:
        return google_drive().delete_file(str(args.get("id") or args.get("file_id") or ""))

    def snowflake_upsert_rows_batch(args: dict[str, Any]) -> dict[str, Any]:
        rows = args.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("snowflake.upsert_rows_batch rows must be a list")
        return snowflake_live().upsert_rows_batch(
            str(args.get("table") or ""),
            args.get("key_columns"),
            rows,
        )

    def snowflake_update_rows(args: dict[str, Any]) -> dict[str, Any]:
        columns = args.get("columns") or {}
        if not isinstance(columns, dict):
            raise RuntimeError("snowflake.update_rows columns must be an object")
        return snowflake_live().update_rows(
            str(args.get("table") or ""),
            str(args.get("where") or ""),
            columns,
        )

    def snowflake_search_rows(args: dict[str, Any]) -> dict[str, Any]:
        fixture = simulated_fixture_result(
            "snowflake.search_rows",
            args,
        )
        if fixture is not no_fixture:
            return fixture
        parameters = args.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise RuntimeError("snowflake.search_rows parameters must be an object")
        return snowflake_live().search_rows(
            str(args.get("table") or ""),
            str(args.get("where") or ""),
            parameters,
            args.get("limit"),
            args.get("offset"),
            args.get("orderby"),
            args.get("output_columns"),
        )

    def snowflake_search_rows_sql(args: dict[str, Any]) -> dict[str, Any]:
        fixture = simulated_fixture_result(
            "snowflake.search_rows_sql",
            args,
        )
        if fixture is not no_fixture:
            return fixture
        parameters = args.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise RuntimeError("snowflake.search_rows_sql parameters must be an object")
        return snowflake_live().search_rows_sql(
            str(args.get("sql") or ""),
            parameters,
            args.get("limit"),
            args.get("offset"),
        )

    def snowflake_run_custom_sql(args: dict[str, Any]) -> dict[str, Any]:
        fixture = simulated_fixture_result(
            "snowflake.run_custom_sql",
            args,
        )
        if fixture is not no_fixture:
            return fixture
        parameters = args.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise RuntimeError("snowflake.run_custom_sql parameters must be an object")
        result = snowflake_live().run_custom_sql(
            str(args.get("sql") or ""),
            parameters,
            args.get("limit"),
            args.get("offset"),
        )
        result.setdefault("rows_affected", len(result.get("rows") or []))
        return result

    def snowflake_snapshot(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, **snowflake_live().snapshot()}

    def snowflake_live_seed_tables(args: dict[str, Any]) -> dict[str, Any]:
        section = args.get("snowflake") or args.get("section") or {}
        if not isinstance(section, dict):
            raise RuntimeError("harness.snowflake_live.seed_tables snowflake must be an object")
        return SnowflakeLiveClient(env, section).seed_tables(section)

    def snowflake_live_cleanup(args: dict[str, Any]) -> dict[str, Any]:
        return snowflake_live().cleanup()

    def dt_get_records(args: dict[str, Any]) -> dict[str, Any]:
        result = datatable.get_records(
            str(args.get("table_id") or ""),
            args.get("continuation_token"),
        )
        if not result.get("ok"):
            return result
        filters = args.get("filters") or []
        if filters and not isinstance(filters, list):
            raise RuntimeError("workato_db_table.get_records filters must be a list")
        rows = result.get("records")
        if not isinstance(rows, list):
            raise RuntimeError("workato_db_table.get_records returned non-list records")
        if filters:
            rows = [row for row in rows if _workato_db_row_matches(row, filters)]
        # The public tool contract is authoritative: explicitly supplied
        # ordering and limits are always honored. Hidden fixture state cannot
        # alter connector semantics.
        if args.get("order_by_field_id") not in (None, "") or args.get(
            "limit"
        ) not in (None, ""):
            from decimal import Decimal, InvalidOperation
            order_field = str(args.get("order_by_field_id") or "")
            if order_field:
                reverse = str(args.get("order_direction") or "asc").lower() == "desc"

                def _order_key(row: Any) -> tuple[int, Decimal, str]:
                    value = row.get(order_field) if isinstance(row, dict) else None
                    text = "" if value is None else str(value)
                    try:
                        return (0, Decimal(text), "")
                    except InvalidOperation:
                        return (1, Decimal(0), text)

                rows = sorted(rows, key=_order_key, reverse=reverse)
            if args.get("limit") not in (None, ""):
                rows = rows[: _integer_arg(
                    args.get("limit"), "workato_db_table.get_records limit"
                )]
        result = dict(result)
        result["records"] = rows
        return result

    def dt_search_records(args: dict[str, Any]) -> dict[str, Any]:
        return datatable.search_records(str(args.get("table_id") or ""), str(args.get("query") or ""))

    def dt_add_record(args: dict[str, Any]) -> dict[str, Any]:
        record = args.get("record") or {}
        if not isinstance(record, dict):
            raise RuntimeError("workato_db_table.add_record record must be an object")
        return datatable.add_record(str(args.get("table_id") or ""), record, args.get("record_id_field"))

    def dt_update_record(args: dict[str, Any]) -> dict[str, Any]:
        record = args.get("record") or {}
        if not isinstance(record, dict):
            raise RuntimeError("workato_db_table.update_record record must be an object")
        return datatable.update_record(
            str(args.get("table_id") or ""),
            args.get("record_id"),
            record,
            args.get("record_id_field"),
        )

    def dt_upsert_record(args: dict[str, Any]) -> dict[str, Any]:
        record = args.get("record") or {}
        if not isinstance(record, dict):
            raise RuntimeError("workato_db_table.upsert_record record must be an object")
        return datatable.upsert_record(
            str(args.get("table_id") or ""),
            record,
            args.get("record_id"),
            args.get("primary_field_id"),
            args.get("record_id_field"),
        )

    def dt_delete_record(args: dict[str, Any]) -> dict[str, Any]:
        return datatable.delete_record(str(args.get("table_id") or ""), args.get("record_id"))

    def dt_snapshot(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, **datatable.snapshot()}

    def lookup_id(args: dict[str, Any]) -> str:
        return str(args.get("lookup_table_id") or args.get("table_id") or "")

    def lt_get_entries(args: dict[str, Any]) -> dict[str, Any]:
        return lookup.get_entries(lookup_id(args))

    def lt_get_entry(args: dict[str, Any]) -> dict[str, Any]:
        params = args.get("parameters") or {}
        if not isinstance(params, dict):
            raise RuntimeError("lookup_table.get_entry parameters must be an object")
        return lookup.get_entry(lookup_id(args), params, args.get("id"))

    def lt_search_entries(args: dict[str, Any]) -> dict[str, Any]:
        params = args.get("parameters") or {}
        if not isinstance(params, dict):
            raise RuntimeError("lookup_table.search_entries parameters must be an object")
        return lookup.search_entries(lookup_id(args), params)

    def lt_add_entry(args: dict[str, Any]) -> dict[str, Any]:
        params = args.get("parameters") or {}
        if not isinstance(params, dict):
            raise RuntimeError("lookup_table.add_entry parameters must be an object")
        return lookup.add_entry(lookup_id(args), params)

    def lt_update_entry(args: dict[str, Any]) -> dict[str, Any]:
        params = args.get("parameters") or {}
        if not isinstance(params, dict):
            raise RuntimeError("lookup_table.update_entry parameters must be an object")
        return lookup.update_entry(lookup_id(args), args.get("id"), params)

    def lt_delete_entry(args: dict[str, Any]) -> dict[str, Any]:
        return lookup.delete_entry(lookup_id(args), args.get("id"), args.get("ignore_not_found"))

    def lt_truncate(args: dict[str, Any]) -> dict[str, Any]:
        return lookup.truncate(lookup_id(args))

    def lt_add_batch_of_entries(args: dict[str, Any]) -> dict[str, Any]:
        entries = args.get("entries") or []
        if not isinstance(entries, list):
            raise RuntimeError("lookup_table.add_batch_of_entries entries must be a list")
        return lookup.add_batch_of_entries(lookup_id(args), entries)

    def lt_snapshot(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, **lookup.snapshot()}

    def sf_seed_records(args: dict[str, Any]) -> dict[str, Any]:
        nonlocal salesforce_seed_invocations
        section = args.get("salesforce") or args.get("section") or {}
        if not isinstance(section, dict):
            raise RuntimeError("harness.salesforce.seed_records section must be an object")
        simulated_section = {
            **section,
            "_simulated_created_date_offset": salesforce_seed_invocations * 100,
        }
        salesforce_seed_invocations += 1
        return provision_records(simulated_section)

    def sf_search_records(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query") or "").strip()
        filters = args.get("filters") or []
        if not isinstance(filters, list):
            raise RuntimeError("salesforce.search_records filters must be a list")
        if query and filters:
            raise RuntimeError(
                "salesforce.search_records accepts either a SOQL query or equality filters, not both"
            )
        if not query and not filters:
            raise RuntimeError(
                "salesforce.search_records requires a SOQL query or at least one equality filter"
            )
        if any(
            not isinstance(item, dict)
            or set(item) != {"field", "value"}
            for item in filters
        ):
            raise RuntimeError(
                "salesforce.search_records filters must contain exactly field and value"
            )
        fixture = simulated_fixture_result(
            "salesforce.search_records",
            args,
        )
        if fixture is not no_fixture:
            return fixture
        sobject = str(args.get("sobject") or "")
        result = salesforce().search_records(
            sobject,
            query,
            filters,
            args.get("limit"),
        )
        if sobject and isinstance(result.get("records"), list):
            result[sobject] = result["records"]
        return result

    def sf_update_record(args: dict[str, Any]) -> dict[str, Any]:
        records = args.get("records")
        if records is not None:
            if not isinstance(records, list):
                raise RuntimeError("salesforce.update_record records must be an array")
            results: list[dict[str, Any]] = []
            success_records: list[dict[str, Any]] = []
            failed_records: list[dict[str, Any]] = []
            outer_sobject = str(args.get("sobject") or "")
            for record in records:
                if not isinstance(record, dict):
                    raise RuntimeError(
                        "salesforce.update_record batch entries must be objects"
                    )
                fields = record.get("fields") or {}
                if not isinstance(fields, dict):
                    raise RuntimeError(
                        "salesforce.update_record batch fields must be an object"
                    )
                record_id = str(record.get("id") or "")
                call_args = {
                    "sobject": str(record.get("sobject") or outer_sobject),
                    "id": record_id,
                    "fields": fields,
                }
                try:
                    raise_simulated_action_fault(
                        "salesforce.update_record",
                        call_args,
                    )
                    result = salesforce().update_record(
                        call_args["sobject"],
                        record_id,
                        fields,
                    )
                    results.append(result)
                    success_records.append(
                        {"Id": record_id, **fields, "success": True}
                    )
                except RuntimeError as exc:
                    error = {"message": str(exc)}
                    results.append({"ok": False, "errors": [error]})
                    failed_records.append(
                        {
                            "Id": record_id,
                            **fields,
                            "success": False,
                            "errors": [error],
                        }
                    )
            return {
                "ok": not failed_records,
                "records": results,
                "successRecords": success_records,
                "failedRecords": failed_records,
                "success_records_size": len(success_records),
                "failed_records_size": len(failed_records),
            }
        fields = args.get("fields") or {}
        if not isinstance(fields, dict):
            raise RuntimeError("salesforce.update_record fields must be an object")
        raise_simulated_action_fault("salesforce.update_record", args)
        return salesforce().update_record(
            str(args.get("sobject") or ""),
            str(args.get("id") or ""),
            fields,
        )

    def sf_create_record(args: dict[str, Any]) -> dict[str, Any]:
        fields = args.get("fields") or {}
        if not isinstance(fields, dict):
            raise RuntimeError("salesforce.create_record fields must be an object")
        return salesforce().create_record(str(args.get("sobject") or ""), fields)

    def sf_upsert_record(args: dict[str, Any]) -> dict[str, Any]:
        fields = args.get("fields") or {}
        if not isinstance(fields, dict):
            raise RuntimeError("salesforce.upsert_record fields must be an object")
        return salesforce().upsert_record(
            str(args.get("sobject") or ""),
            str(args.get("key_field") or args.get("primary_key") or ""),
            fields,
        )

    def sf_snapshot(args: dict[str, Any]) -> dict[str, Any]:
        return salesforce().snapshot()

    def sf_cleanup(args: dict[str, Any]) -> dict[str, Any]:
        return salesforce().cleanup()

    def wrf_return_result(args: dict[str, Any]) -> dict[str, Any]:
        result = args.get("result") or {}
        if not isinstance(result, dict):
            raise RuntimeError("workato_recipe_function.return_result result must be an object")
        return {"ok": True, "result": result}

    def api_return_response(args: dict[str, Any]) -> dict[str, Any]:
        response = args.get("response")
        result = {
            "ok": True,
            "http_status_code": str(args.get("http_status_code") or "200"),
            "response": response,
        }
        response_headers = args.get("response_headers")
        if response_headers is not None:
            if not isinstance(response_headers, dict):
                raise RuntimeError(
                    "workato_api_platform.return_response response_headers "
                    "must be an object"
                )
            result["response_headers"] = response_headers
        return result

    def service_call_service(args: dict[str, Any]) -> dict[str, Any]:
        model_facing_callable_surface = (
            seed_full.get("_q_only_model_surface") is True
        )
        callable_fixtures_present = any(
            str(item.get("tool") or "")
            == "workato_service.call_service"
            for item in fixture_rows
        )
        if model_facing_callable_surface or callable_fixtures_present:
            if "reply" in args:
                raise RuntimeError(
                    "workato_service.call_service reply is simulator output, "
                    "not model input"
                )
            fixture = simulated_fixture_result(
                "workato_service.call_service",
                args,
                strict=True,
            )
            if fixture is no_fixture:
                raise RuntimeError(
                    "workato_service.call_service has no exact deterministic "
                    "fixture for this flow_id/request"
                )
            return fixture
        if "reply" not in args:
            raise RuntimeError(
                "workato_service.call_service requires a deterministic "
                "callable fixture"
            )
        # ``args`` is the ToolRegistry's mutable physical-call copy. Consume
        # the private reference-only fixture before the registry records the
        # public call, so golden and agent trajectories expose the same input
        # contract (flow_id + request) while retaining the deterministic
        # seeded reply as tool output.
        reply = args.pop("reply")
        return {
            "ok": True,
            "flow_id": str(args.get("flow_id") or ""),
            "request": args.get("request"),
            "reply": reply,
        }

    def service_call_service_async(args: dict[str, Any]) -> dict[str, Any]:
        # Async callable-recipe invocation returns an acknowledgement only; the
        # sub-recipe runs independently so no reply data is available.
        return {
            "ok": True,
            "flow_id": str(args.get("flow_id") or ""),
            "request": args.get("request"),
        }

    def workato_app_start_recipe(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "recipe_id": str(args.get("recipe_id") or "")}

    def workato_app_stop_recipe(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "recipe_id": str(args.get("recipe_id") or "")}

    def workato_app_rerun_jobs(args: dict[str, Any]) -> dict[str, Any]:
        job_ids = args.get("job_ids") or []
        if not isinstance(job_ids, list):
            raise RuntimeError("workato_app.rerun_jobs job_ids must be a list")
        return {"ok": True, "job_ids": [str(job) for job in job_ids]}

    def workato_app_list_jobs(args: dict[str, Any]) -> dict[str, Any]:
        # Deterministic seeded jobs. Fail fast when a recipe iterates jobs but no
        # seed key is present; an explicitly empty list is a valid seed.
        if "workato_app_jobs" not in seed_full:
            raise RuntimeError("workato_app.list_jobs requires seed key 'workato_app_jobs'")
        jobs = seed_full.get("workato_app_jobs")
        if not isinstance(jobs, list):
            raise RuntimeError("seed 'workato_app_jobs' must be a list")
        return {"ok": True, "jobs": list(jobs)}

    def workato_app_get_recipe(args: dict[str, Any]) -> dict[str, Any]:
        recipes = seed_full.get("workato_app_recipes")
        if not isinstance(recipes, dict):
            raise RuntimeError("workato_app.get_recipe requires seed dict 'workato_app_recipes'")
        recipe_id = str(args.get("recipe_id") or "")
        if recipe_id not in recipes:
            raise RuntimeError(f"seed 'workato_app_recipes' missing recipe_id {recipe_id}")
        record = recipes[recipe_id]
        if not isinstance(record, dict):
            raise RuntimeError(f"seed 'workato_app_recipes' entry for {recipe_id} must be an object")
        out = {"ok": True, "recipe_id": recipe_id}
        out.update(record)
        return out

    def pub_sub_publish_to_topic(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "topic_id": str(args.get("topic_id") or ""),
            "message": args.get("message"),
        }

    def pub_sub_publish_to_topic_batch(args: dict[str, Any]) -> dict[str, Any]:
        messages = args.get("messages") or []
        if not isinstance(messages, list):
            raise RuntimeError("workato_pub_sub.publish_to_topic_batch messages must be a list")
        return {
            "ok": True,
            "topic_id": str(args.get("topic_id") or ""),
            "messages": list(messages),
        }

    def dt_truncate_table(args: dict[str, Any]) -> dict[str, Any]:
        return datatable.truncate_table(str(args.get("table_id") or ""))

    def service_send_reply(args: dict[str, Any]) -> dict[str, Any]:
        out = {
            "ok": True,
            "reply_type": str(args.get("reply_type") or "success"),
            "reply": args.get("reply"),
        }
        if "message" in args:
            out["message"] = args.get("message")
        return out

    def genie_return_result(args: dict[str, Any]) -> dict[str, Any]:
        result = args.get("result") if "result" in args else {}
        return {"ok": True, "result": result}

    def clock_wait_for_interval(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "interval": str(args.get("interval") or ""), "waited": False}

    def runtime_log_message(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "message": str(args.get("message") or ""),
            "log_level": str(args.get("log_level") or "INFO").upper(),
            "user_logs_enabled": bool(args.get("user_logs_enabled", True)),
        }

    def runtime_declare_variable(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        variables = args.get("variables")
        if isinstance(variables, dict):
            return deepcopy(variables)
        name = str(args.get("name") or "").split(":")[-1]
        return {name: deepcopy(args.get("value"))} if name else {}

    def runtime_update_variables(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            str(key): deepcopy(value)
            for key, value in args.items()
            if key not in {"name", "input_mode"}
        }

    def runtime_declare_list(args: dict[str, Any]) -> dict[str, Any]:
        name = str(args.get("name") or "list")
        items = deepcopy(args.get("list_items") or [])
        if not isinstance(items, list):
            raise RuntimeError(
                "workato_runtime.declare_list list_items must be an array"
            )
        runtime_lists[name] = items
        return {
            name: deepcopy(items),
            "list": deepcopy(items),
            "list_items": deepcopy(items),
        }

    def runtime_insert_to_list(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        name = str(args.get("name") or "list")
        items = runtime_lists.setdefault(name, [])
        item = deepcopy(args.get("list_item"))
        if str(args.get("location") or "end").lower() in {
            "start",
            "beginning",
            "first",
        }:
            items.insert(0, item)
        else:
            items.append(item)
        return {"list_items": deepcopy(items)}

    def runtime_insert_to_list_batch(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        name = str(args.get("name") or "list")
        incoming = args.get("list_items") or []
        if not isinstance(incoming, list):
            raise RuntimeError(
                "workato_runtime.insert_to_list_batch list_items must be "
                "an array"
            )
        items = runtime_lists.setdefault(name, [])
        copied = deepcopy(incoming)
        if str(args.get("location") or "end").lower() in {
            "start",
            "beginning",
            "first",
        }:
            items[0:0] = copied
        else:
            items.extend(copied)
        return {"list_items": deepcopy(items)}

    def runtime_accumulate_list_items(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        accumulated_list_items.append(deepcopy(args.get("list_item")))
        return {
            "list_items": deepcopy(accumulated_list_items),
            "list_size": len(accumulated_list_items),
        }

    def runtime_create_list(args: dict[str, Any]) -> dict[str, Any]:
        size = _integer_arg(
            args.get("size"), "workato_runtime.create_list size", default=0
        )
        if size < 0:
            raise RuntimeError(
                "workato_runtime.create_list size must be non-negative"
            )
        items = [
            {"____Index": index, "____Size": size}
            for index in range(size)
        ]
        name = str(args.get("name") or "list")
        runtime_lists[name] = deepcopy(items)
        return {
            name: deepcopy(items),
            "list": deepcopy(items),
            "list_items": deepcopy(items),
            "list_size": size,
            "size": size,
            "____Size": size,
        }

    def runtime_parse_json(args: dict[str, Any]) -> dict[str, Any]:
        document = args.get("document")
        try:
            parsed = (
                json.loads(document)
                if isinstance(document, str)
                else deepcopy(document)
            )
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError(
                f"workato_runtime.parse_json received invalid JSON: {exc}"
            ) from exc
        return {"ok": True, "document": parsed}

    def smart_list_fixture(
        tool: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        fixture = simulated_fixture_result(tool, args)
        if fixture is no_fixture:
            raise RuntimeError(
                f"{tool} has no exact deterministic fixture for these args"
            )
        return fixture

    def smart_list_create_list(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        return smart_list_fixture(
            "workato_smart_list.create_list",
            args,
        )

    def smart_list_create_list_from_csv(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        return smart_list_fixture(
            "workato_smart_list.create_list_from_csv",
            args,
        )

    def smart_list_query_list(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        return smart_list_fixture(
            "workato_smart_list.query_list",
            args,
        )

    tools.register(
        "slack.post_message",
        slack_post_message,
        description="Post a message to the in-process Slack simulator.",
        input_schema={
            "type": "object",
            "required": ["channel", "text"],
            "properties": {
                "channel": {"type": "string"},
                "text": {"type": "string"},
                "blocks": {"type": "array"},
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "color": {"type": "string"},
                            "pretext": {"type": "string"},
                            "title": {"type": "string"},
                            "title_link": {"type": "string"},
                            "text": {"type": "string"},
                            "footer": {"type": "string"},
                            "footer_icon": {"type": "string"},
                            "fields": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["title", "value"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "value": {"type": "string"},
                                        "short": {"type": "boolean"},
                                    },
                                },
                            },
                            "actions": {"type": "array"},
                        },
                    },
                },
                "thread_ts": {"type": "string"},
                "ts": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "slack.post_reply",
        slack_post_reply,
        description=(
            "Reply to the invoking Slack bot-command conversation, or to an "
            "explicit channel/thread when supplied. Omitting channel uses the "
            "invoking conversation routed through benchmark isolation. The "
            "reply may contain text, Block Kit blocks, or both; it may be "
            "requester-only, replace the original command response, or delete "
            "the original while posting the reply when those modes are set."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "text": {"type": "string"},
                "blocks": {"type": "array", "items": {"type": "object"}},
                "thread_ts": {"type": "string"},
                "user": {"type": "string"},
                "original_ts": {"type": "string"},
                "ephemeral": {"type": "boolean"},
                "replace_original": {"type": "boolean"},
                "delete_original": {"type": "boolean"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "harness.slack.seed_message",
        slack_post_message,
        description="Internal harness setup: create a simulated Slack message that a recipe can act on.",
        input_schema={
            "type": "object",
            "required": ["channel", "text"],
            "properties": {
                "channel": {"type": "string"},
                "text": {"type": "string"},
                "blocks": {"type": "array"},
                "thread_ts": {"type": "string"},
            },
        },
        expose_to_agent=False,
    )
    tools.register(
        "slack.update_blocks_by_block_id",
        slack_update_blocks_by_block_id,
        description="Update a simulated Slack message by replacing or removing Block Kit blocks with matching block IDs.",
        input_schema={
            "type": "object",
            "required": ["message_json", "blocks_to_update"],
            "properties": {
                "message_json": {},
                "blocks_to_update": {"type": "array"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "slack.delete_message",
        slack_delete_message,
        description="Delete a simulated Slack message by channel and timestamp.",
        input_schema={
            "type": "object",
            "required": ["channel", "ts"],
            "properties": {
                "channel": {"type": "string"},
                "ts": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "slack_bot.get_user_by_email",
        slack_lookup_user_by_email,
        description="Look up a deterministic simulated Slack user by email or id.",
        input_schema={
            "type": "object",
            "properties": {"email": {"type": "string"}, "id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "slack_bot.open_bot_app_home",
        slack_open_bot_app_home,
        description="Publish a Slack App Home view in the simulator.",
        input_schema={
            "type": "object",
            "required": ["user_id", "view"],
            "properties": {
                "user_id": {"type": "string"},
                "view": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "slack_bot.block_kit_modals",
        slack_open_modal,
        description="Open a Slack modal in the simulator.",
        input_schema={
            "type": "object",
            "required": ["trigger_id", "view"],
            "properties": {
                "trigger_id": {"type": "string"},
                "view": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "slack_bot.generate_menu_options",
        slack_generate_menu_options,
        description="Return dynamic menu options for a Slack trigger payload.",
        input_schema={
            "type": "object",
            "required": ["options"],
            "properties": {
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["label", "value"],
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                }
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "jira.create_issue",
        jira_create_issue,
        description="Create an issue in the in-process Jira simulator.",
        input_schema={"type": "object", "required": ["project_issuetype", "summary"]},
        expose_to_agent=True,
    )
    tools.register(
        "jira.delete_issue",
        jira_delete_issue,
        description="Internal cleanup: delete a benchmark-created Jira issue.",
        input_schema={"type": "object", "required": ["key"]},
        expose_to_agent=False,
    )
    tools.register(
        "google_sheets.add_spreadsheet_row_v4",
        sheets_add_row,
        description="Append one row to the simulated Google Sheet.",
        input_schema={
            "type": "object",
            "required": ["data"],
            "properties": {
                "spreadsheet": {"type": "string"},
                "sheet": {"type": "string"},
                "headers": {"type": "array"},
                "data": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "google_sheets.get_spreadsheet_rows_v4",
        sheets_get_rows,
        description="Retrieve rows from the simulated Google Sheet.",
        input_schema={
            "type": "object",
            "properties": {
                "spreadsheet": {"type": "string"},
                "sheet": {"type": "string"},
                "range": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "google_sheets.search_spreadsheet_rows_v4_new",
        sheets_search_rows,
        description="Search rows in the simulated Google Sheet using exact column filters.",
        input_schema={
            "type": "object",
            "properties": {
                "spreadsheet": {"type": "string"},
                "sheet": {"type": "string"},
                "data": {"type": "object"},
                "count": {"type": ["integer", "null"], "minimum": 0},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "google_sheets.update_row_v4_new",
        sheets_update_row,
        description="Update one row in the simulated Google Sheet.",
        input_schema={
            "type": "object",
            "required": ["row_number", "data"],
            "properties": {
                "row_number": {"type": "integer"},
                "data": {"type": "object"},
                "spreadsheet": {"type": "string"},
                "sheet": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "clock.wait_for_interval",
        clock_wait_for_interval,
        description="Replay a Workato clock wait interval without sleeping during benchmark execution.",
        input_schema={
            "type": "object",
            "required": ["interval"],
            "properties": {"interval": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "harness.google_sheets.seed_rows",
        sheets_seed_rows,
        description="Internal harness writer for deterministic simulated Google Sheets rows.",
        input_schema={"type": "object", "properties": {"sheets": {"type": "object"}}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.google_sheets.snapshot",
        sheets_snapshot,
        description="Internal harness reader for the simulated Google Sheet.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "google_drive.create_folder",
        drive_create_folder,
        description="Create a folder in the in-process Google Drive simulator.",
        input_schema={
            "type": "object",
            "required": ["parent_id", "name"],
            "properties": {
                "parent_id": {"type": "string"},
                "folderId": {"type": "string"},
                "name": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "harness.google_drive.delete_file",
        drive_delete_file,
        description="Internal harness cleanup for a benchmark-created Google Drive file or folder.",
        input_schema={"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
        expose_to_agent=False,
    )
    tools.register(
        "snowflake.upsert_rows_batch",
        snowflake_upsert_rows_batch,
        description="Upsert rows into an isolated benchmark Snowflake target table.",
        input_schema={
            "type": "object",
            "required": ["table", "key_columns", "rows"],
            "properties": {
                "table": {"type": "string"},
                "key_columns": {},
                "rows": {"type": "array"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "snowflake.update_rows",
        snowflake_update_rows,
        description="Update rows in an isolated benchmark Snowflake target table.",
        input_schema={
            "type": "object",
            "required": ["table", "where", "columns"],
            "properties": {
                "table": {"type": "string"},
                "where": {"type": "string"},
                "columns": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "snowflake.search_rows",
        snowflake_search_rows,
        description="Search rows in an isolated benchmark Snowflake table state.",
        input_schema={
            "type": "object",
            "required": ["table"],
            "properties": {
                "table": {"type": "string"},
                "where": {"type": "string"},
                "parameters": {"type": "object"},
                "limit": {"type": ["integer", "null"], "minimum": 0},
                "offset": {"type": ["integer", "null"], "minimum": 0},
                "orderby": {"type": "string"},
                "output_columns": {
                    "description": (
                        "Optional projection of returned fields. Accepts a "
                        "newline- or comma-separated field list."
                    ),
                    "type": "string",
                },
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "snowflake.search_rows_sql",
        snowflake_search_rows_sql,
        description="Run a constrained SELECT query against isolated benchmark Snowflake table state.",
        input_schema={
            "type": "object",
            "required": ["sql"],
            "properties": {
                "sql": {"type": "string"},
                "parameters": {"type": "object"},
                "limit": {"type": ["integer", "null"], "minimum": 0},
                "offset": {"type": ["integer", "null"], "minimum": 0},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "snowflake.run_custom_sql",
        snowflake_run_custom_sql,
        description=(
            "Run constrained Snowflake SQL against isolated benchmark state. "
            "Supports SELECT, INSERT INTO ... SELECT, ALTER TABLE ... ADD, "
            "COPY INTO from a declared stage, retention DELETE, TRUNCATE "
            "TABLE, and CREATE OR REPLACE TABLE AS SELECT within the "
            "documented simulator SQL subset."
        ),
        input_schema={
            "type": "object",
            "required": ["sql"],
            "properties": {
                "sql": {"type": "string"},
                "parameters": {"type": "object"},
                "limit": {},
                "offset": {},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "harness.snowflake_live.seed_tables",
        snowflake_live_seed_tables,
        description="Internal harness writer for deterministic simulated Snowflake tables.",
        input_schema={"type": "object", "properties": {"snowflake": {"type": "object"}}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.snowflake_live.cleanup",
        snowflake_live_cleanup,
        description="Internal harness cleanup for simulated Snowflake tables.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.snowflake.snapshot",
        snowflake_snapshot,
        description="Internal harness readback of Snowflake table state.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "workato_db_table.get_records",
        dt_get_records,
        description="Read records from a controlled Workato data table.",
        input_schema={
            "type": "object",
            "required": ["table_id"],
            "properties": {
                "table_id": {"type": "string"},
                "filters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["field_id", "op"],
                        "properties": {
                            "field_id": {"type": "string"},
                            "op": {
                                "type": "string",
                                "enum": [
                                    "eq",
                                    "ne",
                                    "gte",
                                    "gt",
                                    "lte",
                                    "lt",
                                    "starts_with",
                                    "isnull",
                                    "isnotnull",
                                ],
                            },
                            "value": {},
                        },
                    },
                },
                "continuation_token": {"type": "string"},
                "limit": {"type": "integer"},
                "order_by_field_id": {"type": "string"},
                "order_direction": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                },
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_db_table.search_records",
        dt_search_records,
        description="Search records in a controlled Workato data table.",
        input_schema={
            "type": "object",
            "required": ["table_id", "query"],
            "properties": {"table_id": {"type": "string"}, "query": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_db_table.add_record",
        dt_add_record,
        description="Add a record to a controlled Workato data table.",
        input_schema={
            "type": "object",
            "required": ["table_id", "record"],
            "properties": {
                "table_id": {"type": "string"},
                "record": {"type": "object"},
                "record_id_field": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_db_table.update_record",
        dt_update_record,
        description="Update a record in a controlled Workato data table.",
        input_schema={
            "type": "object",
            "required": ["table_id", "record_id", "record"],
            "properties": {
                "table_id": {"type": "string"},
                "record_id": {},
                "record": {"type": "object"},
                "record_id_field": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_db_table.upsert_record",
        dt_upsert_record,
        description="Create or update a record in a controlled Workato data table.",
        input_schema={
            "type": "object",
            "required": ["table_id", "record"],
            "properties": {
                "table_id": {"type": "string"},
                "record": {"type": "object"},
                "record_id": {},
                "primary_field_id": {"type": "string"},
                "record_id_field": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_db_table.delete_record",
        dt_delete_record,
        description="Delete a record from a controlled Workato data table.",
        input_schema={
            "type": "object",
            "required": ["table_id", "record_id"],
            "properties": {"table_id": {"type": "string"}, "record_id": {}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "harness.workato_db_table.snapshot",
        dt_snapshot,
        description="Internal harness readback of controlled Workato data table state.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "lookup_table.get_entries",
        lt_get_entries,
        description="Read entries from a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id"],
            "properties": {"lookup_table_id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "lookup_table.get_entry",
        lt_get_entry,
        description="Read one entry from a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id"],
            "properties": {
                "lookup_table_id": {"type": "string"},
                "id": {},
                "parameters": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "lookup_table.search_entries",
        lt_search_entries,
        description="Search entries in a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id", "parameters"],
            "properties": {
                "lookup_table_id": {"type": "string"},
                "parameters": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "lookup_table.add_entry",
        lt_add_entry,
        description="Add an entry to a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id", "parameters"],
            "properties": {
                "lookup_table_id": {"type": "string"},
                "parameters": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "lookup_table.update_entry",
        lt_update_entry,
        description="Update an entry in a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id", "id", "parameters"],
            "properties": {
                "lookup_table_id": {"type": "string"},
                "id": {},
                "parameters": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "lookup_table.delete_entry",
        lt_delete_entry,
        description="Delete an entry from a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id", "id"],
            "properties": {
                "lookup_table_id": {"type": "string"},
                "id": {},
                "ignore_not_found": {},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "lookup_table.truncate",
        lt_truncate,
        description="Delete all entries from a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id"],
            "properties": {"lookup_table_id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "lookup_table.add_batch_of_entries",
        lt_add_batch_of_entries,
        description="Add a batch of entries to a controlled Workato lookup table.",
        input_schema={
            "type": "object",
            "required": ["lookup_table_id", "entries"],
            "properties": {
                "lookup_table_id": {"type": "string"},
                "entries": {"type": "array", "items": {"type": "object"}},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "harness.lookup_table.snapshot",
        lt_snapshot,
        description="Internal harness readback of controlled Workato lookup table state.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.salesforce.seed_records",
        sf_seed_records,
        description="Internal harness setup: create simulated Salesforce seed records.",
        input_schema={
            "type": "object",
            "required": ["salesforce"],
            "properties": {"salesforce": {"type": "object"}},
        },
        expose_to_agent=False,
    )
    tools.register(
        "salesforce.search_records",
        sf_search_records,
        description=(
            "Search simulated Salesforce records. Use exactly one mode: either a "
            "non-empty SOQL-style query with filters omitted, or query='' with "
            "simple equality filters containing only field and value. Never send both."
        ),
        input_schema={
            "type": "object",
            "required": ["sobject", "query"],
            "properties": {
                "sobject": {"type": "string"},
                "query": {"type": "string"},
                "filters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["field", "value"],
                        "properties": {
                            "field": {"type": "string"},
                            "value": {},
                        },
                        "additionalProperties": False,
                    },
                },
                "limit": {"type": "integer", "minimum": 0},
            },
            "oneOf": [
                {
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "filters": {"type": "array", "maxItems": 0},
                    }
                },
                {
                    "required": ["filters"],
                    "properties": {
                        "query": {"const": ""},
                        "filters": {"type": "array", "minItems": 1},
                    },
                },
            ],
        },
        expose_to_agent=True,
    )
    tools.register(
        "salesforce.update_record",
        sf_update_record,
        description="Update a simulated Salesforce record.",
        input_schema={
            "type": "object",
            "properties": {
                "sobject": {"type": "string"},
                "id": {"type": "string"},
                "fields": {"type": "object"},
                "records": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["sobject", "id", "fields"],
                        "properties": {
                            "sobject": {"type": "string"},
                            "id": {"type": "string"},
                            "fields": {"type": "object"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "oneOf": [
                {"required": ["sobject", "id", "fields"]},
                {"required": ["sobject", "records"]},
            ],
        },
        expose_to_agent=True,
    )
    tools.register(
        "salesforce.create_record",
        sf_create_record,
        description="Create a simulated Salesforce record.",
        input_schema={
            "type": "object",
            "required": ["sobject", "fields"],
            "properties": {
                "sobject": {"type": "string"},
                "fields": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "salesforce.upsert_record",
        sf_upsert_record,
        description="Upsert a simulated Salesforce record by a primary key field.",
        input_schema={
            "type": "object",
            "required": ["sobject", "key_field", "fields"],
            "properties": {
                "sobject": {"type": "string"},
                "key_field": {"type": "string"},
                "fields": {"type": "object"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "harness.salesforce.snapshot",
        sf_snapshot,
        description="Internal harness readback of simulated Salesforce state.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.salesforce.cleanup",
        sf_cleanup,
        description="Internal harness cleanup for simulated Salesforce records.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "workato_recipe_function.return_result",
        wrf_return_result,
        description="Controlled Workato recipe-function return_result action.",
        input_schema={
            "type": "object",
            "required": ["result"],
            "properties": {"result": {"type": "object"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_service.call_service",
        service_call_service,
        description="Invoke a controlled callable recipe. The simulator returns the exact deterministic seeded reply for the supplied flow and request.",
        input_schema={
            "type": "object",
            "required": ["flow_id"],
            "properties": {
                "flow_id": {"type": "string"},
                "request": {},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_pub_sub.publish_to_topic",
        pub_sub_publish_to_topic,
        description="Controlled Workato pub/sub publish action.",
        input_schema={
            "type": "object",
            "required": ["topic_id", "message"],
            "properties": {
                "topic_id": {"type": "string"},
                "message": {},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_service.send_reply",
        service_send_reply,
        description="Controlled Workato service (callable recipe) send_reply action.",
        input_schema={
            "type": "object",
            "required": ["reply_type"],
            "properties": {
                "reply_type": {"type": "string"},
                "reply": {},
                "message": {},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_api_platform.return_response",
        api_return_response,
        description="Controlled Workato API Platform return_response action.",
        input_schema={
            "type": "object",
            # HTTP 204 responses intentionally have no body in valid Workato
            # recipes, so only the status is universally required.
            "required": ["http_status_code"],
            "properties": {
                "http_status_code": {"type": "string"},
                "response": {},
                "response_headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_genie.workflow_return_result",
        genie_return_result,
        description="Controlled Workato Genie workflow_return_result action.",
        input_schema={
            "type": "object",
            "properties": {"result": {}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_service.call_service_async",
        service_call_service_async,
        description="Controlled Workato async callable-recipe invocation; returns an ack only (no reply).",
        input_schema={
            "type": "object",
            "required": ["flow_id"],
            "properties": {
                "flow_id": {"type": "string"},
                "request": {},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_app.start_recipe",
        workato_app_start_recipe,
        description="Controlled Workato app recipe-lifecycle start_recipe action.",
        input_schema={
            "type": "object",
            "required": ["recipe_id"],
            "properties": {"recipe_id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_app.stop_recipe",
        workato_app_stop_recipe,
        description="Controlled Workato app recipe-lifecycle stop_recipe action.",
        input_schema={
            "type": "object",
            "required": ["recipe_id"],
            "properties": {"recipe_id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_app.rerun_jobs",
        workato_app_rerun_jobs,
        description="Controlled Workato app recipe-lifecycle rerun_jobs action.",
        input_schema={
            "type": "object",
            "required": ["job_ids"],
            "properties": {
                "job_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "recipe_id": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_app.list_jobs",
        workato_app_list_jobs,
        description="List controlled Workato app jobs (deterministic seeded state).",
        input_schema={
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_app.get_recipe",
        workato_app_get_recipe,
        description="Get a controlled Workato app recipe's details (deterministic seeded state).",
        input_schema={
            "type": "object",
            "required": ["recipe_id"],
            "properties": {"recipe_id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_pub_sub.publish_to_topic_batch",
        pub_sub_publish_to_topic_batch,
        description="Controlled Workato pub/sub batch publish action.",
        input_schema={
            "type": "object",
            "required": ["topic_id", "messages"],
            "properties": {
                "topic_id": {"type": "string"},
                "messages": {"type": "array"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_db_table.truncate_table",
        dt_truncate_table,
        description="Delete all records from a controlled Workato data table.",
        input_schema={
            "type": "object",
            "required": ["table_id"],
            "properties": {"table_id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.log_message",
        runtime_log_message,
        description=(
            "Write one deterministic runtime log message with an optional "
            "INFO, WARN, or ERROR severity and centralized-log visibility."
        ),
        input_schema={
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {"type": "string"},
                "log_level": {
                    "type": "string",
                    "enum": ["INFO", "WARN", "ERROR"],
                },
                "user_logs_enabled": {"type": "boolean"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.declare_variable",
        runtime_declare_variable,
        description=(
            "Declare recipe variables and return their initial values."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "variables": {"type": "object"},
                "name": {"type": "string"},
                "value": {},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.update_variables",
        runtime_update_variables,
        description=(
            "Update recipe variables; pass variable fields alongside the "
            "configured name metadata."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "input_mode": {"type": "string"},
            },
            "additionalProperties": True,
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.declare_list",
        runtime_declare_list,
        description=(
            "Declare a recipe list with an optional initial list_items array."
        ),
        input_schema={
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "list_item_schema_json": {"type": "string"},
                "list_items": {"type": "array"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.insert_to_list",
        runtime_insert_to_list,
        description="Insert one item at the start or end of a recipe list.",
        input_schema={
            "type": "object",
            "required": ["name", "list_item"],
            "properties": {
                "name": {"type": "string"},
                "list_item": {},
                "location": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.insert_to_list_batch",
        runtime_insert_to_list_batch,
        description=(
            "Insert an array of items at the start or end of a recipe list."
        ),
        input_schema={
            "type": "object",
            "required": ["name", "list_items"],
            "properties": {
                "name": {"type": "string"},
                "list_items": {"type": "array"},
                "location": {"type": "string"},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.accumulate_list_items",
        runtime_accumulate_list_items,
        description=(
            "Append one item to the current accumulator and return the "
            "accumulated list."
        ),
        input_schema={
            "type": "object",
            "required": ["list_item"],
            "properties": {"list_item": {}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.create_list",
        runtime_create_list,
        description=(
            "Create an indexed list of the configured non-negative size."
        ),
        input_schema={
            "type": "object",
            "required": ["name", "size"],
            "properties": {
                "name": {"type": "string"},
                "size": {"type": "integer", "minimum": 0},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_runtime.parse_json",
        runtime_parse_json,
        description="Parse a JSON document into a structured value.",
        input_schema={
            "type": "object",
            "required": ["document"],
            "properties": {
                "document": {
                    "type": ["string", "object", "array"]
                }
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_smart_list.create_list",
        smart_list_create_list,
        description=(
            "Create the configured in-memory smart list and return its rows "
            "and columns."
        ),
        input_schema={
            "type": "object",
            "required": ["list_name"],
            "properties": {"list_name": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_smart_list.create_list_from_csv",
        smart_list_create_list_from_csv,
        description=(
            "Create the configured in-memory smart list from CSV columns."
        ),
        input_schema={
            "type": "object",
            "required": ["list_name", "columns"],
            "properties": {
                "list_name": {"type": "string"},
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "workato_smart_list.query_list",
        smart_list_query_list,
        description=(
            "Run the configured SQL statement over in-memory smart lists."
        ),
        input_schema={
            "type": "object",
            "required": ["sql"],
            "properties": {"sql": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    validate_tool_registry(tools)
    return tools

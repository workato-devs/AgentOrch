from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .capabilities import validate_tool_registry
from .config import Env, lookup_table_file, workato_db_table_file
from .google_drive_live import GoogleDriveLiveClient
from .google_sheets_live import GoogleSheetsLiveClient
from .jira_live import JiraLiveClient
from .lookup_table import LookupTableMock
from .salesforce_live_harness import SalesforceRun, provision_records
from .slack_live import SlackLiveClient
from .snowflake_live import SnowflakeLiveClient
from .tools import ToolRegistry
from .workato_db_table import WorkatoDbTableMock


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
        actual = row.get(field_id)
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


def build_live_tools(env: Env, seed: dict[str, Any] | None = None) -> ToolRegistry:
    tools = ToolRegistry()
    seed_full = seed or {}
    slack = SlackLiveClient(env.slack_bot_token)
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
    sheets_client: GoogleSheetsLiveClient | None = None
    drive_client: GoogleDriveLiveClient | None = None

    def salesforce() -> SalesforceRun:
        nonlocal salesforce_run
        if salesforce_run is None:
            salesforce_run = SalesforceRun((seed or {}).get("salesforce_live") or {})
        return salesforce_run

    def google_sheets() -> GoogleSheetsLiveClient:
        nonlocal sheets_client
        if sheets_client is None:
            sheets_client = GoogleSheetsLiveClient(env.sheets_spreadsheet_id, env.sheets_tab)
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
        # Snowflake is a non-Workato backend: it always runs live (backend rule).
        # A legacy `snowflake` seed section provisions the same live tables; no
        # seed section at all means the recipe may not touch Snowflake.
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
                raise RuntimeError(
                    "snowflake tools require an explicit snowflake or snowflake_live seed section"
                )
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
        if args.get("ts") not in (None, ""):
            return slack.update_message(
                str(args.get("channel") or ""),
                str(args.get("ts") or ""),
                str(args.get("text") or ""),
                blocks,
                attachments=attachments,
            )
        return slack.post_message(
            str(args.get("channel") or ""),
            str(args.get("text") or ""),
            blocks,
            str(args.get("thread_ts") or ""),
            attachments,
        )

    def slack_post_reply(args: dict[str, Any]) -> dict[str, Any]:
        blocks = args.get("blocks")
        if blocks is not None and not isinstance(blocks, list):
            raise RuntimeError("slack.post_reply blocks must be a list")
        return slack.post_reply(
            str(args.get("channel") or ""),
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
        out: dict[str, Any] = {"ok": True, "options": options}
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
        return google_sheets().update_row(int(row_number), data)

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
        parameters = args.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise RuntimeError("snowflake.run_custom_sql parameters must be an object")
        result = snowflake_live().search_rows_sql(
            str(args.get("sql") or ""),
            parameters,
            args.get("limit"),
            args.get("offset"),
        )
        result["rows_affected"] = len(result.get("rows") or [])
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
        # Keep live and simulated public contracts identical: supplied
        # ordering/limit arguments are always honored, independent of fixture
        # metadata.
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
                rows = rows[: int(str(args.get("limit")))]
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
        section = args.get("salesforce") or args.get("section") or {}
        if not isinstance(section, dict):
            raise RuntimeError("harness.salesforce.seed_records section must be an object")
        return provision_records(section)

    def sf_search_records(args: dict[str, Any]) -> dict[str, Any]:
        sobject = str(args.get("sobject") or "")
        filters = args.get("filters") or []
        if not isinstance(filters, list):
            raise RuntimeError("salesforce.search_records filters must be a list")
        result = salesforce().search_records(
            sobject,
            str(args.get("query") or ""),
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
            outer_sobject = str(args.get("sobject") or "")
            results: list[dict[str, Any]] = []
            success_records: list[dict[str, Any]] = []
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
                result = salesforce().update_record(
                    str(record.get("sobject") or outer_sobject),
                    record_id,
                    fields,
                )
                results.append(result)
                success_records.append(
                    {"Id": record_id, **fields, "success": True}
                )
            return {
                "ok": True,
                "records": results,
                "successRecords": success_records,
                "failedRecords": [],
                "success_records_size": len(success_records),
                "failed_records_size": 0,
            }
        fields = args.get("fields") or {}
        if not isinstance(fields, dict):
            raise RuntimeError("salesforce.update_record fields must be an object")
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
        return {
            "ok": True,
            "http_status_code": str(args.get("http_status_code") or "200"),
            "response": response,
        }

    def service_call_service(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "flow_id": str(args.get("flow_id") or ""),
            "request": args.get("request"),
            "reply": args.get("reply"),
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

    tools.register(
        "slack.post_message",
        slack_post_message,
        description="Post a message to a live Slack channel.",
        input_schema={
            "type": "object",
            "required": ["channel", "text"],
            "properties": {
                "channel": {"type": "string"},
                "text": {"type": "string"},
                "blocks": {"type": "array"},
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
            "Post a Slack bot-command response as a normal or requester-only "
            "reply, optionally replacing or deleting the original response."
        ),
        input_schema={
            "type": "object",
            "required": ["channel", "text"],
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
        description="Internal harness setup: create a live Slack message that a recipe can act on.",
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
        description="Update a live Slack message by replacing or removing Block Kit blocks with matching block IDs.",
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
        description="Delete a live Slack message by channel and timestamp.",
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
        description="Look up a Slack user by email or id through the live Slack API.",
        input_schema={
            "type": "object",
            "properties": {"email": {"type": "string"}, "id": {"type": "string"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "slack_bot.open_bot_app_home",
        slack_open_bot_app_home,
        description="Publish a Slack App Home view through the live Slack API.",
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
        description="Open a Slack modal through the live Slack API.",
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
            "properties": {"options": {"type": "array"}},
        },
        expose_to_agent=True,
    )
    tools.register(
        "jira.create_issue",
        jira_create_issue,
        description="Create an issue in the live Jira project configured by the raw recipe.",
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
        description="Append one row to the configured live Google Sheet.",
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
        description="Retrieve rows from the configured live Google Sheet.",
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
        description="Search rows in the configured live Google Sheet using exact column filters.",
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
        description="Update one row in the configured live Google Sheet.",
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
        description="Internal harness writer for deterministic live Google Sheets seed rows.",
        input_schema={"type": "object", "properties": {"sheets": {"type": "object"}}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.google_sheets.snapshot",
        sheets_snapshot,
        description="Internal harness reader for the configured live Google Sheet.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "google_drive.create_folder",
        drive_create_folder,
        description="Create a folder in live Google Drive under the requested parent folder.",
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
            "Run Snowflake SELECT, INSERT, ALTER TABLE, COPY INTO, DELETE, "
            "TRUNCATE, or CREATE OR REPLACE TABLE AS SELECT SQL."
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
        description="Internal harness writer for deterministic benchmark-owned live Snowflake seed tables.",
        input_schema={"type": "object", "properties": {"snowflake": {"type": "object"}}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.snowflake_live.cleanup",
        snowflake_live_cleanup,
        description="Internal harness cleanup for benchmark-owned live Snowflake tables.",
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
                "filters": {"type": "array"},
                "continuation_token": {"type": "string"},
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
        description="Internal harness setup: create benchmark-owned live Salesforce seed records.",
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
        description="Search benchmark-owned live Salesforce records with a SOQL-style query.",
        input_schema={
            "type": "object",
            "required": ["sobject", "query"],
            "properties": {
                "sobject": {"type": "string"},
                "query": {"type": "string"},
                "filters": {"type": "array"},
                "limit": {"type": "integer", "minimum": 0},
            },
        },
        expose_to_agent=True,
    )
    tools.register(
        "salesforce.update_record",
        sf_update_record,
        description="Update a benchmark-owned live Salesforce record.",
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
        description="Create a benchmark-owned live Salesforce record.",
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
        description="Upsert a benchmark-owned live Salesforce record by a primary key field.",
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
        description="Internal harness readback of benchmark-owned live Salesforce state.",
        input_schema={"type": "object", "properties": {}},
        expose_to_agent=False,
    )
    tools.register(
        "harness.salesforce.cleanup",
        sf_cleanup,
        description="Internal harness cleanup for benchmark-owned live Salesforce records.",
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
        description="Controlled Workato callable-recipe invocation; reply comes from deterministic seeded state.",
        input_schema={
            "type": "object",
            "required": ["flow_id", "reply"],
            "properties": {
                "flow_id": {"type": "string"},
                "request": {},
                "reply": {},
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
            "required": ["http_status_code", "response"],
            "properties": {
                "http_status_code": {"type": "string"},
                "response": {},
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
            "properties": {"job_ids": {"type": "array"}},
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
    validate_tool_registry(tools)
    return tools

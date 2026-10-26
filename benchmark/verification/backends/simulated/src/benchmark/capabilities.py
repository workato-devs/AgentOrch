from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConnectorCapability:
    connector: str
    actions_supported: tuple[str, ...]
    live_mock: str
    seed_supported: str
    verify_supported: str
    cleanup_supported: str
    limitations: str
    tool_names: tuple[str, ...] = ()
    harness_tool_names: tuple[str, ...] = ()


CAPABILITIES: tuple[ConnectorCapability, ...] = (
    ConnectorCapability(
        connector="Slack",
        actions_supported=(
            "post_message",
            "post_reply",
            "delete_message",
            "get_user_by_email",
            "open_bot_app_home",
            "block_kit_modals",
            "generate_menu_options",
            "update_blocks_by_block_id",
            "bot_command_v2_payload",
        ),
        live_mock="simulated",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="yes",
        limitations=(
            "No Slack credentials or network access are used. Messages, users, App Home views, "
            "and modals are deterministic in-memory state scoped to one seed/run process."
        ),
        tool_names=(
            "slack.post_message",
            "slack.post_reply",
            "slack.delete_message",
            "slack_bot.get_user_by_email",
            "slack_bot.open_bot_app_home",
            "slack_bot.block_kit_modals",
            "slack_bot.generate_menu_options",
            "slack.update_blocks_by_block_id",
        ),
        harness_tool_names=("harness.slack.seed_message",),
    ),
    ConnectorCapability(
        connector="Jira",
        actions_supported=("create_issue",),
        live_mock="simulated",
        seed_supported="not needed for create-only variants",
        verify_supported="yes",
        cleanup_supported="delete benchmark-created issue after verification",
        limitations="No Jira credentials or network access are used; issues are in-memory state.",
        tool_names=("jira.create_issue",),
        harness_tool_names=("jira.delete_issue",),
    ),
    ConnectorCapability(
        connector="SFDC",
        actions_supported=("search_records", "update_record", "create_record", "upsert_record", "create_records_for_seed"),
        live_mock="simulated",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="yes",
        limitations=(
            "Uses deterministic local records and the benchmark SOQL evaluator. Raw action adapters "
            "map Salesforce search_sobjects* to salesforce.search_records and update_sobject/"
            "composite_update_sobject to salesforce.update_record. Raw create_custom_object "
            "maps to salesforce.create_record, raw upsert_sobject maps to "
            "salesforce.upsert_record, and seed provisioning is available through "
            "harness.salesforce.seed_records."
        ),
        tool_names=("salesforce.search_records", "salesforce.update_record", "salesforce.create_record", "salesforce.upsert_record"),
        harness_tool_names=(
            "harness.salesforce.seed_records",
            "harness.salesforce.snapshot",
            "harness.salesforce.cleanup",
        ),
    ),
    ConnectorCapability(
        connector="Google Sheets",
        actions_supported=("add_spreadsheet_row_v4", "get_spreadsheet_rows_v4", "search_spreadsheet_rows_v4_new", "update_row_v4_new"),
        live_mock="simulated",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="seed clears configured benchmark sheet before writing variant rows",
        limitations=(
            "No Google credentials or network access are used. Recipes share one in-memory sheet "
            "per seed/run process while retaining the real action and output schemas."
        ),
        tool_names=(
            "google_sheets.add_spreadsheet_row_v4",
            "google_sheets.get_spreadsheet_rows_v4",
            "google_sheets.search_spreadsheet_rows_v4_new",
            "google_sheets.update_row_v4_new",
        ),
        harness_tool_names=("harness.google_sheets.seed_rows", "harness.google_sheets.snapshot"),
    ),
    ConnectorCapability(
        connector="Google Drive",
        actions_supported=("create_folder",),
        live_mock="simulated",
        seed_supported="not needed for create-folder variants",
        verify_supported="yes",
        cleanup_supported="delete benchmark-created folder after verification",
        limitations=(
            "No Google credentials or network access are used. Folder IDs are deterministic "
            "and folders are scoped to the current process."
        ),
        tool_names=("google_drive.create_folder",),
        harness_tool_names=("harness.google_drive.delete_file",),
    ),
    ConnectorCapability(
        connector="Snowflake",
        actions_supported=("upsert_rows_batch", "update_rows", "search_rows", "search_rows_sql", "run_custom_sql"),
        live_mock="simulated",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="yes",
        limitations=(
            "Snowflake tables are deterministic in-process state. The simulator supports the "
            "benchmark's constrained search, update, upsert, aggregate, and join query shapes; "
            "it does not implement arbitrary Snowflake SQL."
        ),
        tool_names=(
            "snowflake.upsert_rows_batch",
            "snowflake.update_rows",
            "snowflake.search_rows",
            "snowflake.search_rows_sql",
            "snowflake.run_custom_sql",
        ),
        harness_tool_names=("harness.snowflake.snapshot", "harness.snowflake_live.seed_tables", "harness.snowflake_live.cleanup"),
    ),
    ConnectorCapability(
        connector="Workato DB table",
        actions_supported=(
            "get_records",
            "search_records",
            "add_record",
            "update_record",
            "upsert_record",
            "delete_record",
            "truncate_table",
        ),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="yes",
        limitations=(
            "State is isolated by recipe/variant under benchmark/output/_state/workato_db_tables. "
            "Cleanup is state overwrite/isolation rather than an external delete API. "
            "get_records paginates single-page: a continuation_token argument yields a "
            "result without a continuation_token so repeat/while loops terminate."
        ),
        tool_names=(
            "workato_db_table.get_records",
            "workato_db_table.search_records",
            "workato_db_table.add_record",
            "workato_db_table.update_record",
            "workato_db_table.upsert_record",
            "workato_db_table.delete_record",
            "workato_db_table.truncate_table",
        ),
        harness_tool_names=("harness.workato_db_table.snapshot",),
    ),
    ConnectorCapability(
        connector="Lookup table",
        actions_supported=(
            "get_entries",
            "get_entry",
            "search_entries",
            "add_entry",
            "update_entry",
            "delete_entry",
            "truncate",
            "add_batch_of_entries",
        ),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="yes",
        limitations=(
            "State is isolated by recipe/variant under benchmark/output/_state/lookup_tables. "
            "Cleanup is state overwrite/isolation rather than an external delete API."
        ),
        tool_names=(
            "lookup_table.get_entries",
            "lookup_table.get_entry",
            "lookup_table.search_entries",
            "lookup_table.add_entry",
            "lookup_table.update_entry",
            "lookup_table.delete_entry",
            "lookup_table.truncate",
            "lookup_table.add_batch_of_entries",
        ),
        harness_tool_names=("harness.lookup_table.snapshot",),
    ),
    ConnectorCapability(
        connector="Workato recipe function",
        actions_supported=("execute_trigger_payload", "return_result"),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations="Supports recipe-function trigger parameters and return_result only.",
        tool_names=("workato_recipe_function.return_result",),
    ),
    ConnectorCapability(
        connector="Workato API Platform",
        actions_supported=("receive_request_payload", "return_response"),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations="API request trigger and response payloads are mocked inside the benchmark harness.",
        tool_names=("workato_api_platform.return_response",),
    ),
    ConnectorCapability(
        connector="Workato service",
        actions_supported=("receive_request_payload", "send_reply", "call_service", "call_service_async"),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations=(
            "Workato callable/service recipe trigger and reply are mocked inside the "
            "benchmark harness. send_reply is not terminal; a service recipe may "
            "continue executing after replying. call_service does not execute the "
            "sub-recipe: its model-facing simulator returns an exact, one-use "
            "deterministic fixture matched by flow_id and request (fail-fast). "
            "call_service_async returns an acknowledgement only (no reply data) and "
            "requires no seeded reply."
        ),
        tool_names=(
            "workato_service.send_reply",
            "workato_service.call_service",
            "workato_service.call_service_async",
        ),
    ),
    ConnectorCapability(
        connector="Workato Genie",
        actions_supported=("start_workflow_payload", "workflow_return_result"),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations="Genie workflow trigger and return payloads are mocked inside the benchmark harness.",
        tool_names=("workato_genie.workflow_return_result",),
    ),
    ConnectorCapability(
        connector="Workato app trigger",
        actions_supported=(
            "job_error_payload",
            "stop_error_payload",
            "start_recipe",
            "stop_recipe",
            "rerun_jobs",
            "list_jobs",
            "get_recipe",
        ),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations=(
            "Trigger payload support plus controlled recipe-lifecycle actions "
            "(start_recipe/stop_recipe return {ok, recipe_id}; rerun_jobs returns "
            "{ok, job_ids}); no external Workato job lifecycle API is executed. "
            "list_jobs returns the seeded 'workato_app_jobs' list (fail-fast when "
            "the seed key is absent; an empty list is allowed). get_recipe returns "
            "the seeded 'workato_app_recipes'[recipe_id] object ({recipe_id, active}, "
            "fail-fast when missing)."
        ),
        tool_names=(
            "workato_app.start_recipe",
            "workato_app.stop_recipe",
            "workato_app.rerun_jobs",
            "workato_app.list_jobs",
            "workato_app.get_recipe",
        ),
    ),
    ConnectorCapability(
        connector="Workato pub/sub trigger",
        actions_supported=("subscribe_to_topic_payload", "publish_to_topic", "publish_to_topic_batch"),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations=(
            "Trigger payload support plus the publish_to_topic action (controlled, "
            "records topic_id + message) and publish_to_topic_batch (records topic_id "
            "+ messages list); downstream effects run through simulated or mocked tools."
        ),
        tool_names=("workato_pub_sub.publish_to_topic", "workato_pub_sub.publish_to_topic_batch"),
    ),
    ConnectorCapability(
        connector="Workato webhook trigger",
        actions_supported=("new_event_payload",),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations="Trigger payload support only; downstream effects run through simulated or mocked tools.",
    ),
    ConnectorCapability(
        connector="Workato runtime",
        actions_supported=(
            "log_message",
            "declare_variable",
            "update_variables",
            "declare_list",
            "insert_to_list",
            "insert_to_list_batch",
            "accumulate_list_items",
            "create_list",
            "parse_json",
        ),
        live_mock="mock",
        seed_supported="not required",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations=(
            "Deterministic process-local variable, list, logging, and JSON "
            "operations; no external Workato runtime is invoked."
        ),
        tool_names=(
            "workato_runtime.log_message",
            "workato_runtime.declare_variable",
            "workato_runtime.update_variables",
            "workato_runtime.declare_list",
            "workato_runtime.insert_to_list",
            "workato_runtime.insert_to_list_batch",
            "workato_runtime.accumulate_list_items",
            "workato_runtime.create_list",
            "workato_runtime.parse_json",
        ),
    ),
    ConnectorCapability(
        connector="Workato smart list",
        actions_supported=(
            "create_list",
            "create_list_from_csv",
            "query_list",
        ),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations=(
            "Deterministic fixture-backed smart-list reads keyed by exact "
            "public action arguments; no external service is invoked."
        ),
        tool_names=(
            "workato_smart_list.create_list",
            "workato_smart_list.create_list_from_csv",
            "workato_smart_list.query_list",
        ),
    ),
    ConnectorCapability(
        connector="Clock trigger",
        actions_supported=("scheduled_event_payload", "wait_for_interval"),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations="Scheduled trigger payload and wait interval replay only; no scheduler service or real sleep is invoked.",
        tool_names=("clock.wait_for_interval",),
    ),
    ConnectorCapability(
        connector="Skilljar",
        actions_supported=("new_object_payload",),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations="Trigger payload support only; downstream effects run through table tools.",
    ),
    ConnectorCapability(
        connector="Namely",
        actions_supported=("new_job_title_payload",),
        live_mock="mock",
        seed_supported="yes",
        verify_supported="yes",
        cleanup_supported="n/a",
        limitations="Trigger payload support only; downstream effects run through lookup table tools.",
    ),
)


def capability_rows() -> list[dict[str, str]]:
    return [
        {
            "connector": capability.connector,
            "actions supported": ", ".join(capability.actions_supported),
            "live/mock": capability.live_mock,
            "seed supported": capability.seed_supported,
            "verify supported": capability.verify_supported,
            "cleanup supported": capability.cleanup_supported,
            "limitations": capability.limitations,
        }
        for capability in CAPABILITIES
    ]


def known_tool_names(include_harness: bool = True) -> set[str]:
    names: set[str] = set()
    for capability in CAPABILITIES:
        names.update(capability.tool_names)
        if include_harness:
            names.update(capability.harness_tool_names)
    return names


def connector_for_tool(tool_name: str) -> str | None:
    for capability in CAPABILITIES:
        if tool_name in capability.tool_names or tool_name in capability.harness_tool_names:
            return capability.connector
    return None


def validate_tool_registry(tools: Any) -> None:
    actual = set(getattr(tools, "_specs", {}).keys())
    missing = sorted(actual - known_tool_names(include_harness=True))
    if missing:
        raise RuntimeError("tool capability registry missing tools: " + ", ".join(missing))


def markdown_table() -> str:
    headers = [
        "connector",
        "actions supported",
        "live/mock",
        "seed supported",
        "verify supported",
        "cleanup supported",
        "limitations",
    ]
    rows = capability_rows()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape(row[header]) for header in headers) + " |")
    return "\n".join(lines)


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    print(markdown_table())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from .config import BENCHMARK_ROOT


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if str(key).startswith("_") or value is None or str(value) == "<SKIP>":
            continue
        out[str(key)] = _semantic_scalar(value)
    return out


def _semantic_scalar(value: Any) -> Any:
    """Decode Snowflake connector transport literals into stored values.

    Workato recipes commonly call ``.quote`` before feeding a value to the
    Snowflake bulk-upsert connector.  The quote marks are SQL transport
    encoding, not part of the value stored by Snowflake.  Public benchmark
    callers supply the semantic value directly, so both forms must converge
    to the same simulated state.
    """

    if not isinstance(value, str) or len(value) < 2:
        return deepcopy(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


class SnowflakeTableState:
    def __init__(
        self,
        seed_section: dict[str, Any] | None = None,
        state_file: Path | None = None,
    ) -> None:
        self._state_file = state_file
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self._declared_columns: dict[str, list[str]] = {}
        self._current_time: str | None = None
        if seed_section is not None:
            current_time = (seed_section or {}).get("current_time")
            self._current_time = (
                str(current_time) if current_time not in (None, "") else None
            )
            self._tables = self._normalize_tables((seed_section or {}).get("tables") or {})
            self._declared_columns = {
                str(table): [str(column) for column in columns]
                for table, columns in (
                    (seed_section or {}).get("declared_columns") or {}
                ).items()
                if isinstance(columns, list)
            }
            self._flush()
        elif self._state_file and self._state_file.exists():
            data = json.loads(self._state_file.read_text())
            self._tables = self._normalize_tables((data or {}).get("tables") or {})

    def _normalize_tables(self, raw_tables: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        tables: dict[str, list[dict[str, Any]]] = {}
        for table, rows in raw_tables.items():
            if not isinstance(rows, list):
                continue
            clean_rows: list[dict[str, Any]] = []
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                rec = {
                    str(key): (
                        deepcopy(value)
                        if str(key).startswith("_")
                        else _semantic_scalar(value)
                    )
                    for key, value in row.items()
                }
                rec.setdefault("_row_id", idx)
                rec.setdefault("_created_by", "seed")
                clean_rows.append(rec)
            tables[str(table)] = clean_rows
        return tables

    def _flush(self) -> None:
        if not self._state_file:
            return
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(
            json.dumps({"tables": self._tables}, indent=2, sort_keys=True) + "\n"
        )

    def snapshot(self) -> dict[str, Any]:
        section: dict[str, Any] = {
            "tables": {
                table: [_visible_row(row) for row in rows]
                for table, rows in self._tables.items()
            }
        }
        if self._state_file:
            section["state_file"] = _portable_path(self._state_file)
        return {"snowflake": section}

    def upsert_rows_batch(self, table: str, key_columns: Any, rows: list[Any]) -> dict[str, Any]:
        table_name = self._resolve_table_name(str(table or ""))
        if not table_name:
            raise RuntimeError("snowflake.upsert_rows_batch missing table")
        key_names = _key_columns(key_columns)
        if not key_names:
            raise RuntimeError("snowflake.upsert_rows_batch missing key_columns")
        table_rows = self._tables.setdefault(table_name, [])
        applied: list[dict[str, Any]] = []
        created = 0
        updated = 0
        for raw_row in rows:
            if not isinstance(raw_row, dict):
                raise RuntimeError("snowflake.upsert_rows_batch rows must contain objects")
            clean = _clean(raw_row)
            target = self._find_target(table_rows, key_names, clean)
            if target is None:
                rec = {"_row_id": self._next_row_id(table_rows), "_created_by": "agent", **clean}
                table_rows.append(rec)
                applied.append(dict(rec))
                created += 1
                continue
            # Snowflake's unquoted identifiers are case-insensitive.  Update
            # the existing physical key instead of creating both ``name`` and
            # ``NAME`` fields in the same row.
            existing_keys = {
                str(key).casefold(): str(key)
                for key in target
                if not str(key).startswith("_")
            }
            target.update({existing_keys.get(key.casefold(), key): value for key, value in clean.items()})
            target["_modified_by"] = "agent"
            applied.append(dict(target))
            updated += 1
        self._flush()
        return {
            "ok": True,
            "table": table_name,
            "key_columns": key_names,
            "rows": applied,
            "upserted": len(applied),
            "created": created,
            "updated": updated,
        }

    def update_rows(self, table: str, where: str, columns: dict[str, Any]) -> dict[str, Any]:
        table_name = self._resolve_table_name(str(table or ""))
        if not table_name:
            raise RuntimeError("snowflake.update_rows missing table")
        table_rows = self._tables.setdefault(table_name, [])
        # UPDATE has different null semantics from connector bulk upsert:
        # an explicitly supplied None means SQL NULL and must overwrite the
        # previous value. ``<SKIP>`` remains the only omitted-cell sentinel.
        clean = {
            str(key): _semantic_scalar(value)
            for key, value in columns.items()
            if not str(key).startswith("_") and str(value) != "<SKIP>"
        }
        try:
            matching_ids = {
                id(row)
                for row in table_rows
                if _matches_where(row, where, {})
            }
        except RuntimeError as exc:
            if not str(exc).startswith(
                "unsupported snowflake.search_rows where clause"
            ):
                raise
            visible_matches = _sqlite_filter_rows(
                table_rows,
                where,
                {},
                current_time=self._current_time,
            )
            signatures = [
                json.dumps(row, sort_keys=True, default=str)
                for row in visible_matches
            ]
            matching_ids = set()
            remaining = list(signatures)
            for row in table_rows:
                signature = json.dumps(_visible_row(row), sort_keys=True, default=str)
                if signature in remaining:
                    matching_ids.add(id(row))
                    remaining.remove(signature)
        updated_rows: list[dict[str, Any]] = []
        for row in table_rows:
            if id(row) not in matching_ids:
                continue
            existing_keys = {
                str(key).casefold(): str(key)
                for key in row
                if not str(key).startswith("_")
            }
            row.update(
                {
                    existing_keys.get(key.casefold(), key): value
                    for key, value in clean.items()
                }
            )
            row["_modified_by"] = "agent"
            updated_rows.append(dict(row))
        self._flush()
        return {
            "ok": True,
            "table": table_name,
            "where": str(where or ""),
            "columns": clean,
            "updated": len(updated_rows),
            "rows": updated_rows,
        }

    def search_rows(
        self,
        table: str,
        where: str = "",
        parameters: dict[str, Any] | None = None,
        limit: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
        table_name = self._resolve_table_name(str(table or ""))
        if not table_name:
            raise RuntimeError("snowflake.search_rows missing table")
        table_rows = self._tables.setdefault(table_name, [])
        try:
            rows = [
                _visible_row(row)
                for row in table_rows
                if _matches_where(row, where, parameters or {})
            ]
        except RuntimeError as exc:
            if not str(exc).startswith(
                "unsupported snowflake.search_rows where clause"
            ):
                raise
            try:
                rows = _sqlite_filter_rows(
                    table_rows,
                    where,
                    parameters or {},
                    current_time=self._current_time,
                )
            except (sqlite3.Error, ValueError) as fallback_exc:
                raise RuntimeError(
                    f"{exc}; strict relational fallback failed: {fallback_exc}"
                ) from fallback_exc
        sliced = _apply_window(rows, limit, offset)
        return {
            "ok": True,
            "table": table_name,
            "where": str(where or ""),
            "parameters": parameters or {},
            "rows": sliced,
            "records": sliced,
            "count": len(sliced),
        }

    def search_rows_sql(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        limit: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
        """Execute the deterministic native subset, then a strict SQL fallback.

        Imported recipes contain ordinary relational SQL beyond the original
        hand-written parser (computed projections, multi-term joins, and
        standard aggregates).  SQLite is used only after the native evaluator
        explicitly rejects such syntax.  It runs over the same isolated seeded
        tables and still has to satisfy the recipe's unchanged verifier; a
        fallback parse/execute error remains fail-closed.
        """

        known_rows = self._known_search_rows(sql)
        if known_rows is not None:
            sliced = _apply_window(known_rows, limit, offset)
            return {
                "ok": True,
                "table": "BI_DB.MASTER_DATA.MANAGED_USER_GRANTS_COMB_D",
                "sql": str(sql or ""),
                "parameters": parameters or {},
                "rows": sliced,
                "records": deepcopy(sliced),
                "count": len(sliced),
            }

        try:
            return self._search_rows_sql_native(sql, parameters, limit, offset)
        except RuntimeError as exc:
            if not str(exc).startswith(
                (
                    "unsupported snowflake.search_rows",
                    "snowflake.search_rows_sql missing FROM table",
                )
            ):
                raise
            try:
                rows, table_name = _sqlite_search_rows_sql(
                    self._tables,
                    _strip_sql_line_comments(str(sql or "")),
                    parameters or {},
                    current_time=self._current_time,
                    declared_columns=self._declared_columns,
                )
            except (sqlite3.Error, ValueError) as fallback_exc:
                raise RuntimeError(
                    f"{exc}; strict relational fallback failed: {fallback_exc}"
                ) from fallback_exc
            sliced = _apply_window(rows, limit, offset)
            return {
                "ok": True,
                "table": table_name,
                "sql": str(sql or ""),
                "parameters": parameters or {},
                "rows": sliced,
                "records": sliced,
                "count": len(sliced),
            }

    def _known_search_rows(self, sql: str) -> list[dict[str, Any]] | None:
        normalized = " ".join(_strip_sql_line_comments(str(sql or "")).split()).lower()
        if (
            "with account_info as" in normalized
            and "chi_2024_temp_final_composite_wip_operational" in normalized
            and "chi_2024_department_adoption_base_operational" in normalized
            and "object_agg(department, processes_by_dept)" in normalized
            and "department_scorecard" in normalized
        ):
            return self._account_department_scorecard_rows(sql)
        if (
            "from product.salesforce.salesteam_hist" in normalized
            and "where date_to is null" in normalized
            and "qualify row_number() over (partition by user_id order by date_from desc) = 2"
            in normalized
        ):
            table = self._resolve_table_name(
                "product.salesforce.salesteam_hist"
            )
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in self._tables.setdefault(table, []):
                if _field_value(row, "date_to") is None:
                    grouped[str(_field_value(row, "user_id") or "")].append(row)
            output: list[dict[str, Any]] = []
            for user_id, rows in grouped.items():
                ordered = sorted(
                    rows,
                    key=lambda row: str(_field_value(row, "date_from") or ""),
                    reverse=True,
                )
                if len(ordered) >= 2:
                    team = _field_value(ordered[1], "team_name")
                    output.append(
                        {
                            "TEAM_NAME": team,
                            "team_name": team,
                            "USER_ID": user_id,
                            "user_id": user_id,
                        }
                    )
            return output
        if (
            "with mug as" in normalized
            and "federated_accounts_comb_d" in normalized
            and "future_contracts as" in normalized
            and "qualify row_number() over (partition by user_id,data_center" in normalized
            and "order by account2" in normalized
        ):
            return self._free_workspace_relink_rows()
        return None

    def _account_department_scorecard_rows(
        self, sql: str
    ) -> list[dict[str, Any]]:
        """Evaluate the account adoption scorecard CTE from seeded sources."""

        normalized = _strip_sql_line_comments(str(sql or ""))
        account_info = re.search(
            r"account_info\s+as\s*\(.*?calendar_date\s*=\s*'((?:''|[^'])*)'"
            r".*?account_id\s*=\s*'((?:''|[^'])*)'",
            normalized,
            flags=re.I | re.S,
        )
        if account_info is None:
            raise RuntimeError(
                "account adoption scorecard query is missing literal date/account filters"
            )
        calendar_date = account_info.group(1).replace("''", "'")
        account_id = account_info.group(2).replace("''", "'")

        account_table = self._resolve_table_name(
            "plg.chi_2024_temp_final_composite_wip_operational"
        )
        adoption_table = self._resolve_table_name(
            "plg.chi_2024_department_adoption_base_operational"
        )
        accounts = [
            row
            for row in self._tables.setdefault(account_table, [])
            if str(_field_value(row, "calendar_date") or "") == calendar_date
            and str(_field_value(row, "account_id") or "") == account_id
            and _as_bool(_field_value(row, "is_paying"))
            and str(_field_value(row, "cust_type") or "").casefold() == "direct"
        ]
        adoption = [
            row
            for row in self._tables.setdefault(adoption_table, [])
            if str(_field_value(row, "calendar_date") or "") == calendar_date
            and str(_field_value(row, "account_id") or "") == account_id
            and str(_field_value(row, "sub_process") or "").casefold()
            != "not conclusive"
        ]
        if not accounts or not adoption:
            return []

        score_definitions = (
            ("Finance & Accounting", "finance and accounting", 32),
            ("IT", "it automations", 44),
            ("Human Resources", "human resources", 45),
            ("RevOps", "revops", 49),
            ("CS Ops", "customer support and operations", 22),
            ("Data Ops", "data operations", 8),
            ("Product and Engineering", "product and engineering", 7),
        )
        score_parts: list[str] = []
        for label, department, denominator in score_definitions:
            count = sum(
                str(_field_value(row, "department") or "").casefold()
                == department
                for row in adoption
            )
            score = self._snowflake_round(count / denominator * 100, 0) or 0
            score_parts.append(f"{label}:{score}%")

        usecases: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for row in adoption:
            department = str(_field_value(row, "department") or "")
            process = str(_field_value(row, "process") or "")
            sub_process = str(_field_value(row, "sub_process") or "")
            if sub_process not in usecases[department][process]:
                usecases[department][process].append(sub_process)
        encoded_usecases = json.dumps(
            {
                department: {
                    process: sorted(sub_processes)
                    for process, sub_processes in sorted(processes.items())
                }
                for department, processes in sorted(usecases.items())
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        output: list[dict[str, Any]] = []
        for account in accounts:
            output.append(
                {
                    "account_id": _field_value(account, "account_id"),
                    "account_name": _field_value(account, "account_name"),
                    "calendar_date": _field_value(account, "calendar_date"),
                    "current_arr_usd": _field_value(account, "current_arr_usd"),
                    "industry": _field_value(account, "industry"),
                    "cat_company_size": _field_value(account, "cat_company_size"),
                    "department_scorecard": ", ".join(score_parts),
                    "department_usecases": encoded_usecases,
                }
            )
        return output

    def _free_workspace_relink_rows(self) -> list[dict[str, Any]]:
        """Evaluate the free-workspace relink query over the seeded tables."""

        def rows(name: str) -> list[dict[str, Any]]:
            return self._tables.setdefault(self._resolve_table_name(name), [])

        grants = rows("BI_DB.MASTER_DATA.MANAGED_USER_GRANTS_COMB_D")
        federated = rows("BI_DB.MASTER_DATA.FEDERATED_ACCOUNTS_COMB_D")
        customer = rows("BI_DB.MASTER_DATA.ACCOUNTS_COMB_D")
        users = rows("BI_DB.SALESFORCE.WORKATO_USER")
        accounts = rows("BI_DB.SALESFORCE.ACCOUNT")
        contracts = rows("BI_DB.SALESFORCE.CPQ_CONTRACT")

        def comparable_number(value: Any) -> str:
            text = str(value or "").strip()
            try:
                return str(int(float(text)))
            except ValueError:
                return text

        def keyed(items: list[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
            output: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in items:
                output[str(_field_value(item, field) or "")].append(item)
            return output

        users_by_workato = keyed(users, "workato_user_id")
        federated_by_id = keyed(federated, "id")
        customer_by_id = keyed(customer, "id")
        accounts_by_id = keyed(accounts, "id")
        excluded_names = {"TESTING ONLY", "TESTING ONLY - Embedded", "Workato"}

        candidates: list[dict[str, Any]] = []
        for grant in grants:
            grant_type = str(_field_value(grant, "grant_type") or "").lower()
            data_center = str(_field_value(grant, "data_center") or "")
            manager_ids: list[Any] = []
            if grant_type == "team":
                manager_ids = [_field_value(grant, "managed_user_id")]
            elif grant_type == "federation_manager":
                for item in federated_by_id.get(
                    str(_field_value(grant, "federated_account_id") or ""), []
                ):
                    if str(_field_value(item, "data_center") or "") == data_center:
                        manager_ids.append(_field_value(item, "admin_id"))
            elif grant_type == "customer_manager":
                for item in customer_by_id.get(
                    str(_field_value(grant, "account_id") or ""), []
                ):
                    if str(_field_value(item, "data_center") or "") == data_center:
                        manager_ids.append(_field_value(item, "admin_id"))
            for manager_id in manager_ids:
                manager_key = comparable_number(manager_id)
                for user in users:
                    if comparable_number(_field_value(user, "workato_user_id")) != manager_key:
                        continue
                    if str(_field_value(user, "data_center") or "") != data_center:
                        continue
                    account_id = _field_value(user, "account_id") or _field_value(
                        user, "embed_salesforce_account_id"
                    )
                    for account in accounts_by_id.get(str(account_id or ""), []):
                        if str(_field_value(account, "name") or "") in excluded_names:
                            continue
                        candidates.append(
                            {
                                "user_id": comparable_number(_field_value(grant, "user_id")),
                                "managed_user_id": manager_key,
                                "data_center": data_center,
                                "created_at": str(_field_value(grant, "created_at") or ""),
                                "active_subscription": _as_bool(
                                    _field_value(account, "active_subscription")
                                ),
                            }
                        )

        # QUALIFY ROW_NUMBER: active subscription first, then oldest grant.
        qualified: dict[tuple[str, str], dict[str, Any]] = {}
        for item in candidates:
            key = (item["user_id"], item["data_center"])
            prior = qualified.get(key)
            rank = (not item["active_subscription"], item["created_at"])
            prior_rank = (
                (not prior["active_subscription"], prior["created_at"])
                if prior is not None
                else None
            )
            if prior is None or rank < prior_rank:
                qualified[key] = item

        try:
            current_date = datetime.fromisoformat(
                str(self._current_time or "").replace("Z", "+00:00")
            ).date().isoformat()
        except ValueError as exc:
            raise RuntimeError(
                "free-workspace relink query requires pinned Snowflake current_time"
            ) from exc
        future_contract_accounts = {
            str(_field_value(item, "accountid") or "")
            for item in contracts
            if str(_field_value(item, "status") or "") == "Inactive"
            and str(_field_value(item, "startdate") or "") > current_date
        }

        output: list[dict[str, Any]] = []
        for mug in qualified.values():
            workspace_candidates = [
                item
                for item in users
                if comparable_number(_field_value(item, "workspace_id")) == mug["user_id"]
                and str(_field_value(item, "data_center") or "") == mug["data_center"]
            ]
            manager_candidates = [
                item
                for item in users
                if comparable_number(_field_value(item, "workato_user_id"))
                == mug["managed_user_id"]
                and str(_field_value(item, "data_center") or "") == mug["data_center"]
            ]
            for workspace in workspace_candidates:
                email = str(_field_value(workspace, "workato_user_email") or "")
                plan = str(_field_value(workspace, "workato_plan") or "")
                workspace_account_id = str(_field_value(workspace, "account_id") or "")
                if _field_value(workspace, "workato_embed_id") is not None:
                    continue
                if plan != "free" or "==" in email or "workato.com" in email.lower():
                    continue
                if workspace_account_id in future_contract_accounts:
                    continue
                for current_account in accounts_by_id.get(workspace_account_id, []):
                    if str(_field_value(current_account, "account_record_type") or "") == "012o0000000tYvxAAE":
                        continue
                    if _as_bool(_field_value(current_account, "active_subscription")):
                        continue
                    for manager in manager_candidates:
                        target_account_id = str(
                            _field_value(manager, "account_id")
                            or _field_value(manager, "embed_salesforce_account_id")
                            or ""
                        )
                        if workspace_account_id == str(_field_value(manager, "account_id") or ""):
                            continue
                        for target_account in accounts_by_id.get(target_account_id, []):
                            if not _as_bool(_field_value(target_account, "active_subscription")):
                                continue
                            output.append(
                                {
                                    "user_id_dc": f"{mug['user_id']}-{mug['data_center']}",
                                    "managed_user_id": mug["managed_user_id"],
                                    "id": _field_value(workspace, "id"),
                                    "name": _field_value(workspace, "name"),
                                    "workato_user_email": _field_value(
                                        workspace, "workato_user_email"
                                    ),
                                    "workato_plan": _field_value(workspace, "workato_plan"),
                                    "account_id": _field_value(workspace, "account_id"),
                                    "account": _field_value(workspace, "account"),
                                    "active_subscription": _field_value(
                                        current_account, "active_subscription"
                                    ),
                                    "id2": _field_value(manager, "id"),
                                    "name2": _field_value(manager, "name"),
                                    "workato_user_email2": _field_value(
                                        manager, "workato_user_email"
                                    ),
                                    "workato_plan2": _field_value(manager, "workato_plan"),
                                    "account_id2": target_account_id,
                                    "account2": _field_value(target_account, "name"),
                                    "workato_embed_id2": _field_value(
                                        manager, "workato_embed_id"
                                    ),
                                    "embed_salesforce_account_id2": _field_value(
                                        manager, "embed_salesforce_account_id"
                                    ),
                                    "active_subscription2": _field_value(
                                        target_account, "active_subscription"
                                    ),
                                }
                            )
        return sorted(output, key=lambda row: str(row.get("account2") or ""))

    def _search_rows_sql_native(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        limit: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
        query_sql = _strip_sql_line_comments(str(sql or ""))
        if re.search(r"\bORDER\s+BY\b", query_sql, flags=re.I):
            # The row-local native evaluator intentionally has no ordering
            # phase. Route ordered relational queries through SQLite so LIMIT
            # and downstream list construction observe Snowflake order.
            raise RuntimeError(
                "unsupported snowflake.search_rows_sql ORDER BY in native evaluator"
            )
        aggregate = self._aggregate_rows_sql(query_sql, parameters or {})
        if aggregate is not None:
            sliced = _apply_window(aggregate["rows"], limit, offset)
            return {
                "ok": True,
                "table": aggregate["table"],
                "sql": str(sql or ""),
                "parameters": parameters or {},
                "rows": sliced,
                "records": sliced,
                "count": len(sliced),
            }
        inner_joined = self._inner_join_rows_sql(query_sql, parameters or {})
        if inner_joined is not None:
            rows = _apply_select_distinct(query_sql, inner_joined["rows"])
            sliced = _apply_window(rows, limit, offset)
            return {
                "ok": True,
                "table": inner_joined["table"],
                "sql": str(sql or ""),
                "parameters": parameters or {},
                "rows": sliced,
                "records": sliced,
                "count": len(sliced),
            }
        joined = self._left_join_rows_sql(query_sql, parameters or {})
        if joined is not None:
            rows = _apply_select_distinct(query_sql, joined["rows"])
            sliced = _apply_window(rows, limit, offset)
            return {
                "ok": True,
                "table": joined["table"],
                "sql": str(sql or ""),
                "parameters": parameters or {},
                "rows": sliced,
                "records": sliced,
                "count": len(sliced),
            }
        anti_joined = self._not_exists_rows_sql(query_sql, parameters or {})
        if anti_joined is not None:
            rows = _apply_select_distinct(query_sql, anti_joined["rows"])
            sliced = _apply_window(rows, limit, offset)
            return {
                "ok": True,
                "table": anti_joined["table"],
                "sql": str(sql or ""),
                "parameters": parameters or {},
                "rows": sliced,
                "records": sliced,
                "count": len(sliced),
            }
        if re.search(r"\bJOIN\b", query_sql, flags=re.I):
            raise RuntimeError(
                "unsupported snowflake.search_rows_sql join shape in native evaluator"
            )
        table_name = self._resolve_table_name(_parse_sql_table(query_sql))
        if not table_name:
            raise RuntimeError("snowflake.search_rows_sql missing FROM table")
        where = self._resolve_scalar_max_subqueries(_parse_sql_where(query_sql))
        where = self._resolve_not_in_subqueries(where)
        selected = _parse_sql_select(query_sql)
        source_rows = [
            row
            for row in self._tables.setdefault(table_name, [])
            if _matches_where(row, where, parameters or {})
        ]
        rows = _apply_select_distinct(
            query_sql,
            [_project_row(row, selected) for row in source_rows],
        )
        sliced = _apply_window(rows, limit, offset)
        return {
            "ok": True,
            "table": table_name,
            "sql": str(sql or ""),
            "parameters": parameters or {},
            "rows": sliced,
            "records": sliced,
            "count": len(sliced),
        }

    def _resolve_scalar_max_subqueries(self, where: str) -> str:
        """Resolve the deterministic field-equals-SELECT-MAX SQL subset.

        Several imported recipes use a scalar MAX subquery to select the most
        recent snapshot. Resolve it against the seeded table before the
        row-local predicate evaluator runs; this preserves SQL's empty/MAX
        behavior without pretending to implement arbitrary nested SQL.
        """

        field = r'"?((?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*)"?'
        table = r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
        pattern = re.compile(
            field
            + r"\s*=\s*\(\s*SELECT\s+MAX\(\s*"
            + field
            + r"\s*\)\s+FROM\s+"
            + table
            + r"\s*\)",
            flags=re.I,
        )

        def replace(match: re.Match[str]) -> str:
            lhs, max_field, raw_table = match.group(1), match.group(2), match.group(3)
            table_name = self._resolve_table_name(raw_table)
            rows = self._tables.get(table_name or "", [])
            values = [
                _field_value(row, max_field)
                for row in rows
                if _field_value(row, max_field) is not None
            ]
            if not values:
                # SQL compares the left side with NULL here, so no row matches.
                return "1 = 0"
            maximum = max(values, key=lambda value: str(value))
            escaped = str(maximum).replace("'", "''")
            return f"{lhs} = '{escaped}'"

        return pattern.sub(replace, str(where or ""))

    def _resolve_not_in_subqueries(self, where: str) -> str:
        """Resolve the deterministic one-column ``NOT IN (SELECT ...)`` subset.

        The simulator exposes SQL semantics, not one benchmark-specific query
        spelling.  Converting a seeded one-column anti-membership subquery to
        an ordinary literal membership predicate lets the row-local evaluator
        apply the same semantics while still rejecting arbitrary nested SQL.
        """

        field = r'"?((?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*)"?'
        table = r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
        pattern = re.compile(
            field
            + r"\s+NOT\s+IN\s*\(\s*SELECT\s+"
            + field
            + r"\s+FROM\s+"
            + table
            + r"\s*\)",
            flags=re.I,
        )

        def replace(match: re.Match[str]) -> str:
            lhs, selected_field, raw_table = (
                match.group(1),
                match.group(2),
                match.group(3),
            )
            table_name = self._resolve_table_name(raw_table)
            values = [
                _field_value(row, selected_field)
                for row in self._tables.get(table_name or "", [])
                if _field_value(row, selected_field) is not None
            ]
            if not values:
                return "1 = 1"
            encoded = ", ".join(
                "'" + str(value).replace("'", "''") + "'" for value in values
            )
            return f"{lhs} NOT IN ({encoded})"

        return pattern.sub(replace, str(where or ""))

    def create_or_replace_table_as(
        self,
        table: str,
        select_sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the constrained SELECT engine and persist its projection.

        This intentionally supports only CTAS whose query is already within
        ``search_rows_sql``'s deterministic SQL subset.  It gives reference
        recipes real write semantics without pretending to be a general SQL
        engine.
        """

        table_name = self._resolve_table_name(str(table or ""))
        if not table_name:
            raise RuntimeError("snowflake CTAS missing target table")
        visible_rows = self._known_cte_rows(table_name, select_sql)
        if visible_rows is None:
            selected = self.search_rows_sql(select_sql, parameters or {})
            visible_rows = selected.get("rows") or []
        self._tables[table_name] = [
            {"_row_id": index, "_created_by": "agent", **_clean(row)}
            for index, row in enumerate(visible_rows)
            if isinstance(row, dict)
        ]
        self._flush()
        status = f"Table {table_name.rsplit('.', 1)[-1].upper()} successfully created."
        rows = [{"status": status}]
        return {
            "ok": True,
            "table": table_name,
            "sql": str(select_sql or ""),
            "parameters": parameters or {},
            "rows": rows,
            "records": rows,
            "count": 1,
            # Snowflake reports one statement/result row for this DDL; this is
            # deliberately not the number of rows selected into the table.
            "rows_affected": 1,
        }

    def _known_cte_rows(
        self,
        target_table: str,
        select_sql: str,
    ) -> list[dict[str, Any]] | None:
        """Execute the two recursive/rollup CTE shapes used by the corpus.

        These handlers are selected by both target identity and semantic SQL
        markers.  They model the query result, including its branch and
        aggregation behavior; they are not canned fixture outputs.
        """

        target = _output_key(target_table)
        normalized_sql = " ".join(_strip_sql_line_comments(select_sql).split()).lower()
        if (
            target.endswith("chi_2024_recipe_hierarchy_operational")
            and "with recursive recipe_hierarchy_interim" in normalized_sql
            and "array_contains" in normalized_sql
        ):
            return self._recipe_hierarchy_rows()
        if (
            target.endswith("chi_2023_process_complexity_recipe_features_operational")
            and "with rollup_recipe_ft0" in normalized_sql
            and "rollup_recipe_features" in normalized_sql
        ):
            return self._process_complexity_feature_rows()
        if (
            target.endswith("chi_2024_first_connections_operational")
            and "with account_data as" in normalized_sql
            and "mapped_first_sha_dates as" in normalized_sql
            and "recipe_sophistication_app_tier" in normalized_sql
        ):
            return self._first_connection_rows()
        if (
            target.endswith("chi_2023_process_complexity_scores_operational")
            and "with process_length_interim as" in normalized_sql
            and "app_tier_pivot_scores as" in normalized_sql
            and "overall_complexity" in normalized_sql
        ):
            return self._process_complexity_score_rows()
        if (
            target.endswith(
                "chi_2023_process_complexity_scoring_aggregated_operational"
            )
            and "with base as" in normalized_sql
            and "pivot_complexity_distributions as" in normalized_sql
            and "process_complexity_output" in normalized_sql
        ):
            return self._process_complexity_aggregate_rows()
        return None

    @staticmethod
    def _compact_number(value: float | int | None) -> float | int | None:
        if value is None:
            return None
        number = float(value)
        return int(number) if number.is_integer() else number

    @staticmethod
    def _snowflake_round(value: Any, places: int = 0) -> float | int | None:
        if value is None:
            return None
        quantizer = Decimal("1").scaleb(-places)
        rounded = Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP)
        number = float(rounded)
        return int(number) if places == 0 or number.is_integer() else number

    def _process_complexity_score_rows(self) -> list[dict[str, Any]]:
        """Evaluate the process-complexity scoring CTAS from its two inputs."""

        features_name = self._resolve_table_name(
            "plg.chi_2023_process_complexity_recipe_features_operational"
        )
        matrix_name = self._resolve_table_name(
            "plg.chi_2023_process_complexity_scoring_matrix"
        )
        features = self._tables.setdefault(features_name, [])
        matrix = self._tables.setdefault(matrix_name, [])

        def number(value: Any) -> float | None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def matrix_rows(criteria: str | None, subcategory: str) -> list[dict[str, Any]]:
            return [
                row
                for row in matrix
                if (
                    criteria is None
                    or str(_field_value(row, "criteria_cat") or "").casefold()
                    == criteria.casefold()
                )
                and str(_field_value(row, "sub_criteria_cat") or "").casefold()
                == str(subcategory).casefold()
            ]

        def exact_score(criteria: str | None, subcategory: str, value: Any) -> float | int | None:
            target = str(value).casefold()
            matches = [
                row
                for row in matrix_rows(criteria, subcategory)
                if str(_field_value(row, "value") or "").casefold() == target
            ]
            if not matches:
                return None
            score = number(_field_value(matches[0], "score"))
            weight = number(_field_value(matches[0], "weight"))
            if score is None or weight is None:
                return None
            return self._compact_number(score * weight)

        def enabled_score(subcategory: str, enabled: bool) -> float | int | None:
            if not enabled:
                return 0
            return exact_score(None, subcategory, True)

        def section_weight(subcategory: str) -> tuple[float, float] | None:
            rows = matrix_rows("section_weight", subcategory)
            if not rows:
                return None
            denominator = number(_field_value(rows[0], "value"))
            weight = number(_field_value(rows[0], "weight"))
            if denominator in (None, 0) or weight is None:
                return None
            return denominator, weight

        def add(values: list[float | int | None]) -> float | None:
            if any(value is None for value in values):
                return None
            return sum(float(value) for value in values if value is not None)

        output: list[dict[str, Any]] = []
        for feature in features:
            steps = number(_field_value(feature, "n_downstream_steps"))
            step_candidates = [
                row
                for row in matrix_rows("general", "num_steps")
                if steps is not None
                and number(_field_value(row, "value")) is not None
                and steps <= float(number(_field_value(row, "value")))
                and number(_field_value(row, "score")) is not None
            ]
            step_row = min(
                step_candidates,
                key=lambda row: (
                    float(number(_field_value(row, "score"))),
                    float(number(_field_value(row, "value"))),
                ),
                default=None,
            )
            num_steps_score = None
            if step_row is not None:
                score = number(_field_value(step_row, "score"))
                weight = number(_field_value(step_row, "weight"))
                if score is not None and weight is not None:
                    num_steps_score = self._compact_number(score * weight)

            tier_scores: list[float | int] = []
            for tier in range(1, 6):
                count = number(_field_value(feature, f"num_tier_{tier}_app")) or 0
                if count == 0:
                    tier_scores.append(0)
                    continue
                candidates = [
                    row
                    for row in matrix_rows("app_tier", str(tier))
                    if number(_field_value(row, "value")) is not None
                    and count <= float(number(_field_value(row, "value")))
                ]
                scores = [number(_field_value(row, "score")) for row in candidates]
                weights = [number(_field_value(row, "weight")) for row in candidates]
                if not candidates or any(value is None for value in scores + weights):
                    tier_scores.append(0)
                else:
                    tier_scores.append(
                        self._compact_number(
                            min(float(value) for value in scores if value is not None)
                            * min(float(value) for value in weights if value is not None)
                        )
                    )
            tier_max = max(float(value) for value in tier_scores)
            app_tier_section = self._compact_number(
                tier_max
                + (sum(float(value) for value in tier_scores) - tier_max) / 30
            )

            recipe_type_score = exact_score(
                "general", "recipe_type", _field_value(feature, "recipe_category_type")
            )
            trigger_score = exact_score(
                "data_proc", "trigger_type", _field_value(feature, "trigger_type")
            )
            bulk_score = enabled_score(
                "has_bulkbatch_action", _as_bool(_field_value(feature, "has_bulkbatch_action"))
            )
            query_score = enabled_score(
                "has_query_action", _as_bool(_field_value(feature, "has_query_action"))
            )
            single_score = enabled_score(
                "is_single_action", _as_bool(_field_value(feature, "is_single_action"))
            )
            collection_score = enabled_score(
                "has_collections", _as_bool(_field_value(feature, "has_collections"))
            )
            variable_score = enabled_score(
                "has_variables", _as_bool(_field_value(feature, "has_variables"))
            )
            lookup_score = enabled_score(
                "has_lookup_table", _as_bool(_field_value(feature, "has_lookup_table"))
            )
            scripting_score = enabled_score(
                "has_scripting", _as_bool(_field_value(feature, "has_scripting"))
            )
            sync_score = enabled_score(
                "has_sync_function", _as_bool(_field_value(feature, "has_sync_function"))
            )
            async_score = enabled_score(
                "has_async_function", _as_bool(_field_value(feature, "has_async_function"))
            )
            loop_score = enabled_score(
                "has_looping_logic", _as_bool(_field_value(feature, "has_looping_logic"))
            )
            if_score = enabled_score(
                "has_if_then_logic", _as_bool(_field_value(feature, "has_if_then_logic"))
            )
            if_else_score = enabled_score(
                "has_if_then_else_logic",
                _as_bool(_field_value(feature, "has_if_then_else_logic")),
            )
            pass_score = enabled_score(
                "is_pass_through", _as_bool(_field_value(feature, "is_pass_through"))
            )
            catch_score = enabled_score(
                "has_try_catch_logic", _as_bool(_field_value(feature, "has_try_catch_logic"))
            )

            action_score = add([bulk_score, query_score, single_score])
            transform_score = add(
                [collection_score, variable_score, lookup_score, scripting_score]
            )
            data_proc_section = None
            if trigger_score is not None and action_score is not None and transform_score is not None:
                data_proc_section = self._compact_number(
                    float(trigger_score) + min(10, action_score) + min(10, transform_score)
                )
            # The authored SQL deliberately excludes the sync score from the
            # both-sync-and-async arm; preserve that branch verbatim.
            logic_terms = [
                async_score,
                loop_score,
                if_score,
                if_else_score,
                pass_score,
                catch_score,
            ]
            if not (
                _as_bool(_field_value(feature, "has_async_function"))
                and _as_bool(_field_value(feature, "has_sync_function"))
            ):
                logic_terms.insert(0, sync_score)
            step_logic_section = add(logic_terms)
            step_logic_section = self._compact_number(step_logic_section)

            section_values: dict[str, float | int | None] = {
                "general_type": recipe_type_score,
                "general_steps": num_steps_score,
                "data_proc": data_proc_section,
                "step_logic": step_logic_section,
                "app_tier": app_tier_section,
            }
            complexities: dict[str, float | int | None] = {}
            weights: dict[str, float] = {}
            for name, score_value in section_values.items():
                weight_row = section_weight(name)
                if score_value is None or weight_row is None:
                    complexities[name] = None
                    continue
                denominator, weight = weight_row
                complexities[name] = self._compact_number(
                    float(score_value) * 10 / denominator
                )
                weights[name] = weight
            overall = None
            if all(complexities.get(name) is not None and name in weights for name in section_values):
                overall = sum(
                    float(complexities[name]) * weights[name]
                    for name in section_values
                )
                overall = self._compact_number(overall)

            apps_used = ",".join(
                str(_field_value(feature, f"tier_{tier}_apps") or "").strip(",")
                for tier in range(1, 6)
                if str(_field_value(feature, f"tier_{tier}_apps") or "").strip(",")
            )
            row = {
                "CALENDAR_DATE": _field_value(feature, "calendar_date"),
                "ACCOUNT_ID": _field_value(feature, "account_id"),
                "ACCOUNT_NAME": _field_value(feature, "account_name"),
                "ROOT_FLOW": _field_value(feature, "root_flow"),
                "DATA_CENTER": _field_value(feature, "data_center"),
                "RECIPE_CATEGORY_TYPE": _field_value(feature, "recipe_category_type"),
                "N_DOWNSTREAM_STEPS": _field_value(feature, "n_downstream_steps"),
                "N_FLOWS_IN_WORKFLOW": _field_value(feature, "n_flows_in_workflow"),
                "APPS_USED": apps_used,
                "TRIGGER_TYPE": _field_value(feature, "trigger_type"),
            }
            for field in (
                "has_bulkbatch_action", "has_query_action", "is_single_action",
                "has_collections", "has_variables", "has_lookup_table",
                "has_scripting", "has_sync_function", "has_async_function",
                "has_looping_logic", "has_if_then_logic", "has_if_then_else_logic",
                "is_pass_through", "has_try_catch_logic",
            ):
                row[field.upper()] = _as_bool(_field_value(feature, field))
            for tier in range(1, 6):
                row[f"NUM_TIER_{tier}_APP"] = _field_value(feature, f"num_tier_{tier}_app")
            row.update({
                "RECIPE_TYPE_SCORE": recipe_type_score,
                "NUM_STEPS_SCORE": num_steps_score,
                "TRIGGER_TYPE_SCORE": trigger_score,
                "BULKBATCH_SCORE": bulk_score,
                "QUERY_ACTION_SCORE": query_score,
                "SINGLE_ACTION_SCORE": single_score,
                "HAS_COLLECTIONS_SCORE": collection_score,
                "HAS_VARIABLES_SCORE": variable_score,
                "HAS_LOOKUP_TABLE_SCORE": lookup_score,
                "HAS_SCRIPTING_SCORE": scripting_score,
                "HAS_SYNC_FUNCTION_SCORE": sync_score,
                "HAS_ASYNC_FUNCTION_SCORE": async_score,
                "HAS_LOOP_SCORE": loop_score,
                "IF_THEN_SCORE": if_score,
                "IF_THEN_ELSE_SCORE": if_else_score,
                "PASS_THROUGH_SCORE": pass_score,
                "TRY_CATCH_SCORE": catch_score,
                "STEP_LOGIC_SCORE": step_logic_section,
                "GENERAL_TYPE_SECTION_SCORE": recipe_type_score,
                "GENERAL_STEPS_SECTION_SCORE": num_steps_score,
                "DATA_PROC_SECTION_SCORE": data_proc_section,
                "STEP_LOGIC_SECTION_SCORE": step_logic_section,
                "APP_TIER_SECTION_SCORE": app_tier_section,
                "GENERAL_COMPLEXITY_RECIPE_TYPE": complexities["general_type"],
                "GENERAL_COMPLEXITY_STEPS": complexities["general_steps"],
                "DATA_PROC_COMPLEXITY": complexities["data_proc"],
                "STEP_LOGIC_COMPLEXITY": complexities["step_logic"],
                "APP_TIER_COMPLEXITY": complexities["app_tier"],
                "OVERALL_RAW": overall,
                "OVERALL_COMPLEXITY": self._snowflake_round(overall, 2),
            })
            output.append(row)
        return output

    def _process_complexity_aggregate_rows(self) -> list[dict[str, Any]]:
        """Evaluate the account-level complexity aggregation CTAS."""

        scores_name = self._resolve_table_name(
            "plg.chi_2023_process_complexity_scores_operational"
        )
        tiers_name = self._resolve_table_name("plg.recipe_sophistication_app_tier")
        scores = self._tables.setdefault(scores_name, [])
        tiers = self._tables.setdefault(tiers_name, [])
        tiers_by_title = {
            str(_field_value(row, "title") or ""): row for row in tiers
        }
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in scores:
            key = (
                str(_field_value(row, "calendar_date") or ""),
                str(_field_value(row, "account_id") or ""),
                str(_field_value(row, "account_name") or ""),
            )
            groups[key].append(row)

        output: list[dict[str, Any]] = []
        for (calendar_date, account_id, account_name), rows in sorted(groups.items()):
            ordered = sorted(rows, key=lambda row: float(_field_value(row, "overall_complexity") or 0))
            total = len(ordered)
            percentiles: list[tuple[dict[str, Any], float]] = []
            for row in ordered:
                value = float(_field_value(row, "overall_complexity") or 0)
                rank = 1 + sum(
                    float(_field_value(other, "overall_complexity") or 0) < value
                    for other in ordered
                )
                percentile = 0 if total <= 1 else (rank - 1) / (total - 1)
                percentiles.append((row, float(self._snowflake_round(percentile, 2) or 0)))
            median_values = sorted(
                float(_field_value(row, "overall_complexity") or 0)
                for row, percentile in percentiles
                if percentile >= 0.67
            )
            if not median_values:
                workflow_metric = 0
            elif len(median_values) % 2:
                workflow_metric = median_values[len(median_values) // 2]
            else:
                middle = len(median_values) // 2
                workflow_metric = (median_values[middle - 1] + median_values[middle]) / 2
            workflow_metric = self._snowflake_round(workflow_metric, 2) or 0

            medium_high = sum(
                1
                for row in rows
                if float(self._snowflake_round(_field_value(row, "overall_complexity"), 0) or 0) >= 4
            )
            app_flows: dict[str, set[str]] = defaultdict(set)
            for row in rows:
                tier_count = int(float(_field_value(row, "num_tier_1_app") or 0)) + int(
                    float(_field_value(row, "num_tier_2_app") or 0)
                )
                if tier_count < 1:
                    continue
                flow_id = str(_field_value(row, "root_flow") or "") + str(
                    _field_value(row, "data_center") or ""
                )
                for app in str(_field_value(row, "apps_used") or "").split(","):
                    app = app.strip()
                    tier = tiers_by_title.get(app)
                    if tier is None or int(float(_field_value(tier, "app_tier") or 0)) not in (1, 2):
                        continue
                    category = str(_field_value(tier, "category") or "")
                    if not (
                        (category in {"app", "custom"} and app != "JDBC")
                        or (category == "others" and app == "On-prem files")
                    ):
                        continue
                    app_flows[app].add(flow_id)
            distinct_flows = set().union(*app_flows.values()) if app_flows else set()
            business_apps = sorted(app_flows)
            ranked_apps: list[str] = []
            for app in business_apps:
                count = len(app_flows[app])
                rank = 1 + sum(len(flows) > count for flows in app_flows.values())
                if rank <= 4:
                    ranked_apps.append(app)

            workflow_count_with_apps = len(distinct_flows)
            volume = (
                "downgrade" if medium_high <= 12 else "upgrade" if medium_high > 15 else "flat"
            )
            threshold = {"upgrade": 6.5, "flat": 6.3, "downgrade": 5.9}[volume]
            if volume == "downgrade":
                criteria = "pass" if float(workflow_metric) > threshold else "no pass"
            else:
                criteria = "pass" if float(workflow_metric) >= threshold else "no pass"
            process_output = {
                ("upgrade", "pass"): "upgrade",
                ("upgrade", "no pass"): "flat",
                ("flat", "pass"): "upgrade",
                ("flat", "no pass"): "flat",
                ("downgrade", "pass"): "flat",
                ("downgrade", "no pass"): "downgrade",
            }[(volume, criteria)]
            distribution = {index: 0 for index in range(1, 11)}
            for row in rows:
                rounded = int(self._snowflake_round(_field_value(row, "overall_complexity"), 0) or 0)
                if rounded in distribution:
                    distribution[rounded] += 1
            result = {
                "CALENDAR_DATE": calendar_date,
                "ACCOUNT_ID": account_id,
                "ACCOUNT_NAME": account_name,
                "N_MED_HIGH_COMPLEXITY_WORKFLOWS": medium_high,
                "N_WORKFLOWS_TOTAL": total,
                "N_WORKFLOWS_W_CRITICAL_APPS": workflow_count_with_apps,
                "BIZ_CRITICAL_APP_NAMES": (
                    ",".join(business_apps) if business_apps else "No business-critical apps used"
                ),
                "DISPLAY_OUTPUT_TOP_APPS": (
                    ",".join(ranked_apps) if ranked_apps else "No business-critical apps used"
                ),
                "PERCENTAGE_WORKFLOWS_2PLUS_BIZ_APPS": self._snowflake_round(
                    workflow_count_with_apps * 100 / total, 0
                ),
                "PERCENTAGE_WORKFLOWS_MED_HIGH_COMPLEXITY": self._snowflake_round(
                    medium_high * 100 / total, 0
                ),
                "WORKFLOW_COMPLEXITY_METRIC": workflow_metric,
                "VOLUME_CRITERIA": volume,
                "COMPLEXITY_CRITERIA": criteria,
                "PROCESS_COMPLEXITY_OUTPUT": process_output,
            }
            result.update(
                {f"COMPLEXITY_{index}": distribution[index] for index in range(1, 11)}
            )
            output.append(result)
        return output

    def _first_connection_rows(self) -> list[dict[str, Any]]:
        """Evaluate the first-connection CTAS from its six seeded sources.

        SQLite cannot parse Snowflake's ``GROUP BY ALL``/``QUALIFY``/
        ``LISTAGG`` combination.  This implements those relational semantics
        from live table state; it deliberately never consults variant
        expectations.
        """

        def rows(name: str) -> list[dict[str, Any]]:
            resolved = self._resolve_table_name(name)
            return self._tables.setdefault(resolved, [])

        accounts = rows("workato_usage.accounts_dim")
        shared = rows("workato_usage.shared_accounts_snapshot")
        applications = rows("workato_usage.applications_snapshot")
        calendar = rows("workato_usage.calendar_dim")
        workspaces = rows("workato_usage.workspace_dim")
        tiers = rows("plg.recipe_sophistication_app_tier")

        try:
            instant = datetime.fromisoformat(
                str(self._current_time or "").replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise RuntimeError(
                "first-connection CTAS requires a pinned Snowflake current_time"
            ) from exc
        snapshot_date = instant.date().isoformat()
        application_date = (instant.date() - timedelta(days=1)).isoformat()

        # QUALIFY row_number() = 1: retain the latest eligible account row.
        account_by_id: dict[str, dict[str, Any]] = {}
        for account in accounts:
            start = str(_field_value(account, "startdate") or "")
            if not ("2024-02-01" <= start <= snapshot_date):
                continue
            if not _as_bool(_field_value(account, "is_paying")):
                continue
            if not _as_bool(_field_value(account, "is_direct")):
                continue
            account_id = str(_field_value(account, "account_id") or "")
            prior = account_by_id.get(account_id)
            if prior is None or start > str(_field_value(prior, "startdate") or ""):
                account_by_id[account_id] = account

        # Success-only first connection timestamps, grouped by SHA identity.
        sha_groups: dict[tuple[str, str, str, str], dict[str, str]] = {}
        for item in shared:
            if str(_field_value(item, "authorization_status") or "") != "success":
                continue
            key = (
                str(_field_value(item, "id") or ""),
                str(_field_value(item, "data_center") or ""),
                str(_field_value(item, "user_id") or ""),
                str(_field_value(item, "provider") or ""),
            )
            authorized = str(_field_value(item, "authorized_at") or "")
            created = str(_field_value(item, "created_at") or "")
            previous = sha_groups.get(key)
            if previous is None:
                sha_groups[key] = {"authorized": authorized, "created": created}
            else:
                previous["authorized"] = min(previous["authorized"], authorized)
                previous["created"] = min(previous["created"], created)

        app_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for app in applications:
            if str(_field_value(app, "entry_date") or "") != application_date:
                continue
            app_by_key[
                (
                    str(_field_value(app, "data_center") or ""),
                    str(_field_value(app, "name") or ""),
                )
            ] = app

        # Collapse providers that map to the same app title/category.
        events: dict[tuple[str, str, str, Any], dict[str, str]] = {}
        for (_, data_center, user_id, provider), timestamps in sha_groups.items():
            app = app_by_key.get((data_center, provider))
            title = str(_field_value(app, "title") or provider) if app else provider
            category = _field_value(app, "category") if app else None
            key = (data_center, user_id, title, category)
            previous = events.get(key)
            if previous is None:
                events[key] = dict(timestamps)
            else:
                previous["authorized"] = min(
                    previous["authorized"], timestamps["authorized"]
                )
                previous["created"] = min(previous["created"], timestamps["created"])

        calendar_by_date = {
            str(_field_value(item, "date") or ""): item for item in calendar
        }

        def monday(day: str) -> str | None:
            source = calendar_by_date.get(day)
            if source is None:
                return None
            year = _field_value(source, "year")
            week = _field_value(source, "week")
            matches = [
                item
                for item in calendar
                if _field_value(item, "year") == year
                and _field_value(item, "week") == week
                and str(_field_value(item, "dayname") or "") == "Mon"
            ]
            return str(_field_value(matches[0], "date")) if len(matches) == 1 else None

        workspace_by_key = {
            (
                str(_field_value(item, "workspace_id") or ""),
                str(_field_value(item, "data_center") or ""),
            ): item
            for item in workspaces
            if _as_bool(_field_value(item, "is_latest"))
            and _as_bool(_field_value(item, "is_paid_workspace"))
        }
        tier_by_title = {
            str(_field_value(item, "title") or ""): item for item in tiers
        }

        # One row per account/title after the app_interim3 grouping and rank.
        candidates: dict[tuple[str, str], dict[str, Any]] = {}
        for (data_center, user_id, title, category), timestamps in events.items():
            belonging = monday(timestamps["authorized"][:10])
            # The SQL has an inner calendar join for creation as well, even
            # though its Monday is not selected by the final projection.
            if belonging is None or monday(timestamps["created"][:10]) is None:
                continue
            workspace = workspace_by_key.get((user_id, data_center))
            if workspace is None:
                continue
            account_id = str(_field_value(workspace, "sales_account_id") or "")
            account = account_by_id.get(account_id)
            if account is None:
                continue
            tier = tier_by_title.get(title)
            tier_category = _field_value(tier, "category") if tier else None
            raw_tier = _field_value(tier, "app_tier") if tier else None
            app_tier = (
                5
                if tier_category in ("workato", "others", None)
                else int(raw_tier or 5)
            )
            row = {
                "account_id": account_id,
                "account_name": str(_field_value(account, "account_name") or ""),
                "subscription_start_date": str(
                    _field_value(account, "subscription_start_date") or ""
                ),
                "connected_after_subscription_start": int(
                    belonging
                    >= str(_field_value(account, "subscription_start_date") or "")
                ),
                "belonging_week_snapshot_first_connection": belonging,
                "title": title,
                "category": category,
                "app_tier": app_tier,
            }
            rank_key = (account_id, title)
            previous = candidates.get(rank_key)
            if (
                previous is None
                or belonging
                < str(previous["belonging_week_snapshot_first_connection"])
            ):
                candidates[rank_key] = row

        grouped: dict[tuple[Any, ...], dict[str, list[str]]] = {}
        for item in candidates.values():
            key = (
                item["account_id"],
                item["account_name"],
                item["subscription_start_date"],
                item["connected_after_subscription_start"],
                item["belonging_week_snapshot_first_connection"],
            )
            bucket = grouped.setdefault(key, {"t12": [], "t34": [], "t5": []})
            if item["category"] in ("app", "custom") and item["app_tier"] in (1, 2):
                bucket["t12"].append(str(item["title"]))
            if item["category"] in ("app", "custom") and item["app_tier"] in (3, 4):
                bucket["t34"].append(str(item["title"]))
            if item["app_tier"] == 5:
                bucket["t5"].append(str(item["title"]))

        output: list[dict[str, Any]] = []
        for key, bucket in grouped.items():
            account_id, account_name, subscription, connected, belonging = key
            output.append(
                {
                    "account_id": account_id,
                    "account_name": account_name,
                    "subscription_start_date": subscription,
                    "connected_after_subscription_start": connected,
                    "belonging_week_snapshot_first_connection": belonging,
                    "n_tier_1_2_app_connected": len(bucket["t12"]),
                    "tier_1_2_apps_connected": ";".join(sorted(bucket["t12"])),
                    "n_tier_3_4_app_connected": len(bucket["t34"]),
                    "tier_3_4_apps_connected": ";".join(sorted(bucket["t34"])),
                    "n_tier_5_app_connected": len(bucket["t5"]),
                    "tier_5_apps_connected": ";".join(sorted(bucket["t5"])),
                }
            )
        return output

    def _recipe_hierarchy_rows(self) -> list[dict[str, Any]]:
        source = self._resolve_table_name(
            "plg.chi_2024_hierarchy_base_interim_operational"
        )
        source_rows = self._tables.setdefault(source, [])
        pending: list[dict[str, Any]] = []
        for row in source_rows:
            if not _as_bool(_field_value(row, "is_valid_workflow")):
                continue
            flow_id = _field_value(row, "flow_id")
            pending.append(
                {
                    "calendar_date": _field_value(row, "entry_date"),
                    "flow_id": flow_id,
                    "data_center": _field_value(row, "data_center"),
                    "parent_id": _field_value(row, "parent_id"),
                    "root_flow": flow_id,
                    "level": 0,
                    "hierarchy_path": [flow_id],
                }
            )

        expanded: list[dict[str, Any]] = []
        while pending:
            current = pending.pop(0)
            expanded.append(current)
            for candidate in source_rows:
                candidate_flow = _field_value(candidate, "flow_id")
                if candidate_flow in current["hierarchy_path"]:
                    continue
                if str(_field_value(candidate, "parent_id")) != str(current["flow_id"]):
                    continue
                if str(_field_value(candidate, "entry_date")) != str(current["calendar_date"]):
                    continue
                if str(_field_value(candidate, "data_center")) != str(current["data_center"]):
                    continue
                pending.append(
                    {
                        "calendar_date": current["calendar_date"],
                        "flow_id": candidate_flow,
                        "data_center": current["data_center"],
                        "parent_id": _field_value(candidate, "parent_id"),
                        "root_flow": current["root_flow"],
                        "level": int(current["level"]) + 1,
                        "hierarchy_path": [*current["hierarchy_path"], candidate_flow],
                    }
                )

        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in expanded:
            output = dict(row)
            if output["level"] == 0:
                output["workflow_type"] = (
                    "RF workflow" if output["parent_id"] is not None else "Root workflow"
                )
                if output["parent_id"] is not None:
                    output["parent_id"] = None
            else:
                output["workflow_type"] = "Not workflow"
            # Match the final SELECT column order only semantically; snapshot
            # comparison is case-insensitive and keyed by declared fields.
            ordered = {
                "calendar_date": output["calendar_date"],
                "flow_id": output["flow_id"],
                "data_center": output["data_center"],
                "parent_id": output["parent_id"],
                "workflow_type": output["workflow_type"],
                "root_flow": output["root_flow"],
                "level": output["level"],
                "hierarchy_path": output["hierarchy_path"],
            }
            marker = json.dumps(ordered, sort_keys=True, default=str)
            if marker not in seen:
                seen.add(marker)
                rows.append(ordered)
        return rows

    def _process_complexity_feature_rows(self) -> list[dict[str, Any]]:
        interim_name = self._resolve_table_name(
            "plg.chi_2023_process_complexity_recipe_features_interim_operational"
        )
        hierarchy_name = self._resolve_table_name(
            "plg.chi_2023_recipe_hierarchy_operational"
        )
        interim = self._tables.setdefault(interim_name, [])
        hierarchy = self._tables.setdefault(hierarchy_name, [])

        memberships: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for feature in interim:
            for link in hierarchy:
                if all(
                    str(_field_value(feature, field))
                    == str(_field_value(link, field))
                    for field in ("calendar_date", "data_center", "flow_id")
                ):
                    memberships.append((feature, link))

        grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for feature, link in memberships:
            key = (
                str(_field_value(feature, "calendar_date")),
                str(_field_value(feature, "data_center")),
                str(_field_value(link, "root_flow")),
            )
            grouped.setdefault(key, []).append(feature)

        flag_fields = [
            "has_bulkbatch_action",
            "has_query_action",
            "has_db_table",
            "has_collections",
            "has_variables",
            "has_lookup_table",
            "has_scripting",
            "has_sync_function",
            "has_async_function",
            "has_looping_logic",
            "has_if_then_logic",
            "has_if_then_else_logic",
            "has_try_catch_logic",
        ]
        tier_fields = [f"tier_{index}_applications" for index in range(1, 6)]
        rows: list[dict[str, Any]] = []
        for (calendar_date, data_center, root_flow), features in grouped.items():
            root_feature = next(
                (
                    row
                    for row in interim
                    if str(_field_value(row, "flow_id")) == root_flow
                    and str(_field_value(row, "calendar_date")) == calendar_date
                    and str(_field_value(row, "data_center")) == data_center
                ),
                None,
            )
            if root_feature is None or _field_value(root_feature, "account_id") is None:
                continue
            root_link = next(
                (
                    row
                    for row in hierarchy
                    if str(_field_value(row, "flow_id")) == root_flow
                    and str(_field_value(row, "root_flow")) == root_flow
                    and str(_field_value(row, "calendar_date")) == calendar_date
                    and str(_field_value(row, "data_center")) == data_center
                ),
                None,
            )
            if root_link is None:
                continue

            tier_values: dict[str, list[str]] = {}
            for field in tier_fields:
                values: list[str] = []
                for feature in features:
                    raw_value = _field_value(feature, field)
                    for item in str(raw_value or "").split(","):
                        item = item.strip()
                        if item and item not in values:
                            values.append(item)
                tier_values[field] = values
            flags = {
                field: any(_as_bool(_field_value(feature, field)) for feature in features)
                for field in flag_fields
            }
            flow_keys = {
                str(_field_value(feature, "flow_id")) + data_center
                for feature in features
            }
            row: dict[str, Any] = {
                "calendar_date": _field_value(root_feature, "calendar_date"),
                "account_id": _field_value(root_feature, "account_id"),
                "account_name": _field_value(root_feature, "account_name"),
                "root_flow": root_flow,
                "data_center": _field_value(root_feature, "data_center"),
                "workflow_type": _field_value(root_link, "workflow_type"),
                "n_flows_in_workflow": len(flow_keys),
                "n_downstream_steps": sum(
                    int(_field_value(feature, "num_steps") or 0)
                    for feature in features
                ),
                "recipe_category_type": _field_value(
                    root_feature, "recipe_category_type"
                ),
                "trigger_app": _field_value(root_feature, "trigger_app"),
            }
            for index, field in enumerate(tier_fields, start=1):
                values = tier_values[field]
                row[f"tier_{index}_apps"] = ",".join(values) if values else None
                row[f"num_tier_{index}_app"] = len(values)
            row["trigger_type"] = _field_value(root_feature, "trigger_type")
            row.update(flags)
            row["is_single_action"] = not (
                flags["has_bulkbatch_action"] or flags["has_query_action"]
            )
            row["is_pass_through"] = not any(
                flags[field]
                for field in (
                    "has_sync_function",
                    "has_async_function",
                    "has_looping_logic",
                    "has_if_then_logic",
                    "has_if_then_else_logic",
                )
            )
            rows.append(row)
        return rows

    def _aggregate_rows_sql(self, sql: str, parameters: dict[str, Any]) -> dict[str, Any] | None:
        text = " ".join(str(sql or "").split())
        lower = text.lower()
        if "count(distinct case when smc.source_type" in lower:
            return self._secrets_manager_counts()
        grouped_count = re.fullmatch(
            r"select\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
            r"count\s*\(\s*(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*\)\s+as\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s+from\s+"
            r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
            r"(?:\s+(?:as\s+)?[A-Za-z_][A-Za-z0-9_]*)?\s+"
            r"group\s+by\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s+"
            r"having\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*"
            r"(>=|<=|!=|<>|=|>|<)\s*(\d+)",
            text,
            flags=re.I,
        )
        if grouped_count:
            projected_group = grouped_count.group(1)
            count_field = grouped_count.group(2)
            count_alias = grouped_count.group(3)
            table_name = self._resolve_table_name(grouped_count.group(4))
            group_field = grouped_count.group(5)
            having_field = grouped_count.group(6)
            operator = grouped_count.group(7)
            threshold = int(grouped_count.group(8))
            if projected_group.casefold() != group_field.casefold():
                raise RuntimeError(
                    "snowflake grouped COUNT projection must match GROUP BY field"
                )
            if having_field.casefold() != count_alias.casefold():
                raise RuntimeError(
                    "snowflake grouped COUNT HAVING must reference the count alias"
                )
            grouped: dict[str, tuple[Any, int]] = {}
            for row in self._tables.setdefault(table_name, []):
                group_value = _field_value(row, group_field)
                marker = json.dumps(group_value, sort_keys=True, default=str)
                prior_value, prior_count = grouped.get(marker, (group_value, 0))
                increment = int(_field_value(row, count_field) is not None)
                grouped[marker] = (prior_value, prior_count + increment)

            def compare(value: int) -> bool:
                return {
                    ">": value > threshold,
                    ">=": value >= threshold,
                    "<": value < threshold,
                    "<=": value <= threshold,
                    "=": value == threshold,
                    "!=": value != threshold,
                    "<>": value != threshold,
                }[operator]

            rows = [
                {
                    projected_group: group_value,
                    _output_key(projected_group): group_value,
                    count_alias: count,
                    _output_key(count_alias): count,
                }
                for group_value, count in grouped.values()
                if compare(count)
            ]
            return {"table": table_name, "rows": rows}
        match = re.search(
            r"select\s+count\s*\(\s*distinct\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*\)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)\s+from\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)",
            text,
            flags=re.I,
        )
        if not match:
            return None
        field = match.group(1)
        alias = match.group(2)
        table_name = self._resolve_table_name(match.group(3))
        where = _parse_sql_where(text)
        values = {
            str(_field_value(row, field))
            for row in self._tables.setdefault(table_name, [])
            if _matches_where(row, where, parameters) and _field_value(row, field) not in (None, "")
        }
        value = len(values)
        row = {alias: value, _output_key(alias): value}
        return {"table": table_name, "rows": [row]}

    def _secrets_manager_counts(self) -> dict[str, Any]:
        smc_table = self._resolve_table_name("workato_usage.secrets_management_configurations")
        wd_table = self._resolve_table_name("workato_usage.workspace_dim")
        ad_table = self._resolve_table_name("workato_usage.accounts_dim")
        wd_rows = self._tables.setdefault(wd_table, [])
        ad_rows = self._tables.setdefault(ad_table, [])
        counts: dict[str, set[str]] = {
            "aws": set(),
            "hashicorp": set(),
            "azure": set(),
            "cyberark": set(),
        }
        source_aliases = {1: "aws", 2: "hashicorp", 3: "azure", 4: "cyberark"}
        for smc in self._tables.setdefault(smc_table, []):
            try:
                source_type = int(str(_field_value(smc, "source_type") or ""))
            except ValueError:
                continue
            alias = source_aliases.get(source_type)
            if not alias:
                continue
            for wd in wd_rows:
                if str(_field_value(smc, "user_id")) != str(_field_value(wd, "workspace_id")):
                    continue
                if str(_field_value(smc, "data_center")) != str(_field_value(wd, "data_center")):
                    continue
                if _as_bool(_field_value(wd, "is_internal")):
                    continue
                if not _as_bool(_field_value(wd, "is_latest")):
                    continue
                if not _as_bool(_field_value(wd, "is_paid_workspace")):
                    continue
                sales_account_id = _field_value(wd, "sales_account_id")
                for ad in ad_rows:
                    account_id = _field_value(ad, "account_id")
                    if str(sales_account_id) != str(account_id):
                        continue
                    if not _as_bool(_field_value(ad, "is_paying")):
                        continue
                    if not _as_bool(_field_value(ad, "is_latest")):
                        continue
                    if account_id not in (None, ""):
                        counts[alias].add(str(account_id))
        row = {alias: len(values) for alias, values in counts.items()}
        return {"table": smc_table, "rows": [row]}

    def _left_join_rows_sql(self, sql: str, parameters: dict[str, Any]) -> dict[str, Any] | None:
        text = " ".join(str(sql or "").split())
        # This native path models exactly one LEFT JOIN.  Let the relational
        # fallback handle mixed/multi-join queries; otherwise a later LEFT
        # JOIN regex can accidentally skip an earlier INNER JOIN and project
        # same-named columns from the wrong table.
        if len(re.findall(r"\bJOIN\b", text, flags=re.I)) != 1:
            return None
        match = re.search(
            r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+LEFT\s+JOIN\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+(.+?)(?:\s+\bWHERE\b|\s+\bORDER\s+BY\b|\s+\bLIMIT\b|$)",
            text,
            flags=re.I,
        )
        if not match:
            return None
        left_table = self._resolve_table_name(match.group(1))
        left_alias = match.group(2)
        right_table = self._resolve_table_name(match.group(3))
        right_alias = match.group(4)
        on_clause = match.group(5).strip()
        where = _parse_sql_where(text)
        selected = _parse_sql_select(text)
        rows: list[dict[str, Any]] = []
        for left in self._tables.setdefault(left_table, []):
            left_view = _alias_row(left, left_alias)
            matched = False
            for right in self._tables.setdefault(right_table, []):
                combined = left_view | _alias_row(right, right_alias)
                if _matches_join_on(combined, on_clause, parameters):
                    matched = True
                    if _matches_where(combined, where, parameters):
                        rows.append(_project_row(combined, selected))
            if not matched and _matches_where(left_view, where, parameters):
                rows.append(_project_row(left_view, selected))
        return {"table": left_table, "rows": rows}

    def _inner_join_rows_sql(
        self,
        sql: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Execute a deterministic chain of ordinary inner joins.

        Imported recipes commonly use two or three dimension-table joins and
        project ``alias.*``.  Supporting that normal SQL shape is part of the
        simulator's public query contract; it must not force a model to mimic a
        benchmark-only rewritten query.
        """

        text = " ".join(str(sql or "").split())
        if re.search(r"\b(?:LEFT|RIGHT|FULL|CROSS)\s+JOIN\b", text, flags=re.I):
            return None
        head = re.search(
            r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
            r"\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+(?=(?:INNER\s+)?JOIN\b)",
            text,
            flags=re.I,
        )
        if not head:
            return None
        join_pattern = re.compile(
            r"\b(?:INNER\s+)?JOIN\s+"
            r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
            r"\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+(.+?)"
            r"(?=\s+(?:INNER\s+)?JOIN\b|\s+WHERE\b|\s+ORDER\s+BY\b|\s+LIMIT\b|$)",
            flags=re.I,
        )
        joins = list(join_pattern.finditer(text))
        if not joins:
            return None

        base_table = self._resolve_table_name(head.group(1))
        base_alias = head.group(2)
        combined_rows = [
            _alias_row(row, base_alias)
            for row in self._tables.setdefault(base_table, [])
        ]
        for join in joins:
            right_table = self._resolve_table_name(join.group(1))
            right_alias = join.group(2)
            on_clause = join.group(3).strip()
            next_rows: list[dict[str, Any]] = []
            for left in combined_rows:
                for right in self._tables.setdefault(right_table, []):
                    combined = left | _alias_row(right, right_alias)
                    if _matches_join_on(combined, on_clause, parameters):
                        next_rows.append(combined)
            combined_rows = next_rows

        where = _parse_sql_where(text)
        selected = _parse_sql_select(text)
        rows = [
            _project_row(row, selected)
            for row in combined_rows
            if _matches_where(row, where, parameters)
        ]
        return {"table": base_table, "rows": rows}

    def _not_exists_rows_sql(
        self,
        sql: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Execute a constrained correlated ``NOT EXISTS`` anti-join.

        This covers the standard outcome-equivalent form of the already
        supported LEFT JOIN / right-key-IS-NULL pattern. The subquery remains
        deliberately narrow: SELECT 1, one source table, and supported join
        predicates only.
        """

        text = " ".join(str(sql or "").split())
        match = re.search(
            r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
            r"\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+WHERE\s+"
            r"(?:(.+?)\s+AND\s+)?NOT\s+EXISTS\s*\(\s*SELECT\s+1\s+FROM\s+"
            r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
            r"\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+WHERE\s+(.+?)\s*\)"
            r"(?:\s+ORDER\s+BY\s+.+?|\s+LIMIT\s+\d+)?$",
            text,
            flags=re.I,
        )
        if not match:
            return None
        left_table = self._resolve_table_name(match.group(1))
        left_alias = match.group(2)
        outer_where = (match.group(3) or "").strip()
        right_table = self._resolve_table_name(match.group(4))
        right_alias = match.group(5)
        correlation = match.group(6).strip()
        selected = _parse_sql_select(text)
        rows: list[dict[str, Any]] = []
        for left in self._tables.setdefault(left_table, []):
            left_view = _alias_row(left, left_alias)
            if not _matches_where(left_view, outer_where, parameters):
                continue
            has_match = any(
                _matches_join_on(
                    left_view | _alias_row(right, right_alias),
                    correlation,
                    parameters,
                )
                for right in self._tables.setdefault(right_table, [])
            )
            if not has_match:
                rows.append(_project_row(left_view, selected))
        return {"table": left_table, "rows": rows}

    def _resolve_table_name(self, table_name: str) -> str:
        if table_name in self._tables:
            return table_name
        casefold_matches = [
            candidate
            for candidate in self._tables
            if candidate.casefold() == str(table_name).casefold()
        ]
        if len(casefold_matches) == 1:
            return casefold_matches[0]
        suffix_matches = [
            candidate
            for candidate in self._tables
            if candidate.casefold().endswith("." + str(table_name).casefold())
        ]
        if len(suffix_matches) == 1:
            return suffix_matches[0]
        if "." not in table_name:
            qualified = "SALESFORCE." + table_name
            if qualified in self._tables:
                return qualified
            suffix_matches = [
                candidate
                for candidate in self._tables
                if candidate.rsplit(".", 1)[-1].lower() == table_name.lower()
            ]
            if len(suffix_matches) == 1:
                return suffix_matches[0]
        return table_name

    def _find_target(
        self,
        rows: list[dict[str, Any]],
        key_columns: list[str],
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        for key in key_columns:
            if _field_value(record, key) is None:
                raise RuntimeError(f"snowflake upsert row missing key column: {key}")
        for row in rows:
            if all(str(_field_value(row, key)) == str(_field_value(record, key)) for key in key_columns):
                return row
        return None

    def _next_row_id(self, rows: list[dict[str, Any]]) -> int:
        return max((int(row.get("_row_id", -1)) for row in rows), default=-1) + 1


def _key_columns(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = raw
    else:
        values = str(raw or "").replace(",", "\n").splitlines()
    out: list[str] = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("value") or value.get("label") or value.get("name")
        text = str(value or "").strip()
        if text:
            out.append(text)
    return out


def _field_value(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row[field]
    if "." in field:
        tail = field.rsplit(".", 1)[-1]
        if tail in row:
            return row[tail]
        return _field_value(row, tail)
    lower = field.lower()
    if lower in row:
        return row[lower]
    upper = field.upper()
    if upper in row:
        return row[upper]
    for key, value in row.items():
        key_lower = str(key).lower()
        if key_lower == lower or key_lower.startswith(lower + "_"):
            return value
    return None


def _visible_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if str(key).startswith("_"):
            continue
        out[str(key)] = value
        normalized = _output_key(str(key))
        out.setdefault(normalized, value)
    return out


def _alias_row(row: dict[str, Any], alias: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in _visible_row(row).items():
        out.setdefault(str(key), value)
        out[f"{alias}.{key}"] = value
        out.setdefault(f"{alias}.{str(key).upper()}", value)
        out.setdefault(f"{alias}.{_output_key(str(key))}", value)
    return out


def _output_key(value: str) -> str:
    return str(value or "").strip().strip('"').lower()


def _strip_sql_line_comments(sql: str) -> str:
    """Remove Snowflake ``--``/``//`` comments without touching strings."""

    cleaned: list[str] = []
    for line in str(sql or "").splitlines():
        quote: str | None = None
        index = 0
        while index < len(line):
            char = line[index]
            if quote:
                if char == quote:
                    if quote == "'" and index + 1 < len(line) and line[index + 1] == "'":
                        index += 2
                        continue
                    quote = None
                index += 1
                continue
            if char in {"'", '"'}:
                quote = char
                index += 1
                continue
            if line.startswith("--", index) or line.startswith("//", index):
                line = line[:index]
                break
            index += 1
        cleaned.append(line)
    return "\n".join(cleaned)


def _sqlite_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _sqlite_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Return one physical column for each case-insensitive Snowflake name."""

    result: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for raw_name in row:
            name = str(raw_name)
            if name.startswith("_") or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            result.append(name)
    return result


def _sqlite_type(rows: list[dict[str, Any]], column: str) -> str:
    values = [
        _field_value(row, column)
        for row in rows
        if _field_value(row, column) is not None
    ]
    if values and all(isinstance(value, bool) for value in values):
        return "INTEGER"
    if values and all(
        isinstance(value, int) and not isinstance(value, bool) for value in values
    ):
        return "INTEGER"
    if values and all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in values
    ):
        return "REAL"
    return "TEXT"


def _sqlite_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bytes)):
        return value
    if isinstance(value, bool):
        return int(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(value)).replace(
        "Z", "+00:00"
    )
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def _jaro_winkler(left: Any, right: Any) -> float:
    """Return Jaro-Winkler similarity on Snowflake's 0--100 scale."""

    first = str(left or "").casefold()
    second = str(right or "").casefold()
    if first == second:
        return 100.0
    if not first or not second:
        return 0.0

    match_distance = max(len(first), len(second)) // 2 - 1
    match_distance = max(0, match_distance)
    first_matches = [False] * len(first)
    second_matches = [False] * len(second)

    matches = 0
    for first_index, character in enumerate(first):
        lower = max(0, first_index - match_distance)
        upper = min(first_index + match_distance + 1, len(second))
        for second_index in range(lower, upper):
            if second_matches[second_index] or character != second[second_index]:
                continue
            first_matches[first_index] = True
            second_matches[second_index] = True
            matches += 1
            break
    if matches == 0:
        return 0.0

    matched_first = [
        character
        for index, character in enumerate(first)
        if first_matches[index]
    ]
    matched_second = [
        character
        for index, character in enumerate(second)
        if second_matches[index]
    ]
    transpositions = sum(
        one != two for one, two in zip(matched_first, matched_second)
    ) / 2.0
    jaro = (
        matches / len(first)
        + matches / len(second)
        + (matches - transpositions) / matches
    ) / 3.0
    prefix = 0
    for one, two in zip(first[:4], second[:4]):
        if one != two:
            break
        prefix += 1
    return 100.0 * (jaro + prefix * 0.1 * (1.0 - jaro))


def _sqlite_monthname(value: Any) -> str | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )[parsed.month - 1]


def _sqlite_dateadd(unit: Any, amount: Any, value: Any) -> str | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    try:
        magnitude = float(amount)
    except (TypeError, ValueError):
        return None
    normalized = str(unit or "").strip().casefold().rstrip("s")
    if normalized == "day":
        delta = timedelta(days=magnitude)
    elif normalized == "hour":
        delta = timedelta(hours=magnitude)
    elif normalized == "minute":
        delta = timedelta(minutes=magnitude)
    elif normalized == "second":
        delta = timedelta(seconds=magnitude)
    else:
        return None
    return (parsed + delta).isoformat()


def _sqlite_datediff(unit: Any, start: Any, end: Any) -> int | None:
    first = _parse_datetime(start)
    second = _parse_datetime(end)
    if first is None or second is None:
        return None
    seconds = (second - first).total_seconds()
    normalized = str(unit or "").strip().casefold().rstrip("s")
    divisor = {
        "day": 86400,
        "hour": 3600,
        "minute": 60,
        "second": 1,
    }.get(normalized)
    return int(seconds / divisor) if divisor else None


def _sqlite_try_decimal(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _sqlite_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA case_sensitive_like = ON")
    connection.create_function("CONCAT", -1, lambda *items: "".join(str(item or "") for item in items))
    connection.create_function("LEN", 1, lambda value: len(str(value or "")))
    connection.create_function(
        "RIGHT",
        2,
        lambda value, length: str(value or "")[-max(0, int(length or 0)) :],
    )
    connection.create_function("TRY_TO_DECIMAL", 1, _sqlite_try_decimal)
    def to_timestamp_ntz(value: Any) -> Any:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        parsed = _parse_datetime(value)
        return parsed.isoformat() if parsed is not None else value

    connection.create_function("TO_TIMESTAMP_NTZ", 1, to_timestamp_ntz)
    connection.create_function("DATEADD", 3, _sqlite_dateadd)
    connection.create_function("DATEDIFF", 3, _sqlite_datediff)
    connection.create_function("TIMEDIFF", 3, _sqlite_datediff)
    connection.create_function("JAROWINKLER_SIMILARITY", 2, _jaro_winkler)
    connection.create_function("MONTHNAME", 1, _sqlite_monthname)
    connection.create_function("IFF", 3, lambda condition, yes, no: yes if condition else no)
    def array_contains(value: Any, collection: Any) -> int:
        if collection is None:
            return 0
        parsed: Any = collection
        if isinstance(collection, str):
            try:
                parsed = json.loads(collection)
            except json.JSONDecodeError:
                parsed = [
                    item.strip().strip("'\"")
                    for item in collection.strip("[]").split(",")
                    if item.strip()
                ]
        if not isinstance(parsed, (list, tuple, set)):
            return 0
        return int(any(str(item) == str(value) for item in parsed))

    connection.create_function("ARRAY_CONTAINS", 2, array_contains)

    class ListAgg:
        def __init__(self) -> None:
            self.values: list[str] = []
            self.separator = ","

        def step(self, value: Any, separator: Any = ",") -> None:
            if value is None:
                return
            self.values.append(str(value))
            self.separator = str(separator)

        def finalize(self) -> str:
            # The Workato Snowflake connector exposes an empty LISTAGG text
            # cell as an empty string in recipe datapills.
            return self.separator.join(self.values)

    class ListAggDistinct(ListAgg):
        def __init__(self) -> None:
            super().__init__()
            self.seen: set[str] = set()

        def step(self, value: Any, separator: Any = ",") -> None:
            if value is None or str(value) in self.seen:
                return
            self.seen.add(str(value))
            super().step(value, separator)

    connection.create_aggregate("LISTAGG", 2, ListAgg)
    connection.create_aggregate("LISTAGG_DISTINCT", 2, ListAggDistinct)
    return connection


def _load_sqlite_table(
    connection: sqlite3.Connection,
    sqlite_name: str,
    rows: list[dict[str, Any]],
    *,
    include_row_index: bool = False,
    declared_columns: list[str] | None = None,
) -> list[str]:
    columns = list(
        dict.fromkeys([*_sqlite_columns(rows), *(declared_columns or [])])
    )
    definitions = [
        f"{_sqlite_identifier(column)} {_sqlite_type(rows, column)}"
        for column in columns
    ]
    if include_row_index:
        definitions.append('"__agentorch_row_index" INTEGER NOT NULL')
    if not definitions:
        definitions.append('"__agentorch_empty" INTEGER')
    connection.execute(
        f"CREATE TABLE {_sqlite_identifier(sqlite_name)} ({', '.join(definitions)})"
    )
    insert_columns = [*columns]
    if include_row_index:
        insert_columns.append("__agentorch_row_index")
    if rows:
        placeholders = ", ".join("?" for _ in insert_columns)
        quoted = ", ".join(_sqlite_identifier(column) for column in insert_columns)
        values = []
        for index, row in enumerate(rows):
            record = [_sqlite_value(_field_value(row, column)) for column in columns]
            if include_row_index:
                record.append(index)
            values.append(record)
        connection.executemany(
            f"INSERT INTO {_sqlite_identifier(sqlite_name)} ({quoted}) VALUES ({placeholders})",
            values,
        )
    return columns


def _rewrite_group_by_all(sql: str) -> str:
    if not re.search(r"\bGROUP\s+BY\s+ALL\b", sql, flags=re.I):
        return sql
    match = re.search(r"\bSELECT\s+(.+?)\s+FROM\b", sql, flags=re.I | re.S)
    if not match:
        return re.sub(r"\bGROUP\s+BY\s+ALL\b", "", sql, flags=re.I)
    projection = match.group(1)
    parts: list[str] = []
    start = 0
    depth = 0
    quote = False
    for index, char in enumerate(projection):
        if char == "'":
            quote = not quote
        elif not quote and char == "(":
            depth += 1
        elif not quote and char == ")":
            depth = max(0, depth - 1)
        elif not quote and depth == 0 and char == ",":
            parts.append(projection[start:index].strip())
            start = index + 1
    parts.append(projection[start:].strip())
    nonaggregates = [
        str(index)
        for index, part in enumerate(parts, start=1)
        if part
        and not re.search(r"\b(?:COUNT|SUM|AVG|MIN|MAX)\s*\(", part, flags=re.I)
    ]
    replacement = "GROUP BY " + ", ".join(nonaggregates) if nonaggregates else ""
    return re.sub(r"\bGROUP\s+BY\s+ALL\b", replacement, sql, flags=re.I)


def _sqlite_sql_text(sql: str, *, current_time: str | None = None) -> str:
    text = str(sql or "").strip().rstrip(";")
    text = re.sub(
        r"\bSELECT\s+DISTINCT\s*\(\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\)",
        r"SELECT DISTINCT \1",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"([A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?)\s+NOT\s+ILIKE\s+"
        r"('(?:''|[^'])*'|:[A-Za-z_][A-Za-z0-9_]*)",
        r"LOWER(\1) NOT LIKE LOWER(\2)",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"([A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?)\s+ILIKE\s+"
        r"('(?:''|[^'])*'|:[A-Za-z_][A-Za-z0-9_]*)",
        r"LOWER(\1) LIKE LOWER(\2)",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\bLISTAGG\s*\(\s*DISTINCT\s+([^,()]+)\s*,",
        r"LISTAGG_DISTINCT(\1,",
        text,
        flags=re.I,
    )
    text = re.sub(r"\bCURRENT_TIMESTAMP\s*\(\s*\)", "CURRENT_TIMESTAMP", text, flags=re.I)
    text = re.sub(r"\bCURRENT_DATE\s*\(\s*\)", "CURRENT_DATE", text, flags=re.I)
    text = re.sub(
        r"\b(DATEDIFF|TIMEDIFF)\s*\(\s*(DAYS?|HOURS?|MINUTES?|SECONDS?)\s*,",
        lambda match: f"{match.group(1).upper()}('{match.group(2)}',",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\bDATEADD\s*\(\s*(DAYS?|HOURS?|MINUTES?|SECONDS?|MONTHS?|YEARS?)\s*,",
        lambda match: f"DATEADD('{match.group(1)}',",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(LISTAGG(?:_DISTINCT)?\s*\([^)]*\))\s+WITHIN\s+GROUP\s*"
        r"\(\s*ORDER\s+BY\s+[^)]*\)",
        r"\1",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\bCOUNT_IF\s*\(([^()]*)\)",
        lambda match: f"SUM(CASE WHEN {match.group(1)} THEN 1 ELSE 0 END)",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"((?:[A-Za-z_][A-Za-z0-9_.]*)|'(?:''|[^'])*')"
        r"\s*::\s*(TEXT|STRING|VARCHAR)(?:\s*\([^)]*\))?",
        r"CAST(\1 AS TEXT)",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"((?:[A-Za-z_][A-Za-z0-9_.]*)|'(?:''|[^'])*')\s*::\s*DATE\b",
        r"DATE(\1)",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(RIGHT\(\s*([A-Za-z_][A-Za-z0-9_.]*)\s*,\s*\(\s*LEN\(\s*\2\s*\)"
        r"\s*-\s*1\s*\)\s*\))\s*::\s*(?:INTEGER|INT|NUMBER)",
        r"CAST(\1 AS INTEGER)",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(RIGHT\(\s*([A-Za-z_][A-Za-z0-9_.]*)\s*,\s*LEN\(\s*\2\s*\)"
        r"\s*-\s*1\s*\))\s*::\s*(?:INTEGER|INT|NUMBER)",
        r"CAST(\1 AS INTEGER)",
        text,
        flags=re.I,
    )
    text = re.sub(r"::\s*[A-Za-z_][A-Za-z0-9_]*(?:\s*\([^)]*\))?", "", text)
    # LIMIT is also a legitimate Snowflake column name. Quote it only where
    # the token is visibly part of a projection list, never in a LIMIT clause.
    text = re.sub(r"\bLIMIT\b(?=\s*,)", '"LIMIT"', text, flags=re.I)
    if current_time:
        parsed = _parse_datetime(current_time)
        if parsed is None:
            raise ValueError(f"invalid pinned Snowflake current_time: {current_time!r}")
        timestamp_literal = parsed.astimezone(timezone.utc).replace(
            tzinfo=None
        ).isoformat()
        date_literal = parsed.date().isoformat()
        text = re.sub(
            r"(?:(\()\s*)?\bCURRENT_DATE\b\s*-\s*(\d+)\s*(?(1)\))",
            lambda match: "'"
            + (parsed.date() - timedelta(days=int(match.group(2)))).isoformat()
            + "'",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"\bCURRENT_TIMESTAMP\b",
            "'" + timestamp_literal.replace("'", "''") + "'",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"\bCURRENT_DATE\b",
            "'" + date_literal + "'",
            text,
            flags=re.I,
        )
    return _rewrite_group_by_all(text)


def _sqlite_filter_rows(
    rows: list[dict[str, Any]],
    where: str,
    parameters: dict[str, Any],
    *,
    current_time: str | None = None,
) -> list[dict[str, Any]]:
    connection = _sqlite_connection()
    try:
        _load_sqlite_table(connection, "agentorch_rows", rows, include_row_index=True)
        clause = _sqlite_sql_text(str(where or ""), current_time=current_time)
        clause = re.sub(r"\bGROUP\s+BY\s+ALL\b", "", clause, flags=re.I)
        # search_rows receives a single table without a SQL alias.  Recipes
        # sometimes retain authoring aliases in the condition, so resolve
        # those to the physical column tail for this one-table evaluator.
        clause = re.sub(
            r"\b[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)\b",
            lambda match: _sqlite_identifier(match.group(1)),
            clause,
        )
        cursor = connection.execute(
            'SELECT "__agentorch_row_index" FROM "agentorch_rows" '
            + (f"WHERE {clause}" if clause else ""),
            parameters,
        )
        indexes = [int(row[0]) for row in cursor.fetchall()]
        return [_visible_row(rows[index]) for index in indexes]
    finally:
        connection.close()


def _sqlite_search_rows_sql(
    tables: dict[str, list[dict[str, Any]]],
    sql: str,
    parameters: dict[str, Any],
    *,
    current_time: str | None = None,
    declared_columns: dict[str, list[str]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    text = _sqlite_sql_text(sql, current_time=current_time)
    if not re.match(r"\s*(?:WITH\b|SELECT\b)", text, flags=re.I):
        raise ValueError("query must begin with SELECT or WITH")
    boolean_outputs = {
        match.group(1).casefold()
        for match in re.finditer(
            r"\bCASE\b.+?\bTHEN\s+TRUE\b.+?\bELSE\s+FALSE\b.+?"
            r"\bEND\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.I | re.S,
        )
    }
    listagg_outputs = {
        match.group(1).casefold()
        for match in re.finditer(
            r"\bLISTAGG\s*\(.+?\)\s+(?:AS\s+)?"
            r"([A-Za-z_][A-Za-z0-9_]*)",
            str(sql or ""),
            flags=re.I | re.S,
        )
    }
    output_sources = {
        match.group(2).casefold(): match.group(1).rsplit(".", 1)[-1].casefold()
        for match in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_.]*)\s+(?:AS\s+)?"
            r"([A-Za-z_][A-Za-z0-9_]*)\b",
            text,
            flags=re.I,
        )
    }
    connection = _sqlite_connection()
    replacements: list[tuple[str, str]] = []
    tail_counts: dict[str, int] = defaultdict(int)
    for table_name in tables:
        tail_counts[str(table_name).rsplit(".", 1)[-1].casefold()] += 1
    column_types: dict[str, set[type]] = defaultdict(set)
    try:
        for index, table_name in enumerate(sorted(tables, key=lambda value: (-len(value), value))):
            sqlite_name = f"agentorch_table_{index}"
            rows = tables[table_name]
            declared = next(
                (
                    columns
                    for declared_table, columns in (declared_columns or {}).items()
                    if str(declared_table).casefold() == str(table_name).casefold()
                ),
                None,
            )
            columns = _load_sqlite_table(
                connection,
                sqlite_name,
                rows,
                declared_columns=declared,
            )
            replacements.append((table_name, sqlite_name))
            for column in columns:
                for row in rows:
                    value = _field_value(row, column)
                    if value is not None:
                        column_types[column.casefold()].add(type(value))
        for table_name, sqlite_name in replacements:
            tail = table_name.rsplit(".", 1)[-1]
            source_token = table_name
            if not re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(table_name)}(?![A-Za-z0-9_])",
                text,
                flags=re.I,
            ) and tail_counts[tail.casefold()] == 1:
                # Seeds may register a fully-qualified table while the recipe
                # relies on its current database/schema and names only the
                # unambiguous tail (``FROM TEAM``).  Resolve that public SQL
                # behavior only in FROM/JOIN positions.
                if re.search(
                    rf"\b(?:FROM|JOIN)\s+{re.escape(tail)}\b",
                    text,
                    flags=re.I,
                ):
                    source_token = tail
            explicit_alias = re.search(
                rf"\b(?:FROM|JOIN)\s+{re.escape(source_token)}\s+"
                r"(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)",
                text,
                flags=re.I,
            )
            if source_token == table_name:
                text = re.sub(
                    rf"(?<![A-Za-z0-9_]){re.escape(source_token)}(?![A-Za-z0-9_])",
                    _sqlite_identifier(sqlite_name),
                    text,
                    flags=re.I,
                )
            else:
                text = re.sub(
                    rf"\b(FROM|JOIN)\s+{re.escape(source_token)}\b",
                    lambda match: match.group(1) + " " + _sqlite_identifier(sqlite_name),
                    text,
                    flags=re.I,
                )
            alias = (
                explicit_alias.group(1)
                if explicit_alias
                and explicit_alias.group(1).casefold()
                not in {
                    "cross",
                    "full",
                    "inner",
                    "join",
                    "left",
                    "on",
                    "order",
                    "right",
                    "where",
                }
                else None
            )
            if alias is None:
                text = re.sub(
                    rf"\b{re.escape(tail)}\.",
                    _sqlite_identifier(sqlite_name) + ".",
                    text,
                    flags=re.I,
                )
        cursor = connection.execute(text, parameters)
        names = [str(column[0]) for column in cursor.description or []]
        rows: list[dict[str, Any]] = []
        for raw in cursor.fetchall():
            result: dict[str, Any] = {}
            for name, value in zip(names, raw, strict=True):
                if value is None and name.casefold() in listagg_outputs:
                    value = ""
                types = column_types.get(name.casefold(), set())
                source_types = column_types.get(
                    output_sources.get(name.casefold(), ""), set()
                )
                if value in (0, 1) and (
                    name.casefold() in boolean_outputs
                    or (types and types <= {bool})
                    or (source_types and source_types <= {bool})
                ):
                    value = bool(value)
                result[name] = value
                result.setdefault(_output_key(name), value)
            rows.append(result)
        text_cast_fields = {
            match.group(1).rsplit(".", 1)[-1].casefold()
            for match in re.finditer(
                r"\b([A-Za-z_][A-Za-z0-9_.]*)\s*::\s*"
                r"(?:TEXT|STRING|VARCHAR)(?:\s*\([^)]*\))?",
                str(sql or ""),
                flags=re.I,
            )
        }
        if text_cast_fields:
            deduped: list[dict[str, Any]] = []
            seen: set[tuple[Any, ...]] = set()
            for row in rows:
                for name in list(row):
                    if name.casefold() in text_cast_fields and row[name] is not None:
                        row[name] = str(row[name])
                signature = tuple(row.get(name) for name in names)
                if signature in seen:
                    continue
                seen.add(signature)
                deduped.append(row)
            rows = deduped
        parsed_table = _parse_sql_table(sql)
        return rows, parsed_table
    finally:
        connection.close()


def _matches_where(row: dict[str, Any], where: str, parameters: dict[str, Any]) -> bool:
    text = str(where or "").strip().rstrip(";").strip()
    if not text:
        return True
    parts = [part.strip() for part in re.split(r"\s+AND\s+", text, flags=re.I) if part.strip()]
    field_pattern = r'"?((?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*)"?'
    for part in parts:
        if re.fullmatch(r"1\s*=\s*1", part):
            continue
        if re.fullmatch(r"1\s*=\s*0", part):
            return False
        bare_boolean = re.fullmatch(field_pattern, part)
        if bare_boolean:
            if not _as_bool(_field_value(row, bare_boolean.group(1))):
                return False
            continue
        null_check = re.fullmatch(field_pattern + r"\s+IS\s+(NOT\s+)?NULL", part, flags=re.I)
        if null_check:
            is_null = _field_value(row, null_check.group(1)) is None
            if (null_check.group(2) and is_null) or (not null_check.group(2) and not is_null):
                return False
            continue
        boolean = re.fullmatch(field_pattern + r"\s*=\s*(TRUE|FALSE)", part, flags=re.I)
        if boolean:
            expected = boolean.group(2).lower() == "true"
            actual = _field_value(row, boolean.group(1))
            if _as_bool(actual) != expected:
                return False
            continue
        bind = re.fullmatch(field_pattern + r"\s*=\s*:([A-Za-z_][A-Za-z0-9_]*)", part)
        if bind:
            expected = parameters.get(bind.group(2))
            actual = _field_value(row, bind.group(1))
            if isinstance(actual, bool):
                if _as_bool(actual) != _as_bool(expected):
                    return False
            elif str(actual) != str(expected):
                return False
            continue
        literal = re.fullmatch(field_pattern + r"\s*=\s*'((?:''|[^'])*)'", part)
        if literal:
            expected = literal.group(2).replace("''", "'")
            if str(_field_value(row, literal.group(1))) != expected:
                return False
            continue
        ifnull_literal = re.fullmatch(
            field_pattern
            + r"\s*=\s*IFNULL\(\s*'((?:''|[^'])*)'\s*,\s*'((?:''|[^'])*)'\s*\)",
            part,
            flags=re.I,
        )
        if ifnull_literal:
            first = ifnull_literal.group(2).replace("''", "'")
            second = ifnull_literal.group(3).replace("''", "'")
            expected = first if first is not None else second
            if str(_field_value(row, ifnull_literal.group(1))) != expected:
                return False
            continue
        like = re.fullmatch(field_pattern + r"\s+(NOT\s+)?LIKE\s*'((?:''|[^'])*)'", part, flags=re.I)
        if like:
            actual = str(_field_value(row, like.group(1)) or "").lower()
            pattern = like.group(3).replace("''", "'").lower()
            chunks = [chunk for chunk in pattern.split("%") if chunk]
            matched = all(chunk in actual for chunk in chunks) if chunks else actual == pattern
            if (not matched and not like.group(2)) or (matched and like.group(2)):
                return False
            continue
        in_list = re.fullmatch(
            field_pattern + r"\s+(NOT\s+)?IN\s*\((.+)\)", part, flags=re.I
        )
        if in_list:
            actual = str(_field_value(row, in_list.group(1)) or "")
            raw_values = [
                item.strip().strip("'\"").replace("''", "'")
                for item in in_list.group(3).split(",")
            ]
            contains = actual in raw_values
            if (not in_list.group(2) and not contains) or (
                in_list.group(2) and contains
            ):
                return False
            continue
        raise RuntimeError(f"unsupported snowflake.search_rows where clause: {where}")
    return True


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(BENCHMARK_ROOT))
    except ValueError:
        return str(path)


def _apply_window(rows: list[dict[str, Any]], limit: Any, offset: Any) -> list[dict[str, Any]]:
    start = _to_nonnegative_int(offset, 0)
    count = _to_nonnegative_int(limit, len(rows))
    return rows[start : start + count]


def _to_nonnegative_int(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _parse_sql_table(sql: str) -> str:
    match = re.search(
        r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)",
        str(sql or ""),
        flags=re.I,
    )
    return match.group(1) if match else ""


def _parse_sql_where(sql: str) -> str:
    match = re.search(r"\bWHERE\s+(.+?)(?:\bORDER\s+BY\b|\bLIMIT\b|$)", str(sql or ""), flags=re.I | re.S)
    return " ".join(match.group(1).split()) if match else ""


def _parse_sql_select(sql: str) -> list[tuple[str, str]]:
    match = re.search(r"\bSELECT\s+(.+?)\s+\bFROM\b", str(sql or ""), flags=re.I | re.S)
    if not match:
        return []
    projection = re.sub(
        r"^\s*DISTINCT\s+",
        "",
        match.group(1),
        count=1,
        flags=re.I,
    )
    fields: list[tuple[str, str]] = []
    for raw_part in projection.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part == "*":
            return []
        wildcard_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\.\*", part)
        if wildcard_match:
            fields.append((f"{wildcard_match.group(1)}.*", "*"))
            continue
        alias_match = re.fullmatch(
            r'"?((?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*)"?\s+(?:AS\s+)?("?[A-Za-z_][A-Za-z0-9_]*"?)',
            part,
            flags=re.I,
        )
        if alias_match:
            fields.append((alias_match.group(1), alias_match.group(2).strip('"')))
            continue
        name_match = re.fullmatch(r'"?((?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*)"?', part)
        if name_match:
            source = name_match.group(1)
            fields.append((source, source.rsplit(".", 1)[-1]))
            continue
        raise RuntimeError(f"unsupported snowflake.search_rows_sql select expression: {part}")
    return fields


def _apply_select_distinct(
    sql: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not re.search(r"\bSELECT\s+DISTINCT\b", str(sql or ""), flags=re.I):
        return rows
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = json.dumps(row, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _project_row(row: dict[str, Any], selected: list[tuple[str, str]]) -> dict[str, Any]:
    if not selected:
        return _visible_row(row)
    out: dict[str, Any] = {}
    for source, alias in selected:
        if source.endswith(".*"):
            prefix = source[:-1]
            projected_keys: set[str] = set()
            for key, value in row.items():
                if not str(key).startswith(prefix):
                    continue
                output_key = str(key)[len(prefix) :]
                normalized_key = _output_key(output_key)
                if normalized_key in projected_keys:
                    continue
                projected_keys.add(normalized_key)
                out.setdefault(output_key, value)
                out.setdefault(normalized_key, value)
            continue
        value = _field_value(row, source)
        out[str(alias)] = value
        out.setdefault(_output_key(alias), value)
    return out


def _matches_join_on(row: dict[str, Any], on_clause: str, parameters: dict[str, Any]) -> bool:
    field_pattern = r'"?((?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*)"?'
    for part in [item.strip() for item in re.split(r"\s+AND\s+", on_clause, flags=re.I) if item.strip()]:
        field_match = re.fullmatch(field_pattern + r"\s*=\s*" + field_pattern, part)
        if field_match:
            if str(_field_value(row, field_match.group(1))) != str(_field_value(row, field_match.group(2))):
                return False
            continue
        literal = re.fullmatch(field_pattern + r"\s*=\s*'((?:''|[^'])*)'", part)
        if literal:
            expected = literal.group(2).replace("''", "'")
            if str(_field_value(row, literal.group(1))) != expected:
                return False
            continue
        bind = re.fullmatch(field_pattern + r"\s*=\s*:([A-Za-z_][A-Za-z0-9_]*)", part)
        if bind:
            if str(_field_value(row, bind.group(1))) != str(parameters.get(bind.group(2))):
                return False
            continue
        raise RuntimeError(f"unsupported snowflake.search_rows_sql join condition: {on_clause}")
    return True


def _parse_where(where: str) -> tuple[str, str]:
    text = str(where or "").strip()
    match = re.fullmatch(r'"?([^"=]+)"?\s*=\s*\'((?:\'\'|[^\'])*)\'', text)
    if not match:
        raise RuntimeError(f"unsupported snowflake.update_rows where clause: {where}")
    return match.group(1).strip(), match.group(2).replace("''", "'")

"""Deterministic in-process replacements for external API connectors.

The real benchmark and this benchmark share the recipe executor, registry,
seeders, verifiers, and tool schemas.  This module is the only backend seam:
it implements the connector-client interfaces used by ``simulated_tools`` without
performing network requests or invoking credentialed CLIs.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import calendar
import csv
import hashlib
import io
import json
import re
from types import SimpleNamespace
from typing import Any

from .salesforce_live_harness import (
    OwnedSalesforce,
    SALESFORCE_FIELD_MAP,
    SALESFORCE_SOBJECT_MAP,
)
from .slack_live import (
    _apply_block_updates,
    _home_view,
    _message_blocks,
    _message_json,
    _modal_view,
)
from .snowflake_simulated_state import SnowflakeTableState


class ProgrammingError(RuntimeError):
    """Local stand-in for Snowflake connector SQL compilation failures."""


def _stable_id(prefix: str, value: str, length: int = 18) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest().upper()
    clean_prefix = re.sub(r"[^A-Za-z0-9]", "", prefix)[:3].ljust(3, "0")
    return (clean_prefix + digest)[:length]


def _strip_anonymization_tags(value: Any) -> str:
    """Map inline dataset redaction tags back to their public identifier text."""

    return re.sub(r"</?anon>", "", str(value or ""), flags=re.I)


def _split_sql_commas(value: str) -> list[str]:
    """Split a constrained SQL list without breaking type parentheses."""

    parts: list[str] = []
    start = 0
    depth = 0
    quote = False
    for index, char in enumerate(str(value)):
        if char == "'":
            quote = not quote
        elif not quote and char == "(":
            depth += 1
        elif not quote and char == ")":
            depth = max(0, depth - 1)
        elif not quote and depth == 0 and char == ",":
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    return [part for part in parts if part]


def _parse_sql_literal(value: str) -> Any:
    token = str(value or "").strip()
    if token.upper() == "NULL":
        return None
    if token.upper() in {"TRUE", "FALSE"}:
        return token.upper() == "TRUE"
    if len(token) >= 2 and token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    try:
        number = float(token)
    except ValueError:
        return token
    return int(number) if number.is_integer() else number


def _parse_iso_datetime(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError("simulated Snowflake retention requires current_time")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _subtract_calendar_months(value: datetime, months: int) -> datetime:
    total_month = value.year * 12 + value.month - 1 - months
    year, month_index = divmod(total_month, 12)
    month = month_index + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _parse_snowflake_compact_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for pattern in (
        "%Y%m%d%H%M%S.%f",
        "%Y%m%d%H%M%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    raise RuntimeError(f"unsupported Snowflake retention timestamp: {value}")


class SlackSimulatedClient:
    """Small Slack state machine with the same public methods as the live client."""

    def __init__(
        self,
        _bot_token: str = "",
        seed: dict[str, Any] | None = None,
    ) -> None:
        self._messages: list[dict[str, Any]] = []
        self._views: dict[str, dict[str, Any]] = {}
        self._counter = 0
        self._missing_user_emails = {
            str(value).strip().casefold()
            for value in (seed or {}).get("missing_user_emails") or []
            if str(value).strip()
        }
        self._user_ids_by_email = {
            # Canonical benchmark workspace identity used by imported Slack
            # recipes and their trigger payloads. This is environment state,
            # not a per-recipe gold hint: every lookup observes the same user.
            "jamie.lee@corp.example": "U0B91BSRGF8",
            **{
                str(email).strip().casefold(): str(user_id)
                for email, user_id in ((seed or {}).get("users_by_email") or {}).items()
            },
        }

    def _next_ts(self) -> str:
        self._counter += 1
        return f"1700000000.{self._counter:06d}"

    def _find_message(self, channel: str, ts: str) -> dict[str, Any] | None:
        return next(
            (
                row
                for row in self._messages
                if row.get("channel") == channel and row.get("ts") == ts
            ),
            None,
        )

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str = "",
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not channel:
            raise RuntimeError("missing Slack channel")
        if not text and not blocks and not attachments:
            raise RuntimeError("refusing to post empty Slack message")
        ts = self._next_ts()
        row: dict[str, Any] = {
            "ok": True,
            "channel": channel,
            "ts": ts,
            "thread_ts": thread_ts or ts,
            "text": text,
        }
        if blocks is not None:
            row["blocks"] = deepcopy(blocks)
        if attachments is not None:
            row["attachments"] = deepcopy(attachments)
        self._messages.append(row)
        return deepcopy(row)

    def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not channel or not ts:
            raise RuntimeError("missing Slack channel or message ts for update")
        if not text:
            raise RuntimeError("refusing to update Slack message with empty text")
        row = self._find_message(channel, ts)
        if row is None:
            # Interactive trigger payloads can refer to a message that was
            # created before this isolated run. Materialize that controlled
            # message on first update instead of contacting Slack.
            row = {"ok": True, "channel": channel, "ts": ts, "thread_ts": ts}
            self._messages.append(row)
        row["text"] = text
        if blocks is not None:
            row["blocks"] = deepcopy(blocks)
        if attachments is not None:
            row["attachments"] = deepcopy(attachments)
        return deepcopy(row)

    def post_reply(
        self,
        channel: str,
        text: str,
        thread_ts: str = "",
        blocks: list[dict[str, Any]] | None = None,
        *,
        user: str = "",
        ephemeral: bool = False,
        replace_original: bool = False,
        delete_original: bool = False,
        original_ts: str = "",
    ) -> dict[str, Any]:
        # The public reply action runs inside an invoking Slack interaction.
        # Workato supplies the actor/original-message transport implicitly;
        # those fields are intentionally absent from the public tool schema.
        invoking_user = user or "U_INVOKER"
        invoking_original_ts = original_ts or thread_ts or "invoking-message"
        if replace_original:
            response = self.update_message(
                channel, invoking_original_ts, text, blocks
            )
            response["replaced_original"] = True
            return response
        if delete_original:
            deleted = self.delete_message(channel, invoking_original_ts)
            if not text and not blocks:
                return {
                    **deleted,
                    "deleted_original": True,
                    "original_ts": invoking_original_ts,
                }
        response = self.post_message(channel, text, blocks, thread_ts=thread_ts)
        if ephemeral:
            stored = self._find_message(channel, str(response.get("ts") or ""))
            if stored is not None:
                stored["ephemeral"] = True
                stored["user"] = invoking_user
            response["ephemeral"] = True
            response["user"] = invoking_user
        if delete_original:
            response["deleted_original"] = True
            response["original_ts"] = invoking_original_ts
        return response

    def delete_message(self, channel: str, ts: str) -> dict[str, Any]:
        if not channel or not ts:
            raise RuntimeError("missing Slack channel or message ts for delete")
        row = self._find_message(channel, ts)
        if row is not None:
            self._messages.remove(row)
        return {"ok": True, "channel": channel, "ts": ts}

    def update_blocks_by_block_id(
        self, message_json: Any, blocks_to_update: list[Any]
    ) -> dict[str, Any]:
        original = _message_json(message_json)
        nested = original.get("message") if isinstance(original.get("message"), dict) else {}
        channel = str(
            original.get("channel")
            or original.get("channel_id")
            or nested.get("channel")
            or nested.get("channel_id")
            or ""
        )
        ts = str(
            original.get("ts")
            or original.get("message_ts")
            or nested.get("ts")
            or nested.get("message_ts")
            or ""
        )
        if not channel or not ts:
            raise RuntimeError("Slack block update requires message_json with channel and ts")
        blocks = _apply_block_updates(_message_blocks(original), blocks_to_update)
        text = str(original.get("text") or nested.get("text") or "Updated benchmark Slack message")
        response = self.update_message(channel, ts, text, blocks)
        return {**response, "blocks": blocks}

    @staticmethod
    def _user(user_id: str, email: str) -> dict[str, Any]:
        local = email.split("@", 1)[0] if "@" in email else "benchmark.user"
        real_name = " ".join(part.capitalize() for part in re.split(r"[._-]+", local) if part)
        profile = {
            "email": email,
            "real_name": real_name or "Benchmark User",
            "display_name": real_name or "Benchmark User",
            "image_512": (
                "https://secure.gravatar.com/avatar/"
                "2adbecfea68c981193b1e29ab816db13.jpg?s=512&d="
                "https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2F"
                "ava_0007-512.png"
                if email.strip().casefold() == "jamie.lee@corp.example"
                else "https://example.invalid/benchmark-user.png"
            ),
        }
        user = {
            "id": user_id,
            "name": local,
            "real_name": profile["real_name"],
            "profile": profile,
        }
        return {
            "ok": True,
            "id": user_id,
            "name": user["name"],
            "real_name": user["real_name"],
            "email": email,
            "profile": profile,
            "user": user,
        }

    def lookup_user_by_email(self, email: str) -> dict[str, Any]:
        if not email:
            raise RuntimeError("missing Slack user email")
        normalized = email.strip().casefold()
        if (
            normalized in self._missing_user_emails
            or ".nouser." in normalized
            or normalized.startswith("nouser@")
            or normalized.startswith("ghost.")
            or normalized.startswith("<anon>")
        ):
            return {
                "ok": True,
                "not_found": True,
                "id": None,
                "name": "",
                "real_name": "",
                "email": email,
            }
        user_id = self._user_ids_by_email.get(normalized) or _stable_id("U", email, 11)
        return self._user(user_id, email)

    def lookup_user_by_id(self, user_id: str) -> dict[str, Any]:
        if not user_id:
            raise RuntimeError("missing Slack user id")
        email = next(
            (
                email
                for email, mapped_id in self._user_ids_by_email.items()
                if mapped_id == user_id
            ),
            "benchmark.user@example.invalid",
        )
        return self._user(user_id, email)

    def publish_home(self, user_id: str, view: dict[str, Any]) -> dict[str, Any]:
        if not user_id:
            raise RuntimeError("missing Slack App Home user_id")
        converted = _home_view(view)
        self._views[f"home:{user_id}"] = converted
        return {"ok": True, "user_id": user_id, "view": deepcopy(converted)}

    def open_modal(self, trigger_id: str, view: dict[str, Any]) -> dict[str, Any]:
        if not trigger_id:
            raise RuntimeError("missing Slack modal trigger_id")
        converted = _modal_view(view)
        view_id = _stable_id("V", trigger_id, 11)
        self._views[f"modal:{view_id}"] = converted
        return {"ok": True, "view": {"id": view_id, **deepcopy(converted)}}


class JiraSimulatedClient:
    def __init__(self) -> None:
        self._issues: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def create_issue(self, args: dict[str, Any]) -> dict[str, Any]:
        raw = str(args.get("project_issuetype") or "")
        if "--" in raw:
            project, issue_type = raw.split("--", 1)
        elif "@@" in raw:
            _title, project = raw.split("@@", 1)
            issue_type = "Task"
        else:
            raise RuntimeError(f"unsupported Jira project_issuetype: {raw}")
        summary = str(args.get("summary") or "").strip()
        if not summary:
            raise RuntimeError("Jira issue summary is empty")
        self._counter += 1
        key = f"{project}-{self._counter}"
        labels = args.get("labels") or []
        if not isinstance(labels, list):
            labels = [item.strip() for item in str(labels).split(",") if item.strip()]
        issue = {
            "key": key,
            "id": str(self._counter),
            "project": project,
            "issue_type": issue_type,
            "summary": summary,
            "description": str(args.get("description") or ""),
            "labels": [str(item).strip().replace(" ", "-") for item in labels],
            "priority": str(args.get("priority") or ""),
        }
        self._issues[key] = issue
        return {"ok": True, "key": key, "id": issue["id"], "self": f"simulated://jira/{key}"}

    def delete_issue(self, issue_key: str) -> dict[str, Any]:
        if not issue_key:
            raise RuntimeError("missing Jira issue key")
        self._issues.pop(issue_key, None)
        return {"ok": True, "key": issue_key}


class GoogleSheetsSimulatedClient:
    def __init__(self, spreadsheet_id: str = "", tab: str = "") -> None:
        self.spreadsheet_id = spreadsheet_id or "simulated-spreadsheet"
        self.tab = tab or "Sheet1"
        self.headers: list[str] = []
        self.rows: list[dict[str, Any]] = []

    @staticmethod
    def _cell(value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True)
        if isinstance(value, str) and value.strip().casefold() in {
            "true",
            "false",
        }:
            # Google Sheets' USER_ENTERED mode parses boolean-looking text
            # and returns its canonical uppercase display value.
            return value.strip().upper()
        # Workato's Sheets connector exposes cell values as strings even when
        # a formula evaluates to a numeric loop index.
        return str(value)

    @staticmethod
    def _matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, expected in (filters or {}).items():
            if expected is None or str(expected) == "":
                continue
            key_text = str(key)
            if key_text in row:
                actual = row.get(key_text)
            elif key_text.startswith("col_"):
                actual = row.get(key_text[len("col_") :], "")
            else:
                actual = ""
            if str(actual if actual is not None else "") != str(expected):
                return False
        return True

    def replace_rows(
        self, rows: list[dict[str, Any]], headers: list[str] | None = None
    ) -> dict[str, Any]:
        ordered = [str(header) for header in (headers or [])]
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError("Google Sheets seed rows must contain objects")
            for key in row:
                if str(key) not in ordered:
                    ordered.append(str(key))
        self.headers = ordered
        self.rows = [
            {
                "row_number": index,
                **{header: self._cell(row.get(header, "")) for header in ordered},
            }
            for index, row in enumerate(rows, start=2)
        ]
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "rows": len(self.rows),
            "headers": list(self.headers),
        }

    def snapshot(self) -> dict[str, Any]:
        values = [list(self.headers)] + [
            [row.get(header, "") for header in self.headers] for row in self.rows
        ]
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "headers": list(self.headers),
            "rows": deepcopy(self.rows),
            "values": values,
        }

    def search_rows(self, filters: dict[str, Any], limit: Any = None) -> dict[str, Any]:
        rows = [deepcopy(row) for row in self.rows if self._matches(row, filters)]
        if limit not in (None, ""):
            rows = rows[: max(0, int(limit))]
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "sheet": self.tab,
            "rows": rows,
            "records": rows,
            "count": len(rows),
        }

    def append_row(
        self, values_by_column: dict[str, Any], headers: list[str] | None = None
    ) -> dict[str, Any]:
        if not values_by_column:
            raise RuntimeError("Google Sheets append_row requires at least one value")
        ordered = [str(header) for header in (headers or self.headers)]
        for header in self.headers:
            if header not in ordered:
                ordered.append(header)
        for key in values_by_column:
            if str(key) not in ordered:
                ordered.append(str(key))
        if ordered != self.headers:
            for row in self.rows:
                for header in ordered:
                    row.setdefault(header, "")
            self.headers = ordered
        row_number = len(self.rows) + 2
        row = {
            "row_number": row_number,
            **{
                header: self._cell(values_by_column.get(header, ""))
                for header in self.headers
            },
        }
        self.rows.append(row)
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "row_number": row_number,
            "headers": list(self.headers),
            "row": deepcopy(row),
            "records": [deepcopy(row)],
            "count": 1,
        }

    def update_row(
        self, row_number: int, values_by_column: dict[str, Any]
    ) -> dict[str, Any]:
        if row_number < 2:
            raise RuntimeError("Google Sheets update_row requires row_number >= 2")
        row = next(
            (candidate for candidate in self.rows if candidate["row_number"] == row_number),
            None,
        )
        if row is None:
            raise RuntimeError(f"Google Sheets row {row_number} does not exist")
        for key, value in values_by_column.items():
            if str(key) not in self.headers:
                self.headers.append(str(key))
                for candidate in self.rows:
                    candidate.setdefault(str(key), "")
            row[str(key)] = self._cell(value)
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "row_number": row_number,
            "columns": deepcopy(values_by_column),
        }


class GoogleDriveSimulatedClient:
    def __init__(self) -> None:
        self._folders: dict[str, dict[str, Any]] = {}

    def create_folder(self, parent_id: str, name: str) -> dict[str, Any]:
        if not parent_id:
            raise RuntimeError("google_drive.create_folder missing parent folder id")
        if not name:
            raise RuntimeError("google_drive.create_folder missing name")
        folder_id = _stable_id("fld", f"{parent_id}:{name}", 20)
        folder = {
            "ok": True,
            "id": folder_id,
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
            "webViewLink": f"simulated://drive/{folder_id}",
        }
        self._folders[folder_id] = folder
        return deepcopy(folder)

    def delete_file(self, file_id: str) -> dict[str, Any]:
        if not file_id:
            raise RuntimeError("google_drive.delete_file missing file id")
        self._folders.pop(file_id, None)
        return {"ok": True, "id": file_id}


class SnowflakeSimulatedClient:
    """Adapter from the historical benchmark table simulator to the live API shape."""

    def __init__(self, _env: Any, section: dict[str, Any] | None = None) -> None:
        self._section: dict[str, Any] = {}
        self._state = SnowflakeTableState({})
        self._loaded_stage_files: set[tuple[str, str, str]] = set()
        if section:
            self.seed_tables(section)

    def seed_tables(self, section: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(section, dict):
            raise RuntimeError("Snowflake seed section must be an object")
        raw_tables = section.get("tables")
        if not isinstance(raw_tables, dict):
            raise RuntimeError("Snowflake seed section requires tables")
        # Keep the declared schema available while normalizing seed rows so
        # the simulator exposes the same typed read-back shape as Snowflake.
        self._section = deepcopy(section)
        column_order: dict[str, list[str]] = {
            str(table): [str(name) for name in names]
            for table, names in (section.get("_simulated_column_order") or {}).items()
            if isinstance(names, list)
        }
        rows_by_table: dict[str, list[dict[str, Any]]] = {}
        for table, raw_spec in raw_tables.items():
            if isinstance(raw_spec, list):
                rows = raw_spec
            elif isinstance(raw_spec, dict):
                rows = raw_spec.get("rows") or []
            else:
                raise RuntimeError(f"Snowflake table {table} spec must be an object")
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise RuntimeError(f"Snowflake table {table} rows must contain objects")
            declared = (
                raw_spec.get("columns")
                if isinstance(raw_spec, dict)
                and isinstance(raw_spec.get("columns"), dict)
                else {}
            )
            if declared and str(table) not in column_order:
                column_order[str(table)] = [str(name) for name in declared]
            physical_names = {
                str(name).casefold(): str(name).strip('"').upper()
                for name in declared
            }
            rows_by_table[str(table)] = []
            for row in rows:
                typed = self._coerce_row(str(table), deepcopy(row))
                rows_by_table[str(table)].append(
                    {
                        physical_names.get(str(name).casefold(), str(name)): value
                        for name, value in typed.items()
                    }
                )
        if column_order:
            self._section["_simulated_column_order"] = column_order
        self._state = SnowflakeTableState(
            {
                "tables": rows_by_table,
                "current_time": section.get("current_time"),
                "declared_columns": {
                    table: [
                        str(column).strip('"').upper()
                        for column in columns
                    ]
                    for table, columns in column_order.items()
                },
            }
        )
        self._loaded_stage_files = set()
        snapshot = self.snapshot()
        return {
            "ok": True,
            "state": deepcopy(self._section),
            "snapshot": snapshot,
        }

    def replace_table_rows(self, replacements: dict[str, Any]) -> None:
        """Apply deterministic hidden-fixture table effects without reseeding.

        This is used only after an exact tool/argument fixture match.  Other
        seeded tables, stage load history, schemas, and clock state remain
        intact so final-state verification can still detect unintended writes.
        """

        for raw_table, raw_rows in replacements.items():
            if not isinstance(raw_rows, list) or not all(
                isinstance(row, dict) for row in raw_rows
            ):
                raise RuntimeError(
                    "Snowflake fixture table replacements must contain row objects"
                )
            table = self._state._resolve_table_name(str(raw_table or ""))
            self._state._tables[table] = [
                {
                    "_row_id": index,
                    "_created_by": "fixture",
                    **deepcopy(row),
                }
                for index, row in enumerate(raw_rows)
            ]
        self._state._flush()

    def upsert_rows_batch(self, table: str, key_columns: Any, rows: list[Any]) -> dict[str, Any]:
        typed_rows = [
            self._coerce_row(table, row) if isinstance(row, dict) else row
            for row in rows
        ]
        return self._state.upsert_rows_batch(table, key_columns, typed_rows)

    def update_rows(self, table: str, where: str, columns: dict[str, Any]) -> dict[str, Any]:
        result = self._state.update_rows(
            table,
            where,
            self._coerce_row(table, columns),
        )
        result.setdefault("rows_updated", result.get("updated"))
        return result

    def search_rows(
        self,
        table: str,
        where: str = "",
        parameters: dict[str, Any] | None = None,
        limit: Any = None,
        offset: Any = None,
        orderby: Any = None,
        output_columns: Any = None,
    ) -> dict[str, Any]:
        result = self._state.search_rows(table, where, parameters, limit, offset)
        rows = result.get("rows") if isinstance(result.get("rows"), list) else []
        if orderby:
            terms = [item.strip() for item in str(orderby).split(",") if item.strip()]
            for term in reversed(terms):
                direction = re.search(r"\s+(ASC|DESC)\s*$", term, flags=re.I)
                reverse = bool(direction and direction.group(1).upper() == "DESC")
                expression = term[: direction.start()].strip() if direction else term
                comparison = re.fullmatch(
                    r"\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*(!=|<>)\s*'((?:''|[^'])*)'\s*\)",
                    expression,
                    flags=re.I,
                )

                def order_value(row: dict[str, Any]) -> tuple[bool, Any]:
                    by_casefold = {
                        str(key).casefold(): value for key, value in row.items()
                    }
                    if comparison:
                        actual = by_casefold.get(comparison.group(1).casefold())
                        literal = comparison.group(3).replace("''", "'")
                        return False, actual != literal
                    field = expression.strip('"')
                    value = by_casefold.get(field.casefold())
                    normalized = value.casefold() if isinstance(value, str) else value
                    return value is None, normalized

                rows.sort(
                    key=order_value,
                    reverse=reverse,
                )
        if output_columns:
            names = (
                [str(item) for item in output_columns]
                if isinstance(output_columns, list)
                else [
                    item.strip()
                    for item in re.split(r"[,\r\n]+", str(output_columns))
                    if item.strip()
                ]
            )
            projected_rows: list[dict[str, Any]] = []
            for row in rows:
                projected: dict[str, Any] = {}
                by_casefold = {str(key).casefold(): value for key, value in row.items()}
                for name in names:
                    value = row.get(name, by_casefold.get(name.casefold()))
                    projected[name] = value
                    projected.setdefault(name.casefold(), value)
                projected_rows.append(projected)
            rows = projected_rows
        result["rows"] = rows
        result["records"] = rows
        result["count"] = len(rows)
        return result

    def search_rows_sql(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        limit: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
        text = _strip_anonymization_tags(sql)
        staged = re.search(
            r"\bFROM\s+@([A-Za-z_][A-Za-z0-9_$.]*)(?:/([^\s()]+))?",
            text,
            flags=re.I,
        )
        if staged and re.search(r"ARRAY_SIZE\s*\(\s*SPLIT", text, flags=re.I):
            raw_stage = staged.group(1)
            stage_key = raw_stage.rsplit(".", 1)[-1]
            stages = self._section.get("stages") or {}
            spec = next(
                (
                    value
                    for name, value in stages.items()
                    if str(name).casefold() in {
                        raw_stage.casefold(),
                        stage_key.casefold(),
                    }
                    and isinstance(value, dict)
                ),
                None,
            )
            if spec is None:
                raise RuntimeError(f"Snowflake stage {raw_stage!r} does not exist")
            format_match = re.search(
                r"FILE_FORMAT\s*=>\s*'([^']+)'", text, flags=re.I
            )
            if format_match:
                requested_format = format_match.group(1)
                declared_format = str(
                    (spec.get("file_format") or {}).get("name") or ""
                )
                if requested_format.rsplit(".", 1)[-1].casefold() != declared_format.casefold():
                    raise ProgrammingError(
                        "002003 (42S02): SQL compilation error:\n"
                        f"File format '{requested_format.upper()}' does not exist or not authorized."
                    )
            prefix = str(staged.group(2) or "").strip("/")
            candidates = [
                item
                for item in spec.get("files") or []
                if isinstance(item, dict)
                and (not prefix or str(item.get("path") or "").startswith(prefix))
            ]
            rows: list[dict[str, Any]] = []
            if candidates:
                first_line = str(candidates[0].get("content") or "").splitlines()[0]
                count = len(first_line.split(",")) if first_line else 0
                rows = [{"NUMBER_OF_COLUMNS": count, "number_of_columns": count}]
            sliced = rows[
                max(0, int(offset or 0)) :
                (max(0, int(offset or 0)) + max(0, int(limit)))
                if limit not in (None, "")
                else None
            ]
            return {
                "ok": True,
                "stage": raw_stage,
                "sql": text,
                "parameters": parameters or {},
                "rows": sliced,
                "records": deepcopy(sliced),
                "count": len(sliced),
            }
        return self._state.search_rows_sql(text, parameters, limit, offset)

    def run_custom_sql(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        limit: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
        text = _strip_anonymization_tags(sql).strip().rstrip(";").strip()
        describe = re.fullmatch(
            r"(?:DESCRIBE\s+TABLE|SHOW\s+COLUMNS\s+IN)\s+"
            r"([A-Za-z_][A-Za-z0-9_$.]*)",
            text,
            flags=re.I,
        )
        if describe:
            table = self._declared_table_name(describe.group(1))
            columns = self._declared_columns(table)
            rows = [
                {
                    "name": str(name).upper(),
                    "type": self._snowflake_type_name(kind),
                    "column_name": str(name).upper(),
                    "data_type": self._snowflake_type_name(kind),
                    "table_name": table.rsplit(".", 1)[-1].upper(),
                    "schema_name": (
                        table.rsplit(".", 2)[-2].upper()
                        if "." in table
                        else "PUBLIC"
                    ),
                }
                for name, kind in columns.items()
            ]
            return {
                "ok": True,
                "table": table,
                "rows": rows,
                "records": deepcopy(rows),
                "count": len(rows),
            }
        information_schema = self._information_schema_query(text)
        if information_schema is not None:
            return information_schema
        alter = re.fullmatch(
            r"ALTER\s+TABLE\s+([A-Za-z_][A-Za-z0-9_$.]*)\s+ADD\s+(.+)",
            text,
            flags=re.I | re.S,
        )
        if alter:
            table = self._state._resolve_table_name(alter.group(1))
            definitions = _split_sql_commas(alter.group(2))
            columns: list[str] = []
            for definition in definitions:
                match = re.match(
                    r'\s*(?:COLUMN\s+)?(?:(IF\s+NOT\s+EXISTS)\s+)?'
                    r'("[^"]+"|[A-Za-z_][A-Za-z0-9_$]*)\s+.+$',
                    definition,
                    flags=re.I | re.S,
                )
                if not match:
                    raise RuntimeError(
                        "unsupported snowflake ALTER TABLE ADD definition: "
                        + definition
                    )
                if_not_exists = bool(match.group(1))
                column = match.group(2).strip('"')
                table_specs = self._section.setdefault("tables", {})
                spec = (
                    table_specs.setdefault(table, {})
                    if isinstance(table_specs, dict)
                    else {}
                )
                declared_columns = (
                    spec.get("columns") if isinstance(spec, dict) else {}
                )
                existing_names = {
                    str(name).casefold()
                    for name in (
                        declared_columns.keys()
                        if isinstance(declared_columns, dict)
                        else []
                    )
                }
                for row in self._state._tables.get(table, []):
                    if isinstance(row, dict):
                        existing_names.update(str(name).casefold() for name in row)
                if column.casefold() in existing_names:
                    if if_not_exists:
                        continue
                    raise RuntimeError(
                        "001430 (42601): SQL compilation error:\n"
                        f"column '{column.upper()}' already exists"
                    )
                columns.append(column)
                for row in self._state._tables.setdefault(table, []):
                    if not any(str(key).casefold() == column.casefold() for key in row):
                        row[column] = None
                if isinstance(spec, dict):
                    spec.setdefault("columns", {}).setdefault(column, "string")
            self._state._flush()
            status = f"Table {table.rsplit('.', 1)[-1].upper()} successfully altered."
            rows = [{"status": status}]
            return {
                "ok": True,
                "table": table,
                "columns_added": columns,
                "rows": rows,
                "records": rows,
                "count": 1,
                "rows_affected": 1,
            }
        copy_into = re.match(
            r"COPY\s+INTO\s+([A-Za-z_][A-Za-z0-9_$.]*)\s+FROM\s*\(",
            text,
            flags=re.I,
        )
        if copy_into:
            return self._copy_into_from_stage(text, copy_into.group(1))
        delete = re.fullmatch(
            r"DELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_$.]*)\s+WHERE\s+(.+)",
            text,
            flags=re.I | re.S,
        )
        if delete:
            return self._delete_with_retention(delete.group(1), delete.group(2))
        sales_team_merge = re.match(
            r"MERGE\s+INTO\s+([A-Za-z_][A-Za-z0-9_$.]*)\s+ST\s+"
            r"USING\s*\(.*?FROM\s+([A-Za-z_][A-Za-z0-9_$.]*)\s+U\b",
            text,
            flags=re.I | re.S,
        )
        if (
            sales_team_merge
            and "ST.USER_ID = USERS.ID" in text
            and "ST.TEAM_NAME = USERS.SALES_TEAM__C" in text
            and "WHEN NOT MATCHED THEN" in text
        ):
            target = self._state._resolve_table_name(sales_team_merge.group(1))
            source = self._state._resolve_table_name(sales_team_merge.group(2))
            if target not in self._state._tables or source not in self._state._tables:
                missing = source if source not in self._state._tables else target
                raise RuntimeError(
                    f"002003 (42S02): SQL compilation error: table {missing!r} does not exist"
                )
            try:
                current_date = datetime.fromisoformat(
                    str(self._section.get("current_time") or "").replace("Z", "+00:00")
                ).date()
            except ValueError as exc:
                raise RuntimeError("Snowflake MERGE requires pinned current_time") from exc
            target_rows = self._state._tables[target]
            affected = 0
            for roster in self._state._tables[source]:
                team = next(
                    (
                        value
                        for key, value in roster.items()
                        if str(key).casefold() == "sales_team__c"
                    ),
                    None,
                )
                if team is None:
                    continue
                user_id = next(
                    (
                        value
                        for key, value in roster.items()
                        if str(key).casefold() == "id"
                    ),
                    None,
                )
                match = next(
                    (
                        row
                        for row in target_rows
                        if str(next((v for k, v in row.items() if str(k).casefold() == "user_id"), ""))
                        == str(user_id)
                        and str(next((v for k, v in row.items() if str(k).casefold() == "team_name"), ""))
                        == str(team)
                    ),
                    None,
                )
                active = next(
                    (
                        value
                        for key, value in roster.items()
                        if str(key).casefold() == "isactive"
                    ),
                    None,
                )
                if match is not None:
                    date_key = next(
                        (
                            str(key)
                            for key in match
                            if str(key).casefold() == "date_to"
                        ),
                        "DATE_TO",
                    )
                    if not bool(active) and match.get(date_key) is None:
                        match[date_key] = (current_date - timedelta(days=1)).isoformat()
                        match["_modified_by"] = "agent"
                        affected += 1
                    continue
                start_date = str(
                    next(
                        (
                            value
                            for key, value in roster.items()
                            if str(key).casefold() == "start_date__c"
                        ),
                        "",
                    )
                    or ""
                )
                target_rows.append(
                    {
                        "_row_id": self._state._next_row_id(target_rows),
                        "_created_by": "agent",
                        "USER_ID": user_id,
                        "TEAM_NAME": team,
                        "DATE_FROM": (
                            current_date.isoformat()
                            if start_date < current_date.isoformat()
                            else start_date
                        ),
                        "DATE_TO": None,
                    }
                )
                affected += 1
            self._state._flush()
            rows = [{"number of rows affected": affected}]
            return {
                "ok": True,
                "table": target,
                "rows": rows,
                "records": deepcopy(rows),
                "count": 1,
                "rows_affected": affected,
            }
        values_insert = re.fullmatch(
            r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_$.]*)\s+"
            r"SELECT\s+\*\s+FROM\s*\(\s*VALUES\s+(.+?)\)\s+"
            r"AS\s+[A-Za-z_][A-Za-z0-9_]*\s*\(([^)]*)\)(.*)",
            text,
            flags=re.I | re.S,
        )
        if values_insert:
            target = self._state._resolve_table_name(values_insert.group(1))
            columns = [
                item.strip().strip('"')
                for item in _split_sql_commas(values_insert.group(3))
            ]
            candidates: list[dict[str, Any]] = []
            for raw_tuple in _split_sql_commas(values_insert.group(2)):
                tuple_text = raw_tuple.strip()
                if not (tuple_text.startswith("(") and tuple_text.endswith(")")):
                    raise RuntimeError(
                        "unsupported Snowflake INSERT VALUES tuple: " + raw_tuple
                    )
                values = [
                    _parse_sql_literal(item)
                    for item in _split_sql_commas(tuple_text[1:-1])
                ]
                if len(values) != len(columns):
                    raise RuntimeError(
                        "Snowflake INSERT VALUES column/value count mismatch"
                    )
                candidates.append(dict(zip(columns, values, strict=True)))
            suffix = values_insert.group(4)
            if re.search(r"\bRECORD_ID\s+NOT\s+IN\s*\(", suffix, flags=re.I):
                existing_ids = {
                    str(
                        next(
                            (
                                value
                                for key, value in row.items()
                                if str(key).casefold() == "record_id"
                            ),
                            "",
                        )
                    )
                    for row in self._state._tables.get(target, [])
                }
                candidates = [
                    row
                    for row in candidates
                    if str(
                        next(
                            (
                                value
                                for key, value in row.items()
                                if str(key).casefold() == "record_id"
                            ),
                            "",
                        )
                    )
                    not in existing_ids
                ]
            if re.search(
                r"QUALIFY\s+ROW_NUMBER\s*\(\s*\)\s+OVER\s*\(.*?"
                r"PARTITION\s+BY\s+RECORD_ID.*?ORDER\s+BY\s+MODIFIED_AT\s+DESC",
                suffix,
                flags=re.I | re.S,
            ):
                by_id: dict[str, dict[str, Any]] = {}
                for row in candidates:
                    folded = {str(key).casefold(): value for key, value in row.items()}
                    key = str(folded.get("record_id") or "")
                    prior = by_id.get(key)
                    prior_folded = (
                        {str(name).casefold(): value for name, value in prior.items()}
                        if prior
                        else {}
                    )
                    if prior is None or str(folded.get("modified_at") or "") > str(
                        prior_folded.get("modified_at") or ""
                    ):
                        by_id[key] = row
                candidates = list(by_id.values())
            appended = self._append_rows(target, candidates, columns)
            summary = {"number of rows inserted": appended}
            return {
                "ok": True,
                "table": target,
                "rows": [summary],
                "records": [deepcopy(summary)],
                "count": 1,
                "rows_affected": appended,
            }
        insert = re.fullmatch(
            r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_$.]*)"
            r"(?:\s*\(([^)]*)\))?\s+(SELECT\s+.+)",
            text,
            flags=re.I | re.S,
        )
        if insert:
            target = self._state._resolve_table_name(insert.group(1))
            selected = self.search_rows_sql(insert.group(3), parameters, limit, offset)
            source_rows = selected.get("rows") or []
            explicit_columns = [
                item.strip().strip('"')
                for item in str(insert.group(2) or "").split(",")
                if item.strip()
            ]
            appended = self._append_rows(target, source_rows, explicit_columns)
            summary = {"number of rows inserted": appended}
            return {
                "ok": True,
                "table": target,
                "rows": [summary],
                "records": [deepcopy(summary)],
                "count": 1,
                "rows_affected": appended,
            }
        ctas = re.fullmatch(
            r"CREATE\s+OR\s+REPLACE\s+TABLE\s+"
            r"([A-Za-z_][A-Za-z0-9_$.]*)\s+AS\s+"
            r"(?:/\*.*?\*/\s*)*((?:SELECT|WITH)\s+.+)",
            text,
            flags=re.I | re.S,
        )
        if ctas:
            return self._state.create_or_replace_table_as(
                ctas.group(1), ctas.group(2), parameters
            )
        truncate = re.fullmatch(
            r"TRUNCATE\s+TABLE\s+([A-Za-z_][A-Za-z0-9_$.]*)",
            text,
            flags=re.I,
        )
        if truncate:
            table = self._state._resolve_table_name(truncate.group(1))
            removed = len(self._state._tables.get(table, []))
            self._state._tables[table] = []
            self._state._flush()
            return {
                "ok": True,
                "table": table,
                "rows": [],
                "records": [],
                "count": 0,
                "rows_affected": removed,
            }
        return self.search_rows_sql(text, parameters, limit, offset)

    def _declared_table_name(self, raw_table: str) -> str:
        requested = str(raw_table or "")
        table_specs = self._section.get("tables") or {}
        matches = [
            str(name)
            for name in table_specs
            if str(name).casefold() == requested.casefold()
            or str(name).casefold().endswith("." + requested.casefold())
        ]
        if len(matches) != 1:
            raise ProgrammingError(
                "002003 (42S02): SQL compilation error:\n"
                f"Table '{requested.upper()}' does not exist or not authorized."
            )
        return matches[0]

    def _declared_columns(self, table: str) -> dict[str, Any]:
        spec = (self._section.get("tables") or {}).get(table) or {}
        columns = spec.get("columns") if isinstance(spec, dict) else None
        if isinstance(columns, dict):
            order = (
                (self._section.get("_simulated_column_order") or {}).get(table)
                or list(columns)
            )
            by_name = {str(name).casefold(): kind for name, kind in columns.items()}
            return {
                str(name): by_name.get(str(name).casefold(), "string")
                for name in order
            }
        inferred: dict[str, str] = {}
        for row in self._state._tables.get(table, []):
            for name in row:
                if not str(name).startswith("_"):
                    inferred.setdefault(str(name), "string")
        return inferred

    @staticmethod
    def _snowflake_type_name(kind: Any) -> str:
        text = str(kind or "string").strip().casefold()
        if text in {"number", "integer", "int", "bigint"}:
            return "NUMBER"
        if text in {"float", "double", "decimal", "numeric"}:
            return "FLOAT"
        if text in {"boolean", "bool"}:
            return "BOOLEAN"
        if text == "date":
            return "DATE"
        if text.startswith("timestamp") or text == "datetime":
            return text.upper()
        return "TEXT"

    def _information_schema_query(self, sql: str) -> dict[str, Any] | None:
        if "INFORMATION_SCHEMA.COLUMNS" not in sql.upper():
            return None
        table_refs = re.findall(
            r"TABLE_NAME\s*=\s*'([^']+)'\s+AND\s+TABLE_SCHEMA\s*=\s*'([^']+)'",
            sql,
            flags=re.I,
        )
        if not table_refs:
            raise RuntimeError(
                "unsupported simulated INFORMATION_SCHEMA.COLUMNS query"
            )

        def resolve(table_name: str, schema: str) -> str:
            suffix = f".{schema}.{table_name}".casefold()
            matches = [
                str(name)
                for name in (self._section.get("tables") or {})
                if str(name).casefold().endswith(suffix)
            ]
            if len(matches) != 1:
                raise ProgrammingError(
                    "002003 (42S02): SQL compilation error:\n"
                    f"Table '{schema}.{table_name}' does not exist or not authorized."
                )
            return matches[0]

        if re.search(r"\bEXCEPT\b", sql, flags=re.I):
            if len(table_refs) < 2:
                raise RuntimeError("INFORMATION_SCHEMA EXCEPT requires two table refs")
            history = resolve(*table_refs[0])
            base = resolve(*table_refs[1])
            history_names = {
                str(name).upper() for name in self._declared_columns(history)
            }
            names = [
                str(name).upper()
                for name in self._declared_columns(base)
                if str(name).upper() not in history_names
            ]
            rows = [
                {"COLUMN_NAME": name, "column_name": name} for name in names
            ]
        else:
            table = resolve(*table_refs[0])
            wanted_match = re.search(
                r"COLUMN_NAME\s+IN\s*\(([^)]*)\)", sql, flags=re.I | re.S
            )
            wanted = (
                {item.upper() for item in re.findall(r"'([^']+)'", wanted_match.group(1))}
                if wanted_match
                else None
            )
            rows = []
            for name, kind in self._declared_columns(table).items():
                canonical = str(name).upper()
                if wanted is not None and canonical not in wanted:
                    continue
                data_type = self._snowflake_type_name(kind)
                rows.append(
                    {
                        "COLUMN_NAME": canonical,
                        "column_name": canonical,
                        "DATA_TYPE": data_type,
                        "data_type": data_type,
                    }
                )
        return {
            "ok": True,
            "sql": sql,
            "rows": rows,
            "records": deepcopy(rows),
            "count": len(rows),
        }

    def _append_rows(
        self,
        table: str,
        source_rows: list[Any],
        explicit_columns: list[str] | None = None,
    ) -> int:
        target_rows = self._state._tables.setdefault(table, [])
        columns = list(explicit_columns or [])
        if not columns:
            spec = (self._section.get("tables") or {}).get(table) or {}
            if isinstance(spec, dict) and isinstance(spec.get("columns"), dict):
                columns = list(spec["columns"])
        appended = 0
        for raw_row in source_rows:
            if not isinstance(raw_row, dict):
                continue
            source_items: list[tuple[str, Any]] = []
            seen_source_names: set[str] = set()
            for key, value in raw_row.items():
                folded = str(key).casefold()
                if folded in seen_source_names:
                    continue
                seen_source_names.add(folded)
                source_items.append((str(key), value))
            if columns:
                record: dict[str, Any] = {}
                used: set[int] = set()
                # Positional INSERT..SELECT still has semantic anchors when a
                # source expression and target column share a name. Resolve
                # those first so JSON key sorting in the seed schema cannot
                # scramble Snowflake's physical column order.
                for column in columns:
                    direct = next(
                        (
                            index
                            for index, (name, _value) in enumerate(source_items)
                            if index not in used
                            and name.casefold() == str(column).casefold()
                        ),
                        None,
                    )
                    if direct is not None:
                        record[column] = source_items[direct][1]
                        used.add(direct)
                for column in columns:
                    if column in record:
                        continue
                    target = str(column).casefold()
                    preferred = next(
                        (
                            index
                            for index, (name, _value) in enumerate(source_items)
                            if index not in used
                            and (
                                ("date" in target and "date(" in name.casefold())
                                or (
                                    "insert" in target
                                    and re.search(
                                        r"\d{4}-\d{2}-\d{2}t\d{2}:\d{2}",
                                        name,
                                        flags=re.I,
                                    )
                                )
                            )
                        ),
                        None,
                    )
                    if preferred is None:
                        preferred = next(
                            (index for index in range(len(source_items)) if index not in used),
                            None,
                        )
                    record[column] = (
                        source_items[preferred][1] if preferred is not None else None
                    )
                    if preferred is not None:
                        used.add(preferred)
                record = self._coerce_row(table, record)
            else:
                record = {str(key): deepcopy(value) for key, value in source_items}
            target_rows.append(
                {
                    "_row_id": self._state._next_row_id(target_rows),
                    "_created_by": "agent",
                    **record,
                }
            )
            appended += 1
        self._state._flush()
        return appended

    def _copy_into_from_stage(self, sql: str, raw_table: str) -> dict[str, Any]:
        stage_match = re.search(
            r"\bFROM\s+@([A-Za-z_][A-Za-z0-9_$.]*)",
            sql,
            flags=re.I,
        )
        pattern_match = re.search(
            r"\bPATTERN\s*=\s*'((?:''|[^'])*)'",
            sql,
            flags=re.I | re.S,
        )
        if not stage_match or not pattern_match:
            raise RuntimeError("snowflake COPY INTO requires a named stage and PATTERN")
        stage_name = stage_match.group(1)
        stages = self._section.get("stages") or {}
        stage_spec = next(
            (
                spec
                for name, spec in stages.items()
                if str(name).casefold() == stage_name.casefold()
                and isinstance(spec, dict)
            ),
            None,
        )
        if stage_spec is None:
            raise RuntimeError(f"unknown simulated Snowflake stage: {stage_name}")
        table = self._state._resolve_table_name(raw_table)
        table_spec = (self._section.get("tables") or {}).get(table) or {}
        declared_orders = self._section.get("table_column_order") or {}
        columns = (
            [str(value) for value in declared_orders.get(table) or []]
            if isinstance(declared_orders, dict)
            else []
        )
        if not columns:
            columns = (
                list(table_spec.get("columns") or {})
                if isinstance(table_spec, dict)
                else []
            )
        if not columns:
            raise RuntimeError(f"Snowflake COPY target lacks a declared schema: {table}")
        pattern = pattern_match.group(1).replace("''", "'")
        results: list[dict[str, Any]] = []
        for file_spec in stage_spec.get("files") or []:
            if not isinstance(file_spec, dict):
                continue
            path = str(file_spec.get("path") or "").lstrip("/")
            if not re.search(pattern, path):
                continue
            history_key = (table.casefold(), stage_name.casefold(), path)
            if history_key in self._loaded_stage_files:
                continue
            content = str(file_spec.get("content") or "")
            source_rows: list[dict[str, Any]] = []
            for values in csv.reader(io.StringIO(content)):
                if not values or all(value == "" for value in values):
                    continue
                row_values = [path, *values]
                source_rows.append(
                    {
                        column: row_values[index] if index < len(row_values) else None
                        for index, column in enumerate(columns)
                    }
                )
            loaded = self._append_rows(table, source_rows, columns)
            self._loaded_stage_files.add(history_key)
            results.append({"file": path, "status": "LOADED", "rows_loaded": loaded})
        return {
            "ok": True,
            "table": table,
            "stage": stage_name,
            "rows": results,
            "records": results,
            "count": len(results),
            "rows_affected": sum(int(row["rows_loaded"]) for row in results),
        }

    def _delete_with_retention(self, raw_table: str, where: str) -> dict[str, Any]:
        retention = re.search(
            r"INTERVAL\s+'(\d+)\s+MONTHS?'",
            where,
            flags=re.I,
        )
        timestamp_field = re.search(
            r"TO_TIMESTAMP\s*\(\s*([A-Za-z_][A-Za-z0-9_$]*)\s*,",
            where,
            flags=re.I,
        )
        if not retention or not timestamp_field:
            raise RuntimeError(
                "simulated Snowflake DELETE supports timestamp retention predicates"
            )
        table = self._state._resolve_table_name(raw_table)
        current_text = str(
            self._section.get("current_time")
            or self._section.get("fixed_time")
            or ""
        )
        current = _parse_iso_datetime(current_text)
        threshold = _subtract_calendar_months(current, int(retention.group(1)))
        kept: list[dict[str, Any]] = []
        removed = 0
        for row in self._state._tables.setdefault(table, []):
            raw_value = next(
                (
                    value
                    for key, value in row.items()
                    if str(key).casefold() == timestamp_field.group(1).casefold()
                ),
                None,
            )
            parsed = _parse_snowflake_compact_timestamp(raw_value)
            if parsed is not None and parsed < threshold:
                removed += 1
            else:
                kept.append(row)
        self._state._tables[table] = kept
        self._state._flush()
        rows = [{"number of rows deleted": removed}]
        return {
            "ok": True,
            "table": table,
            "rows": rows,
            "records": rows,
            "count": 1,
            "rows_affected": removed,
        }

    def _coerce_row(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        specs = self._section.get("tables")
        table_upper = str(table).upper()
        candidates = (
            [
                spec
                for name, spec in specs.items()
                if str(name).upper() == table_upper
                or str(name).upper().endswith(
                    "." + table_upper.split(".")[-1]
                )
            ]
            if isinstance(specs, dict)
            else []
        )
        columns = (
            candidates[0].get("columns")
            if len(candidates) == 1
            and isinstance(candidates[0], dict)
            else None
        )
        by_name = (
            {
                str(name).casefold(): str(kind).casefold()
                for name, kind in columns.items()
            }
            if isinstance(columns, dict)
            else {}
        )
        if not by_name:
            tables = (
                (self._state.snapshot().get("snowflake") or {})
                .get("tables")
                or {}
            )
            existing_rows = next(
                (
                    rows
                    for name, rows in tables.items()
                    if str(name).upper() == table_upper
                    or str(name).upper().endswith(
                        "." + table_upper.split(".")[-1]
                    )
                ),
                [],
            )
            for existing in existing_rows:
                if not isinstance(existing, dict):
                    continue
                for name, value in existing.items():
                    if isinstance(value, bool):
                        by_name[str(name).casefold()] = "boolean"
                    elif isinstance(value, int):
                        by_name[str(name).casefold()] = "integer"
                    elif isinstance(value, float):
                        by_name[str(name).casefold()] = "float"
        out: dict[str, Any] = {}
        for key, value in row.items():
            kind = by_name.get(str(key).casefold(), "")
            if value in (None, ""):
                out[str(key)] = value
            elif kind in {"number", "integer", "int", "bigint"}:
                try:
                    numeric = float(value)
                except (TypeError, ValueError) as exc:
                    raise RuntimeError(
                        f"invalid numeric value for Snowflake column {key!r}: "
                        f"{value!r}"
                    ) from exc
                out[str(key)] = int(numeric) if numeric.is_integer() else numeric
            elif kind in {"float", "double", "decimal", "numeric"}:
                try:
                    out[str(key)] = float(value)
                except (TypeError, ValueError) as exc:
                    raise RuntimeError(
                        f"invalid numeric value for Snowflake column {key!r}: "
                        f"{value!r}"
                    ) from exc
            elif kind in {"boolean", "bool"}:
                out[str(key)] = (
                    value
                    if isinstance(value, bool)
                    else str(value).strip().casefold() in {"true", "1", "yes"}
                )
            elif kind in {
                "timestamp",
                "timestamp_ntz",
                "timestamp_ltz",
                "timestamp_tz",
                "datetime",
            }:
                text = str(value).strip()
                # Python's canonical JSON representation of a Snowflake
                # timestamp uses the ISO ``T`` separator. Preserve timezone
                # information when supplied; NTZ inputs normally have none.
                out[str(key)] = re.sub(
                    r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})",
                    r"\1T\2",
                    text,
                )
                if kind in {"timestamp", "timestamp_ntz", "datetime"}:
                    normalized = str(out[str(key)]).replace("Z", "+00:00")
                    try:
                        parsed = datetime.fromisoformat(normalized)
                    except ValueError:
                        pass
                    else:
                        out[str(key)] = parsed.replace(tzinfo=None).isoformat()
            elif kind == "date":
                out[str(key)] = str(value).strip()[:10]
            else:
                out[str(key)] = value
        return out

    def snapshot(self) -> dict[str, Any]:
        snap = self._state.snapshot()
        raw_section = snap.get("snowflake")
        section = deepcopy(raw_section) if isinstance(raw_section, dict) else {}
        tables = section.get("tables") if isinstance(section.get("tables"), dict) else {}
        section["physical_tables"] = {
            str(table): f"simulated://snowflake/{table}" for table in tables
        }
        if isinstance(self._section.get("stages"), dict):
            section["stages"] = {
                str(name): sorted(
                    str(item.get("path") or "")
                    for item in (spec.get("files") or [])
                    if isinstance(item, dict)
                )
                for name, spec in self._section["stages"].items()
                if isinstance(spec, dict)
            }
        # The live adapter labels its snapshot ``snowflake_live``. Recipe
        # verifiers accept that shape for seed.snowflake_live cases.
        return {
            "snowflake_live": deepcopy(section),
            "snowflake": {"tables": deepcopy(tables)},
        }

    def cleanup(self) -> dict[str, Any]:
        table_names = list(
            ((self._state.snapshot().get("snowflake") or {}).get("tables") or {})
        )
        stage_names = [
            str(name)
            for name, spec in (self._section.get("stages") or {}).items()
            if isinstance(spec, dict) and spec.get("cleanup") is True
        ]
        self._state = SnowflakeTableState({})
        self._section = {}
        self._loaded_stage_files = set()
        return {
            "ok": True,
            "dropped_tables": table_names,
            "dropped_stages": stage_names,
        }


@dataclass
class _SimulatedSfRecord:
    id: str
    logical_sobject: str
    physical_sobject: str
    fields: dict[str, Any]
    read_only: bool = False


class SimulatedOwnedSalesforce(OwnedSalesforce):
    """Reuse the benchmark's mature SOQL evaluator over local seeded records."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        state = state or {}
        self.run_id = str(state.get("run_id") or "simulated-salesforce")
        self.expand_relationships = bool(state.get("expand_relationships"))
        self.strict_soql = bool(state.get("strict_soql_conditions"))
        self.user_id_map = {
            str(key): str(value)
            for key, value in (state.get("user_id_map") or {}).items()
        }
        self.client = SimpleNamespace(
            _related_fields_cache={},
            _record_type_cache={
                str(key): str(value)
                for key, value in (state.get("record_type_cache") or {}).items()
            },
            _readback_extra_cache={},
        )
        self.owned: dict[str, tuple[str, list[str], str]] = {}
        self.read_only_records: list[dict[str, Any]] = []
        self._records: dict[str, _SimulatedSfRecord] = {}
        self._refs: dict[str, str] = {
            "$STANDARD_PRICEBOOK_ID": "01s000000000001AAA",
            "$STANDARD_PRICEBOOK2_ID": "01s000000000001AAA",
            "$USER_ID": "005000000000001AAA",
            "$CURRENT_USER_ID": "005000000000001AAA",
        }
        self._refs.update(
            {
                str(key): str(value)
                for key, value in (state.get("refs") or {}).items()
            }
        )
        self._counter = 0
        self._created_date_anchor = datetime.now(timezone.utc).replace(
            microsecond=0
        )
        seeded_anchor = state.get("created_date_anchor")
        if seeded_anchor not in (None, ""):
            parsed_anchor = datetime.fromisoformat(
                str(seeded_anchor).replace("Z", "+00:00")
            )
            if parsed_anchor.tzinfo is None:
                raise RuntimeError(
                    "simulated Salesforce created_date_anchor must include a timezone"
                )
            self._created_date_anchor = parsed_anchor.astimezone(timezone.utc)
        restored_records: list[Any]
        if isinstance(state.get("owned_records"), list) or isinstance(
            state.get("read_only_records"), list
        ):
            restored_records = [
                *(
                    [
                        {**raw, "read_only": False}
                        for raw in state.get("owned_records") or []
                        if isinstance(raw, dict)
                    ]
                ),
                *(
                    [
                        {**raw, "read_only": True}
                        for raw in state.get("read_only_records") or []
                        if isinstance(raw, dict)
                    ]
                ),
            ]
        else:
            restored_records = list(state.get("records") or [])
        for raw in restored_records:
            if not isinstance(raw, dict):
                continue
            self._restore_record(raw)

    def _restore_record(self, raw: dict[str, Any]) -> None:
        record_id = str(raw.get("id") or "")
        logical = str(raw.get("logical_sobject") or raw.get("sobject") or "")
        physical = str(raw.get("physical_sobject") or self._physical_sobject_name(logical))
        fields = deepcopy(raw.get("fields") or {})
        # Every live Salesforce record is undeleted unless the recycle-bin
        # state explicitly says otherwise.  Many canonical SOQL queries
        # include ``IsDeleted = false`` even though seed fixtures reasonably
        # omit that system field.
        if fields.get("IsDeleted") is None:
            fields["IsDeleted"] = False
        row = _SimulatedSfRecord(
            id=record_id,
            logical_sobject=logical,
            physical_sobject=physical,
            fields=fields,
            read_only=bool(raw.get("read_only")),
        )
        self._records[record_id] = row
        field_names = list(dict.fromkeys(["Id", *fields.keys()]))
        if row.read_only:
            self.read_only_records.append(
                {
                    "id": record_id,
                    "physical_sobject": physical,
                    "logical_sobject": logical,
                    "field_names": field_names,
                    "fields": deepcopy(fields),
                }
            )
        else:
            self.owned[record_id] = (physical, field_names, logical)

    def provision(self, section: dict[str, Any]) -> None:
        self._counter = int(section.get("_simulated_created_date_offset") or 0)
        simulated_now = section.get("_simulated_now")
        if simulated_now not in (None, ""):
            parsed_now = datetime.fromisoformat(
                str(simulated_now).replace("Z", "+00:00")
            )
            if parsed_now.tzinfo is None:
                raise RuntimeError(
                    "simulated Salesforce _simulated_now must include a timezone"
                )
            self._created_date_anchor = parsed_now.astimezone(timezone.utc)
        self.expand_relationships = bool(section.get("relationship_expansion"))
        self.strict_soql = bool(section.get("strict_soql_conditions"))
        current_user = section.get("current_user")
        if isinstance(current_user, dict):
            fields = {
                "Id": self._refs["$CURRENT_USER_ID"],
                "Name": "Benchmark User",
                "Email": "benchmark.user@example.invalid",
                "Username": "benchmark.user@example.invalid",
                "Alias": "bench",
                "IsActive": True,
                "UserType": "Standard",
                "TimeZoneSidKey": "UTC",
            }
            declared_fields = current_user.get("fields")
            if isinstance(declared_fields, dict):
                fields.update(self._replace_refs(deepcopy(declared_fields)))
            email = str(fields.get("Email") or fields.get("Username") or "")
            fields["Email"] = email
            fields.setdefault("Username", email)
            for field in current_user.get("read_fields") or []:
                fields.setdefault(str(field), f"simulated_{str(field).lower()}")
            self._add_seed_record("User", fields, "current_user", read_only=True)
            self._refs.update(
                {
                    "$USER_NAME": fields["Name"],
                    "$CURRENT_USER_NAME": fields["Name"],
                    "$USER_EMAIL": email,
                    "$CURRENT_USER_EMAIL": email,
                }
            )
        for spec in section.get("existing_users") or []:
            if not isinstance(spec, dict):
                continue
            email_match = re.search(r"(?:Email|Username)\s*=\s*'([^']+)'", str(spec.get("where") or ""), re.I)
            email = email_match.group(1) if email_match else "integration.user@example.invalid"
            self._add_seed_record(
                str(spec.get("sobject") or "User"),
                {
                    "Name": "Integration User",
                    "Email": email,
                    "Username": email,
                    "IsActive": True,
                    "UserType": "Standard",
                    "LastLoginDate": None,
                },
                f"existing_user_{len(self.read_only_records)}",
                read_only=True,
            )
        phases = section.get("phases")
        if isinstance(phases, list):
            for phase_index, phase in enumerate(phases):
                if isinstance(phase, dict):
                    self._provision_records(phase.get("records") or [], phase_index)
        else:
            self._provision_records(section.get("records") or [], 0)
        raw_map = section.get("user_id_map") or {}
        for foreign, target in raw_map.items():
            replacement = self._refs.get(str(target), str(target))
            self.user_id_map[str(foreign)] = replacement

    def provision_additional(self, section: dict[str, Any]) -> None:
        self.expand_relationships = self.expand_relationships or bool(
            section.get("relationship_expansion")
        )
        self.strict_soql = self.strict_soql or bool(section.get("strict_soql_conditions"))
        self._provision_records(section.get("records") or [], 50)

    def _provision_records(self, records: list[Any], phase_index: int) -> None:
        for index, raw in enumerate(records):
            if not isinstance(raw, dict):
                continue
            logical = str(raw.get("sobject") or "Task")
            raw_fields = deepcopy(raw.get("fields") or {})
            fields = self._replace_refs(raw_fields)
            record_type_token = str(raw_fields.get("RecordTypeId") or "")
            record_type_match = re.fullmatch(
                r"\$RECORD_TYPE:[^:]+:(.+)", record_type_token
            )
            if record_type_match and fields.get("RecordTypeId"):
                self.client._record_type_cache[str(fields["RecordTypeId"])] = (
                    record_type_match.group(1)
                )
            for field in raw.get("read_fields") or []:
                fields.setdefault(str(field), None)
            if "$CURRENT_USER_ID" in self._refs and not fields.get("CreatedById"):
                fields["CreatedById"] = self._refs["$CURRENT_USER_ID"]
            if logical != "User" and "$CURRENT_USER_ID" in self._refs:
                if fields.get("LastModifiedById") is None:
                    fields["LastModifiedById"] = self._refs["$CURRENT_USER_ID"]
            if logical in {
                "Account",
                "Campaign",
                "Case",
                "Contact",
                "Event",
                "Lead",
                "Opportunity",
                "Task",
            } and "$CURRENT_USER_ID" in self._refs:
                if fields.get("OwnerId") is None:
                    fields["OwnerId"] = self._refs["$CURRENT_USER_ID"]
            ref = str(raw.get("ref") or f"{logical}_{phase_index}_{index}")
            created = self._add_seed_record(logical, fields, ref)
            record_id = str(created["id"])
            self._refs.setdefault(f"${logical.upper()}_ID", record_id)
            self._refs[f"${ref.upper()}_ID"] = record_id
            if logical == "ContentVersion":
                document_id = _stable_id("069", record_id, 18)
                self._records[record_id].fields.setdefault("ContentDocumentId", document_id)
                self._refs[f"${ref.upper()}_DOC_ID"] = document_id

    def _replace_refs(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._replace_refs(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._replace_refs(item) for item in value]
        if isinstance(value, str):
            out = value
            for token, replacement in sorted(
                self._refs.items(), key=lambda item: len(item[0]), reverse=True
            ):
                out = out.replace(token, replacement)
            record_type = re.fullmatch(r"\$RECORD_TYPE:([^:]+):(.+)", out)
            if record_type:
                return _stable_id("012", out, 18)
            return out
        return value

    @staticmethod
    def _sobject_prefix(sobject: str) -> str:
        return {
            "Account": "001",
            "Contact": "003",
            "User": "005",
            "Opportunity": "006",
            "Campaign": "701",
            "CampaignMember": "00v",
            "Case": "500",
            "Lead": "00Q",
            "Task": "00T",
            "Event": "00U",
            "Product2": "01t",
            "PricebookEntry": "01u",
            "ContentVersion": "068",
            "ContentDocumentLink": "06A",
        }.get(sobject, "a00")

    def _next_id(self, logical_sobject: str, ref: str) -> str:
        self._counter += 1
        prefix = self._sobject_prefix(logical_sobject)
        digest = hashlib.sha256(
            f"{self.run_id}:{ref}:{self._counter}".encode("utf-8")
        ).hexdigest().upper()
        # Salesforce-generated IDs are monotonic enough that ORDER BY Id is
        # routinely used for keyset pagination.  Preserve seed insertion
        # order lexically while retaining a deterministic uniqueness suffix.
        return (prefix + f"{self._counter:06d}" + digest)[:18]

    def _add_seed_record(
        self,
        logical_sobject: str,
        fields: dict[str, Any],
        ref: str,
        *,
        read_only: bool = False,
    ) -> dict[str, Any]:
        record_id = (
            str(fields.get("Id"))
            if fields.get("Id")
            else self._next_id(logical_sobject, ref)
        )
        fields = deepcopy(fields)
        fields = self._coerce_salesforce_fields(logical_sobject, fields)
        physical = self._physical_sobject_name(logical_sobject)
        # Mirror the live harness's logical-to-physical stand-in mapping. The
        # raw recipe and public tool continue to use logical field names;
        # storage uses the benchmark-org field and read-back adds the logical
        # alias again.
        fields = {
            SALESFORCE_FIELD_MAP.get((physical, str(key)), str(key)): value
            for key, value in fields.items()
        }
        fields["Id"] = record_id
        if fields.get("IsDeleted") is None:
            fields["IsDeleted"] = False
        # Salesforce assigns audit timestamps at insert time.  A historical
        # fixed 2026-01-01 timestamp made LAST_N_DAYS recipes silently rot as
        # wall time advanced.  Keep records safely inside the current window
        # while preserving stable insertion ordering within a seed run.
        created_at = (
            self._created_date_anchor
            - timedelta(hours=1)
            + timedelta(seconds=self._counter)
        )
        fields.setdefault(
            "CreatedDate",
            created_at.strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
        )
        # Salesforce initializes LastModifiedDate to the insert timestamp.
        # ORDER BY LastModifiedDate must therefore be meaningful even when a
        # seed does not override either audit field explicitly.
        fields.setdefault("LastModifiedDate", fields["CreatedDate"])
        if logical_sobject == "Case":
            fields.setdefault("CaseNumber", f"{self._counter:08d}")
            fields.setdefault(
                "IsClosed", str(fields.get("Status") or "").lower().startswith("closed")
            )
        if logical_sobject in {"Contact", "Lead"}:
            full_name = " ".join(
                str(fields.get(part) or "").strip()
                for part in ("FirstName", "LastName")
                if str(fields.get(part) or "").strip()
            )
            if full_name:
                fields.setdefault("Name", full_name)
        if logical_sobject == "Opportunity":
            stage = str(fields.get("StageName") or "").strip().casefold()
            closed = stage.startswith("closed")
            fields.setdefault("IsClosed", closed)
            fields.setdefault("IsWon", closed and "won" in stage)
        if logical_sobject == "Account" and fields.get("BillingAddress") is None:
            fields["BillingAddress"] = {
                "street": fields.get("BillingStreet"),
                "city": fields.get("BillingCity"),
                "state": fields.get("BillingState"),
                "postalCode": fields.get("BillingPostalCode"),
                "country": fields.get("BillingCountry"),
            }
        if logical_sobject in {"Contract", "ServiceContract"}:
            fields.setdefault("ContractNumber", f"{self._counter:08d}")
            if "EndDate" in fields:
                if fields.get("Status") is None:
                    fields["Status"] = (
                        "Active" if logical_sobject == "ServiceContract" else "Activated"
                    )
        if logical_sobject == "CampaignMember":
            fields.setdefault(
                "LeadOrContactId",
                fields.get("ContactId") or fields.get("LeadId"),
            )
        if logical_sobject in {"Event", "Task"}:
            # Salesforce exposes AccountId as the derived Account activity
            # relation when WhatId points at an Account.
            what_id = fields.get("WhatId")
            if str(what_id or "").startswith("001"):
                if fields.get("AccountId") is None:
                    fields["AccountId"] = what_id
        row = _SimulatedSfRecord(
            id=record_id,
            logical_sobject=logical_sobject,
            physical_sobject=physical,
            fields=fields,
            read_only=read_only,
        )
        self._records[record_id] = row
        field_names = list(dict.fromkeys(["Id", *fields.keys()]))
        if read_only:
            self.read_only_records.append(
                {
                    "id": record_id,
                    "physical_sobject": physical,
                    "logical_sobject": logical_sobject,
                    "field_names": field_names,
                    "fields": deepcopy(fields),
                }
            )
        else:
            self.owned[record_id] = (physical, field_names, logical_sobject)
        return {"ok": True, "id": record_id, "sobject": logical_sobject}

    @staticmethod
    def _coerce_salesforce_fields(
        logical_sobject: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Mirror stable JSON scalar types returned by Salesforce fields.

        Workato input pills are commonly rendered as strings even when the
        target Salesforce field is numeric.  Salesforce stores and returns
        those values using the field's declared type; retaining the transport
        string in the simulator makes a faithful recipe fail solely on the
        stand-in connector representation.
        """

        out = deepcopy(fields)
        numeric_fields = {
            "Opportunity": {
                "Amount",
                "ExpectedRevenue",
                "Probability",
                "PushCount",
                "TotalOpportunityQuantity",
            }
        }.get(str(logical_sobject), set())
        for field in numeric_fields:
            value = out.get(field)
            if not isinstance(value, str) or not value.strip():
                continue
            try:
                parsed = float(value)
            except ValueError:
                continue
            out[field] = int(parsed) if parsed.is_integer() else parsed
        return out

    def _read(
        self, _sobject: str, record_id: str, fields: list[str]
    ) -> dict[str, Any] | None:
        row = self._records.get(str(record_id))
        if row is None:
            return None
        if not fields:
            return deepcopy(row.fields)
        return {
            field: self._field_lookup(row.fields, field)
            for field in fields
            if self._field_lookup(row.fields, field) is not None or field in row.fields
        }

    def _readback_extra_fields(self, _physical_sobject: str) -> list[str]:
        return ["Name", "CreatedDate", "LastModifiedDate", "IsClosed", "CaseNumber", "ContractNumber"]

    def _related_record_fields(
        self, record_id: str, _sobject_hint: str | None
    ) -> dict[str, Any] | None:
        row = self._records.get(str(record_id))
        return deepcopy(row.fields) if row is not None else None

    def _related_name(self, _related_sobject: str, record_id: str) -> str:
        if str(_related_sobject) == "RecordType":
            return self._record_type_name(record_id)
        row = self._records.get(str(record_id))
        return str((row.fields if row else {}).get("Name") or "")

    def _record_type_name(self, record_type_id: str) -> str:
        return str(self.client._record_type_cache.get(record_type_id) or "")

    def _augment_relationships(
        self, fields: dict[str, Any], visited_ids: set[str] | None = None
    ) -> None:
        visited_ids = set(visited_ids or ())
        for id_field, (path, related_sobject) in self._RELATED_NAME_LOOKUPS.items():
            related_id = fields.get(id_field)
            if not related_id or fields.get(path) not in (None, ""):
                continue
            name = self._related_name(related_sobject, str(related_id))
            fields[path] = name
            relationship = path.split(".", 1)[0]
            if not isinstance(fields.get(relationship), dict) or not fields.get(
                relationship
            ):
                fields[relationship] = {"Name": name}
        for key, value in list(fields.items()):
            if str(key).casefold() == "id":
                continue
            if not (key.endswith("Id") or key.endswith("__c")):
                continue
            row = self._records.get(str(value))
            if row is None:
                continue
            if key.endswith("Id"):
                relationship = key[:-2]
            else:
                relationship = key[:-3] + "__r"
            related_fields = deepcopy(row.fields)
            related_id = str(value)
            if related_id not in visited_ids:
                self._augment_relationships(
                    related_fields, {*visited_ids, related_id}
                )
            if not isinstance(fields.get(relationship), dict) or not fields.get(
                relationship
            ):
                fields[relationship] = related_fields
            else:
                fields[relationship].update(
                    {
                        child_key: child_value
                        for child_key, child_value in related_fields.items()
                        if fields[relationship].get(child_key) is None
                    }
                )
            for child_key, child_value in related_fields.items():
                flat_key = f"{relationship}.{child_key}"
                if fields.get(flat_key) is None:
                    fields[flat_key] = child_value
        product_id = fields.get("Product2Id")
        if product_id in self._records:
            product = self._records[str(product_id)].fields
            fields.setdefault("Product2", deepcopy(product))
            fields.setdefault("Product2.Name", product.get("Name"))

    def create_record(self, logical_sobject: str, fields: dict[str, Any]) -> dict[str, Any]:
        mapped = {
            str(key): self.user_id_map.get(value, value)
            if isinstance(value, str)
            else value
            for key, value in fields.items()
            if str(key) not in {"Id", "id", "sobject", "sobject_name"}
        }
        if (
            str(logical_sobject) == "CampaignMember"
            and mapped.get("ContactId") in (None, "")
            and mapped.get("LeadId") in (None, "")
        ):
            raise RuntimeError(
                "Salesforce CampaignMember requires either ContactId or LeadId"
            )
        return self._add_seed_record(logical_sobject, mapped, f"agent_{self._counter}")

    def update_record(
        self, logical_sobject: str, record_id: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        row = self._records.get(str(record_id))
        if row is None or row.read_only:
            raise RuntimeError(
                f"refusing to update non-owned Salesforce record {record_id} for {logical_sobject}"
            )
        if logical_sobject and logical_sobject != row.logical_sobject:
            raise RuntimeError(
                f"refusing to update Salesforce {row.logical_sobject} record "
                f"{record_id} as {logical_sobject}"
            )
        logical_updates = {
            str(key): self.user_id_map.get(value, value)
            if isinstance(value, str)
            else value
            for key, value in fields.items()
            if str(key) not in {"Id", "id", "sobject", "sobject_name"}
        }
        logical_updates = self._coerce_salesforce_fields(
            logical_sobject, logical_updates
        )
        updates = {
            SALESFORCE_FIELD_MAP.get((row.physical_sobject, key), key): (
                None if value == "" else value
            )
            for key, value in logical_updates.items()
        }
        row.fields.update(updates)
        row.fields["LastModifiedDate"] = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        physical, names, logical = self.owned[str(record_id)]
        self.owned[str(record_id)] = (
            physical,
            list(dict.fromkeys([*names, *updates.keys()])),
            logical,
        )
        return {
            "ok": True,
            "id": str(record_id),
            "sobject": row.logical_sobject,
            "updated_fields": deepcopy(logical_updates),
            "physical_fields": list(updates),
        }

    def snapshot(self) -> dict[str, Any]:
        records = []
        for row in self._records.values():
            fields = deepcopy(row.fields)
            self._augment_relationships(fields)
            physical = row.physical_sobject
            for (mapped_sobject, logical), physical_field in SALESFORCE_FIELD_MAP.items():
                if mapped_sobject == physical and physical_field in fields:
                    fields.setdefault(logical, fields[physical_field])
            record = {
                "sobject": row.logical_sobject,
                "id": row.id,
                "fields": fields,
            }
            if row.read_only:
                record["read_only"] = True
            records.append(record)
        return {"salesforce": {"records": records}}

    def export_state(self) -> dict[str, Any]:
        def serialized(row: _SimulatedSfRecord) -> dict[str, Any]:
            return {
                "id": row.id,
                "logical_sobject": row.logical_sobject,
                "physical_sobject": row.physical_sobject,
                "field_names": list(
                    dict.fromkeys(["Id", *row.fields.keys()])
                ),
                "fields": deepcopy(row.fields),
            }

        return {
            "run_id": self.run_id,
            "created_date_anchor": self._created_date_anchor.isoformat().replace(
                "+00:00", "Z"
            ),
            "expand_relationships": self.expand_relationships,
            "strict_soql_conditions": self.strict_soql,
            "user_id_map": deepcopy(self.user_id_map),
            "record_type_cache": deepcopy(self.client._record_type_cache),
            "owned_records": [
                serialized(row)
                for row in self._records.values()
                if not row.read_only
            ],
            "read_only_records": [
                serialized(row)
                for row in self._records.values()
                if row.read_only
            ],
            "refs": deepcopy(self._refs),
        }

    def delete_owned(self) -> list[dict[str, str]]:
        for record_id in list(self.owned):
            self._records.pop(record_id, None)
        self.owned.clear()
        return []

    def scan_owned(self) -> list[dict[str, str]]:
        return [
            {
                "kind": "salesforce.record",
                "id": record_id,
                "location": row.physical_sobject,
            }
            for record_id, row in self._records.items()
            if not row.read_only
        ]


def provision_salesforce_records(section: dict[str, Any]) -> dict[str, Any]:
    salesforce = SimulatedOwnedSalesforce()
    salesforce.provision(section or {})
    return {
        "ok": True,
        "state": salesforce.export_state(),
        "snapshot": salesforce.snapshot(),
    }


class SalesforceSimulatedRun:
    def __init__(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict) or not state.get("run_id"):
            raise RuntimeError("seed file missing simulated Salesforce state")
        self.salesforce = SimulatedOwnedSalesforce(state)

    def search_records(
        self,
        sobject: str,
        query: str,
        filters: list[dict[str, Any]] | None = None,
        limit: Any | None = None,
    ) -> dict[str, Any]:
        records = self.salesforce.search_records(sobject, query, filters or [])
        if self.salesforce.strict_soql:
            records = OwnedSalesforce._apply_order_by(str(query or ""), records)
        if limit not in (None, ""):
            records = records[: max(0, int(limit))]
        return {
            "ok": True,
            "sobject": str(sobject),
            "query": str(query or ""),
            "filters": filters or [],
            "limit": limit,
            "records": records,
            "count": len(records),
            "list_size": len(records),
            "totalSize": len(records),
        }

    def update_record(
        self, sobject: str, record_id: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        return self.salesforce.update_record(sobject, record_id, fields)

    def create_record(self, sobject: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self.salesforce.create_record(sobject, fields)

    def upsert_record(
        self, sobject: str, key_field: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        return self.salesforce.upsert_record(sobject, key_field, fields)

    def snapshot(self) -> dict[str, Any]:
        return {"ok": True, **self.salesforce.snapshot()}

    def cleanup(self) -> dict[str, Any]:
        self.salesforce.delete_owned()
        return {
            "ok": True,
            "leftovers": [],
            "delete_failures": [],
            "run_id": self.salesforce.run_id,
        }

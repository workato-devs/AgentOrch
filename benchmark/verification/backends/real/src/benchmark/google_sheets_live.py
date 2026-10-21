from __future__ import annotations

import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote


API = "https://sheets.googleapis.com/v4"


class GoogleSheetsError(RuntimeError):
    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self.body = body
        super().__init__(f"Google Sheets {status}: {body}")


class GoogleSheetsLiveClient:
    def __init__(self, spreadsheet_id: str, tab: str) -> None:
        if not spreadsheet_id:
            raise RuntimeError("missing SHEETS_SPREADSHEET_ID")
        if not tab:
            raise RuntimeError("missing SHEETS_TAB")
        self.spreadsheet_id = spreadsheet_id
        self.tab = tab
        ca_file = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
        self.ssl_context = (
            ssl.create_default_context(cafile=ca_file)
            if ca_file
            else ssl.create_default_context()
        )
        self.token: str | None = None

    def _auth(self) -> None:
        out = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if out.returncode != 0:
            raise RuntimeError(f"gcloud token failed: {(out.stderr or '')[:200]}")
        token = out.stdout.strip()
        if not token:
            raise RuntimeError("gcloud returned an empty access token")
        self.token = token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.token:
            self._auth()
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(2):
            request = urllib.request.Request(
                API + path,
                data=data,
                method=method,
                headers={
                    "Authorization": "Bearer " + str(self.token),
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, context=self.ssl_context, timeout=60) as response:
                    raw = response.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                raw_body: Any = exc.read().decode()
                try:
                    raw_body = json.loads(raw_body)
                except Exception:
                    pass
                if exc.code == 401 and attempt == 0:
                    self._auth()
                    continue
                raise GoogleSheetsError(exc.code, raw_body) from exc
        raise RuntimeError("unreachable Google Sheets retry state")

    def get_values(self) -> list[list[Any]]:
        path = f"/spreadsheets/{self.spreadsheet_id}/values/{quote(self.tab, safe='')}"
        values = self.request("GET", path).get("values", [])
        return values if isinstance(values, list) else []

    def clear_values(self) -> dict[str, Any]:
        path = f"/spreadsheets/{self.spreadsheet_id}/values/{quote(self.tab, safe='')}:clear"
        response = self.request("POST", path, {})
        return {"ok": True, "spreadsheet_id": self.spreadsheet_id, "tab": self.tab, **response}

    def _sheet_id(self) -> int:
        meta = self.request("GET", f"/spreadsheets/{self.spreadsheet_id}?fields=sheets.properties")
        for sheet in meta.get("sheets") or []:
            props = sheet.get("properties") or {}
            if props.get("title") == self.tab:
                return int(props["sheetId"])
        raise RuntimeError(f"Google Sheets tab {self.tab!r} not found in spreadsheet")

    def clear_formats(self) -> None:
        # values:clear keeps per-cell formats, and USER_ENTERED writes STAMP a
        # number format onto any cell whose text parses as a date/number — so a
        # predecessor recipe's seed can silently change how a later seed's
        # date-like cell renders (e.g. '2026-07-21' displaying as 'July 21').
        # Reset formats at every seed so the tab state is fully deterministic.
        self.request(
            "POST",
            f"/spreadsheets/{self.spreadsheet_id}:batchUpdate",
            {
                "requests": [
                    {
                        "updateCells": {
                            "range": {"sheetId": self._sheet_id()},
                            "fields": "userEnteredFormat",
                        }
                    }
                ]
            },
        )

    def replace_rows(self, rows: list[dict[str, Any]], headers: list[str] | None = None) -> dict[str, Any]:
        if not isinstance(rows, list):
            raise RuntimeError("Google Sheets seed rows must be a list")
        ordered_headers = list(headers or [])
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError("Google Sheets seed rows must contain objects")
            for key in row:
                text_key = str(key)
                if text_key not in ordered_headers:
                    ordered_headers.append(text_key)
        self.clear_values()
        self.clear_formats()
        if not ordered_headers:
            return {"ok": True, "spreadsheet_id": self.spreadsheet_id, "tab": self.tab, "rows": 0}
        values = [ordered_headers]
        for row in rows:
            values.append([_cell(row.get(header, "")) for header in ordered_headers])
        row_count = len(values)
        col_count = len(ordered_headers)
        update_range = f"{quote(self.tab, safe='')}!A1:{_column_name(col_count)}{row_count}"
        response = self.request(
            "PUT",
            f"/spreadsheets/{self.spreadsheet_id}/values/{update_range}?valueInputOption=USER_ENTERED",
            {"values": values},
        )
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "rows": len(rows),
            "headers": ordered_headers,
            "updatedRange": response.get("updatedRange"),
            "updatedCells": response.get("updatedCells"),
        }

    def search_rows(self, filters: dict[str, Any], limit: Any = None) -> dict[str, Any]:
        values = self.get_values()
        headers = [str(cell) for cell in values[0]] if values and isinstance(values[0], list) else []
        rows: list[dict[str, Any]] = []
        for idx, raw_row in enumerate(values[1:], start=2):
            if not isinstance(raw_row, list):
                continue
            row = {"row_number": idx}
            for col_idx, header in enumerate(headers):
                row[header] = raw_row[col_idx] if col_idx < len(raw_row) else ""
            if _matches(row, filters):
                rows.append(row)
        if limit not in (None, ""):
            try:
                limit_int = int(limit)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"Google Sheets search count must be an integer: {limit}") from exc
            rows = rows[:limit_int]
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            # Workato's search output schema exposes the tab as "sheet"
            # (recipes bind add-row sheet_name pills to it).
            "sheet": self.tab,
            "rows": rows,
            "records": rows,
            "count": len(rows),
        }

    def snapshot(self) -> dict[str, Any]:
        values = self.get_values()
        headers = [str(cell) for cell in values[0]] if values and isinstance(values[0], list) else []
        rows: list[dict[str, Any]] = []
        for idx, raw_row in enumerate(values[1:], start=2):
            if not isinstance(raw_row, list):
                continue
            row = {"row_number": idx}
            for col_idx, header in enumerate(headers):
                row[header] = raw_row[col_idx] if col_idx < len(raw_row) else ""
            rows.append(row)
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "headers": headers,
            "rows": rows,
            "values": values,
        }

    def append_row(self, values_by_column: dict[str, Any], headers: list[str] | None = None) -> dict[str, Any]:
        if not values_by_column:
            raise RuntimeError("Google Sheets append_row requires at least one value")
        values = self.get_values()
        existing_headers = [str(cell) for cell in values[0]] if values and isinstance(values[0], list) else []
        ordered_headers = list(headers or existing_headers)
        for header in existing_headers:
            if header not in ordered_headers:
                ordered_headers.append(header)
        for key in values_by_column:
            text_key = str(key)
            if text_key not in ordered_headers:
                ordered_headers.append(text_key)
        if not ordered_headers:
            raise RuntimeError("Google Sheets append_row could not build a header row")

        if ordered_headers != existing_headers:
            header_range = f"{quote(self.tab, safe='')}!A1:{_column_name(len(ordered_headers))}1"
            self.request(
                "PUT",
                f"/spreadsheets/{self.spreadsheet_id}/values/{header_range}?valueInputOption=USER_ENTERED",
                {"values": [ordered_headers]},
            )

        row_number = max(2, len(values) + 1)
        row_values = [_cell(values_by_column.get(header, "")) for header in ordered_headers]
        row_range = f"{quote(self.tab, safe='')}!A{row_number}:{_column_name(len(ordered_headers))}{row_number}"
        response = self.request(
            "PUT",
            f"/spreadsheets/{self.spreadsheet_id}/values/{row_range}?valueInputOption=USER_ENTERED",
            {"values": [row_values]},
        )
        row = {"row_number": row_number}
        row.update({header: row_values[idx] for idx, header in enumerate(ordered_headers)})
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "row_number": row_number,
            "headers": ordered_headers,
            "row": row,
            "records": [row],
            "count": 1,
            "updatedRange": response.get("updatedRange"),
            "updatedCells": response.get("updatedCells"),
        }

    def update_row(self, row_number: int, values_by_column: dict[str, Any]) -> dict[str, Any]:
        if row_number < 2:
            raise RuntimeError("Google Sheets update_row requires row_number >= 2")
        if not values_by_column:
            raise RuntimeError("Google Sheets update_row requires at least one value")
        values = self.get_values()
        headers = [str(cell) for cell in values[0]] if values and isinstance(values[0], list) else []
        for key in values_by_column:
            if key not in headers:
                headers.append(str(key))
        if not headers:
            raise RuntimeError("Google Sheets update_row could not build a header row")

        header_range = f"{quote(self.tab, safe='')}!A1:{_column_name(len(headers))}1"
        self.request(
            "PUT",
            f"/spreadsheets/{self.spreadsheet_id}/values/{header_range}?valueInputOption=USER_ENTERED",
            {"values": [headers]},
        )

        existing_row = values[row_number - 1] if len(values) >= row_number and isinstance(values[row_number - 1], list) else []
        row_values = list(existing_row) + [""] * max(0, len(headers) - len(existing_row))
        for key, value in values_by_column.items():
            row_values[headers.index(str(key))] = _cell(value)
        row_values = row_values[: len(headers)]
        row_range = f"{quote(self.tab, safe='')}!A{row_number}:{_column_name(len(headers))}{row_number}"
        response = self.request(
            "PUT",
            f"/spreadsheets/{self.spreadsheet_id}/values/{row_range}?valueInputOption=USER_ENTERED",
            {"values": [row_values]},
        )
        return {
            "ok": True,
            "spreadsheet_id": self.spreadsheet_id,
            "tab": self.tab,
            "row_number": row_number,
            "columns": values_by_column,
            "updatedRange": response.get("updatedRange"),
            "updatedCells": response.get("updatedCells"),
        }


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, value in (filters or {}).items():
        if value is None or str(value) == "":
            # Workato drops nil/blank search criteria (a formula-mode criterion
            # resolving to "" means retrieve-all, not match-empty-cell).
            continue
        key_text = str(key)
        if key_text in row:
            actual = row.get(key_text)
        elif key_text.startswith("col_"):
            # Workato encodes header names as col_<Header>; live rows are
            # keyed by the actual header. Raw key wins when a tab literally
            # uses col_-prefixed headers (legacy seeds).
            actual = row.get(key_text[len("col_"):], "")
        else:
            actual = ""
        if str(actual if actual is not None else "") != str(value):
            return False
    return True


def _column_name(index: int) -> str:
    if index <= 0:
        raise RuntimeError("column index must be positive")
    name = ""
    current = index
    while current:
        current, rem = divmod(current - 1, 26)
        name = chr(65 + rem) + name
    return name

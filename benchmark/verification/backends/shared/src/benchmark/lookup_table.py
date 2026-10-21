from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .config import BENCHMARK_ROOT


# Public task descriptions name business columns, while the historical
# Workato lookup-table fixtures persist those same columns as col1..colN.
# This is connector metadata, not recipe logic: callers may use either public
# label or physical key and both resolve to one canonical stored row.
LOOKUP_TABLE_COLUMN_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "2342983": {
        "col1": ("invoice_id", "invoice identifier"),
        "col3": ("status", "current status"),
        "col4": ("current_approval_id", "current approval id"),
        "col5": ("approval_position", "approval position"),
        "col6": ("current_approver", "current approver"),
        "col7": ("latest_slack_notification_tracking_details",),
        "col8": ("latest_slack_notification_tracking_details",),
        "col9": ("latest_slack_notification_tracking_details",),
        "col10": ("latest_slack_notification_tracking_details",),
    },
    "2343001": {
        "col3": ("conversation_id", "conversation identifier"),
        "col4": ("last_message_id", "last-message identifier"),
    },
    "3208153": {
        "col1": ("AE firstname lastname", "ae_fullname"),
        "col2": ("Pod coverage", "pod_coverage"),
        "col3": ("Pod leader", "pod_lead"),
    },
    "3227680": {
        "col1": ("id", "employee_id", "employee ID"),
        "col2": ("first_name", "first name"),
        "col3": ("last_name", "last name"),
        "col4": ("email",),
        "col5": ("job_title", "job title"),
        "col6": ("status",),
        "col7": ("start_date", "start date"),
        "col8": ("end_date", "end date"),
        "col9": ("manager_id", "manager ID"),
        "col10": ("department_id", "department ID"),
    },
    "3256641": {
        "col1": ("ACCOUNT ID", "account_id"),
        "col3": ("CSM", "CSM email", "csm_email"),
        "col4": ("CUSTOMER NAME", "account name", "customer_name"),
        "col5": ("FLAGGED?", "flagged"),
        "col6": ("PROPOSED NAME", "proposed name", "proposed_name"),
    },
    "3260814": {
        "col2": ("Email", "email"),
        "col4": ("Access Granted", "access_granted"),
        "col7": ("New Version Access Status", "new_version_access_status"),
        "col8": ("Slack ID", "slack_id"),
    },
    "3357221": {"col2": ("Channel ID", "channel_id")},
    "3357223": {
        "col2": ("User ID", "user_id"),
        "col3": ("Channel ID", "channel_id"),
    },
    "3455031": {"col1": ("Jargon", "jargon"), "col2": ("Meaning", "meaning")},
    "3603613": {"col1": ("Jargon", "jargon"), "col2": ("Meaning", "meaning")},
    "3897246": {
        "col3": ("Full Name", "full_name"),
        "col4": ("LinkedIn Person URL", "linkedin_person_url"),
        "col7": ("Connection", "connection"),
    },
    "4077484": {"col1": ("Token", "token"), "col2": ("Active", "active")},
    "4082138": {"col1": ("Token", "token"), "col2": ("Active", "active")},
}


def _alias_key(value: Any) -> str:
    return " ".join(
        part for part in "".join(
            char.casefold() if char.isalnum() else " " for char in str(value)
        ).split() if part
    )


def canonical_lookup_parameters(table_id: Any, parameters: dict[str, Any]) -> dict[str, Any]:
    """Map public business labels to canonical Workato colN keys.

    One public aggregate label may map to several legacy physical columns;
    this is used only where the public contract describes those fields as one
    grouped tracking value.
    """

    aliases = LOOKUP_TABLE_COLUMN_ALIASES.get(str(table_id), {})
    by_alias: dict[str, list[str]] = {}
    for column, labels in aliases.items():
        by_alias.setdefault(_alias_key(column), []).append(column)
        for label in labels:
            by_alias.setdefault(_alias_key(label), []).append(column)
    out: dict[str, Any] = {}
    for key, value in (parameters or {}).items():
        columns = by_alias.get(_alias_key(key), [str(key)])
        for column in columns:
            out[column] = value
    return out


def public_lookup_entry(table_id: Any, row: dict[str, Any]) -> dict[str, Any]:
    """Add readable aliases to a connector result without changing state."""

    out = deepcopy(row)
    for column, labels in LOOKUP_TABLE_COLUMN_ALIASES.get(str(table_id), {}).items():
        if column not in row:
            continue
        for label in labels:
            # ``id`` is reserved for the lookup-table entry identifier.
            if _alias_key(label) == "id":
                continue
            out.setdefault(label, deepcopy(row[column]))
    return out


def _clean(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (record or {}).items():
        if str(key).startswith("_") or value is None or str(value) == "<SKIP>":
            continue
        out[str(key)] = value if isinstance(value, str) else str(value)
    return out


class LookupTableMock:
    def __init__(
        self,
        seed_section: dict[str, Any] | None = None,
        state_file: Path | None = None,
    ) -> None:
        self._state_file = state_file
        self._tables: dict[str, list[dict[str, Any]]] = {}
        # Optional name -> table-id alias map. Lets a variant seed lookup tables
        # by human-readable name (e.g. "[DC] Region__c") in addition to the
        # opaque table id. Purely additive: id-based lookups are unaffected
        # because _resolve() returns any argument that is already a known id
        # (or unknown) unchanged.
        self._names: dict[str, str] = {}
        if seed_section is not None:
            self._names = self._normalize_names((seed_section or {}).get("names") or {})
            self._tables = self._normalize_tables((seed_section or {}).get("tables") or {})
            self._flush()

    def snapshot(self) -> dict[str, Any]:
        section: dict[str, Any] = {"tables": deepcopy(self._tables)}
        if self._names:
            section["names"] = deepcopy(self._names)
        if self._state_file:
            section["state_file"] = _portable_path(self._state_file)
        return {"lookup_table": section}

    def _normalize_names(self, raw_names: dict[str, Any]) -> dict[str, str]:
        if not isinstance(raw_names, dict):
            return {}
        return {str(name): str(table_id) for name, table_id in raw_names.items()}

    def _resolve(self, table_id: Any) -> str:
        """Resolve a table name alias to its underlying id. Returns the argument
        unchanged when it is already a table id or is not a known name, so
        existing id-based behavior is preserved."""
        key = str(table_id)
        if key in self._tables:
            return key
        if key in self._names:
            return str(self._names[key])
        return key

    def get_entries(self, table_id: str) -> dict[str, Any]:
        table = self._resolve(table_id)
        if table not in self._tables:
            raise RuntimeError(f"lookup_table {table} is not part of the seeded benchmark state")
        entries: list[dict[str, Any]] = []
        for row in self._tables[table]:
            entry = public_lookup_entry(table, row)
            out = {"entry": entry}
            if "id" not in entry and "_row_id" in entry:
                out["id"] = entry["_row_id"]
            out.update(entry)
            entries.append(out)
        return {"ok": True, "entries": entries}

    def get_entry(
        self,
        table_id: str,
        parameters: dict[str, Any] | None = None,
        entry_id: Any = None,
    ) -> dict[str, Any]:
        table = self._resolve(table_id)
        rows = self._rows(table)
        if entry_id is not None:
            row = self._find(rows, entry_id)
            return self._entry_result(public_lookup_entry(table, row) if row else None)
        match = _clean(canonical_lookup_parameters(table, parameters or {}))
        for row in rows:
            if all(str(row.get(key)) == str(value) for key, value in match.items()):
                return self._entry_result(public_lookup_entry(table, row))
        return self._entry_result(None)

    def search_entries(self, table_id: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        table = self._resolve(table_id)
        rows = self._rows(table)
        # Build per-key matchers. A list param value means IN-matching (the row
        # matches when its cell equals ANY list element); scalar params keep the
        # existing exact-string-equality behavior. The same skip rules as _clean
        # apply (underscore-prefixed keys, None, and <SKIP> sentinels are ignored).
        matchers: list[tuple[str, Any]] = []
        for key, value in canonical_lookup_parameters(table, parameters or {}).items():
            if str(key).startswith("_") or value is None or str(value) == "<SKIP>":
                continue
            if isinstance(value, list):
                allowed = {str(item) for item in value}
                matchers.append((str(key), lambda cell, allowed=allowed: str(cell) in allowed))
            else:
                want = value if isinstance(value, str) else str(value)
                matchers.append((str(key), lambda cell, want=want: str(cell) == want))
        entries: list[dict[str, Any]] = []
        for row in rows:
            if all(match(row.get(key)) for key, match in matchers):
                entry = public_lookup_entry(table, row)
                out = {"entry": entry}
                if "id" not in entry and "_row_id" in entry:
                    out["id"] = entry["_row_id"]
                out.update(entry)
                entries.append(out)
        return {
            "ok": True,
            "entries": entries,
        }

    def add_entry(self, table_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        table_id = self._resolve(table_id)
        rows = self._rows(table_id)
        rec = {
            "_row_id": self._next_row_id(rows),
            "_created_by": "agent",
            **_clean(canonical_lookup_parameters(table_id, parameters)),
        }
        rows.append(rec)
        self._flush()
        out = self._entry_result(public_lookup_entry(table_id, rec))
        out.update({"lookup_table_id": str(table_id), "id": rec["_row_id"]})
        return out

    def update_entry(self, table_id: str, entry_id: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        table_id = self._resolve(table_id)
        rows = self._rows(table_id)
        row = self._find(rows, entry_id)
        if row is None:
            return {"ok": False, "error": "entry_not_found", "id": entry_id}
        row.update(_clean(canonical_lookup_parameters(table_id, parameters)))
        row["_modified_by"] = "agent"
        self._flush()
        out = self._entry_result(public_lookup_entry(table_id, row))
        out.update({"lookup_table_id": str(table_id), "id": entry_id})
        return out

    def truncate(self, table_id: str) -> dict[str, Any]:
        table_id = self._resolve(table_id)
        rows = self._rows(table_id)
        removed = len(rows)
        self._tables[str(table_id)] = []
        self._flush()
        return {"ok": True, "lookup_table_id": str(table_id), "deleted_rows": removed}

    def add_batch_of_entries(self, table_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
        table_id = self._resolve(table_id)
        rows = self._rows(table_id)
        added: list[dict[str, Any]] = []
        for parameters in entries or []:
            if not isinstance(parameters, dict):
                continue
            rec = {
                "_row_id": self._next_row_id(rows),
                "_created_by": "agent",
                **_clean(canonical_lookup_parameters(table_id, parameters)),
            }
            rows.append(rec)
            out = self._entry_result(public_lookup_entry(table_id, rec))
            out.update({"id": rec["_row_id"]})
            added.append(out)
        self._flush()
        return {"ok": True, "lookup_table_id": str(table_id), "added_count": len(added), "entries": added}

    def delete_entry(self, table_id: str, entry_id: Any, ignore_not_found: Any = None) -> dict[str, Any]:
        table_id = self._resolve(table_id)
        rows = self._rows(table_id)
        row = self._find(rows, entry_id)
        if row is None:
            if str(ignore_not_found).lower() in {"true", "1", "yes"}:
                return {"ok": True, "lookup_table_id": str(table_id), "id": entry_id, "deleted": False}
            return {"ok": False, "error": "entry_not_found", "id": entry_id}
        rows.remove(row)
        self._flush()
        return {"ok": True, "lookup_table_id": str(table_id), "id": entry_id, "deleted": True}

    def _normalize_tables(self, raw_tables: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        tables: dict[str, list[dict[str, Any]]] = {}
        for table_id, rows in raw_tables.items():
            if not isinstance(rows, list):
                continue
            clean_rows: list[dict[str, Any]] = []
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                rec = dict(row)
                rec.setdefault("_row_id", idx)
                rec.setdefault("_created_by", "seed")
                clean_rows.append(rec)
            tables[str(table_id)] = clean_rows
        return tables

    def _flush(self) -> None:
        if not self._state_file:
            return
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"tables": self._tables}
        if self._names:
            payload["names"] = self._names
        self._state_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _rows(self, table_id: str) -> list[dict[str, Any]]:
        key = str(table_id)
        rows = self._tables.get(key)
        if rows is None:
            raise RuntimeError(f"lookup_table {key} is not part of the seeded benchmark state")
        return rows

    def _next_row_id(self, rows: list[dict[str, Any]]) -> int:
        return max((int(row.get("_row_id", -1)) for row in rows), default=-1) + 1

    def _find(self, rows: list[dict[str, Any]], entry_id: Any) -> dict[str, Any] | None:
        for row in rows:
            if str(row.get("id")) == str(entry_id) or str(row.get("_row_id")) == str(entry_id):
                return row
        return None

    @staticmethod
    def _entry_result(entry: dict[str, Any] | None) -> dict[str, Any]:
        out: dict[str, Any] = {"ok": True, "entry": entry}
        if isinstance(entry, dict):
            if "id" not in entry and "_row_id" in entry:
                out["id"] = entry["_row_id"]
            for key, value in entry.items():
                if key not in out:
                    out[key] = value
        return out


def _portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(BENCHMARK_ROOT))
    except ValueError:
        return str(path)

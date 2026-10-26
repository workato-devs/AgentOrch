from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .config import BENCHMARK_ROOT


WORKATO_RECORD_ID_FIELD = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"


def public_record_id(record: dict[str, Any]) -> Any:
    """Resolve Workato's documented generic Record ID output alias.

    Public data-table resource cards expose both the connector-independent
    ``record_id`` name and the table's physical Record ID field.  Persisted
    Reference seeds predate that alias and usually contain only the
    physical UUID column (or the mock's internal row id).  Keep storage byte
    compatible while making reads honor the published connector contract.
    """

    for key in ("record_id", WORKATO_RECORD_ID_FIELD, "id", "_row_id"):
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(record)
    record_id = public_record_id(out)
    if record_id is not None:
        out.setdefault("record_id", record_id)
    return out


def _clean(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (record or {}).items():
        if str(key).startswith("_") or value is None or str(value) == "<SKIP>":
            continue
        if isinstance(value, bool):
            out[str(key)] = "true" if value else "false"
        else:
            out[str(key)] = value if isinstance(value, str) else str(value)
    return out


class WorkatoDbTableMock:
    def __init__(
        self,
        seed_section: dict[str, Any] | None = None,
        state_file: Path | None = None,
    ) -> None:
        self._state_file = state_file
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self._continuation_tokens: dict[str, Any] = {}
        # Opt-in (seed.workato_db_table.record_id_column): stamp Workato's
        # built-in Record ID column on written rows like the live output
        # schema does. Off by default — legacy groundtruth stays byte-stable.
        self._record_id_column = bool((seed_section or {}).get("record_id_column"))
        if seed_section is not None:
            self._tables = self._normalize_tables((seed_section or {}).get("tables") or {})
            self._continuation_tokens = {
                str(table_id): token
                for table_id, token in ((seed_section or {}).get("continuation_tokens") or {}).items()
            }
            self._flush()

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
        self._state_file.write_text(
            json.dumps(
                {
                    "continuation_tokens": self._continuation_tokens,
                    "tables": self._tables,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def snapshot(self) -> dict[str, Any]:
        section: dict[str, Any] = {"tables": deepcopy(self._tables)}
        if self._continuation_tokens:
            section["continuation_tokens"] = deepcopy(self._continuation_tokens)
        if self._state_file:
            section["state_file"] = _portable_path(self._state_file)
        return {"workato_db_table": section}

    def get_records(self, table_id: str, continuation_token: Any = None) -> dict[str, Any]:
        table = str(table_id)
        if table not in self._tables:
            raise RuntimeError(f"workato_db_table {table} is not part of the seeded benchmark state")
        out: dict[str, Any] = {
            "ok": True,
            "records": [public_record(row) for row in self._tables[table]],
        }
        # Deterministic seeded pagination. A table's seeded continuation config
        # is either a plain token (returned only on the FIRST page, so
        # repeat/while pagination loops terminate) or a mapping of
        # incoming-token -> next-token ("" = first page) for recipes that pass
        # pagination through (e.g. API endpoints serving page N). Unseeded
        # incoming tokens never yield a token, preserving loop termination.
        if table in self._continuation_tokens:
            seeded = self._continuation_tokens[table]
            if isinstance(seeded, dict):
                key = str(continuation_token or "")
                if key in seeded:
                    out["continuation_token"] = seeded[key]
            elif continuation_token in (None, ""):
                out["continuation_token"] = seeded
        return out

    def search_records(self, table_id: str, query: str) -> dict[str, Any]:
        found = self.get_records(table_id)
        if not found.get("ok"):
            return found
        q = str(query or "").lower()
        return {
            "ok": True,
            "records": [
                row for row in found["records"]
                if any(q in str(value).lower() for value in row.values())
            ],
        }

    def add_record(
        self,
        table_id: str,
        record: dict[str, Any],
        record_id_field: Any = None,
    ) -> dict[str, Any]:
        rows = self._rows(table_id)
        rec = {"_row_id": self._next_row_id(rows), "_created_by": "agent", **_clean(record)}
        self._apply_record_id_field(rec, record_id_field)
        rows.append(rec)
        self._flush()
        return {"ok": True, "table_id": str(table_id), "record_id": rec["_row_id"], "record": dict(rec)}

    def update_record(
        self,
        table_id: str,
        record_id: Any,
        record: dict[str, Any],
        record_id_field: Any = None,
    ) -> dict[str, Any]:
        rows = self._rows(table_id)
        target = self._find(rows, record_id)
        if target is None:
            return {"ok": False, "error": "record_not_found", "record_id": record_id}
        target.update(_clean(record))
        self._apply_record_id_field(target, record_id_field)
        target["_modified_by"] = "agent"
        self._flush()
        return {"ok": True, "table_id": str(table_id), "record_id": record_id, "record": dict(target)}

    def upsert_record(
        self,
        table_id: str,
        record: dict[str, Any],
        record_id: Any = None,
        primary_field_id: Any = None,
        record_id_field: Any = None,
    ) -> dict[str, Any]:
        rows = self._rows(table_id)
        clean = _clean(record)
        target = self._find_upsert_target(rows, record_id, primary_field_id, clean)
        if target is None:
            rec = {"_row_id": self._next_row_id(rows), "_created_by": "agent", **clean}
            self._apply_record_id_field(rec, record_id_field)
            rows.append(rec)
            self._flush()
            return {
                "ok": True,
                "table_id": str(table_id),
                "record_id": rec["_row_id"],
                "created": True,
                "record": dict(rec),
            }
        target.update(clean)
        self._apply_record_id_field(target, record_id_field)
        target["_modified_by"] = "agent"
        self._flush()
        return {
            "ok": True,
            "table_id": str(table_id),
            "record_id": target.get("_row_id"),
            "created": False,
            "record": dict(target),
        }

    def truncate_table(self, table_id: str) -> dict[str, Any]:
        rows = self._rows(table_id)
        removed = len(rows)
        self._tables[str(table_id)] = []
        self._flush()
        return {"ok": True, "table_id": str(table_id), "deleted_rows": removed}

    def delete_record(self, table_id: str, record_id: Any) -> dict[str, Any]:
        rows = self._rows(table_id)
        target = self._find(rows, record_id)
        if target is None:
            return {"ok": False, "error": "record_not_found", "record_id": record_id}
        rows.remove(target)
        self._flush()
        return {"ok": True, "table_id": str(table_id), "record_id": record_id}

    def _rows(self, table_id: str) -> list[dict[str, Any]]:
        key = str(table_id)
        rows = self._tables.get(key)
        if rows is None:
            raise RuntimeError(f"workato_db_table {key} is not part of the seeded benchmark state")
        return rows

    def _next_row_id(self, rows: list[dict[str, Any]]) -> int:
        return max((int(row.get("_row_id", -1)) for row in rows), default=-1) + 1

    def _find(self, rows: list[dict[str, Any]], record_id: Any) -> dict[str, Any] | None:
        for row in rows:
            if (
                str(row.get("id")) == str(record_id)
                or str(row.get("_row_id")) == str(record_id)
                or str(row.get(WORKATO_RECORD_ID_FIELD)) == str(record_id)
            ):
                return row
        return None

    def _apply_record_id_field(self, record: dict[str, Any], record_id_field: Any) -> None:
        if record_id_field in (None, "") and self._record_id_column:
            record_id_field = WORKATO_RECORD_ID_FIELD
        if record_id_field not in (None, ""):
            record[str(record_id_field).replace("-", "_")] = str(record["_row_id"])

    def _primary_keys(self, primary_field_id: Any) -> list[str]:
        if not primary_field_id:
            return []
        raw = str(primary_field_id)
        return [raw, raw.replace("-", "_")]

    def _find_upsert_target(
        self,
        rows: list[dict[str, Any]],
        record_id: Any,
        primary_field_id: Any,
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        if record_id is not None:
            found = self._find(rows, record_id)
            if found is not None:
                return found
        for key in self._primary_keys(primary_field_id):
            if key not in record:
                continue
            want = str(record.get(key))
            for row in rows:
                if str(row.get(key)) == want:
                    return row
        return None


def _portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(BENCHMARK_ROOT))
    except ValueError:
        return str(path)

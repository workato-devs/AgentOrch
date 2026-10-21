from __future__ import annotations

import datetime
import json
import re
import zoneinfo
from decimal import Decimal
from typing import Any

from .config import Env


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


class SnowflakeLiveClient:
    def __init__(self, env: Env, section: dict[str, Any] | None = None) -> None:
        self.env = env
        self.section = dict(section or {})
        self._conn: Any = None

    def seed_tables(self, section: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(section, dict):
            raise RuntimeError("harness.snowflake_live.seed_tables requires a snowflake object")
        tables = section.get("tables")
        if not isinstance(tables, dict):
            raise RuntimeError("harness.snowflake_live.seed_tables requires snowflake.tables")
        state_tables: dict[str, dict[str, Any]] = {}
        for raw_table, raw_spec in tables.items():
            spec = _normalize_spec(raw_spec)
            columns = self._replace_table(str(raw_table), spec)
            state_tables[str(raw_table)] = {
                "columns": columns,
                "cleanup": bool(spec.get("cleanup", True)),
            }
        self.section = {
            "tables": state_tables,
            "current_time": str(section.get("current_time") or section.get("fixed_time") or ""),
        }
        stages = section.get("stages")
        if stages is not None:
            if not isinstance(stages, dict):
                raise RuntimeError("snowflake.stages must be an object of stage specs")
            self.section["stages"] = {
                str(name): self._replace_stage(str(name), spec) for name, spec in stages.items()
            }
        snapshot = self.snapshot()
        return {"ok": True, "state": self.section, "snapshot": snapshot}

    def _replace_stage(self, stage_name: str, raw_spec: Any) -> dict[str, Any]:
        """Create-or-replace a named internal STAGE (plus its named FILE FORMAT)
        and PUT the declared files onto it. Everything is declared explicitly in
        the seed — stage name, file format options, file paths and contents —
        so the run is reproducible and cleanup can drop exactly what was made."""
        if not isinstance(raw_spec, dict):
            raise RuntimeError(f"snowflake stage {stage_name} spec must be an object")
        file_format = raw_spec.get("file_format")
        if not isinstance(file_format, dict) or not str(file_format.get("name") or "").strip():
            raise RuntimeError(f"snowflake stage {stage_name} requires file_format.name")
        format_name = self._qualified_object(str(file_format["name"]))
        options: list[str] = [f"TYPE = {str(file_format.get('type') or 'CSV').upper()}"]
        for key, value in (file_format.get("options") or {}).items():
            key_text = str(key).upper()
            if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key_text):
                raise RuntimeError(f"invalid file format option name: {key}")
            if isinstance(value, bool):
                options.append(f"{key_text} = {'TRUE' if value else 'FALSE'}")
            elif isinstance(value, (int, float)):
                options.append(f"{key_text} = {value}")
            else:
                options.append(f"{key_text} = '" + str(value).replace("'", "''") + "'")
        self._execute(f"create or replace file format {format_name} {' '.join(options)}")
        qualified_stage = self._qualified_object(stage_name)
        self._execute(
            f"create or replace stage {qualified_stage} file_format = {format_name}"
        )
        files = raw_spec.get("files")
        if not isinstance(files, list):
            raise RuntimeError(f"snowflake stage {stage_name} requires an explicit files list")
        staged: list[str] = []
        import os
        import tempfile
        for entry in files:
            if not isinstance(entry, dict) or not str(entry.get("path") or "").strip():
                raise RuntimeError(f"snowflake stage {stage_name} file entry requires path")
            if "content" not in entry:
                raise RuntimeError(f"snowflake stage {stage_name} file {entry.get('path')} requires content")
            rel_path = str(entry["path"]).strip().strip("/")
            prefix, _, base_name = rel_path.rpartition("/")
            with tempfile.TemporaryDirectory() as tmp_dir:
                local = os.path.join(tmp_dir, base_name)
                with open(local, "w", encoding="utf-8") as handle:
                    handle.write(str(entry["content"]))
                target = f"@{qualified_stage}" + (f"/{prefix}" if prefix else "")
                self._execute(
                    f"put 'file://{local}' '{target}' auto_compress = false overwrite = true"
                )
            staged.append(rel_path)
        return {
            "qualified_stage": qualified_stage,
            "file_format": format_name,
            "files": staged,
            "cleanup": bool(raw_spec.get("cleanup", True)),
        }

    def _qualified_object(self, name: str) -> str:
        return ".".join(_quote_identifier(part) for part in self._parts(name))

    def snapshot(self) -> dict[str, Any]:
        tables = self._section_tables()
        out: dict[str, list[dict[str, Any]]] = {}
        physical: dict[str, str] = {}
        for raw_table in tables:
            physical[raw_table] = self._qualified_table(raw_table)
            if not self._table_exists(raw_table):
                out[raw_table] = []
                continue
            sql = f"select * from {self._qualified_table(raw_table)}"
            out[raw_table] = self._fetch_rows(sql, {})
        section = {"tables": out, "physical_tables": physical}
        stages = self.section.get("stages") if isinstance(self.section.get("stages"), dict) else {}
        if stages:
            listings: dict[str, list[str]] = {}
            for name, spec in stages.items():
                rows = self._fetch_rows(f"list @{spec['qualified_stage']}", {})
                listings[name] = sorted(str(row.get("name") or row.get("NAME") or "") for row in rows)
            section["stages"] = listings
        return {"snowflake_live": section, "snowflake": {"tables": out}}

    def cleanup(self) -> dict[str, Any]:
        dropped: list[str] = []
        for raw_table, spec in self._section_tables().items():
            if isinstance(spec, dict) and spec.get("cleanup") is False:
                continue
            self._execute(f"drop table if exists {self._qualified_table(raw_table)}")
            dropped.append(raw_table)
        dropped_stages: list[str] = []
        for name, spec in (self.section.get("stages") or {}).items():
            if not isinstance(spec, dict) or spec.get("cleanup") is False:
                continue
            self._execute(f"drop stage if exists {spec['qualified_stage']}")
            self._execute(f"drop file format if exists {spec['file_format']}")
            dropped_stages.append(name)
        out: dict[str, Any] = {"ok": True, "dropped_tables": dropped}
        if dropped_stages:
            out["dropped_stages"] = dropped_stages
        return out

    def upsert_rows_batch(self, table: str, key_columns: Any, rows: list[Any]) -> dict[str, Any]:
        if not table:
            raise RuntimeError("snowflake.upsert_rows_batch missing table")
        keys = _key_columns(key_columns)
        if not keys:
            raise RuntimeError("snowflake.upsert_rows_batch missing key_columns")
        clean_rows = [_clean_row(row) for row in rows]
        self._ensure_table_columns(table, clean_rows, keys)
        applied: list[dict[str, Any]] = []
        created = 0
        updated = 0
        for row in clean_rows:
            where_sql, params = self._key_where(keys, row)
            count = self._fetch_scalar(
                f"select count(*) from {self._qualified_table(table)} where {where_sql}",
                params,
            )
            if int(count or 0) > 0:
                key_names = {key.lower() for key in keys}
                set_columns = [column for column in row if column.lower() not in key_names]
                if set_columns:
                    set_sql = ", ".join(f"{_quote_identifier(column)} = %({column})s" for column in set_columns)
                    update_params = dict(params)
                    update_params.update({column: row[column] for column in set_columns})
                    self._execute(
                        f"update {self._qualified_table(table)} set {set_sql} where {where_sql}",
                        update_params,
                    )
                updated += 1
            else:
                self._insert_row(table, row)
                created += 1
            selected = self._fetch_rows(
                f"select * from {self._qualified_table(table)} where {where_sql}",
                params,
            )
            applied.extend(selected[:1])
        self._register_table(table)
        return {
            "ok": True,
            "table": table,
            "key_columns": keys,
            "rows": applied,
            "upserted": len(clean_rows),
            "created": created,
            "updated": updated,
        }

    def update_rows(self, table: str, where: str, columns: dict[str, Any]) -> dict[str, Any]:
        if not table:
            raise RuntimeError("snowflake.update_rows missing table")
        for key, value in (columns or {}).items():
            if isinstance(value, (list, dict)):
                raise RuntimeError(
                    f"snowflake.update_rows column {key} received a non-scalar value; "
                    "recipes must render arrays/objects to strings explicitly"
                )
        clean = _clean_row(columns)
        # Explicit NULL assignments must reach the SET list — dropping them
        # (insert semantics) silently keeps the old value where the recipe
        # demanded a clear. None binds as SQL NULL through the connector.
        for key, value in (columns or {}).items():
            if value is None:
                clean[_column_name(key)] = None
        self._ensure_table_columns(table, [{k: v for k, v in clean.items() if v is not None}], [])
        set_sql = ", ".join(f"{_quote_identifier(column)} = %({column})s" for column in clean)
        sql = f"update {self._qualified_table(table)} set {set_sql}"
        if str(where or "").strip():
            mapped = self._rewrite_where_identifiers(table, str(where))
            sql += " where " + self._bind_sql(self._rewrite_time(mapped))
        updated = self._execute_dml(sql, clean)
        self._register_table(table)
        # Workato's connector exposes the count as `rows_updated`; keep the
        # legacy `updated` key alongside for existing pins.
        return {
            "ok": True,
            "table": table,
            "where": where,
            "columns": clean,
            "updated": updated,
            "rows_updated": updated,
        }

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
        if not table:
            raise RuntimeError("snowflake.search_rows missing table")
        select_columns = _select_columns(output_columns)
        sql = f"select {select_columns} from {self._qualified_table(table)}"
        if str(where or "").strip():
            mapped = self._rewrite_where_identifiers(table, str(where))
            sql += " where " + self._bind_sql(self._rewrite_time(mapped))
        order_sql = _order_by(orderby)
        if order_sql:
            sql += " order by " + order_sql
        sql = _append_limit_offset(sql, limit, offset)
        rows = self._fetch_rows(sql, parameters or {})
        return {
            "ok": True,
            "table": table,
            "where": str(where or ""),
            "parameters": parameters or {},
            "rows": rows,
            "records": rows,
            "count": len(rows),
        }

    def search_rows_sql(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        limit: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
        rewritten = self._bind_sql(self._rewrite_time(self._rewrite_sql(str(sql or ""))))
        rewritten = _append_limit_offset(rewritten, limit, offset)
        rows = self._fetch_rows(rewritten, parameters or {})
        return {
            "ok": True,
            "sql": str(sql or ""),
            "parameters": parameters or {},
            "rows": rows,
            "records": rows,
            "count": len(rows),
        }

    def _rewrite_where_identifiers(self, table: str, where: str) -> str:
        """Map recipe display-name identifiers in a WHERE clause to the table's
        physical hash-suffixed columns (uniqueId -> UNIQUEID_815CAC11), same
        convention as _row_key_column. Only double-quoted identifiers are
        rewritten (SQL identifier position is unambiguous there); ambiguity
        raises, never guesses."""
        columns = list((self._section_tables().get(table, {}) or {}).get("columns") or {})
        if not columns:
            return where
        def _map(match: "re.Match[str]") -> str:
            name = match.group(1)
            lower = name.lower()
            for column in columns:
                if column.lower() == lower:
                    return f'"{column.upper()}"'
            prefixed = [column for column in columns if column.lower().startswith(lower + "_")]
            if len(prefixed) == 1:
                return f'"{prefixed[0].upper()}"'
            if len(prefixed) > 1:
                raise RuntimeError(f"ambiguous Snowflake WHERE identifier {name}: {sorted(prefixed)}")
            return match.group(0)
        return re.sub(r'"([A-Za-z_][A-Za-z0-9_$]*)"', _map, where)

    def _execute_dml(self, sql: str, params: dict[str, Any] | None = None) -> int:
        cursor = self._cursor()
        try:
            cursor.execute(_executable_sql(sql, params), params or {})
            return int(cursor.rowcount or 0)
        finally:
            cursor.close()

    def _replace_table(self, table: str, spec: dict[str, Any]) -> dict[str, str]:
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(f"snowflake live table {table} rows must be a list")
        columns = _columns(spec, rows)
        self._execute(f"create schema if not exists {self._qualified_schema(table)}")
        if not columns:
            self._execute(f"drop table if exists {self._qualified_table(table)}")
            return {}
        col_sql = ", ".join(f"{_quote_identifier(name)} {_column_type(kind)}" for name, kind in columns.items())
        self._execute(f"create or replace table {self._qualified_table(table)} ({col_sql})")
        for row in rows:
            self._insert_row(table, _clean_row(row), columns)
        return columns

    def _ensure_table_columns(self, table: str, rows: list[dict[str, Any]], keys: list[str]) -> None:
        self._execute(f"create schema if not exists {self._qualified_schema(table)}")
        columns = _normalized_columns(self._section_tables().get(table, {}).get("columns") or {})
        for row in rows:
            for key, value in row.items():
                columns.setdefault(key, _infer_type(value))
        for key in keys:
            lower = _column_name(key)
            if any(name == lower or name.startswith(lower + "_") for name in columns):
                continue
            columns.setdefault(lower, "string")
        if not columns:
            raise RuntimeError(f"snowflake live table {table} requires columns")
        if not self._table_exists(table):
            col_sql = ", ".join(f"{_quote_identifier(name)} {_column_type(kind)}" for name, kind in columns.items())
            self._execute(f"create table {self._qualified_table(table)} ({col_sql})")
        else:
            for name, kind in columns.items():
                self._execute(
                    f"alter table {self._qualified_table(table)} add column if not exists "
                    f"{_quote_identifier(name)} {_column_type(kind)}"
                )
        self._register_table(table, columns)

    def _insert_row(
        self,
        table: str,
        row: dict[str, Any],
        columns: dict[str, str] | None = None,
    ) -> None:
        all_columns = list((columns or {}).keys()) or list(row.keys())
        if not all_columns:
            return
        # VARIANT/ARRAY columns cannot bind a spliced list (002020) or a
        # VARCHAR json string (002023) — wrap the bind in PARSE_JSON via
        # INSERT..SELECT and serialize list/dict values.
        variant_columns = {
            column for column in all_columns
            if _column_type(str((columns or {}).get(column) or "")) == "VARIANT"
            or isinstance(row.get(column), (list, dict))
        }
        names = ", ".join(_quote_identifier(column) for column in all_columns)
        params: dict[str, Any] = {}
        exprs: list[str] = []
        for column in all_columns:
            value = row.get(column)
            if column in variant_columns:
                params[column] = json.dumps(value) if isinstance(value, (list, dict)) else value
                exprs.append(f"PARSE_JSON(%({column})s)")
            else:
                params[column] = value
                exprs.append(f"%({column})s")
        select_list = ", ".join(exprs)
        if variant_columns:
            self._execute(
                f"insert into {self._qualified_table(table)} ({names}) select {select_list}", params
            )
        else:
            self._execute(
                f"insert into {self._qualified_table(table)} ({names}) values ({select_list})", params
            )

    def _key_where(self, keys: list[str], row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        for idx, key in enumerate(keys):
            column = _row_key_column(row, key)
            if column is None:
                raise RuntimeError(f"snowflake upsert row missing key column: {key}")
            param = f"key_{idx}"
            clauses.append(f"{_quote_identifier(column)} = %({param})s")
            params[param] = row[column]
        return " and ".join(clauses), params

    def _register_table(self, table: str, columns: dict[str, str] | None = None) -> None:
        tables = self.section.setdefault("tables", {})
        if not isinstance(tables, dict):
            tables = {}
            self.section["tables"] = tables
        spec = tables.setdefault(table, {})
        if isinstance(spec, dict) and columns:
            current = spec.setdefault("columns", {})
            if isinstance(current, dict):
                current.update(columns)

    def _section_tables(self) -> dict[str, Any]:
        tables = self.section.get("tables")
        return tables if isinstance(tables, dict) else {}

    def _table_exists(self, table: str) -> bool:
        database, schema, name = self._parts(table)
        sql = (
            "select count(*) from information_schema.tables "
            "where table_catalog = %(database)s and table_schema = %(schema)s and table_name = %(table)s"
        )
        return int(self._fetch_scalar(sql, {"database": database, "schema": schema, "table": name}) or 0) > 0

    def _rewrite_sql(self, sql: str) -> str:
        out = _strip_inline_anon(sql)
        for raw_table in sorted(self._section_tables(), key=len, reverse=True):
            cleaned = _clean_table_name(raw_table)
            pattern = re.compile(
                r"(?<![A-Za-z0-9_$])" + re.escape(cleaned) + r"(?![A-Za-z0-9_$])",
                flags=re.I,
            )
            out = pattern.sub(self._qualified_table(raw_table), out)
        # Recipes may reference a seeded table by its bare name (the original
        # connection's default schema resolved it, e.g. a table name carried in
        # a workato_variable pill). Map the bare last component to the
        # registered table when the mapping is unambiguous; ambiguity is an
        # error, never a guess.
        by_bare: dict[str, list[str]] = {}
        for raw_table in self._section_tables():
            bare = _clean_table_name(raw_table).split(".")[-1].strip().strip('"')
            by_bare.setdefault(bare.upper(), []).append(raw_table)
        for bare, raw_tables in by_bare.items():
            # Only rewrite bare names in TABLE positions (after FROM/JOIN/etc.);
            # a bare word elsewhere (e.g. a column alias "AS TEAM") is not a
            # table reference.
            pattern = re.compile(
                r"(\b(?:from|join|into|update|table)\s+)" + re.escape(bare) + r"(?![A-Za-z0-9_$.])",
                flags=re.I,
            )
            if not pattern.search(out):
                continue
            if len(raw_tables) > 1:
                raise RuntimeError(
                    f"ambiguous bare Snowflake table reference {bare}: {sorted(raw_tables)}"
                )
            out = pattern.sub(lambda m: m.group(1) + self._qualified_table(raw_tables[0]), out)
        return self._rewrite_stage_pattern(out)

    def _rewrite_stage_pattern(self, sql: str) -> str:
        """COPY PATTERN faithfulness on internal stand-in stages: Snowflake
        anchors PATTERN against the full internal cloud-storage path
        ('stages/<uuid>/<relative>' — live-probed; the LIST-visible
        '<stagename>/<relative>' is display-only and never matches).
        Customer stages are external, where PATTERN matches stage-relative
        paths, so prepend '.*/' to keep the recipe's anchored-relative
        PATTERN semantics (Snowflake's own documented internal-stage
        idiom). Faithful as long as seeded relative paths carry no interior
        segment re-matching the pattern head — the seeds control the
        declared paths. A PATTERN clause with no seeded-stage reference is
        an error, never a guess."""
        stages = self.section.get("stages") if isinstance(self.section.get("stages"), dict) else {}
        if not stages:
            return sql
        pattern_re = re.compile(r"(pattern\s*=\s*')([^']*)(')", flags=re.I)
        if not pattern_re.search(sql):
            return sql
        referenced: list[str] = []
        for name in stages:
            bare = name.split(".")[-1].strip().strip('"')
            if re.search(r"@[A-Za-z0-9_$.\"]*" + re.escape(bare) + r"(?![A-Za-z0-9_$])", sql, flags=re.I):
                referenced.append(bare)
        if len(referenced) != 1:
            raise RuntimeError(
                f"COPY PATTERN references {len(referenced)} seeded stages: {sorted(referenced)}"
            )
        return pattern_re.sub(lambda m: m.group(1) + ".*/" + m.group(2) + m.group(3), sql, count=1)

    def _rewrite_time(self, sql: str) -> str:
        if not re.search(r"\bcurrent_(?:date|timestamp)\b|\bsysdate\b", sql, flags=re.I):
            return sql
        fixed = str(self.section.get("current_time") or "")
        if not fixed:
            raise RuntimeError("live Snowflake SQL uses current date/time but seed.snowflake_live.current_time is missing")
        dt = _parse_fixed_time(fixed)
        date_sql = "TO_DATE('%s')" % dt.date().isoformat()
        timestamp_sql = "TO_TIMESTAMP_NTZ('%s')" % dt.strftime("%Y-%m-%d %H:%M:%S")
        # Consume optional call parens so CURRENT_DATE() does not leave a
        # stray () after substitution.
        out = re.sub(r"\bcurrent_date\b(?:\s*\(\s*\))?", date_sql, sql, flags=re.I)
        out = re.sub(r"\bcurrent_timestamp\b(?:\s*\(\s*\))?", timestamp_sql, out, flags=re.I)
        # sysdate() is UTC like _parse_fixed_time's normalization.
        out = re.sub(r"\bsysdate\b(?:\s*\(\s*\))?", timestamp_sql, out, flags=re.I)
        return out

    def _bind_sql(self, sql: str) -> str:
        escaped = str(sql).replace("%", "%%")
        return re.sub(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)", r"%(\1)s", escaped)

    def _qualified_schema(self, table: str) -> str:
        database, schema, _name = self._parts(table)
        return ".".join(_quote_identifier(part) for part in (database, schema))

    def _qualified_table(self, table: str) -> str:
        return ".".join(_quote_identifier(part) for part in self._parts(table))

    def _parts(self, table: str) -> tuple[str, str, str]:
        if not self.env.snowflake_database:
            raise RuntimeError("missing SNOWFLAKE_DATABASE")
        cleaned = _clean_table_name(table)
        parts = [part.strip().strip('"') for part in cleaned.split(".") if part.strip()]
        if len(parts) >= 3:
            return self.env.snowflake_database.upper(), parts[-2].upper(), parts[-1].upper()
        if len(parts) == 2:
            return self.env.snowflake_database.upper(), parts[0].upper(), parts[1].upper()
        if len(parts) == 1:
            schema = self.env.snowflake_schema or "BENCH"
            return self.env.snowflake_database.upper(), schema.upper(), parts[0].upper()
        raise RuntimeError(f"invalid Snowflake table name: {table}")

    def _fetch_scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        rows = self._fetch(sql, params or {})
        return rows[0][0] if rows else None

    def _fetch_rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        cursor = self._cursor()
        try:
            cursor.execute(_executable_sql(sql, params), params or {})
            names = [str(item[0]) for item in (cursor.description or [])]
            rows: list[dict[str, Any]] = []
            for raw_row in cursor.fetchall():
                row: dict[str, Any] = {}
                for idx, name in enumerate(names):
                    value = _json_value(raw_row[idx])
                    row[name] = value
                    row.setdefault(name.lower(), value)
                rows.append(row)
            return rows
        finally:
            cursor.close()

    def _fetch(self, sql: str, params: dict[str, Any] | None = None) -> list[Any]:
        cursor = self._cursor()
        try:
            cursor.execute(_executable_sql(sql, params), params or {})
            return cursor.fetchall()
        finally:
            cursor.close()

    def _execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        cursor = self._cursor()
        try:
            cursor.execute(_executable_sql(sql, params), params or {})
        finally:
            cursor.close()

    def _cursor(self) -> Any:
        return self._connection().cursor()

    def _connection(self) -> Any:
        if self._conn is not None:
            return self._conn
        required = {
            "SNOWFLAKE_ACCOUNT": self.env.snowflake_account,
            "SNOWFLAKE_USER": self.env.snowflake_user,
            "SNOWFLAKE_WAREHOUSE": self.env.snowflake_warehouse,
            "SNOWFLAKE_DATABASE": self.env.snowflake_database,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise RuntimeError("missing Snowflake env values: " + ", ".join(missing))
        params: dict[str, Any] = {
            "account": self.env.snowflake_account,
            "user": self.env.snowflake_user,
            "warehouse": self.env.snowflake_warehouse,
            "database": self.env.snowflake_database,
            "schema": self.env.snowflake_schema or "BENCH",
        }
        if self.env.snowflake_role:
            params["role"] = self.env.snowflake_role
        if self.env.snowflake_pat:
            params["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
            params["token"] = self.env.snowflake_pat
        elif self.env.snowflake_private_key_path:
            params["private_key_file"] = self.env.snowflake_private_key_path
        else:
            raise RuntimeError("missing Snowflake authentication: SNOWFLAKE_PAT or SNOWFLAKE_PRIVATE_KEY_PATH")
        # Lazy: the connector package is only required when a Snowflake
        # recipe actually connects (README: optional dependency), while this
        # module is imported by raw_executor for every recipe.
        import snowflake.connector
        self._conn = snowflake.connector.connect(**params)
        return self._conn


def epoch_seconds_in_timezone(seconds: Any, timezone_name: Any) -> str:
    try:
        value = float(str(seconds or "0"))
    except ValueError as exc:
        raise RuntimeError(f"invalid epoch seconds: {seconds}") from exc
    tz_name = str(timezone_name or "UTC")
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except zoneinfo.ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"invalid timezone: {tz_name}") from exc
    return datetime.datetime.fromtimestamp(value, datetime.timezone.utc).astimezone(tz).isoformat()


def _normalize_spec(raw_spec: Any) -> dict[str, Any]:
    if isinstance(raw_spec, list):
        return {"rows": raw_spec}
    if isinstance(raw_spec, dict):
        spec = dict(raw_spec)
        spec.setdefault("rows", [])
        return spec
    raise RuntimeError("snowflake live table spec must be an object or row list")


def _columns(spec: dict[str, Any], rows: list[Any]) -> dict[str, str]:
    columns = _normalized_columns(spec.get("columns"))
    for row in rows:
        clean = _clean_row(row)
        for key, value in clean.items():
            columns.setdefault(key, _infer_type(value))
    return columns


def _normalized_columns(raw_columns: Any) -> dict[str, str]:
    columns: dict[str, str] = {}
    if isinstance(raw_columns, dict):
        for key, value in raw_columns.items():
            columns[_column_name(key)] = str(value or "string")
    return columns


def _clean_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise RuntimeError("snowflake live rows must contain objects")
    clean: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            continue
        clean[_column_name(key)] = _json_value(value)
    return clean


def _column_name(value: Any) -> str:
    text = str(value or "").strip().strip('"')
    if not text:
        raise RuntimeError("snowflake live column name cannot be blank")
    return text.lower()


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "number"
    if isinstance(value, (float, Decimal)):
        return "number"
    text = str(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return "date"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?", text):
        return "timestamp_ntz"
    return "string"


def _column_type(value: str) -> str:
    text = str(value or "string").strip().upper()
    aliases = {
        "STRING": "VARCHAR",
        "TEXT": "VARCHAR",
        "VARCHAR": "VARCHAR",
        "NUMBER": "NUMBER",
        "INTEGER": "NUMBER",
        "INT": "NUMBER",
        "FLOAT": "FLOAT",
        "DOUBLE": "FLOAT",
        "DECIMAL": "FLOAT",
        "BOOLEAN": "BOOLEAN",
        "BOOL": "BOOLEAN",
        "DATE": "DATE",
        "TIMESTAMP": "TIMESTAMP_NTZ",
        "TIMESTAMP_NTZ": "TIMESTAMP_NTZ",
        "VARIANT": "VARIANT",
        "ARRAY": "VARIANT",
    }
    if text not in aliases:
        raise RuntimeError(f"unsupported Snowflake live column type: {value}")
    return aliases[text]


def _key_columns(raw: Any) -> list[str]:
    values = raw if isinstance(raw, list) else str(raw or "").replace(",", "\n").splitlines()
    out: list[str] = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("value") or value.get("label") or value.get("name")
        text = str(value or "").strip()
        if text:
            out.append(text)
    return out


def _row_key_column(row: dict[str, Any], field: str) -> str | None:
    """Resolve a recipe-config key column (display name) to the row's actual
    column name, honoring Workato's hash-suffix convention (uniqueId ->
    uniqueid_815cac11). Ambiguity raises; absence returns None."""
    if field in row:
        return field
    lower = field.lower()
    for key in row:
        if key.lower() == lower:
            return key
    prefixed = [key for key in row if key.lower().startswith(lower + "_")]
    if len(prefixed) == 1:
        return prefixed[0]
    if len(prefixed) > 1:
        raise RuntimeError(f"ambiguous Snowflake key column {field}: {sorted(prefixed)}")
    return None


def _row_value(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row[field]
    lower = field.lower()
    for key, value in row.items():
        if key.lower() == lower:
            return value
    # Workato suffixes schema field names with a hash (uniqueId ->
    # uniqueid_815cac11) while recipe config references the display name.
    # Match the suffixed key only when it is unique — same convention the
    # retired in-process mock used; ambiguity raises, never guesses.
    prefixed = [key for key in row if key.lower().startswith(lower + "_")]
    if len(prefixed) == 1:
        return row[prefixed[0]]
    if len(prefixed) > 1:
        raise RuntimeError(f"ambiguous Snowflake key column {field}: {sorted(prefixed)}")
    return None


def _select_columns(raw: Any) -> str:
    values = [part.strip() for part in str(raw or "").splitlines() if part.strip()]
    if not values:
        return "*"
    return ", ".join(_quote_identifier(value) for value in values)


def _split_order_terms(text: str) -> list[str]:
    """Comma-split honoring parens and single quotes — expression terms like
    `(office_location_id != 'All') asc` must stay whole."""
    parts: list[str] = []
    depth = 0
    quote = False
    start = 0
    for idx, char in enumerate(text):
        if quote:
            if char == "'":
                quote = False
            continue
        if char == "'":
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(text[start:idx])
            start = idx + 1
    parts.append(text[start:])
    return parts


def _order_by(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    parts: list[str] = []
    for item in _split_order_terms(text):
        item = item.strip()
        if not item:
            continue
        # Parenthesized expression term — live Snowflake accepts these; pass
        # the recipe's own expression through verbatim.
        expr = re.fullmatch(r"(\(.*\))\s*(asc|desc)?", item, flags=re.I | re.S)
        if expr:
            direction = " " + expr.group(2).upper() if expr.group(2) else ""
            parts.append(expr.group(1) + direction)
            continue
        tokens = item.split()
        direction = ""
        if len(tokens) > 1:
            if len(tokens) != 2 or tokens[1].lower() not in {"asc", "desc"}:
                raise RuntimeError(f"unsupported Snowflake order by: {raw}")
            direction = " " + tokens[1].upper()
        parts.append(_quote_identifier(tokens[0]) + direction)
    return ", ".join(parts)


def _append_limit_offset(sql: str, limit: Any, offset: Any) -> str:
    out = sql
    limit_value = _nonnegative_int(limit)
    offset_value = _nonnegative_int(offset)
    if limit_value is not None and not re.search(r"\blimit\b", out, flags=re.I):
        out += f" limit {limit_value}"
    if offset_value is not None and offset_value > 0 and not re.search(r"\boffset\b", out, flags=re.I):
        out += f" offset {offset_value}"
    return out


def _executable_sql(sql: str, params: dict[str, Any] | None) -> str:
    """_bind_sql doubles % for pyformat interpolation; with no params the
    connector never interpolates, so un-double or a literal '50%' reaches
    Snowflake as '50%%' (silent result corruption)."""
    return str(sql) if params else str(sql).replace("%%", "%")


def _nonnegative_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _strip_inline_anon(text: str) -> str:
    """Drop inline anonymizer tags (`analytics_<anon>2023</anon>_summary`) —
    corpus artifacts that would never compile as live SQL identifiers. The
    inner text is the semantic content. Snowflake-live only; mock backends
    store tagged literals verbatim by design."""
    return re.sub(r"<anon>(.*?)</anon>", r"\1", str(text or ""), flags=re.S)


def _clean_table_name(table: str) -> str:
    return re.sub(r"\s+\(view\)\s*$", "", _strip_inline_anon(table).strip(), flags=re.I)


def _quote_identifier(value: str) -> str:
    text = _strip_inline_anon(value).strip().strip('"').upper()
    if not IDENTIFIER_RE.fullmatch(text):
        raise RuntimeError(f"invalid Snowflake identifier: {value}")
    return '"' + text + '"'


def _parse_fixed_time(value: str) -> datetime.datetime:
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value

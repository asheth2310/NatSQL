"""Schema introspection and caching.

Reads table/column/foreign-key metadata from MySQL INFORMATION_SCHEMA and
keeps an in-memory summary. A SELECT-only DB role can still read
INFORMATION_SCHEMA for the objects it has privileges on.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pymysql

logger = logging.getLogger(__name__)


class SchemaError(Exception):
    """Raised when the schema cannot be loaded from the database."""


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = False


@dataclass
class ForeignKey:
    column: str
    ref_table: str
    ref_column: str


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)


class SchemaSummary:
    """Immutable-ish snapshot of the queryable schema."""

    def __init__(self, tables: dict[str, TableInfo], database: str = "demo") -> None:
        self.database = database
        self.tables: dict[str, TableInfo] = {t.name.lower(): t for t in tables.values()}

    def table_names(self) -> list[str]:
        return sorted(self.tables.keys())

    def column_names(self, table: str) -> set[str]:
        info = self.tables.get(table.lower())
        if info is None:
            return set()
        return {c.name.lower() for c in info.columns}

    def to_text(self) -> str:
        """Human-readable schema dump used inside the LLM prompt."""
        lines: list[str] = []
        for name in self.table_names():
            info = self.tables[name]
            lines.append(f"Table: {info.name}")
            for col in info.columns:
                pk = ", primary key" if col.is_primary_key else ""
                lines.append(f"  - {col.name} ({col.data_type}{pk})")
            for fk in info.foreign_keys:
                lines.append(f"  - FK: {fk.column} -> {fk.ref_table}.{fk.ref_column}")
        return "\n".join(lines)

    def to_meta(self) -> list[dict]:
        return [
            {
                "name": info.name,
                "columns": [
                    {
                        "name": c.name,
                        "data_type": c.data_type,
                        "nullable": c.nullable,
                        "is_primary_key": c.is_primary_key,
                    }
                    for c in info.columns
                ],
                "foreign_keys": [
                    {"column": fk.column, "ref_table": fk.ref_table, "ref_column": fk.ref_column}
                    for fk in info.foreign_keys
                ],
            }
            for info in (self.tables[n] for n in self.table_names())
        ]


class SchemaService:
    def __init__(self, host: str, port: int, user: str, password: str, database: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._summary: SchemaSummary | None = None
        self._loaded_at: datetime | None = None
        self._lock = threading.Lock()

    def _connect(self) -> pymysql.Connection:
        try:
            return pymysql.connect(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                database=self._database,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=5,
                read_timeout=10,
            )
        except pymysql.MySQLError as e:
            raise SchemaError(f"cannot connect to MySQL at {self._host}:{self._port}: {e}") from e

    def load(self) -> SchemaSummary:
        """Fetch the schema fresh from INFORMATION_SCHEMA and cache it."""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
                    (self._database,),
                )
                table_names = [row[0] for row in cur.fetchall()]

                cur.execute(
                    "SELECT table_name, column_name, data_type, is_nullable, column_key "
                    "FROM information_schema.columns "
                    "WHERE table_schema = %s ORDER BY table_name, ordinal_position",
                    (self._database,),
                )
                col_rows = cur.fetchall()

                cur.execute(
                    "SELECT table_name, column_name, referenced_table_name, referenced_column_name "
                    "FROM information_schema.key_column_usage "
                    "WHERE table_schema = %s AND referenced_table_name IS NOT NULL "
                    "ORDER BY table_name, ordinal_position",
                    (self._database,),
                )
                fk_rows = cur.fetchall()
        finally:
            conn.close()

        tables: dict[str, TableInfo] = {
            name: TableInfo(name=name) for name in table_names
        }
        for tname, cname, dtype, nullable, col_key in col_rows:
            info = tables.get(tname)
            if info is None:
                continue
            info.columns.append(
                ColumnInfo(
                    name=cname,
                    data_type=dtype,
                    nullable=nullable == "YES",
                    is_primary_key=col_key == "PRI",
                )
            )
        for tname, cname, rtname, rcname in fk_rows:
            info = tables.get(tname)
            if info is not None:
                info.foreign_keys.append(ForeignKey(column=cname, ref_table=rtname, ref_column=rcname))

        summary = SchemaSummary(tables, database=self._database)
        with self._lock:
            self._summary = summary
            self._loaded_at = datetime.now(timezone.utc)
        logger.info("Schema loaded: %d tables from %s", len(summary.tables), self._database)
        return summary

    def get_summary(self) -> SchemaSummary:
        with self._lock:
            if self._summary is None:
                summary = None
            else:
                summary = self._summary
        if summary is None:
            summary = self.load()
        return summary

    def refresh(self) -> SchemaSummary:
        return self.load()

    def is_loaded(self) -> bool:
        with self._lock:
            return self._summary is not None

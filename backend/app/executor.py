"""Executes validated queries against MySQL as the read-only role.

Additional runtime hardening on top of the validator:
  - Connects with the dedicated SELECT-only MySQL user.
  - Pins every session to READ ONLY (defense in depth even if grants drift).
  - MAX_EXECUTION_TIME + client read timeout bound runaway queries.
  - Autocommit, no transaction held open.
"""
from __future__ import annotations

import logging

import pymysql

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class QueryExecutor:
    def __init__(self, host: str, port: int, user: str, password: str, database: str,
                 query_timeout_ms: int = 5000, connect_timeout: int = 5) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._query_timeout_ms = query_timeout_ms
        self._connect_timeout = connect_timeout

    def _connect(self) -> pymysql.Connection:
        return pymysql.connect(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=self._connect_timeout,
            read_timeout=max(10, self._query_timeout_ms // 1000 + 5),
            write_timeout=10,
        )

    def run(self, sql: str) -> tuple[list[str], list[list]]:
        """Execute and return (column_names, rows). Raises ExecutionError."""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                # Server-side kill switch for SELECTs that run too long.
                cur.execute("SET SESSION MAX_EXECUTION_TIME = %s", (self._query_timeout_ms,))
                # Runtime read-only pin (works alongside the DB role grants).
                cur.execute("SET SESSION TRANSACTION READ ONLY")
                cur.execute(sql)
                columns = [d[0] for d in cur.description] if cur.description else []
                rows = [list(r) for r in cur.fetchall()]
                return columns, rows
        except pymysql.MySQLError as e:
            code = getattr(e, "args", [None])[0] if e.args else None
            raise ExecutionError(str(e), code=code) from e
        finally:
            conn.close()

    def healthcheck(self) -> str | None:
        """Return an error string if the DB is unreachable, else None."""
        try:
            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            finally:
                conn.close()
            return None
        except pymysql.MySQLError as e:
            return str(e)

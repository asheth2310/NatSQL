"""Hard SQL validation layer (defense in depth).

Never trust the model: every generated query must pass this gate before it
reaches the database. Enforced checks:
  - Parses as valid SQL in the MySQL dialect.
  - Exactly one statement, and it is a SELECT (no writes, DDL, raw commands).
  - No INTO OUTFILE, no known-dangerous functions (SLEEP, LOAD_FILE, ...).
  - Every referenced table exists in the whitelisted schema.
  - Every referenced column exists in the schema; qualified refs resolve
    through aliases; unqualified refs must exist in a referenced table.
  - A LIMIT is always present and clamped to the configured maximum.
"""
from __future__ import annotations

import logging
from typing import Callable

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError

from .schema import SchemaSummary

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when generated SQL fails a safety check."""


# Functions that are useless for read-only analytics and are common attack vectors.
DANGEROUS_FUNCTIONS = {
    "sleep",
    "benchmark",
    "load_file",
    "get_lock",
    "release_lock",
    "master_pos_wait",
}

# Statement-ish node types that may never appear anywhere in the tree.
# (sqlglot has no single Statement base class, so we reject these explicitly.)
REJECTED_NODE_TYPES = (
    exp.DML,        # INSERT / UPDATE / DELETE / MERGE
    exp.DDL,        # CREATE / DROP / ALTER family
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,    # SHOW / SET / raw commands
    exp.Use,
    exp.Transaction,
    exp.Into,       # SELECT ... INTO OUTFILE
)


class SQLValidator:
    def __init__(self, schema: SchemaSummary, max_rows: int = 100, dialect: str = "mysql") -> None:
        self.schema = schema
        self.max_rows = max_rows
        self.dialect = dialect

    # -- public API ---------------------------------------------------------

    def validate(self, sql: str) -> tuple[str, list[str]]:
        """Validate and normalize. Returns (final_sql, notes). Raises ValidationError."""
        notes: list[str] = []
        root = self._parse_single_select(sql)
        self._reject_unsafe_nodes(root)
        tables = self._check_tables(root)
        self._check_columns(root, tables)
        self._enforce_limit(root, notes)
        normalized = root.sql(dialect=self.dialect)
        notes.append("passed: SELECT-only, whitelisted identifiers, LIMIT enforced")
        logger.info("Validator: query accepted (%s)", "; ".join(notes))
        return normalized, notes

    # -- parsing ------------------------------------------------------------

    def _parse_single_select(self, sql: str) -> exp.Select:
        try:
            expressions = sqlglot.parse(sql, dialect=self.dialect)
        except (ParseError, TokenError) as e:
            raise ValidationError(f"SQL could not be parsed: {e}") from e

        if not expressions:
            raise ValidationError("Empty SQL")
        if len(expressions) > 1:
            raise ValidationError("Multiple statements are not allowed")
        root = expressions[0]
        if not isinstance(root, exp.Select):
            raise ValidationError(
                f"Only SELECT statements are allowed (got {root.__class__.__name__})"
            )
        if isinstance(root, (exp.Union, exp.Intersect, exp.Except)):
            # A UNION's LIMIT can't reliably bound the whole result set.
            raise ValidationError("UNION / INTERSECT / EXCEPT are not supported")
        return root

    # -- tree walk ----------------------------------------------------------

    def _reject_unsafe_nodes(self, root: exp.Expression) -> None:
        for node in root.walk():
            if isinstance(node, REJECTED_NODE_TYPES):
                raise ValidationError(
                    f"Statement type not allowed: {node.__class__.__name__}"
                )
            if isinstance(node, exp.Anonymous) and node.name.lower() in DANGEROUS_FUNCTIONS:
                raise ValidationError(f"Function {node.name}() is not allowed")

    # -- identifiers --------------------------------------------------------

    # Marker for aliases that refer to derived tables / CTEs rather than real tables.
    DERIVED = object()

    def _check_tables(self, root: exp.Expression) -> list[str]:
        cte_names = {cte.alias.lower() for cte in root.find_all(exp.CTE)}
        tables: list[str] = []
        for node in root.find_all(exp.Table):
            if node.db:
                raise ValidationError(
                    f"Cross-database reference not allowed: {node.db}.{node.name}"
                )
            if node.catalog:
                raise ValidationError(f"Catalog-qualified reference not allowed: {node.name}")
            name = node.name.lower()
            if name in cte_names:
                continue  # CTE name, not a physical table; its body is validated separately
            if name not in self.schema.tables:
                raise ValidationError(f"Unknown table: {node.name}")
            if name not in tables:
                tables.append(name)
        if not tables:
            raise ValidationError("Query does not reference any table")
        return tables

    def _alias_map(self, root: exp.Expression) -> dict[str, str | object]:
        amap: dict[str, str | object] = {}
        for table in root.find_all(exp.Table):
            alias = (table.alias or table.name).lower()
            amap[alias] = table.name.lower()
        # Derived tables (subqueries in FROM/JOIN) and CTEs: columns qualified
        # with these resolve to the derived output, not a physical table.
        for sub in root.find_all(exp.Subquery):
            if sub.alias:
                amap[sub.alias.lower()] = self.DERIVED
        for cte in root.find_all(exp.CTE):
            if cte.alias:
                amap[cte.alias.lower()] = self.DERIVED
        return amap

    def _check_columns(self, root: exp.Expression, tables: list[str]) -> None:
        amap = self._alias_map(root)
        # SELECT aliases (usable in ORDER BY / HAVING without existing as columns)
        select_aliases = {
            (alias.alias or "").lower() for alias in root.find_all(exp.Alias)
        }

        for col in root.find_all(exp.Column):
            name = col.name.lower()
            qualifier = col.table
            if qualifier:
                resolved = amap.get(qualifier.lower())
                if resolved is None:
                    raise ValidationError(f"Unknown table qualifier: {qualifier}")
                if resolved is self.DERIVED:
                    continue  # column of a derived table / CTE output
                if name not in self.schema.column_names(resolved):
                    raise ValidationError(f"Unknown column: {qualifier}.{col.name}")
            else:
                if name in select_aliases:
                    continue  # ORDER BY <alias>
                if not any(name in self.schema.column_names(t) for t in tables):
                    raise ValidationError(f"Unknown column: {col.name}")

    # -- limits -------------------------------------------------------------

    def _enforce_limit(self, root: exp.Select, notes: list[str]) -> None:
        limit = root.args.get("limit")
        if limit is None:
            root.set("limit", exp.Limit(expression=exp.Literal.number(self.max_rows)))
            notes.append(f"LIMIT {self.max_rows} injected")
            return

        expr = limit.expression
        if isinstance(expr, exp.Literal) and expr.is_number:
            value = int(expr.this)
            if value > self.max_rows:
                limit.set("expression", exp.Literal.number(self.max_rows))
                notes.append(f"LIMIT clamped from {value} to {self.max_rows}")
        else:
            limit.set("expression", exp.Literal.number(self.max_rows))
            notes.append(f"non-literal LIMIT replaced with {self.max_rows}")


def make_validator(schema: SchemaSummary, max_rows: int = 100) -> SQLValidator:
    return SQLValidator(schema=schema, max_rows=max_rows)

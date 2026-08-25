"""Tests for the hard SQL validation layer."""
from __future__ import annotations

import pytest

from app.validator import SQLValidator, ValidationError


def make_validator(demo_schema):
    return SQLValidator(schema=demo_schema, max_rows=100)


# -- acceptance --------------------------------------------------------------

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM customers",
        "SELECT name, region FROM customers WHERE region = 'Europe'",
        "SELECT COUNT(*) AS total FROM orders WHERE order_date >= '2026-01-01'",
        "SELECT c.name, SUM(oi.quantity * oi.unit_price) AS s FROM customers c "
        "JOIN orders o ON o.customer_id = c.customer_id "
        "JOIN order_items oi ON oi.order_id = o.order_id GROUP BY c.customer_id, c.name "
        "ORDER BY s DESC LIMIT 5",
        "SELECT region, COUNT(*) AS n FROM customers GROUP BY region HAVING n > 1",
        "SELECT name, price FROM products WHERE price > 100 ORDER BY price LIMIT 10",
        # ORDER BY a select alias that isn't a real column
        "SELECT name, stock_quantity AS q FROM products ORDER BY q",
        "SELECT (SELECT COUNT(*) FROM orders) AS total",
        "SELECT p.name, SUM(oi.quantity) AS units FROM order_items oi "
        "JOIN products p ON p.product_id = oi.product_id GROUP BY p.product_id, p.name "
        "ORDER BY units DESC LIMIT 3",
        "SELECT DATE_FORMAT(order_date, '%Y-%m') AS month, COUNT(*) FROM orders "
        "GROUP BY month ORDER BY month",
    ],
)
def test_accepts_valid_sql(demo_schema, sql):
    normalized, notes = make_validator(demo_schema).validate(sql)
    assert "SELECT" in normalized.upper()


# -- rejection ---------------------------------------------------------------

@pytest.mark.parametrize(
    "sql,reason",
    [
        ("INSERT INTO customers (name) VALUES ('x')", "write"),
        ("UPDATE customers SET name = 'x'", "write"),
        ("DELETE FROM orders", "write"),
        ("DROP TABLE customers", "write"),
        ("ALTER TABLE customers ADD COLUMN x INT", "write"),
        ("CREATE TABLE x (id INT)", "write"),
        ("TRUNCATE TABLE orders", "write"),
        ("SELECT 1; DROP TABLE customers", "multiple statements"),
        ("SELECT 1; SELECT 2", "multiple statements"),
        ("SELECT * FROM nonexistent_table", "unknown table"),
        ("SELECT nope FROM customers", "unknown column"),
        ("SELECT customers.nope FROM customers", "unknown column"),
        ("SELECT bogus FROM customers c", "unknown column"),
        ("SELECT c.id FROM customers c", "unknown column"),
        ("SELECT * FROM customers WHERE SLEEP(10)", "dangerous function"),
        ("SELECT BENCHMARK(1000000, SHA1('x'))", "dangerous function"),
        ("SELECT 1 INTO OUTFILE '/tmp/x'", "into"),
        ("SELECT * FROM demo.customers", "cross-database"),
        ("SELECT * FROM other_db.customers", "cross-database"),
        ("USE demo", "non-select"),
        ("SHOW TABLES", "non-select"),
        ("SET @x = 1", "non-select"),
        ("SELECT 1 UNION SELECT 2", "union"),
        ("", "empty"),
    ],
)
def test_rejects_unsafe_sql(demo_schema, sql, reason):
    with pytest.raises(ValidationError):
        make_validator(demo_schema).validate(sql)


def test_rejects_unknown_column_in_join(demo_schema):
    sql = (
        "SELECT c.name, o.nope FROM customers c "
        "JOIN orders o ON o.customer_id = c.customer_id"
    )
    with pytest.raises(ValidationError):
        make_validator(demo_schema).validate(sql)


# -- limit enforcement -------------------------------------------------------

def test_injects_limit_when_missing(demo_schema):
    sql, notes = make_validator(demo_schema).validate("SELECT * FROM customers")
    assert "LIMIT 100" in sql.upper()
    assert any("injected" in n for n in notes)


def test_clamps_oversized_limit(demo_schema):
    sql, notes = make_validator(demo_schema).validate(
        "SELECT * FROM customers LIMIT 10000"
    )
    assert "LIMIT 100" in sql.upper()
    assert any("clamped" in n for n in notes)


def test_keeps_small_limit(demo_schema):
    sql, _ = make_validator(demo_schema).validate("SELECT * FROM customers LIMIT 5")
    assert "LIMIT 5" in sql.upper()


def test_replaces_non_literal_limit(demo_schema):
    sql, _ = make_validator(demo_schema).validate(
        "SELECT * FROM customers LIMIT @n"
    )
    assert "LIMIT 100" in sql.upper()

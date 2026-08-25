"""The fallback engine must produce SQL that passes the validator."""
from __future__ import annotations

import pytest

from app.llm import FallbackClient, LLMError, extract_sql
from app.validator import SQLValidator

CLIENT = FallbackClient()

QUESTIONS = [
    "How many orders were placed last month?",
    "Who are the top 5 customers by total spend?",
    "What's the average order value by region?",
    "List all products with less than 10 units in stock.",
    "Which employees have been with the company longer than 5 years?",
    "What is the total revenue for each product category?",
    "Show me the 3 best-selling products by quantity sold.",
    "How many customers signed up in each region last year?",
    "How many orders were placed in the last 3 months?",
    "What is the total revenue?",
    "How many pending orders are there?",
    "List all products in category Books",
    "How many customers do we have?",
]


@pytest.mark.parametrize("question", QUESTIONS)
def test_fallback_produces_valid_sql(demo_schema, question):
    sql = CLIENT.generate(question)
    assert "SELECT" in sql.upper()
    normalized, _ = SQLValidator(schema=demo_schema, max_rows=100).validate(sql)
    assert "LIMIT" in normalized.upper() or "COUNT(" in normalized.upper()


@pytest.mark.parametrize(
    "question,fragment",
    [
        # Regression: "less than N units in stock" must hit the stock rule,
        # not the price rule (which would return 0 rows here).
        ("List all products with less than 10 units in stock.", "stock_quantity < 10"),
        ("Which products have stock below 5?", "stock_quantity < 5"),
        # Regression: "3 best-selling" must respect the count.
        ("Show me the 3 best-selling products by quantity sold.", "LIMIT 3"),
        ("Top 3 customers by total spend?", "LIMIT 3"),
        ("How many orders were placed last month?", "COUNT(*)"),
        ("What's the average order value by region?", "c.region"),
        ("Show me the 2 most expensive products", "ORDER BY price DESC LIMIT 2"),
        ("What are the cheapest products?", "ORDER BY price ASC"),
    ],
)
def test_fallback_answer_semantics(demo_schema, question, fragment):
    sql = CLIENT.generate(question)
    assert fragment.lower() in sql.lower()
    SQLValidator(schema=demo_schema, max_rows=100).validate(sql)


def test_fallback_extract_sql_fences():
    raw = "```sql\nSELECT * FROM orders\n```"
    assert extract_sql(raw) == "SELECT * FROM orders"


def test_fallback_extract_sql_preamble():
    raw = "Here is your query:\nSELECT COUNT(*) FROM orders"
    assert extract_sql(raw) == "SELECT COUNT(*) FROM orders"


def test_fallback_raises_on_gibberish():
    with pytest.raises(LLMError):
        CLIENT.generate("the quick brown fox jumps over the lazy dog")

"""Prompt assembly: system instructions + schema + few-shot examples + question."""
from __future__ import annotations

from datetime import date

from .schema import SchemaSummary

# Curated few-shot examples tuned to the demo e-commerce schema.
FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (
        "How many orders were placed last month?",
        "SELECT COUNT(*) AS total_orders FROM orders "
        "WHERE order_date >= DATE_FORMAT(CURDATE() - INTERVAL 1 MONTH, '%Y-%m-01') "
        "AND order_date < DATE_FORMAT(CURDATE(), '%Y-%m-01')",
    ),
    (
        "Who are the top 5 customers by total spend?",
        "SELECT c.name, SUM(oi.quantity * oi.unit_price) AS total_spend "
        "FROM customers c "
        "JOIN orders o ON o.customer_id = c.customer_id "
        "JOIN order_items oi ON oi.order_id = o.order_id "
        "WHERE o.status = 'completed' "
        "GROUP BY c.customer_id, c.name "
        "ORDER BY total_spend DESC LIMIT 5",
    ),
    (
        "What's the average order value by region?",
        "SELECT c.region, AVG(t.total) AS avg_order_value "
        "FROM (SELECT o.order_id, o.customer_id, SUM(oi.quantity * oi.unit_price) AS total "
        "      FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
        "      WHERE o.status = 'completed' GROUP BY o.order_id) t "
        "JOIN customers c ON c.customer_id = t.customer_id "
        "GROUP BY c.region ORDER BY avg_order_value DESC",
    ),
    (
        "List all products with less than 10 units in stock.",
        "SELECT name, stock_quantity FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity",
    ),
    (
        "Which employees have been with the company longer than 5 years?",
        "SELECT name, hire_date FROM employees "
        "WHERE hire_date < DATE_SUB(CURDATE(), INTERVAL 5 YEAR) ORDER BY hire_date",
    ),
    (
        "What is the total revenue for each product category?",
        "SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue "
        "FROM order_items oi "
        "JOIN products p ON p.product_id = oi.product_id "
        "JOIN orders o ON o.order_id = oi.order_id "
        "WHERE o.status = 'completed' "
        "GROUP BY p.category ORDER BY revenue DESC",
    ),
    (
        "Show me the 3 best-selling products by quantity sold.",
        "SELECT p.name, SUM(oi.quantity) AS units_sold "
        "FROM order_items oi JOIN products p ON p.product_id = oi.product_id "
        "GROUP BY p.product_id, p.name ORDER BY units_sold DESC LIMIT 3",
    ),
    (
        "How many customers signed up in each region last year?",
        "SELECT region, COUNT(*) AS customers "
        "FROM customers WHERE signup_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR) "
        "GROUP BY region ORDER BY customers DESC",
    ),
]

SYSTEM_INSTRUCTIONS = """\
You are NatSQL, a system that converts natural-language questions about a MySQL \
database into safe, correct SQL queries.

Rules:
- Return ONLY the SQL query. No explanations, no markdown code fences, no trailing semicolons.
- SELECT statements only. Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or any write operation.
- Use exactly the table and column names from the schema below. Never invent identifiers.
- Today's date is {today}. Use MySQL date functions (CURDATE, DATE_SUB, DATE_FORMAT) for relative dates.
- If a question cannot be answered with the given schema, return exactly: ERROR: cannot answer with this schema
- Prefer readable column aliases. Order results sensibly.
- Aggregations over orders should usually filter status = 'completed' when computing spend/revenue.

Schema:
{schema}

Examples (question -> SQL):
{examples}
"""


class PromptBuilder:
    def __init__(self, schema: SchemaSummary, examples: list[tuple[str, str]] | None = None) -> None:
        self.schema = schema
        self.examples = examples if examples is not None else FEW_SHOT_EXAMPLES

    def _render_examples(self) -> str:
        return "\n".join(
            f"Q: {q}\nSQL: {s}" for q, s in self.examples
        )

    def build(self, question: str, error_context: str | None = None) -> str:
        system = SYSTEM_INSTRUCTIONS.format(
            today=date.today().isoformat(),
            schema=self.schema.to_text(),
            examples=self._render_examples(),
        )
        user = f"Question: {question}\nSQL:"
        if error_context:
            user = (
                f"The previous SQL failed to execute with this error: {error_context}\n"
                f"Fix the query and return only the corrected SQL.\n\n" + user
            )
        return f"{system}\n\n{user}"

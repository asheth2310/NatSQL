"""LLM integration.

Two engines behind the same interface:
- OllamaClient: talks to a local Ollama server (localhost:11434 by default).
- FallbackClient: deterministic keyword->SQL generator used when Ollama is
  unavailable, so the pipeline stays demoable fully offline.

The fallback is intentionally transparent: the UI shows which engine produced
the answer, and the SQL is always shown alongside results.
"""
from __future__ import annotations

import logging
import re
from typing import Union

import httpx

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM engine cannot produce SQL."""


# ---------------------------------------------------------------------------
# SQL extraction helper
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL)


def extract_sql(text: str) -> str:
    """Pull SQL out of a raw model response (strips fences and preamble)."""
    text = text.strip()
    if not text:
        raise LLMError("LLM returned an empty response")
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip().rstrip(";")
    # Take everything from the first SELECT onward (models sometimes add a preamble).
    idx = text.lower().find("select")
    if idx > 0:
        text = text[idx:]
    return text.rstrip(";")


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

class OllamaClient:
    name = "ollama"
    # Ollama consumes the full assembled prompt.
    takes_prompt = True

    def __init__(self, base_url: str, model: str, timeout: float = 60.0, temperature: float = 0.1) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature

    def engine_label(self) -> str:
        return f"ollama/{self.model}"

    def available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def generate(self, prompt: str) -> str:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "30m",  # stay loaded across demo questions
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": 800,
                    },
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama request failed: {e}") from e
        data = resp.json()
        if "error" in data:
            raise LLMError(f"Ollama error: {data['error']}")
        return data.get("response", "")


# ---------------------------------------------------------------------------
# Deterministic fallback (no external dependency)
# ---------------------------------------------------------------------------

_LOW_STOCK = 10
_COMPLETED_JOIN = (
    "FROM customers c JOIN orders o ON o.customer_id = c.customer_id "
    "JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'completed'"
)


class FallbackClient:
    """Keyword-driven SQL generator covering the demo question set."""

    name = "fallback"
    # The fallback matches on the raw question, not the assembled prompt.
    takes_prompt = False

    def engine_label(self) -> str:
        return "fallback (rule-based)"

    def generate(self, question: str) -> str:
        q = re.sub(r"[^a-z0-9\s%]", " ", question.lower())
        q = re.sub(r"\s+", " ", q).strip()

        def has(*words: str) -> bool:
            return any(w in q for w in words)

        # 1. Average order value by region
        if has("average order value") and has("region"):
            return (
                "SELECT c.region, AVG(t.total) AS avg_order_value "
                "FROM (SELECT o.order_id, o.customer_id, SUM(oi.quantity * oi.unit_price) AS total "
                "FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
                "WHERE o.status = 'completed' GROUP BY o.order_id) t "
                "JOIN customers c ON c.customer_id = t.customer_id "
                "GROUP BY c.region ORDER BY avg_order_value DESC"
            )

        # 2. Average order value overall
        if has("average order value", "avg order value", "aov"):
            return (
                "SELECT AVG(t.total) AS avg_order_value "
                "FROM (SELECT o.order_id, SUM(oi.quantity * oi.unit_price) AS total "
                "FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
                "WHERE o.status = 'completed' GROUP BY o.order_id) t"
            )

        # 3. Top N customers by spend / revenue
        m = re.search(r"top\s+(\d+)\s+customers?", q)
        if m and has("spend", "revenue", "purchase", "value", "money"):
            n = m.group(1)
            return (
                f"SELECT c.name, SUM(oi.quantity * oi.unit_price) AS total_spend "
                f"{_COMPLETED_JOIN} GROUP BY c.customer_id, c.name "
                f"ORDER BY total_spend DESC LIMIT {n}"
            )

        # 4. Best-selling / top products by quantity sold
        m = re.search(r"top\s+(\d+)\s+products?", q)
        if not m:
            m = re.search(r"(\d+)\s+best[\- ]?selling", q)
        if m or has("best-selling", "best selling", "most sold", "most popular"):
            n = m.group(1) if m else "5"
            return (
                f"SELECT p.name, SUM(oi.quantity) AS units_sold "
                f"FROM order_items oi JOIN products p ON p.product_id = oi.product_id "
                f"JOIN orders o ON o.order_id = oi.order_id WHERE o.status = 'completed' "
                f"GROUP BY p.product_id, p.name ORDER BY units_sold DESC LIMIT {n}"
            )

        # 5. Revenue / sales by category
        if has("revenue", "sales") and has("categor"):
            return (
                "SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue "
                "FROM order_items oi JOIN products p ON p.product_id = oi.product_id "
                "JOIN orders o ON o.order_id = oi.order_id WHERE o.status = 'completed' "
                "GROUP BY p.category ORDER BY revenue DESC"
            )

        # 6. Total revenue / sales
        if has("total revenue", "total sales", "how much revenue", "how much money"):
            return (
                "SELECT SUM(oi.quantity * oi.unit_price) AS total_revenue "
                "FROM order_items oi JOIN orders o ON o.order_id = oi.order_id "
                "WHERE o.status = 'completed'"
            )

        # 7. Products with low stock ("stock less than N", "less than N units in stock")
        m = re.search(r"stock[^a-z]*(?:is\s+)?(?:less than|below|under|<)\s*(\d+)", q)
        if not m:
            m = re.search(r"less than\s*(\d+)\s*units?\s+(?:in\s+)?stock", q)
        if m:
            n = m.group(1)
            return f"SELECT name, stock_quantity FROM products WHERE stock_quantity < {n} ORDER BY stock_quantity"
        if has("low stock", "out of stock", "running low"):
            return (
                f"SELECT name, stock_quantity FROM products "
                f"WHERE stock_quantity < {_LOW_STOCK} ORDER BY stock_quantity"
            )

        # 8. Employee tenure
        m = re.search(r"(?:longer than|more than|over|at least)\s*(\d+)\s*years", q)
        if has("employee", "tenure", "hired", "senior"):
            n = m.group(1) if m else "5"
            return (
                f"SELECT name, department, hire_date FROM employees "
                f"WHERE hire_date < DATE_SUB(CURDATE(), INTERVAL {n} YEAR) ORDER BY hire_date"
            )

        # 9. Orders placed last month
        if has("last month", "previous month", "last 30 days", "past month"):
            return (
                "SELECT COUNT(*) AS total_orders FROM orders "
                "WHERE order_date >= DATE_FORMAT(CURDATE() - INTERVAL 1 MONTH, '%Y-%m-01') "
                "AND order_date < DATE_FORMAT(CURDATE(), '%Y-%m-01')"
            )

        # 10. Orders in last N months
        m = re.search(r"(?:last|past)\s+(\d+)\s+months", q)
        if m and has("orders"):
            return (
                f"SELECT COUNT(*) AS total_orders FROM orders "
                f"WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL {m.group(1)} MONTH)"
            )

        # 11. Order counts by status / specific status
        status_words = ["pending", "cancelled", "completed"]
        mentioned = [s for s in status_words if s in q]
        if has("orders") and (mentioned or has("status")):
            if mentioned:
                return (
                    f"SELECT COUNT(*) AS total FROM orders WHERE status = '{mentioned[0]}'"
                )
            return (
                "SELECT status, COUNT(*) AS total FROM orders GROUP BY status ORDER BY total DESC"
            )

        # 12. Total number of orders
        if has("how many orders", "number of orders", "count of orders"):
            return "SELECT COUNT(*) AS total_orders FROM orders"

        # 13. Customers by region
        if has("customer") and has("region"):
            return (
                "SELECT region, COUNT(*) AS customers FROM customers "
                "GROUP BY region ORDER BY customers DESC"
            )

        # 14. Total customers
        if has("how many customers", "number of customers"):
            return "SELECT COUNT(*) AS total_customers FROM customers"

        # 15. Products in a category
        m = re.search(r"category\s+([a-z &]+)$", q)
        if m and has("product"):
            return (
                f"SELECT name, price, stock_quantity FROM products "
                f"WHERE category = '{m.group(1).strip()}' ORDER BY price DESC"
            )

        # 16. Products above/below a price
        m = re.search(r"(?:more than|over|above|greater than|>)\s*(\d+)", q)
        if m and has("product"):
            return (
                f"SELECT name, price, stock_quantity FROM products "
                f"WHERE price > {m.group(1)} ORDER BY price"
            )
        m = re.search(r"(?:less than|under|below|<)\s*(\d+)", q)
        if m and has("product"):
            return (
                f"SELECT name, price, stock_quantity FROM products "
                f"WHERE price < {m.group(1)} ORDER BY price"
            )

        # 17. Most/least expensive products
        # (check the "N most expensive" form first so the digit isn't skipped)
        m = re.search(r"(\d+)\s+most\s+expensive\s+products?", q)
        if not m:
            m = re.search(r"(?:most|top)\s*(\d+)?\s*expensive\s+products?", q)
        if m:
            n = m.group(1) or "5"
            return f"SELECT name, price FROM products ORDER BY price DESC LIMIT {n}"
        if has("cheapest", "least expensive"):
            return "SELECT name, price FROM products ORDER BY price ASC LIMIT 5"

        # 18. List all products
        if has("product"):
            return "SELECT product_id, name, category, price, stock_quantity FROM products ORDER BY name"

        # 19. Recent orders
        if has("orders"):
            return "SELECT order_id, customer_id, order_date, status FROM orders ORDER BY order_date DESC"

        # 19. Last resort: mention of a known table name
        table_map = {
            "customer": "SELECT * FROM customers",
            "product": "SELECT * FROM products",
            "order": "SELECT * FROM orders",
            "employee": "SELECT * FROM employees",
        }
        for key, sql in table_map.items():
            if key in q:
                return sql

        raise LLMError("could not map the question to a query")


def llm_input_for(client: LLMClient, prompt: str, question: str) -> str:
    """Return the input the engine expects: full prompt or bare question."""
    return prompt if client.takes_prompt else question


def build_llm_client(settings) -> "LLMClient":
    """Pick the engine: explicit setting, else Ollama if reachable, else fallback."""
    from .config import Settings  # noqa: F401  (type hint only)

    if settings.ollama_enabled is False:
        logger.info("Ollama disabled via env; using fallback engine")
        return FallbackClient()

    ollama = OllamaClient(
        settings.ollama_url,
        settings.ollama_model,
        timeout=settings.llm_timeout_s,
        temperature=settings.llm_temperature,
    )
    if ollama.available():
        logger.info("Ollama reachable at %s (model %s)", settings.ollama_url, settings.ollama_model)
        return ollama

    logger.warning(
        "Ollama not reachable at %s — falling back to the rule-based engine",
        settings.ollama_url,
    )
    return FallbackClient()


# Union type for the interchangeable engines
LLMClient = Union[OllamaClient, FallbackClient]

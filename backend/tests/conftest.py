"""Shared test fixtures — an in-memory SchemaSummary mirroring db/*.sql."""
from __future__ import annotations

import pytest

from app.schema import ColumnInfo, ForeignKey, SchemaSummary, TableInfo


def _col(name: str, dtype: str = "VARCHAR", pk: bool = False) -> ColumnInfo:
    return ColumnInfo(name=name, data_type=dtype, nullable=not pk, is_primary_key=pk)


@pytest.fixture(scope="session")
def demo_schema() -> SchemaSummary:
    tables: dict[str, TableInfo] = {
        "customers": TableInfo(
            name="customers",
            columns=[
                _col("customer_id", "INT", pk=True),
                _col("name"),
                _col("email"),
                _col("region"),
                _col("signup_date", "DATE"),
            ],
            foreign_keys=[],
        ),
        "products": TableInfo(
            name="products",
            columns=[
                _col("product_id", "INT", pk=True),
                _col("name"),
                _col("category"),
                _col("price", "DECIMAL"),
                _col("stock_quantity", "INT"),
            ],
            foreign_keys=[],
        ),
        "orders": TableInfo(
            name="orders",
            columns=[
                _col("order_id", "INT", pk=True),
                _col("customer_id", "INT"),
                _col("order_date", "DATE"),
                _col("status", "VARCHAR"),
            ],
            foreign_keys=[ForeignKey("customer_id", "customers", "customer_id")],
        ),
        "order_items": TableInfo(
            name="order_items",
            columns=[
                _col("order_item_id", "INT", pk=True),
                _col("order_id", "INT"),
                _col("product_id", "INT"),
                _col("quantity", "INT"),
                _col("unit_price", "DECIMAL"),
            ],
            foreign_keys=[
                ForeignKey("order_id", "orders", "order_id"),
                ForeignKey("product_id", "products", "product_id"),
            ],
        ),
        "employees": TableInfo(
            name="employees",
            columns=[
                _col("employee_id", "INT", pk=True),
                _col("name"),
                _col("department"),
                _col("hire_date", "DATE"),
            ],
            foreign_keys=[],
        ),
    }
    return SchemaSummary(tables, database="demo")

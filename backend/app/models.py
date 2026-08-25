"""Pydantic models for the API."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Natural-language question")


class QueryResponse(BaseModel):
    question: str
    engine: str
    sql: Optional[str] = None
    columns: list[str] = []
    rows: list[list[Any]] = []
    row_count: int = 0
    truncated: bool = False
    retries: int = 0
    notes: list[str] = []
    error: Optional[str] = None
    error_type: Optional[str] = None  # "validation" | "execution" | "llm"
    elapsed_ms: int = 0


class VerifyRequest(BaseModel):
    sql: str = Field(..., description="The generated SQL to re-run directly against MySQL")
    question: Optional[str] = None


class VerifyResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    elapsed_ms: int


class ColumnMeta(BaseModel):
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool


class ForeignKeyMeta(BaseModel):
    column: str
    ref_table: str
    ref_column: str


class TableMeta(BaseModel):
    name: str
    columns: list[ColumnMeta]
    foreign_keys: list[ForeignKeyMeta]


class SchemaResponse(BaseModel):
    database: str
    tables: list[TableMeta]


class HealthResponse(BaseModel):
    status: str
    database: str
    schema_tables: int
    llm_engine: str

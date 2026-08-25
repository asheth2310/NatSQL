"""NatSQL backend — FastAPI application.

Pipeline per request (FR1-FR10):
  question -> prompt -> LLM -> validate -> execute -> (retry once on exec error) -> results
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .executor import ExecutionError, QueryExecutor
from .llm import LLMError, build_llm_client, extract_sql, llm_input_for
from .models import HealthResponse, QueryRequest, QueryResponse, SchemaResponse, VerifyRequest, VerifyResponse
from .prompt import PromptBuilder
from .schema import SchemaError, SchemaService
from .validator import SQLValidator, ValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("natsql")

app = FastAPI(title="NatSQL", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

schema_service = SchemaService(
    host=settings.db_host,
    port=settings.db_port,
    user=settings.db_user,
    password=settings.db_password,
    database=settings.db_name,
)
executor = QueryExecutor(
    host=settings.db_host,
    port=settings.db_port,
    user=settings.db_user,
    password=settings.db_password,
    database=settings.db_name,
    query_timeout_ms=settings.query_timeout_ms,
)
llm = build_llm_client(settings)


def _load_schema() -> "SchemaSummary":
    try:
        return schema_service.get_summary()
    except SchemaError as e:
        logger.error("Schema load failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}") from e


def _validator_for(schema) -> SQLValidator:
    return SQLValidator(schema=schema, max_rows=settings.max_rows)


# -- endpoints ---------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_status = executor.healthcheck()
    schema_loaded = schema_service.is_loaded()
    return HealthResponse(
        status="ok",
        database="ok" if db_status is None else f"error: {db_status}",
        schema_tables=len(schema_service.get_summary().tables) if schema_loaded else 0,
        llm_engine=llm.engine_label(),
    )


@app.get("/api/schema", response_model=SchemaResponse)
def get_schema() -> SchemaResponse:
    summary = _load_schema()
    return SchemaResponse(database=summary.database, tables=summary.to_meta())


@app.post("/api/schema/refresh", response_model=SchemaResponse)
def refresh_schema() -> SchemaResponse:
    summary = schema_service.refresh()
    return SchemaResponse(database=summary.database, tables=summary.to_meta())


@app.post("/api/query/verify", response_model=VerifyResponse)
def verify_query(req: VerifyRequest) -> VerifyResponse:
    """Re-run an already-generated SQL directly against MySQL.

    Proof point for the demo: the exact SQL shown in the UI, executed
    through the same validator and read-only connection, produces the
    same rows the app reported. The SQL is validated again here — this
    endpoint never executes unvalidated text.
    """
    summary = _load_schema()
    validator = _validator_for(summary)
    try:
        normalized, _ = validator.validate(req.sql)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"SQL rejected by validator: {e}") from e

    started = time.monotonic()
    try:
        columns, rows = executor.run(normalized)
    except ExecutionError as e:
        logger.warning("Verify execution failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}") from e

    elapsed = int((time.monotonic() - started) * 1000)
    logger.info("Verify OK question=%r rows=%d elapsed_ms=%d", req.question, len(rows), elapsed)
    return VerifyResponse(sql=normalized, columns=columns, rows=rows, row_count=len(rows), elapsed_ms=elapsed)


@app.post("/api/query", response_model=QueryResponse)
def run_query(req: QueryRequest) -> QueryResponse:
    question = req.question.strip()
    started = time.monotonic()
    summary = _load_schema()
    builder = PromptBuilder(summary)
    validator = _validator_for(summary)

    last_error: str | None = None
    normalized_sql: str | None = None
    raw_sql: str | None = None
    notes: list[str] = []
    retries = 0

    for attempt in range(settings.max_retries + 1):
        if attempt > 0:
            retries = attempt
            prompt = builder.build(question, error_context=last_error)
            logger.info("Retry %d after execution error: %s", attempt, last_error)
        else:
            prompt = builder.build(question)

        try:
            raw_sql = extract_sql(llm.generate(llm_input_for(llm, prompt, question)))
        except LLMError as e:
            logger.warning("LLM failed for question=%r: %s", question, e)
            return _response(req, started, error=f"The language model could not generate a query: {e}",
                             error_type="llm", sql=raw_sql)

        logger.info("Generated SQL (engine=%s): %s", llm.engine_label(), raw_sql)

        try:
            normalized_sql, notes = validator.validate(raw_sql)
        except ValidationError as e:
            logger.info("Validation rejected SQL: %s", e)
            return _response(req, started, error=f"Could not produce a safe query: {e}",
                             error_type="validation", sql=raw_sql, notes=[str(e)])

        try:
            columns, rows = executor.run(normalized_sql)
        except ExecutionError as e:
            last_error = str(e)
            logger.warning("Execution failed (attempt %d): %s", attempt + 1, last_error)
            continue  # retry with error context

        elapsed = int((time.monotonic() - started) * 1000)
        logger.info(
            "Query OK question=%r rows=%d retries=%d elapsed_ms=%d",
            question, len(rows), retries, elapsed,
        )
        truncated = len(rows) == settings.max_rows
        return QueryResponse(
            question=question,
            engine=llm.engine_label(),
            sql=normalized_sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            retries=retries,
            notes=notes,
            elapsed_ms=elapsed,
        )

    elapsed = int((time.monotonic() - started) * 1000)
    logger.warning("Query failed after %d retries: %s", settings.max_retries, last_error)
    return _response(req, started, error=f"Query failed to execute: {last_error}",
                     error_type="execution", sql=normalized_sql, retries=retries,
                     notes=[f"last execution error: {last_error}"])


def _response(req: QueryRequest, started: float, *, error: str, error_type: str,
              sql: str | None = None, notes: list[str] | None = None,
              retries: int = 0) -> QueryResponse:
    elapsed = int((time.monotonic() - started) * 1000)
    return QueryResponse(
        question=req.question.strip(),
        engine=llm.engine_label(),
        sql=sql,
        error=error,
        error_type=error_type,
        notes=notes or [],
        retries=retries,
        elapsed_ms=elapsed,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)

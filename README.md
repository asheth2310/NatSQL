# NatSQL — Natural Language Interface for Databases

Ask a MySQL database a question in plain English; NatSQL turns it into a validated, safe SQL query, executes it, and shows you the results — along with the SQL it generated, so you never have to trust it blindly.

Built as a fully local MVP: **no external API keys, no internet required** for the demo. If Ollama is installed it uses a local LLM; otherwise it transparently falls back to a deterministic rule-based engine, so the pipeline is demoable anywhere.

```
question ─▶ prompt ─▶ LLM (Ollama or fallback) ─▶ hard SQL validator ─▶ read-only MySQL ─▶ results table
                                                       │ (sqlglot)
                                                   rejects writes, unknown tables/columns,
                                                   injects & clamps LIMIT
```

---

## Quickstart (demo in under 5 minutes)

Prerequisites: Docker, Python 3.11+, Node 18+.

```bash
# 1. Start the demo MySQL database (schema + seed + read-only role are applied automatically)
docker compose up -d mysql

# 2. Start the backend
cd backend
python -m venv ../.venv
../.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# ../.venv/bin/pip install -r requirements.txt               # macOS/Linux
../.venv/Scripts/python -m uvicorn app.main:app --port 8000  # Windows
# ../.venv/bin/python -m uvicorn app.main:app --port 8000    # macOS/Linux

# 3. Start the frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — a terminal-style UI. Type a question at the
`user@natsql:~$` prompt (or click a suggestion) and press Enter. Ask:

- *"How many orders were placed last month?"*
- *"Who are the top 5 customers by total spend?"*
- *"What's the average order value by region?"*
- *"List all products with less than 10 units in stock."*
- *"Which employees have been with the company longer than 5 years?"*

> The demo MySQL listens on host port **3307** so it never collides with a local MySQL on 3306.

### Local LLM via Ollama (the "ask anything" engine)

```bash
ollama pull qwen2.5-coder:3b   # CPU-friendly; 7b+ if you have a GPU
```

The backend auto-detects Ollama at startup (`GET /api/tags`) and answers **arbitrary**
questions with it — anything the few-shot patterns don't cover, because the prompt
embeds the live schema and the model composes SQL from it. Set `NATSQL_OLLAMA_MODEL`
to choose the model (the bundled `.env` already sets `qwen2.5-coder:3b`).

If Ollama is absent or unreachable, the rule-based fallback takes over automatically
and the UI badge shows which engine answered. Force a specific engine with
`NATSQL_OLLAMA_ENABLED=false` (always fallback) or `=true` (require Ollama).

Latency on CPU-only hardware is roughly 5–15s per question for a 3b model (the model
stays warm for 30 minutes between questions); the fallback answers the curated set in
~100ms. Either way, every query — LLM or fallback — passes the same hard validator.

---

## Architecture

```
┌──────────────┐   POST /api/query   ┌───────────────────────────────────────────────┐   ┌───────────┐
│  React/Vite  │───────────────────▶│                 FastAPI backend                 │──▶│   MySQL   │
│   frontend   │◀───────────────────│                                                 │◀──│ (read-only│
└──────────────┘   results + SQL    │  SchemaService → PromptBuilder → LLMClient      │   │   role)   │
                                    │       → SQLValidator (sqlglot) → QueryExecutor  │   └───────────┘
                                    └───────────────────────────────────────────────┘
```

| Component | File | Responsibility |
|---|---|---|
| `SchemaService` | `backend/app/schema.py` | Introspects `INFORMATION_SCHEMA` (tables, columns, types, PKs, FKs), caches in memory, refreshable via `POST /api/schema/refresh` |
| `PromptBuilder` | `backend/app/prompt.py` | System instructions + schema dump + 8 few-shot examples + user question; appends the execution error on retry |
| `LLMClient` | `backend/app/llm.py` | `OllamaClient` (local REST) and `FallbackClient` (deterministic, offline-safe), interchangeable via `build_llm_client` |
| `SQLValidator` | `backend/app/validator.py` | **Hard safety gate.** Parses with sqlglot (MySQL dialect) and enforces: single SELECT statement, no writes/DDL/raw commands, no `INTO OUTFILE`, no dangerous functions (`SLEEP`, `BENCHMARK`, `LOAD_FILE`, …), all tables/columns exist in the whitelisted schema (aliases, subqueries and CTEs resolved), LIMIT always present and clamped to the configured maximum |
| `QueryExecutor` | `backend/app/executor.py` | Runs the query as the dedicated read-only MySQL user; pins the session to `READ ONLY`, sets `MAX_EXECUTION_TIME` and a client read timeout, autocommit only |
| `main.py` | `backend/app/main.py` | FastAPI app: `POST /api/query`, `GET /api/schema`, `POST /api/schema/refresh`, `GET /api/health`; one error-driven retry with the DB error fed back to the LLM |

### Data flow per request

1. User submits a question → `POST /api/query`
2. Schema summary is loaded from cache (introspected on first use)
3. `PromptBuilder` assembles prompt = instructions + schema + few-shots + question
4. `LLMClient` returns SQL (Ollama, or fallback if offline)
5. `SQLValidator` parses/validates/normalizes — rejects with a clear message if unsafe
6. `QueryExecutor` runs it; if execution fails, the error is appended to the prompt for one retry
7. Results (columns + rows), the final SQL, engine, and validation notes return to the UI

---

## Safety design (defense in depth)

The model is never trusted. Every query must pass all layers:

1. **Prompt level** — system instructions demand SELECT-only, real identifiers, and forbid writes; user input stays structurally separated from instructions.
2. **Hard validation layer** — sqlglot parses the SQL and rejects anything that isn't a single, whitelisted SELECT: no `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/`CREATE`, no multi-statements, no `INTO OUTFILE`, no `SLEEP()`/`LOAD_FILE()`/etc., no unknown table or column (qualified refs resolved through aliases/CTEs/subqueries).
3. **Row limit** — a `LIMIT` is injected if missing and clamped to `NATSQL_MAX_ROWS` (default 100).
4. **Runtime isolation** — the backend connects as a MySQL user with `SELECT`-only grants on the demo schema (`db/03_roles.sql`); the session is additionally pinned to read-only and given a query timeout.
5. **Transparency** — the generated SQL and engine are always shown in the UI, so a wrong answer is visible and inspectable rather than silently trusted.

---

## Demo dataset

E-commerce schema (see `db/`):

- **customers** (name, email, region, signup_date)
- **products** (name, category, price, stock_quantity)
- **orders** (customer_id, order_date, status) — 60 orders spanning ~8 months
- **order_items** (order_id, product_id, quantity, unit_price) — 95 line items
- **employees** (department, hire_date) — for tenure questions

Seed dates are relative to `CURDATE()`, so "last month", "last 3 months", and "longer than 5 years" questions stay correct no matter when the demo runs. Reset anytime: `docker compose down -v && docker compose up -d mysql`.

---

## API

| Endpoint | Description |
|---|---|
| `POST /api/query` `{"question": "..."}` | Run the NL→SQL pipeline. Returns `{sql, columns, rows, engine, notes, error, ...}` |
| `POST /api/query/verify` `{"sql": "..."}` | Re-run a generated SQL directly against MySQL (re-validated first) — the UI's proof that the shown query is what produced the results |

### CLI commands (frontend)

The UI is a terminal emulator — everything is a command:

| Command | What it does |
|---|---|
| *anything else* | Ask the database in plain English |
| `/schema` | Introspect and print the database schema (tables, columns, PKs, FKs) |
| `/verify` | Re-run the last generated SQL directly against MySQL and confirm the output is identical |
| `/help` | List commands |
| `/clear` | Clear the terminal |

`↑` / `↓` cycle through previously asked questions like shell history.
| `GET /api/schema` | Introspected schema (tables, columns, FKs) |
| `POST /api/schema/refresh` | Re-introspect and refresh the schema cache |
| `GET /api/health` | Backend/DB/LLM status |

### Configuration (`backend/.env`, see `.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `NATSQL_DB_HOST/PORT/USER/PASSWORD/NAME` | `127.0.0.1:3307 natsql_ro/…/demo` | Read-only MySQL connection |
| `NATSQL_OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `NATSQL_OLLAMA_MODEL` | `qwen2.5-coder:3b` (set in `backend/.env`) | Model name |
| `NATSQL_OLLAMA_ENABLED` | auto | `false` forces fallback, `true` requires Ollama |
| `NATSQL_MAX_ROWS` | `100` | Hard cap on returned rows |
| `NATSQL_QUERY_TIMEOUT_MS` | `5000` | Server-side kill switch per query |
| `NATSQL_MAX_RETRIES` | `1` | Execution-error retries through the LLM |

---

## Tests

```bash
cd backend
../.venv/Scripts/python -m pytest tests/ -q     # 69 tests, no DB required
```

Covers the validator (accept/reject matrices, LIMIT enforcement, alias/CTE/subquery resolution), the fallback engine's output correctness, prompt assembly, and LLM engine routing.

## Project layout

```
├── backend/app/          FastAPI app (schema, prompt, llm, validator, executor)
├── backend/tests/        pytest suite
├── frontend/             Vite + React UI
├── db/                   01_schema.sql · 02_seed.sql · 03_roles.sql
├── docker-compose.yml    Demo MySQL on host port 3307
└── .env.example          Configuration reference
```

## Known limitations (MVP scope)

- SELECT-only by design; no writes, no multi-database joins, no multi-turn memory.
- The rule-based fallback covers the demo question set — it is a safety net and test harness, not a general NL2SQL engine. The real capability comes from Ollama.
- `UNION`/`INTERSECT`/`EXCEPT` are rejected (a union's LIMIT can't reliably bound the result set).
- A single shared read-only DB role; row-level access control is out of scope.

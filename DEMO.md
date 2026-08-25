# NatSQL — Interview Demo Runbook

How to present NatSQL in a 5–10 minute demo. Everything here is verified against the
live stack; the answer key at the bottom has the exact numbers you'll see.

---

## 0. The 60-second pitch (memorize this)

> "NatSQL is a natural-language interface for a MySQL database. You type a question in
> plain English — *'top 5 customers by revenue last quarter'* — and it generates a SQL
> query with a local LLM, runs it through a hard safety validator, executes it against a
> **read-only** database role, and shows you the results *and* the SQL it generated.
>
> Three things I want you to notice: **safety is enforced in code, not in the prompt** —
> nothing reaches the database unless it parses as a single SELECT against the whitelisted
> schema. **Transparency** — the SQL is always on screen, so you never trust the model
> blindly. And it runs **fully offline** — if the local LLM isn't available it falls back
> to a deterministic engine, so the demo never dies because of the network."

---

## 1. Pre-demo checklist (do this 15 minutes before)

```bash
# 1. Everything up?
curl http://127.0.0.1:8000/api/health        # expect status ok, database ok
curl -o /dev/null -w "%{http_code}" http://localhost:5173/   # expect 200

# 2. (Optional but recommended) fresh DB so row counts match this runbook exactly
docker compose down -v && docker compose up -d mysql
# wait ~30s for healthy, then restart the backend once

# 3. Frontend: hard-refresh the browser (Cmd/Ctrl+Shift+R)
#    → clears the session history so your demo starts clean
```

Also: close unused tabs, disable notifications, and have a second terminal window open
with `cd backend` ready — you'll use it once, to show the test suite.

---

## 2. The walkthrough (~8 minutes, timed)

### 0:00–1:00 — Pitch
Say the 60-second pitch above while the page loads. Point at the badge in the top-right:
**`ollama/qwen2.5-coder:3b`** and explain: *"that badge tells you which engine answered —
a local LLM. If the model goes away it falls back to a deterministic engine, so the demo
never dies because of infrastructure."* (Being upfront about the engine is a strength:
it shows demo-reliability was a design goal, not a shortcut.)

**Warm up before the interviewer arrives:** ask one throwaway question (e.g. "what is the
total revenue?") a minute before the demo — the first LLM call loads the model into
memory (can take ~30–60s); after that each question is ~5–15s on CPU.

### 1:00–3:30 — Live queries (start with these, in order)
The UI is a terminal: type at the `user@natsql:~$` prompt and press Enter, or click a
suggestion chip. Narrate *what* you expect before the result appears — that's what makes
it look like you understand the system:

1. **"How many orders were placed last month?"** → `15`.
   Say: *"Note the SQL filters to the previous calendar month with `DATE_FORMAT` — the
   model knows today's date because it's injected into the prompt. The seed data uses
   relative dates, so this question stays correct no matter when the demo runs."*
2. **"Who are the top 5 customers by total spend?"** → Alice Johnson $3,531.96 at the top.
   Say: *"This is a three-table join with aggregation. Notice it only counts
   `status = 'completed'` orders — it didn't just guess; it excluded cancelled orders."*
3. **"What's the average order value by region?"** → North America $296.96, then Asia
   Pacific, Europe… Say: *"This one needs a subquery — average order value is the average
   of per-order totals, which requires a two-level aggregation. The system handled it."*
4. **"What is the total revenue?"** → `8,926.80`.
   Then immediately: **"What is the total revenue for each product category?"** →
   Electronics 4,449.32 + Home & Kitchen 1,934.92 + Clothing 1,467.87 + Sports 819.78 +
   Books 254.91 = **8,926.80**. Say: *"The answers reconcile. You can cross-check the
   system's output the same way you'd verify an analyst's — that's what the SQL is for."*

Pause here and let them ask a question themselves — *"ask it anything"*. This is the
moment the LLM shines: "revenue by month", "customers who never ordered", "how many
orders did Alice Johnson place" — arbitrary questions work because the prompt embeds
the live schema. If Ollama were down, the fallback would answer the curated set and
gracefully say "could not map the question to a query" for anything else — no guessing,
no wrong answers.

### 3:30–5:00 — Safety deep dive (this is what engineers interviewers care about)
The SQL is always visible — each result echoes it as a `sql>` line before the table.
Point at the footer under the results: `5 rows in set (81 ms) [engine: fallback (rule-based)]`
and the injected `LIMIT 100` in the SQL.

> "Every query — from the LLM or the fallback — passes through a hard validation gate
> before it touches the database. sqlglot parses it; the validator rejects anything that
> isn't a single SELECT, any table or column not in the introspected schema, `INTO
> OUTFILE`, functions like `SLEEP()`; and it injects a `LIMIT 100` if the model forgot
> one — you can see it added `LIMIT 100` right here. The prompt asks for safe SQL, but
> the prompt is **not** the safety boundary. The validator is. And even if the validator
> were bypassed, the DB role can't write — I created a user with SELECT-only grants, and
> the session is additionally pinned to read-only with a 5-second kill switch."

Then type `/verify` at the prompt.

> "Watch this — I'm re-running the *exact* SQL you see here, not the natural-language
> question, straight through the same validator and the read-only connection. The app
> rendered the result as a table; MySQL's own output appears below. Same rows, same
> numbers: **verified, the query shown is literally what produced this answer.**"

Then the flex: switch to your prepared terminal and run

```bash
cd backend && ../.venv/Scripts/python -m pytest tests/ -q
```

> "69 tests — here's the rejection matrix: `DELETE`, `UPDATE`, `DROP`, `SELECT … INTO
> OUTFILE`, `SLEEP()`, unknown columns, cross-database references, multi-statement
> injection — all rejected before execution."

(~5 seconds of scrolling green dots; then back to the browser.)

### 5:00–6:30 — Architecture + retry
> "The pipeline is: question → prompt (schema + 8 few-shot examples + the question) →
> LLM → validator → executor. If execution fails — say the model joined on the wrong
> column — the database error is fed back into a second prompt with 'fix the query', and
> it retries once before giving up. Every request is logged: generated SQL, validation
> outcome, row count, latency. That's the observability story — during the interview I
> could narrate exactly what every query did."

Optional live proof of the retry: ask a question that generates SQL that *validates but
fails to execute*. With the fallback this is hard to trigger, so if you want to show it,
say it works "end-to-end with the LLM engine" and don't fake it.

### 6:30–8:00 — Close
> "The MVP deliberately scoped out writes, multi-turn memory, and auth — the demo is
> read-only on a shared schema, which is what makes the safety argument airtight. Natural
> next steps: an accuracy harness scoring the ~20-question set (the PRD targets ≥80%),
> adversarial prompt-injection tests, and tuning the few-shot examples against the real
> model. What would you like to dig into?"

---

## 3. Answer key (exact values you'll see)

| Question | Expected result |
|---|---|
| How many orders were placed last month? | `15` |
| Who are the top 5 customers by total spend? | Alice Johnson 3531.96 · Elena Rodriguez 1638.86 · Hannah Lee 1257.89 · Bob Martinez 1219.41 · Chen Wei 537.39 |
| What's the average order value by region? | North America 296.96 · Asia Pacific 128.23 · Europe 124.72 · Africa 54.98 · South America 40.98 |
| List all products with less than 10 units in stock | The Pragmatic Programmer (3) · Chef's Knife Set (5) · USB-C Hub (8) |
| Which employees have been with the company longer than 5 years? | Sarah Connor · Marcus Bell · Priya Sharma · Tom O'Reilly (4 rows) |
| Show me the 3 best-selling products by quantity sold | Resistance Bands (15) · Cotton T-Shirt (13) · Wireless Mouse (8) |
| What is the total revenue? | `8926.80` |
| Total revenue for each product category? | Electronics 4449.32 · Home & Kitchen 1934.92 · Clothing 1467.87 · Sports 819.78 · Books 254.91 |
| How many pending orders are there? | `5` |

---

## 4. What the interviewer is actually evaluating — and how to hit it

| They're checking | How you hit it |
|---|---|
| **Do you understand your own safety design?** | Lead with "the prompt is not the safety boundary." Name the layers: prompt → validator → read-only role → read-only session → timeout. |
| **Is this real or a demo hack?** | The SQL is shown; results are cross-checkable; the fallback is labeled, not hidden; 69 tests exist. Show the tests. |
| **Did you think about failure modes?** | Mention: validation failure returns a clear message, execution failure retries once with error context, DB-down returns 503 with a readable detail, unanswerable questions say so. |
| **Architecture judgment** | Schema cache + refresh endpoint, engine abstraction (Ollama/fallback behind one interface), defense in depth, observability logging. |
| **Scope discipline** | Know exactly what's cut (writes, auth, multi-turn) and *why* — it makes the MVP credible. |

---

## 5. Likely questions and short answers

**"How do you stop the model from writing `DROP TABLE`?"**
Three layers. The prompt forbids it. The validator *rejects* anything that isn't a single
SELECT — sqlglot parses first, so even obfuscated multi-statement strings split and fail.
And the MySQL user physically cannot write: SELECT-only grants, session pinned read-only.
Even a perfect prompt bypass still can't write.

**"What if the model hallucinates a column?"**
The validator checks every identifier against the introspected schema — tables, columns,
aliases resolved through joins and subqueries. Unknown identifier → rejected with a clear
message. That's also why schema drift is handled: `POST /api/schema/refresh` re-introspects.

**"Why the rule-based fallback? Isn't that cheating?"**
It's a demo-reliability feature, and it's labeled in the UI. The PRD requires running
fully offline — no internet dependency during the interview. The fallback guarantees the
pipeline is demonstrable, and it doubles as a test harness for the validator. The real
NL2SQL capability is the Ollama path; the fallback covers the curated question set.

**"Why sqlglot instead of just regex?"**
Regex can't parse nested SQL. sqlglot gives a real AST for the MySQL dialect, so we can
walk every table and column node, distinguish `SELECT` from `INSERT`, and reliably inject
a `LIMIT`. It's the difference between "looks safe" and "is provably a single SELECT."

**"Latency?"**
With the fallback: ~60–200 ms round-trip (measured: 59–187 ms). With a local 7B model the
PRD budget is under 5 seconds including generation. All local — no network hop to a cloud API.

**"Why not just show results and skip the SQL?"**
Hiding the SQL is how you get silent wrong answers. Showing it is the trust mechanism:
the user can sanity-check the query, and in a demo the audience can audit the reasoning.
It's also the PRD's transparency requirement (FR9).

**"What would you do next?"**
An accuracy harness (run the ~20-question set, score ≥80% per the PRD), adversarial
prompt-injection tests, per-user row-level security once auth lands, and multi-turn
memory for follow-ups like "and what about last quarter?"

---

## 6. Failure handling (know these cold)

| If this happens | Do this |
|---|---|
| `Database unavailable` / health shows error | `docker compose up -d mysql`, wait ~30s for healthy, restart backend |
| Backend not running | `cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --port 8000` |
| Frontend blank / not running | `cd frontend && npm run dev` (it proxies `/api` to :8000) |
| Page works but history shows your rehearsal questions | Hard-refresh the browser — history is per-session state |
| Row counts don't match the answer key | You or someone reseeded/queried since — run the reset (`docker compose down -v && up -d mysql`) before the demo and don't run writes |
| An example question returns "could not map the question to a query" | That's the fallback being honest. Say so, and pivot to a question it handles. Do not reload and retry the same thing 3×. |
| Interviewer asks a question the fallback can't do (e.g. "revenue by month") | "This specific phrasing exceeds the fallback's curated ruleset; with Ollama installed it generates this from the schema. Let me show you what it *does* handle —" then run a working one. Honest + smooth. |

---

## 7. Cold-start script (if they want to see it boot from zero)

```bash
docker compose up -d mysql                          # ~30s first time
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &                        # then open http://localhost:5173
```

Narrate: *"One command brings up the database with the schema and seed applied by the
init scripts — including the read-only role. The backend introspects `INFORMATION_SCHEMA`
on first query. The frontend proxies to it. No env keys, no cloud, nothing to sign up for."*

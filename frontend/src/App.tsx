import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchHealth,
  fetchSchema,
  runQuery,
  verifyQuery,
  type QueryResponse,
} from "./api";

type Tone = "ok" | "warn" | "err" | "muted";
type Cell = string | number | null;

type Line =
  | { kind: "banner"; text: string }
  | { kind: "prompt"; text: string }
  | { kind: "text"; text: string }
  | { kind: "sql"; text: string }
  | { kind: "table"; columns: string[]; rows: Cell[][] }
  | { kind: "note"; text: string; tone: Tone }
  | { kind: "suggestions" };

const EXAMPLES = [
  "How many orders were placed last month?",
  "Who are the top 5 customers by total spend?",
  "What's the average order value by region?",
  "List all products with less than 10 units in stock.",
  "Which employees have been with the company longer than 5 years?",
  "Show me the 3 best-selling products by quantity sold.",
];

const BANNER = `┌────────────────────────────────────────────────────────────────────┐
│   N A T S Q L   —  natural language interface for MySQL           │
│   question → SQL → validated → executed → results + SQL           │
└────────────────────────────────────────────────────────────────────┘`;

const MAX_CELL = 42;

/** Render rows as a mysql-CLI-style text table. */
function renderAsciiTable(columns: string[], rows: Cell[][]): string {
  const cells = (r: Cell[]) =>
    r.map((c) => {
      const s = c === null ? "NULL" : String(c);
      return s.length > MAX_CELL ? s.slice(0, MAX_CELL - 1) + "…" : s;
    });
  const widths = columns.map((c, i) =>
    Math.max(c.length, ...rows.map((r) => cells(r)[i].length))
  );
  const border = "+" + widths.map((w) => "-".repeat(w + 2)).join("+") + "+";
  const line = (vals: string[]) =>
    "| " + vals.map((v, i) => v.padEnd(widths[i])).join(" | ") + " |";
  const out = [border, line(columns), border];
  rows.forEach((r) => out.push(line(cells(r))));
  out.push(border, `${rows.length} row${rows.length === 1 ? "" : "s"} in set`);
  return out.join("\n");
}

export default function App() {
  const [lines, setLines] = useState<Line[]>([
    { kind: "banner", text: BANNER },
    {
      kind: "note",
      text: 'type a question and press Enter.  commands:  /help  /schema  /verify  /clear',
      tone: "muted",
    },
    { kind: "suggestions" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [engine, setEngine] = useState("…");
  const [asked, setAsked] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);
  const lastResult = useRef<QueryResponse | null>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => setEngine(h.llm_engine))
      .catch(() => setEngine("backend offline"));
  }, []);

  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines, loading]);

  const push = useCallback((line: Line) => setLines((prev) => [...prev, line]), []);
  const pushAll = useCallback(
    (more: Line[]) => setLines((prev) => [...prev, ...more]),
    []
  );

  const printSchema = useCallback(async () => {
    try {
      const s = await fetchSchema();
      const more: Line[] = [
        { kind: "note", text: `database: ${s.database} — ${s.tables.length} tables`, tone: "muted" },
      ];
      for (const t of s.tables) {
        more.push({ kind: "text", text: `TABLE ${t.name}  (${t.columns.length} columns)` });
        for (const c of t.columns) {
          more.push({
            kind: "text",
            text: `  ${c.name.padEnd(26)} ${c.data_type.padEnd(14)} ${c.is_primary_key ? "PK " : "   "}${c.nullable ? "NULL" : "NOT NULL"}`,
          });
        }
        for (const fk of t.foreign_keys) {
          more.push({ kind: "text", text: `  FK: ${fk.column} -> ${fk.ref_table}.${fk.ref_column}` });
        }
      }
      pushAll(more);
    } catch (e) {
      push({ kind: "note", text: `error: ${e instanceof Error ? e.message : String(e)}`, tone: "err" });
    }
  }, [push, pushAll]);

  const runVerify = useCallback(async () => {
    const cur = lastResult.current;
    if (!cur?.sql) {
      push({ kind: "note", text: "no query to verify yet — ask a question first", tone: "warn" });
      return;
    }
    push({ kind: "note", text: "re-running the SQL directly against MySQL (read-only)…", tone: "muted" });
    try {
      const v = await verifyQuery(cur.sql, cur.question);
      const matches =
        JSON.stringify(v.columns) === JSON.stringify(cur.columns) &&
        JSON.stringify(v.rows) === JSON.stringify(cur.rows);
      pushAll([
        { kind: "sql", text: v.sql },
        { kind: "table", columns: v.columns, rows: v.rows },
        {
          kind: "note",
          text: matches
            ? `✓ verified — direct MySQL output is identical to the app result (${v.row_count} row${v.row_count === 1 ? "" : "s"} · ${v.elapsed_ms} ms)`
            : "✗ output differs from the app result!",
          tone: matches ? "ok" : "err",
        },
      ]);
    } catch (e) {
      push({ kind: "note", text: `verification failed: ${e instanceof Error ? e.message : String(e)}`, tone: "err" });
    }
  }, [push, pushAll]);

  const run = useCallback(
    async (raw: string) => {
      const cmd = raw.trim();
      if (!cmd || loading) return;
      push({ kind: "prompt", text: cmd });
      setInput("");
      setHistIdx(-1);

      if (cmd.startsWith("/")) {
        const name = cmd.split(/\s+/)[0];
        switch (name) {
          case "/help":
            pushAll([
              { kind: "text", text: "commands:" },
              { kind: "text", text: "  /help      show this help" },
              { kind: "text", text: "  /schema    introspect the database schema" },
              { kind: "text", text: "  /verify    re-run the last SQL directly against MySQL" },
              { kind: "text", text: "  /clear     clear the terminal" },
              { kind: "text", text: "  /exit      (just kidding — it never exits)" },
              { kind: "text", text: "anything else is treated as a question for the database." },
            ]);
            return;
          case "/clear":
            setLines([{ kind: "banner", text: BANNER }, { kind: "suggestions" }]);
            return;
          case "/schema":
            await printSchema();
            return;
          case "/verify":
            await runVerify();
            return;
          case "/exit":
            push({ kind: "note", text: "demo mode — this terminal never exits 😉 try a question instead", tone: "muted" });
            return;
          default:
            push({ kind: "note", text: `unknown command: ${name} — try /help`, tone: "warn" });
            return;
        }
      }

      setLoading(true);
      try {
        const res = await runQuery(cmd);
        lastResult.current = res;
        setAsked((prev) => [cmd, ...prev.filter((q) => q !== cmd)].slice(0, 20));
        setEngine(res.engine);
        const more: Line[] = [];
        if (res.error) {
          more.push({
            kind: "note",
            text: `${res.error_type === "validation" ? "could not build a safe query" : "query failed"}: ${res.error}`,
            tone: "err",
          });
          if (res.sql) more.push({ kind: "sql", text: res.sql });
        } else {
          more.push({ kind: "sql", text: res.sql ?? "" });
          more.push({ kind: "table", columns: res.columns, rows: res.rows });
          more.push({
            kind: "note",
            text:
              `${res.row_count} row${res.row_count === 1 ? "" : "s"} in set (${res.elapsed_ms} ms)  ` +
              `[engine: ${res.engine}]` +
              (res.truncated ? "  [truncated at row limit]" : "") +
              (res.retries > 0 ? `  [retries: ${res.retries}]` : ""),
            tone: "ok",
          });
          more.push({
            kind: "note",
            text: 'hint: run "/verify" to re-execute this SQL directly against MySQL',
            tone: "muted",
          });
        }
        pushAll(more);
      } catch (e) {
        push({ kind: "note", text: `error: ${e instanceof Error ? e.message : String(e)}`, tone: "err" });
      } finally {
        setLoading(false);
      }
    },
    [loading, push, pushAll, printSchema, runVerify]
  );

  const renderLine = (l: Line, i: number) => {
    switch (l.kind) {
      case "banner":
        return (
          <pre className="line banner" key={i}>
            {l.text}
          </pre>
        );
      case "prompt":
        return (
          <div className="line prompt-line" key={i}>
            <span className="ps1">user@natsql:~$</span> <span className="cmd">{l.text}</span>
          </div>
        );
      case "text":
        return (
          <div className="line" key={i}>
            {l.text}
          </div>
        );
      case "sql":
        return (
          <pre className="line sql" key={i}>
            <span className="sql-tag">sql&gt;</span> {l.text}
          </pre>
        );
      case "table":
        return (
          <pre className="line table" key={i}>
            {renderAsciiTable(l.columns, l.rows)}
          </pre>
        );
      case "note":
        return (
          <div className={`line note-${l.tone}`} key={i}>
            {l.text}
          </div>
        );
      case "suggestions":
        return (
          <div className="line suggestions" key={i}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="sugg"
                disabled={loading}
                onClick={() => {
                  setInput(ex);
                  void run(ex);
                }}
              >
                {ex}
              </button>
            ))}
          </div>
        );
    }
  };

  return (
    <div className="wrap">
      <div className="term">
        <div className="term-bar">
          <span className="dots">
            <i className="dot red" />
            <i className="dot yellow" />
            <i className="dot green" />
          </span>
          <span className="term-title">user@natsql: ~/demo — natsql</span>
          <span className="term-badges">{engine} · demo@127.0.0.1:3307</span>
        </div>

        <div className="term-body" ref={transcriptRef}>
          {lines.map(renderLine)}
          {loading && <div className="line note-muted">⠋ translating question to SQL…</div>}
        </div>

        <div className="term-input">
          <span className="ps1">user@natsql:~$</span>
          <input
            value={input}
            autoFocus
            spellCheck={false}
            autoComplete="off"
            placeholder="ask the database…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void run(input);
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (asked.length === 0) return;
                const idx = histIdx === -1 ? asked.length - 1 : Math.max(0, histIdx - 1);
                setHistIdx(idx);
                setInput(asked[idx]);
              } else if (e.key === "ArrowDown") {
                e.preventDefault();
                if (histIdx === -1 || asked.length === 0) return;
                const idx = histIdx + 1;
                if (idx >= asked.length) {
                  setHistIdx(-1);
                  setInput("");
                } else {
                  setHistIdx(idx);
                  setInput(asked[idx]);
                }
              }
            }}
          />
        </div>
      </div>

      <div className="status">
        Enter = ask&nbsp;&nbsp;·&nbsp;&nbsp;↑/↓ = history&nbsp;&nbsp;·&nbsp;&nbsp;/help /schema /verify /clear
      </div>
    </div>
  );
}

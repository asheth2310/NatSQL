export interface QueryResponse {
  question: string;
  engine: string;
  sql: string | null;
  columns: string[];
  rows: (string | number | null)[][];
  row_count: number;
  truncated: boolean;
  retries: number;
  notes: string[];
  error: string | null;
  error_type: "validation" | "execution" | "llm" | null;
  elapsed_ms: number;
}

export async function runQuery(question: string): Promise<QueryResponse> {
  const res = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return res.json();
}

export interface VerifyResponse {
  sql: string;
  columns: string[];
  rows: (string | number | null)[][];
  row_count: number;
  elapsed_ms: number;
}

export async function fetchHealth(): Promise<{ llm_engine: string; database: string }> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error("backend unreachable");
  return res.json();
}

export async function verifyQuery(sql: string, question?: string): Promise<VerifyResponse> {
  const res = await fetch("/api/query/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql, question }),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return res.json();
}

export interface ColumnMeta {
  name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
}

export interface ForeignKeyMeta {
  column: string;
  ref_table: string;
  ref_column: string;
}

export interface TableMeta {
  name: string;
  columns: ColumnMeta[];
  foreign_keys: ForeignKeyMeta[];
}

export interface SchemaResponse {
  database: string;
  tables: TableMeta[];
}

export async function fetchSchema(): Promise<SchemaResponse> {
  const res = await fetch("/api/schema");
  if (!res.ok) throw new Error(`schema request failed: ${res.status}`);
  return res.json();
}

export type Citation = {
  label: string;
  url: string;
  source_type: string;
  retrieved_at?: string | null;
};

export type ToolTrace = {
  tool: string;
  input?: Record<string, unknown>;
  status: "success" | "partial" | "fallback" | "error" | string;
  duration_ms: number;
  fallback_used: boolean;
  message?: string | null;
};

export type ReportResponse = {
  markdown: string;
  citations: Citation[];
  tool_trace: ToolTrace[];
  fallback_used: boolean;
  warnings: string[];
};

type FetchInit = {
  method: string;
  headers: Record<string, string>;
  body: string;
};

type FetchResponse = {
  ok: boolean;
  status: number;
  text: () => Promise<string>;
  json: () => Promise<unknown>;
};

export type FetchLike = (url: string, init: FetchInit) => Promise<FetchResponse>;

type CreateReportOptions = {
  baseUrl?: string;
  days?: number;
  pdfUrl?: string;
  fetchImpl?: FetchLike;
};

function isReportResponse(value: unknown): value is ReportResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.markdown === "string" &&
    Array.isArray(record.citations) &&
    Array.isArray(record.tool_trace) &&
    typeof record.fallback_used === "boolean" &&
    Array.isArray(record.warnings)
  );
}

export async function createReport(
  query: string,
  options: CreateReportOptions = {},
): Promise<ReportResponse> {
  const baseUrl =
    options.baseUrl ?? import.meta.env.VITE_AGENT_API_URL ?? "http://localhost:8000";
  const days = options.days ?? 7;
  const fetchImpl = options.fetchImpl ?? (globalThis.fetch as unknown as FetchLike);
  const body: Record<string, unknown> = { query, days };
  if (options.pdfUrl?.trim()) {
    body.pdf_url = options.pdfUrl.trim();
  }

  const response = await fetchImpl(`${baseUrl.replace(/\/$/, "")}/reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Agent API failed: ${response.status}${body ? ` ${body}` : ""}`);
  }

  const payload = await response.json();
  if (!isReportResponse(payload)) {
    throw new Error("Agent API returned an unexpected report payload.");
  }

  return payload;
}

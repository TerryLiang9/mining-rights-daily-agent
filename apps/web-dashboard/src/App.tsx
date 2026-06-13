import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Database,
  ExternalLink,
  FileText,
  Loader2,
  Send,
} from "lucide-react";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import { createReport, type ReportResponse, type ToolTrace } from "./api";

const sampleQueries = [
  "给我生成一份关于 Pilbara 锂矿的今日简报",
  "生成一份关于 copper mining 的矿权日报",
];

function statusClass(status: string): string {
  if (status === "success") {
    return "status success";
  }
  if (status === "fallback" || status === "partial") {
    return "status warning";
  }
  return "status error";
}

function TraceStatusIcon({ trace }: { trace: ToolTrace }) {
  if (trace.status === "success" && !trace.fallback_used) {
    return <CheckCircle2 aria-hidden="true" />;
  }
  if (trace.status === "fallback" || trace.fallback_used) {
    return <AlertTriangle aria-hidden="true" />;
  }
  return <CircleDashed aria-hidden="true" />;
}

export default function App() {
  const [query, setQuery] = useState(sampleQueries[0]);
  const [days, setDays] = useState(7);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const traceSummary = useMemo(() => {
    const traces = report?.tool_trace ?? [];
    return {
      total: traces.length,
      fallback: traces.filter((trace) => trace.fallback_used).length,
      duration: traces.reduce((sum, trace) => sum + trace.duration_ms, 0),
    };
  }, [report]);

  async function onGenerate() {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("请输入简报主题。");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      setReport(await createReport(trimmedQuery, { days }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="control-panel">
        <div className="brand-block">
          <div className="brand-mark">
            <Database aria-hidden="true" />
          </div>
          <div>
            <p className="eyebrow">MCP Mining Intelligence</p>
            <h1>Mining Rights Daily Agent</h1>
          </div>
        </div>

        <div className="field">
          <label htmlFor="query">简报主题</label>
          <textarea
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            spellCheck={false}
          />
        </div>

        <div className="field compact">
          <label htmlFor="days">观察窗口</label>
          <input
            id="days"
            type="number"
            min={1}
            max={90}
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          />
        </div>

        <div className="query-presets" aria-label="示例主题">
          {sampleQueries.map((sample) => (
            <button
              className="preset-button"
              type="button"
              key={sample}
              onClick={() => setQuery(sample)}
            >
              {sample}
            </button>
          ))}
        </div>

        <button className="primary-action" type="button" onClick={onGenerate} disabled={loading}>
          {loading ? <Loader2 className="spin" aria-hidden="true" /> : <Send aria-hidden="true" />}
          <span>{loading ? "生成中" : "生成日报"}</span>
        </button>

        {error && (
          <div className="notice error" role="alert">
            <AlertTriangle aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {report && (
          <div className={report.fallback_used ? "notice warning" : "notice success"}>
            {report.fallback_used ? (
              <AlertTriangle aria-hidden="true" />
            ) : (
              <CheckCircle2 aria-hidden="true" />
            )}
            <span>{report.fallback_used ? "已使用 fallback 数据" : "全部工具返回真实状态"}</span>
          </div>
        )}
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Evidence-first report</p>
            <h2>矿权日报工作台</h2>
          </div>
          <div className="metrics" aria-label="运行摘要">
            <div>
              <span>{traceSummary.total}</span>
              <small>Tools</small>
            </div>
            <div>
              <span>{traceSummary.fallback}</span>
              <small>Fallback</small>
            </div>
            <div>
              <span>{traceSummary.duration}ms</span>
              <small>Trace time</small>
            </div>
          </div>
        </header>

        <div className="dashboard-grid">
          <section className="report-panel" aria-label="Markdown report">
            <div className="panel-title">
              <FileText aria-hidden="true" />
              <h3>Markdown Report</h3>
            </div>
            <div className={report ? "report-body" : "empty-state"}>
              {report ? (
                <ReactMarkdown>{report.markdown}</ReactMarkdown>
              ) : (
                <span>等待生成矿权日报。</span>
              )}
            </div>
          </section>

          <section className="side-stack" aria-label="Evidence panels">
            <article className="panel">
              <div className="panel-title">
                <Activity aria-hidden="true" />
                <h3>Tool Trace</h3>
              </div>
              <div className="trace-list">
                {(report?.tool_trace ?? []).map((trace, index) => (
                  <div className="trace-row" key={`${trace.tool}-${index}`}>
                    <div className="trace-icon">
                      <TraceStatusIcon trace={trace} />
                    </div>
                    <div className="trace-main">
                      <strong>{trace.tool}</strong>
                      <span>{trace.duration_ms}ms</span>
                    </div>
                    <span className={statusClass(trace.status)}>{trace.status}</span>
                  </div>
                ))}
                {!report && <div className="empty-inline">暂无工具调用。</div>}
              </div>
            </article>

            <article className="panel">
              <div className="panel-title">
                <Database aria-hidden="true" />
                <h3>Sources</h3>
              </div>
              <div className="source-list">
                {(report?.citations ?? []).map((citation, index) => (
                  <a
                    className="source-row"
                    href={citation.url.startsWith("http") ? citation.url : undefined}
                    target="_blank"
                    rel="noreferrer"
                    key={`${citation.url}-${index}`}
                  >
                    <span>
                      <strong>{citation.label}</strong>
                      <small>{citation.source_type}</small>
                    </span>
                    {citation.url.startsWith("http") ? <ExternalLink aria-hidden="true" /> : null}
                  </a>
                ))}
                {!report && <div className="empty-inline">暂无引用来源。</div>}
              </div>
            </article>

            <article className="panel">
              <div className="panel-title">
                <AlertTriangle aria-hidden="true" />
                <h3>Data Quality</h3>
              </div>
              {report ? (
                <div className="quality-list">
                  <div className="quality-row">
                    <span>Fallback</span>
                    <strong>{String(report.fallback_used)}</strong>
                  </div>
                  {report.warnings.map((warning, index) => (
                    <p key={`${warning}-${index}`}>{warning}</p>
                  ))}
                  {report.warnings.length === 0 && <p>未返回额外数据质量警告。</p>}
                </div>
              ) : (
                <div className="empty-inline">等待 Agent API 返回数据质量信息。</div>
              )}
            </article>
          </section>
        </div>
      </section>
    </main>
  );
}

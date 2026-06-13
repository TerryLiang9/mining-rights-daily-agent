import type { ReportResponse } from "./agent-api.js";

export type ParsedCommand =
  | { command: "report"; query: string; pdfUrl?: string }
  | { command: "help"; query: "" };

export function parseCommand(args: string[]): ParsedCommand {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  const [command, ...rest] = normalizedArgs;
  if (command !== "report") {
    return { command: "help", query: "" };
  }

  const queryParts: string[] = [];
  let pdfUrl: string | undefined;
  for (let index = 0; index < rest.length; index += 1) {
    const value = rest[index];
    if (value === "--pdf") {
      pdfUrl = rest[index + 1];
      index += 1;
      continue;
    }
    if (value.startsWith("--pdf=")) {
      pdfUrl = value.slice("--pdf=".length);
      continue;
    }
    queryParts.push(value);
  }

  return {
    command,
    query: queryParts.join(" ").trim(),
    pdfUrl,
  };
}

export function formatReportOutput(report: ReportResponse): string {
  const lines = [
    report.markdown,
    "",
    `Fallback Used: ${report.fallback_used}`,
  ];

  if (report.warnings.length > 0) {
    lines.push("", "Warnings:", ...report.warnings.map((warning) => `- ${warning}`));
  }

  lines.push(
    "",
    "Tool Trace:",
    ...report.tool_trace.map(
      (trace) =>
        `- ${trace.tool}: ${trace.status}, ${trace.duration_ms}ms, fallback=${trace.fallback_used}`,
    ),
  );

  lines.push(
    "",
    "Sources:",
    ...report.citations.map((citation) => `- ${citation.label}: ${citation.url}`),
  );

  return lines.join("\n");
}

export function usage(): string {
  return 'Usage: pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报" --pdf data/pdfs/report.pdf';
}

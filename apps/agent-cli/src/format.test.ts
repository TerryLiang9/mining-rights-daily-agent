import assert from "node:assert/strict";
import test from "node:test";

import { formatReportOutput, parseCommand } from "./format.js";

test("parseCommand accepts report queries after the report command", () => {
  assert.deepEqual(parseCommand(["report", "Pilbara", "lithium"]), {
    command: "report",
    query: "Pilbara lithium",
    pdfUrl: undefined,
  });
});

test("parseCommand ignores pnpm forwarded separator before the command", () => {
  assert.deepEqual(parseCommand(["--", "report", "Pilbara", "lithium"]), {
    command: "report",
    query: "Pilbara lithium",
    pdfUrl: undefined,
  });
});

test("parseCommand accepts a PDF path after --pdf", () => {
  assert.deepEqual(
    parseCommand([
      "report",
      "Pilbara",
      "lithium",
      "--pdf",
      "data/pdfs/custom-report.pdf",
    ]),
    {
      command: "report",
      query: "Pilbara lithium",
      pdfUrl: "data/pdfs/custom-report.pdf",
    },
  );
});

test("formatReportOutput includes markdown, tool trace, sources, warnings, and fallback state", () => {
  const output = formatReportOutput({
    markdown: "# Pilbara Brief",
    fallback_used: true,
    warnings: ["Using fixture data"],
    tool_trace: [
      {
        tool: "lme-price-mcp.get_trend",
        status: "fallback",
        duration_ms: 12,
        fallback_used: true,
      },
    ],
    citations: [
      {
        label: "price fixture",
        url: "data/fixtures/prices.json",
        source_type: "price",
      },
    ],
  });

  assert.match(output, /# Pilbara Brief/);
  assert.match(output, /Fallback Used: true/);
  assert.match(output, /lme-price-mcp\.get_trend: fallback, 12ms, fallback=true/);
  assert.match(output, /price fixture: data\/fixtures\/prices\.json/);
  assert.match(output, /Using fixture data/);
});

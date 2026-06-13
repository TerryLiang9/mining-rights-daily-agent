import assert from "node:assert/strict";
import test from "node:test";

import { createReport } from "./agent-api.js";

test("createReport posts the query to the Agent API reports endpoint", async () => {
  const calls: Array<{ url: string; init: { body?: string; method?: string } }> = [];

  const result = await createReport("Pilbara lithium brief", {
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return {
        ok: true,
        status: 200,
        text: async () => "",
        json: async () => ({
          markdown: "# Report",
          citations: [],
          tool_trace: [],
          fallback_used: false,
          warnings: [],
        }),
      };
    },
  });

  assert.equal(result.markdown, "# Report");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/reports");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body ?? "{}"), {
    query: "Pilbara lithium brief",
    days: 7,
  });
});

test("createReport posts pdf_url when provided", async () => {
  const calls: Array<{ url: string; init: { body?: string; method?: string } }> = [];

  await createReport("Pilbara lithium brief", {
    pdfUrl: "data/pdfs/custom-report.pdf",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return {
        ok: true,
        status: 200,
        text: async () => "",
        json: async () => ({
          markdown: "# Report",
          citations: [],
          tool_trace: [],
          fallback_used: false,
          warnings: [],
        }),
      };
    },
  });

  assert.deepEqual(JSON.parse(calls[0].init.body ?? "{}"), {
    query: "Pilbara lithium brief",
    days: 7,
    pdf_url: "data/pdfs/custom-report.pdf",
  });
});

import assert from "node:assert/strict";
import test from "node:test";

import { createReport } from "./api.js";

test("createReport calls only the Agent API reports endpoint", async () => {
  const calls: Array<{ url: string; init: { body?: string; method?: string } }> = [];

  const result = await createReport("给我生成一份关于 Pilbara 锂矿的今日简报", {
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
          fallback_used: true,
          warnings: ["Using fixture data"],
        }),
      };
    },
    baseUrl: "http://localhost:8000",
  });

  assert.equal(result.fallback_used, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/reports");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body ?? "{}"), {
    query: "给我生成一份关于 Pilbara 锂矿的今日简报",
    days: 7,
  });
});

test("createReport includes pdf_url when a PDF path is provided", async () => {
  const calls: Array<{ url: string; init: { body?: string; method?: string } }> = [];

  await createReport("给我生成一份关于 Pilbara 锂矿的今日简报", {
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
    baseUrl: "http://localhost:8000",
  });

  assert.deepEqual(JSON.parse(calls[0].init.body ?? "{}"), {
    query: "给我生成一份关于 Pilbara 锂矿的今日简报",
    days: 7,
    pdf_url: "data/pdfs/custom-report.pdf",
  });
});

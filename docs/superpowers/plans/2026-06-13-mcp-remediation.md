# MCP Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the mining rights daily Agent so the delivered project uses real MCP stdio server calls, has working Claude Desktop / Cursor MCP config, supports minimal PDF extraction, and passes the original interview验收清单.

**Architecture:** Keep the existing deterministic Agent workflow and replace the tool adapter layer with an MCP stdio adapter. MCP servers continue to reuse the existing Python tool functions; the Agent API calls those servers through the official MCP client. PDF extraction gains a minimal `pypdf` text path before abstaining.

**Tech Stack:** Python 3.11, official MCP Python SDK, FastAPI, Pydantic v2, httpx, pypdf, pytest, TypeScript, pnpm, Docker Compose.

---

## Task 1: MCP Config And Server Launch Tests

**Files:**
- Modify: `mcp-config.json`
- Modify: `mcp_servers/mining_news/tools.py`
- Modify: `mcp_servers/mineral_pdf/tools.py`
- Modify: `mcp_servers/lme_price/tools.py`
- Create: `mcp_servers/tests/test_mcp_stdio.py`

- [ ] **Step 1: Write failing MCP stdio test**

Create `mcp_servers/tests/test_mcp_stdio.py` with tests that load the three server commands from `mcp-config.json`, start each server with `stdio_client`, assert `list_tools()`, and call one required tool per server.

- [ ] **Step 2: Verify red**

Run:

```bash
python -m pytest mcp_servers/tests/test_mcp_stdio.py -v
```

Expected before fix: failure from `ModuleNotFoundError: No module named 'mcp_servers'`.

- [ ] **Step 3: Fix config and fixture paths**

Update `mcp-config.json` commands to use `python -m mcp_servers.<server>.server`. Update fixture paths to derive from repository root instead of current working directory.

- [ ] **Step 4: Verify green**

Run:

```bash
python -m pytest mcp_servers/tests/test_mcp_stdio.py -v
```

Expected after fix: all MCP stdio tests pass.

## Task 2: Agent Uses MCP Adapter

**Files:**
- Create: `apps/agent-api/app/adapters/mcp_stdio.py`
- Modify: `apps/agent-api/app/orchestrator.py`
- Modify: `apps/agent-api/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing orchestrator adapter test**

Add a recording adapter test for `generate_report()` that asserts the Agent calls:

```text
mining-news.search
mining-news.fetch_article
mineral-pdf.extract_resources
lme-price.get_trend
```

- [ ] **Step 2: Verify red**

Run:

```bash
python -m pytest apps/agent-api/tests/test_orchestrator.py -v
```

Expected before fix: `generate_report()` does not accept an injected adapter or does not call it.

- [ ] **Step 3: Implement MCP adapter**

Add `MCPStdioToolAdapter` using `mcp.client.stdio.stdio_client` and `ClientSession`. Add a synchronous `call_tool()` wrapper around the async MCP call so the current FastAPI path can stay sync.

- [ ] **Step 4: Wire orchestrator**

Update `generate_report()` to accept optional `tool_adapter`. If not supplied, default to `MCPStdioToolAdapter`. Convert returned dictionaries into existing Pydantic models.

- [ ] **Step 5: Verify green**

Run:

```bash
python -m pytest apps/agent-api/tests/test_orchestrator.py -v
```

Expected after fix: existing report tests and adapter call-order test pass.

## Task 3: Minimal Real PDF Extraction

**Files:**
- Modify: `mcp_servers/mineral_pdf/tools.py`
- Modify: `mcp_servers/mineral_pdf/parser.py`
- Modify: `mcp_servers/mineral_pdf/tests/test_tools.py`

- [ ] **Step 1: Write failing local PDF test**

Add a test that creates a temporary PDF containing:

```text
Indicated 120.5 Mt 1.25% Li2O 1.5 Mt LCE
Inferred 80.2 Mt 1.05% Li2O 0.9 Mt LCE
```

Then call `extract_resources(str(pdf_path), project_name="Pilbara")` and assert two resource rows.

- [ ] **Step 2: Verify red**

Run:

```bash
python -m pytest mcp_servers/mineral_pdf/tests/test_tools.py -v
```

Expected before fix: real local PDF path returns `abstain=True` and no resources.

- [ ] **Step 3: Implement PDF read path**

Implement local path reading, HTTP PDF download, `pypdf.PdfReader` text extraction, and parser invocation. Keep fixture fallback unchanged.

- [ ] **Step 4: Verify green**

Run:

```bash
python -m pytest mcp_servers/mineral_pdf/tests/test_tools.py -v
```

Expected after fix: fixture test and real PDF extraction test pass.

## Task 4: Docs And Default Test Coverage

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `RUN.md`

- [ ] **Step 1: Expand pytest testpaths**

Add `packages/shared` to `[tool.pytest.ini_options].testpaths`.

- [ ] **Step 2: Update docs**

Document:

```bash
docker compose up --build
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
```

Also document that MCP config uses module execution and the Agent API defaults to MCP stdio tool calls.

- [ ] **Step 3: Verify docs-aligned commands**

Run:

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
```

Expected: all available local commands pass, except Docker build is only run if Docker engine is available.

## Task 5: End-To-End CLI Verification

**Files:**
- No code changes expected unless verification exposes a bug.

- [ ] **Step 1: Start Agent API on a temporary port**

Run:

```bash
python -m uvicorn app.main:app --app-dir apps/agent-api --host 127.0.0.1 --port 8010
```

- [ ] **Step 2: Run CLI against API**

Run:

```bash
$env:AGENT_API_URL="http://127.0.0.1:8010"
pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报"
```

Expected: Markdown report includes news, resource data, price trend, risk notes, data quality notes, tool trace, and sources.


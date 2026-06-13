# MCP 验收修复设计文档

日期：2026-06-13

## 1. 背景

本项目已经能通过 API 和 CLI 生成“Pilbara 锂矿今日简报”，但验收发现它仍停留在 Demo 级：

- `mcp-config.json` 使用 `python mcp_servers/.../server.py` 启动，真实 MCP stdio 连接会因为 `ModuleNotFoundError: No module named 'mcp_servers'` 失败。
- Agent 编排层的 trace 写着 `*-mcp.*`，但实际通过 `app.adapters.local_tools` 直接 import 工具函数，不是真正 MCP client。
- `mineral-pdf-mcp.extract_resources()` 对真实 `pdf_url` 不下载、不读 PDF，也不调用 parser；非 fixture URL 直接 abstain。
- `RUN.md` 只写了 `docker compose config`，没有一条完整的 `docker compose up --build` 启动路径。
- 默认 `python -m pytest` 没覆盖 `packages/shared/tests`。

本轮修复目标是把项目从“可演示”提升到“按题目严格可验收”。

## 2. 修复目标

修复后必须满足：

1. 三个 MCP server 能通过 `mcp-config.json` 被 Claude Desktop / Cursor 按 stdio 启动。
2. 三个 MCP server 能被官方 MCP Python client `list_tools` 和 `call_tool` 验证。
3. Agent 默认通过 MCP stdio client 调用三个 server，而不是直接 import 本地工具函数。
4. `mineral-pdf-mcp` 对真实 HTTP PDF URL 和本地 PDF 路径有最小解析能力。
5. fixture fallback 继续保留，但必须显式披露。
6. `RUN.md` 提供一条 `docker compose up --build` 跑起路径。
7. 默认测试命令覆盖共享包、MCP server、Agent API 和 smoke eval。

## 3. 非目标

本轮不做以下事情：

- 不引入 LangGraph 或复杂 ReAct 规划。
- 不接入需要账号或付费的真实 LME / SHFE / 新闻 API。
- 不追求兼容所有 NI 43-101 PDF 表格格式。
- 不重做前端 UI。
- 不做数据库、登录、权限或生产部署。

## 4. 推荐架构

继续保留当前 deterministic orchestration，但把工具调用层从本地函数替换成 MCP stdio adapter。

```text
CLI / Web
  |
  v
FastAPI Agent API
  |
  v
orchestrator.generate_report()
  |
  |-- MCPToolAdapter.call_tool("mining-news", "search", ...)
  |-- MCPToolAdapter.call_tool("mining-news", "fetch_article", ...)
  |-- MCPToolAdapter.call_tool("mineral-pdf", "extract_resources", ...)
  |-- MCPToolAdapter.call_tool("lme-price", "get_trend", ...)
  |
  v
EvidencePack
  |
  v
Ollama / Mock LLM
  |
  v
Markdown 简报 + citations + tool_trace + warnings
```

设计理由：

- deterministic workflow 已经能稳定生成日报，不需要改成更重的 agent 框架。
- MCP stdio adapter 是本轮核心缺口，单独抽层后可测试、可替换。
- 本地工具函数仍可保留，作为 MCP server 内部实现和必要时的测试 fallback。

## 5. 文件改动范围

### 配置与路径

- 修改 `mcp-config.json`
  - 使用 `python -m mcp_servers.<name>.server`。
  - 后续 Claude Desktop / Cursor 从仓库根目录启动即可连接。

- 修改 fixture 路径解析
  - `mcp_servers/mining_news/tools.py`
  - `mcp_servers/mineral_pdf/tools.py`
  - `mcp_servers/lme_price/tools.py`
  - 统一使用项目根目录推导，避免依赖当前工作目录。

### MCP client adapter

- 新增 `apps/agent-api/app/adapters/mcp_stdio.py`
  - 封装 `mcp.client.stdio.stdio_client` 和 `ClientSession`。
  - 支持 `call_tool(server_name, tool_name, arguments)`。
  - 默认 server 命令与 `mcp-config.json` 保持一致。

- 修改 `apps/agent-api/app/orchestrator.py`
  - 默认使用 MCP adapter 调用工具。
  - 保留 `llm_provider` 参数。
  - 测试可注入 adapter，避免所有单元测试都必须反复拉起子进程。

### PDF 解析

- 修改 `mcp_servers/mineral_pdf/tools.py`
  - `fixture://` 继续走 fixture。
  - `http://` / `https://` 使用 `httpx` 下载 PDF。
  - 本地路径使用 `Path.read_bytes()`。
  - 使用 `pypdf.PdfReader` 抽文本。
  - 调用 `parser.parse_resource_lines(text)` 提取 Indicated/Inferred。
  - 抽不到资源量时返回 `abstain=True` 和 warnings。

- 修改或扩展 `mcp_servers/mineral_pdf/parser.py`
  - 保持当前正则解析，必要时补页码和更稳健的大小写处理。

### 测试

- 新增 `mcp_servers/tests/test_mcp_stdio.py`
  - 启动三个 MCP server。
  - 验证工具列表和一次真实 `call_tool`。

- 新增或扩展 `apps/agent-api/tests/test_orchestrator.py`
  - 验证 `generate_report()` 通过 adapter 调用预期工具。
  - 验证输出仍包含 `Executive Summary`、`风险提示`、`数据质量说明`、`Sources`。

- 扩展 `mcp_servers/mineral_pdf/tests/test_tools.py`
  - 用临时 PDF 或本地 fixture PDF 验证真实 PDF 路径能解析 Indicated/Inferred。

- 修改 `pyproject.toml`
  - `testpaths` 增加 `packages/shared`。

### 文档

- 修改 `RUN.md`
  - 增加 `docker compose up --build`。
  - 增加 MCP stdio 直连验证命令。
  - 明确没有 Ollama 时会 fallback 到 mock provider。

- 修改 `README.md`
  - 更新 MCP 配置说明。
  - 标明 Agent 默认走 MCP stdio adapter。

## 6. 测试策略

先补红灯测试，再实现。

### 红灯测试 1：MCP config 可启动

用官方 MCP client 读取 `mcp-config.json` 的 server 命令，依次执行：

- `list_tools`
- `call_tool`

当前预期失败原因：`python mcp_servers/.../server.py` 方式无法 import `mcp_servers`。

### 红灯测试 2：Agent 使用 MCP adapter

给 `generate_report()` 注入 recording adapter，断言调用顺序包含：

- `mining-news.search`
- `mining-news.fetch_article`
- `mineral-pdf.extract_resources`
- `lme-price.get_trend`

当前预期失败原因：`generate_report()` 不接受 adapter，且直接调用本地函数。

### 红灯测试 3：真实 PDF 路径解析

创建一个最小 PDF fixture，文本包含：

```text
Indicated 120.5 Mt 1.25% Li2O 1.5 Mt LCE
Inferred 80.2 Mt 1.05% Li2O 0.9 Mt LCE
```

调用 `extract_resources(local_pdf_path, project_name="Pilbara")`，断言返回两个资源项。

当前预期失败原因：非 fixture URL 直接 abstain。

## 7. 验收命令

修复完成后必须运行：

```bash
python -m pytest
python -m pytest packages/shared
pnpm --recursive test
pnpm --recursive build
docker compose config
```

端到端验证：

```bash
python -m uvicorn app.main:app --app-dir apps/agent-api --host 127.0.0.1 --port 8010
```

另一个终端：

```bash
$env:AGENT_API_URL="http://127.0.0.1:8010"
pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报"
```

MCP stdio 验证：

```bash
python -m mcp_servers.mining_news.server
python -m mcp_servers.mineral_pdf.server
python -m mcp_servers.lme_price.server
```

实际自动化测试中通过 MCP client 启动，不需要人工交互。

## 8. 风险与处理

- MCP stdio 每次工具调用都拉起 server 子进程会较慢，但面试题更看重协议闭环和可验收性，本轮优先正确性。
- 如果后续要提升性能，可把 adapter 改成长生命周期 session pool。
- PDF 抽取只保证文本型 PDF 的最小路径，扫描件、复杂表格和多列版式仍应返回 abstain。
- Docker 构建依赖本机 Docker Desktop，本轮只能在 Docker engine 可用时验证 build；engine 不可用时至少验证 `docker compose config`。

## 9. 实施顺序

1. 补 MCP stdio 配置测试并确认失败。
2. 修 `mcp-config.json` 和 fixture 路径。
3. 新增 MCP stdio adapter。
4. 修改 orchestrator 默认走 MCP adapter。
5. 补 PDF 真实路径解析。
6. 更新 RUN/README。
7. 跑完整测试、构建、端到端 CLI 验证。


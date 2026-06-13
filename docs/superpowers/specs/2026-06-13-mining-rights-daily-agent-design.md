# Mining Rights Daily Agent 设计文档

日期：2026-06-13

## 1. 背景与目标

本项目用于完成凌云智矿面试题 #2：在 24 小时内用 MCP 协议搭建一个“矿权日报 Agent”。系统输入一个自然语言主题，例如“给我生成一份关于 Pilbara 锂矿的今日简报”，自动聚合矿业新闻、矿权报告资源量信息和金属价格趋势，最终输出带引用来源的 Markdown 日报。

项目目标不是做一个只会拼接文本的演示脚本，而是交付一个边界清晰、可运行、可解释、可扩展的工程化 Agent 项目。核心展示点包括：

- 3 个真实 MCP server：新闻、矿权 PDF、价格行情。
- 1 个 Agent 编排层：负责工具调用、证据整理、LLM 生成和校验。
- 本地 Ollama Gemma 模型：不依赖外部 API Key。
- TypeScript Web Dashboard：方便面试官可视化查看日报、引用和工具轨迹。
- TypeScript CLI：方便命令行验收和自动化演示。
- Docker Compose、README、RUN.md、DATA_NOTES.md 和测试：满足工程化交付要求。

## 2. 范围

### 2.1 本期范围

- 实现 `mining-news-mcp`，提供新闻搜索和文章抓取工具。
- 实现 `mineral-pdf-mcp`，提供 NI 43-101 资源量抽取工具。
- 实现 `lme-price-mcp`，提供价格查询和趋势查询工具。
- 实现 FastAPI `agent-api`，编排 MCP 工具并调用 Ollama Gemma 生成日报。
- 实现 TypeScript Web Dashboard，用于输入主题、展示 Markdown 日报、引用、工具轨迹和数据质量。
- 实现 TypeScript CLI，用于命令行生成日报。
- 提供 `mcp-config.json`，可接入 Claude Desktop 或 Cursor 验证 MCP server。
- 提供 fixture 数据和 fallback 逻辑，保证在外部数据源不可用时仍能演示完整流程。
- 提供单元测试、基础构建验证和运行文档。

### 2.2 非本期范围

- 不承诺覆盖所有 NI 43-101 PDF 格式。
- 不承诺实时接入 LME、SHFE 或上海钢联受限接口。
- 不做复杂多轮 ReAct 或 LangGraph 动态规划。
- 不做用户登录、权限系统、数据库持久化和生产级部署。
- 不做投资建议或矿权估值决策。

## 3. 总体架构

```text
用户
  |
  | Web Dashboard / TypeScript CLI
  v
Agent API (FastAPI)
  |
  | 解析主题、调用工具、整理证据、调用 LLM、校验输出
  v
Agent Orchestrator
  |
  |---- mining-news-mcp
  |       search(query, days, limit)
  |       fetch_article(url)
  |
  |---- mineral-pdf-mcp
  |       extract_resources(pdf_url, project_name)
  |
  |---- lme-price-mcp
          get_price(commodity, date)
          get_trend(commodity, days)
  |
  v
Ollama Gemma / Mock LLM
  |
  v
Markdown 矿权日报
```

架构原则：

- MCP server 按协议独立运行，可被 Claude Desktop 或 Cursor 调用。
- Agent API 为演示和产品化提供 HTTP 包装层。
- MCP 协议入口和 Agent API 复用同一套工具函数，避免重复实现。
- 先获取结构化证据，再让 LLM 写日报，降低幻觉。
- 真实数据失败时显式 fallback，并在输出中标注数据质量。

## 4. 目录结构

```text
mining-rights-daily-agent/
  README.md
  RUN.md
  DATA_NOTES.md
  docker-compose.yml
  mcp-config.json
  .env.example

  apps/
    agent-api/
      app/
        main.py
        schemas.py
        orchestrator.py
        llm/
          base.py
          ollama.py
          mock.py
        adapters/
          mcp_client.py
          local_tools.py
      tests/

    web-dashboard/
      package.json
      src/
        App.tsx
        api.ts
        components/

    agent-cli/
      package.json
      src/
        index.ts

  mcp_servers/
    mining_news/
      server.py
      tools.py
      sources.py
      tests/

    mineral_pdf/
      server.py
      tools.py
      parser.py
      tests/

    lme_price/
      server.py
      tools.py
      prices.py
      tests/

  packages/
    shared/
      pyproject.toml
      mining_agent_shared/
        models.py
        logging.py
        config.py
        citations.py

  data/
    fixtures/
      news.json
      prices.json
      resources.json
    sample_reports/
      README.md

  eval/
    sample_prompts.json
    run_smoke_eval.py

  docs/
    architecture.md
    decisions.md
    superpowers/
      specs/
        2026-06-13-mining-rights-daily-agent-design.md
```

## 5. MCP 工具设计

### 5.1 mining-news-mcp

工具：

- `search(query: string, days: int = 7, limit: int = 5)`
- `fetch_article(url: string)`

`search` 返回新闻列表：

```json
{
  "items": [
    {
      "title": "Pilbara lithium project update",
      "url": "https://example.com/article",
      "source": "mining.com",
      "published_at": "2026-06-12",
      "summary": "Short structured summary",
      "score": 0.86
    }
  ],
  "fallback_used": false,
  "retrieved_at": "2026-06-13T10:00:00Z"
}
```

错误与降级：

- RSS 或页面请求失败时使用 `data/fixtures/news.json`。
- 抓取正文失败时返回已有摘要，并设置 `status=partial`。
- 空结果不抛异常，由 Agent 在数据质量说明中标注。

### 5.2 mineral-pdf-mcp

工具：

- `extract_resources(pdf_url: string, project_name?: string)`

返回资源量结构：

```json
{
  "project_name": "Pilbara lithium sample",
  "report_title": "Sample NI 43-101 Technical Report",
  "resources": [
    {
      "category": "Indicated",
      "ore_tonnage": 120.5,
      "ore_tonnage_unit": "Mt",
      "grade": 1.25,
      "grade_unit": "% Li2O",
      "contained_metal": 1.5,
      "contained_metal_unit": "Mt LCE",
      "page": 42,
      "confidence": 0.78
    }
  ],
  "abstain": false,
  "fallback_used": true,
  "source_url": "data/fixtures/resources.json"
}
```

错误与降级：

- PDF 下载失败时使用 fixture。
- PDF 可读但抽不到表格时返回 `abstain=true`。
- 字段不完整时返回 partial，并在 `warnings` 中说明缺失字段。
- 不允许硬编资源量；证据不足时 abstain。

### 5.3 lme-price-mcp

工具：

- `get_price(commodity: string, date?: string)`
- `get_trend(commodity: string, days: int = 30)`

趋势返回：

```json
{
  "commodity": "lithium",
  "days": 30,
  "points": [
    {
      "date": "2026-05-15",
      "price": 12100
    },
    {
      "date": "2026-06-13",
      "price": 12850
    }
  ],
  "change_pct": 6.2,
  "trend": "up",
  "source": "fixture",
  "fallback_used": true
}
```

错误与降级：

- 不支持的矿种返回 `unsupported_commodity`。
- 外部价格接口失败时使用 fixture。
- 日期无数据时返回最近可用价格。
- 价格点不足时返回 `trend=insufficient_data`。

## 6. Agent 编排

Agent 采用 deterministic workflow，不把工具规划交给小模型自由决定。流程如下：

```text
parse_topic
  -> collect_news
  -> collect_resources
  -> collect_prices
  -> build_evidence_pack
  -> generate_markdown_report
  -> validate_report
```

主题解析先使用规则：

- `Pilbara` -> `region=Pilbara`
- `锂` 或 `lithium` -> `commodity=lithium`
- `铜` 或 `copper` -> `commodity=copper`
- 默认 `days=7`
- 默认输出中文

Evidence Pack 是 LLM 唯一事实来源：

```json
{
  "topic": {
    "region": "Pilbara",
    "commodity": "lithium",
    "days": 7
  },
  "news": [],
  "resources": [],
  "prices": {},
  "citations": [],
  "tool_trace": [],
  "data_quality": {
    "fallback_used": true,
    "warnings": []
  }
}
```

## 7. LLM 设计

默认使用 Ollama Gemma：

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma
```

同时提供 mock provider：

```env
LLM_PROVIDER=mock
```

Prompt 约束：

```text
You are a mining intelligence analyst.

Write a concise Markdown daily brief in Chinese.

Rules:
1. Use only the evidence provided in <evidence>.
2. Do not invent numbers, project names, dates, or URLs.
3. If evidence is missing or fallback data is used, explicitly mention it in "数据质量说明".
4. Every factual claim about news, resources, or prices must be supported by a source listed in citations.
5. Keep the report structured and decision-oriented.

Required sections:
- Executive Summary
- 新闻动态
- 储量/资源量快照
- 价格趋势
- 风险提示
- 数据质量说明
- Sources
```

输出后校验：

- 必须包含 `Sources`。
- 必须包含 `风险提示`。
- 必须包含 `数据质量说明`。
- 如果 `fallback_used=true`，报告必须说明使用了样例数据或 fallback。
- 报告中的 URL 必须来自 `citations`。

校验失败时最多重试一次；仍失败则返回报告并附带 warning。

## 8. Web Dashboard

Web Dashboard 使用 TypeScript 和 React 实现，目标是专业清晰，不做营销页。

界面区域：

- 主题输入区：输入简报主题、days、commodity。
- 运行状态区：显示生成中、成功、失败、fallback。
- 报告区：渲染 Markdown 日报。
- Sources 区：展示引用 URL、报告名、fixture 来源和抓取时间。
- Tool Trace 区：展示每个工具调用、耗时、状态和 fallback。
- Data Quality 区：展示 warnings、abstain 和数据缺口。

Web 只调用 Agent API，不直接访问 MCP server。

## 9. TypeScript CLI

命令示例：

```bash
pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报"
```

CLI 输出：

- 报告文件路径。
- 工具调用摘要。
- 引用源列表。
- fallback 或 warning 信息。

CLI 只调用 Agent API，不重复实现业务逻辑。

## 10. 配置与运行

`.env.example` 包含：

```env
AGENT_API_PORT=8000
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma
USE_FIXTURES_ON_FAILURE=true
```

Docker Compose 启动：

```bash
docker compose up --build
```

服务：

- `agent-api`：FastAPI，端口 `8000`
- `web-dashboard`：Vite React，端口 `5173`

MCP server 提供独立 stdio 入口，并通过 `mcp-config.json` 接入 Claude Desktop 或 Cursor。

## 11. 测试与验收

基础验证命令：

```bash
python -m pytest
pnpm --filter web-dashboard build
pnpm --filter agent-cli build
docker compose config
```

API 验证：

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"给我生成一份关于 Pilbara 锂矿的今日简报\"}"
```

验收标准：

- 3 个 MCP server 均能独立启动。
- `mcp-config.json` 能表达三个 server 的接入方式。
- Agent API 能返回 Markdown 日报。
- Web Dashboard 能展示日报、Sources、Tool Trace 和 Data Quality。
- CLI 能生成日报并输出保存路径。
- 任何一个外部数据源失败时，系统不崩溃，并显式标注 fallback。
- 测试、构建和 `docker compose config` 通过。

## 12. 开发顺序

1. 初始化项目结构、Python 和 TypeScript 工具链。
2. 定义共享 schema、日志结构和 fixture 数据。
3. 实现 3 个工具函数。
4. 将工具函数包装成 3 个 MCP server。
5. 实现 Agent API、Ollama provider 和 mock provider。
6. 实现报告生成 prompt 和输出校验。
7. 实现 TypeScript CLI。
8. 实现 Web Dashboard。
9. 补充 README、RUN.md、DATA_NOTES.md、mcp-config.json。
10. 运行测试、构建和 Docker 配置验证。
11. 上传 GitHub，并准备面试讲解稿。

## 13. 风险与取舍

- Ollama Gemma 对复杂工具规划和严格 JSON 输出不如大模型稳定，所以本期采用 deterministic workflow。
- NI 43-101 PDF 格式差异很大，所以本期优先做可解释抽取、fixture 和 abstain，不追求通吃。
- LME、SHFE 和上海钢联数据源存在登录墙和频控，所以本期使用 fixture 保证可复现，并保留真实接口替换点。
- Web Dashboard 和 CLI 都通过 Agent API 访问系统，避免前端和 CLI 重复业务逻辑。
- 真实 MCP server 与 HTTP 演示入口并存，既满足题目要求，也降低面试官运行门槛。

## 14. 面试讲解口径

可以这样介绍：

> 我把项目设计成 evidence-first 的 MCP Agent。底层把新闻检索、矿权报告资源量抽取和价格行情拆成 3 个独立 MCP server；上层 Agent 先调用工具收集结构化证据，再用本地 Ollama Gemma 生成 Markdown 日报。为了控制幻觉，模型只能使用 evidence pack 里的事实，输出后还会校验 Sources、风险提示和数据质量说明。真实数据源失败时，系统不会硬编，而是 fallback 到样例数据并明确标注。这种设计更接近生产系统的可测试、可审计和可降级要求。

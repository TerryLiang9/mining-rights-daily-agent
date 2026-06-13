# Configurable Data Providers Design

日期：2026-06-13

## 1. 背景

当前项目已经有三个 MCP server：

- `mining-news-mcp`
- `mineral-pdf-mcp`
- `lme-price-mcp`

它们能够跑通 MCP stdio、Agent 编排、CLI 和 Web Dashboard，但数据源仍存在明显 demo 化问题：

- 新闻工具仍以 `data/fixtures/news.json` 为主要兜底数据，真实新闻源边界不清晰。
- PDF 工具虽然支持本地/HTTP PDF，但 Agent 层仍有默认样例 PDF 路径，容易被理解成资源量被写死。
- 价格工具当前核心数据来自 `data/fixtures/prices.json`，没有真正的可配置行情数据入口。
- fixture 与真实源逻辑混在 `tools.py` 中，不利于审查、替换和测试。

本设计目标是把 fixture 从“默认主数据”降级为“明确披露的 fallback provider”，并把真实数据入口抽象成可替换 provider。

## 2. 目标

1. 每个 MCP server 都有清晰的 `providers.py`，区分真实源 provider 和 fixture provider。
2. `tools.py` 只负责参数校验、provider 调用顺序、fallback 决策和统一返回模型。
3. 新闻、PDF、价格三个域都支持可配置真实源。
4. fixture 只在显式 fixture 请求或真实源失败后的 fallback 场景使用。
5. 所有 fallback 都必须设置 `fallback_used=true` 并写入 `warnings`。
6. Agent、CLI 和 Web 能把用户提供的 PDF URL 传到 `mineral-pdf-mcp.extract_resources(pdf_url)`。
7. 测试覆盖真实源配置路径、fallback 路径和 MCP stdio 调用路径。

## 3. 非目标

- 不接入需要账号、付费或合同授权的 LME/SHFE/上海钢联接口。
- 不保证能解析所有 NI 43-101 PDF 表格和扫描件。
- 不引入数据库、队列、缓存服务或新的 Agent 框架。
- 不移除 fixture 文件；fixture 仍用于可复现测试和演示降级。

## 4. 总体架构

```text
MCP tool function
  |
  |-- validate arguments
  |-- choose provider chain
  |-- call live/configured provider
  |-- if unavailable, call fixture provider when allowed
  |-- normalize result into shared Pydantic model
  v
MCP JSON response
```

每个 MCP server 内部结构：

```text
mcp_servers/<domain>/
  server.py       # FastMCP wrapper
  tools.py        # stable tool contract and fallback orchestration
  providers.py    # external source and fixture source implementations
  tests/
```

## 5. Provider 设计

### 5.1 mining-news-mcp

文件：`mcp_servers/mining_news/providers.py`

Provider：

- `RssNewsProvider`
  - 输入：RSS feed URL 列表、query、days、limit。
  - 配置：`MINING_NEWS_RSS_FEEDS`，逗号分隔。
  - 输出：`NewsSearchResult` 和 `Article` 所需字段。
  - 失败：返回空结果和 warning，不直接抛出到 MCP 层。

- `FixtureNewsProvider`
  - 输入：query、days、limit、url。
  - 数据：`data/fixtures/news.json`。
  - 使用场景：RSS 未配置、RSS 失败、或 fixture URL 命中。
  - 输出必须标记 `fallback_used=true`。

`tools.py` 规则：

- `search(query, days)`：
  - blank query 返回空列表和 warning，不返回 fixture 噪音。
  - 优先 `RssNewsProvider`。
  - 若 RSS 未配置或无可用结果，走 `FixtureNewsProvider`。

- `fetch_article(url)`：
  - 先匹配 fixture URL，作为可复现演示路径。
  - 非 fixture URL 只允许 HTTP(S)，拒绝 `file://`、localhost 和 `.local`。
  - HTTP 抓取失败时返回 partial/fallback warning，不伪造正文。

### 5.2 mineral-pdf-mcp

文件：`mcp_servers/mineral_pdf/providers.py`

Provider：

- `PdfResourceProvider`
  - 输入：本地 PDF 路径或 HTTP(S) PDF URL。
  - 配置：可选 `MINERAL_PDF_DEFAULT_URL`。
  - 行为：下载或读取 PDF，使用 `pypdf` 提取页面文本，调用 parser 提取资源量。
  - 输出：`ResourceExtractionResult`，资源项带页码。

- `FixtureResourceProvider`
  - 数据：`data/fixtures/resources.json`。
  - 使用场景：仅当 `pdf_url` 显式为 `fixture://...` 或 fixture JSON 路径。
  - 不作为无 `pdf_url` 时的静默默认值。

`tools.py` 规则：

- `extract_resources(pdf_url)`：
  - 如果 `pdf_url` 为空，尝试读取 `MINERAL_PDF_DEFAULT_URL`。
  - 如果仍为空，返回 `abstain=true`，warning 说明未提供 PDF 源。
  - 如果显式 fixture URL，走 `FixtureResourceProvider`。
  - 如果真实 PDF 读取或解析失败，返回 `abstain=true`，不硬编资源量。

Agent 层规则：

- `generate_report(..., pdf_url=None)` 不再默认绑定样例 PDF。
- API、CLI、Web 都允许用户传入 `pdf_url`。
- 若没有 PDF 源，报告要在数据质量说明中披露资源量缺失。

### 5.3 lme-price-mcp

文件：`mcp_servers/lme_price/providers.py`

Provider：

- `ConfiguredPriceProvider`
  - 支持本地文件：`PRICE_DATA_FILE`。
  - 支持 HTTP JSON：`PRICE_DATA_URL`。
  - JSON 结构沿用当前 fixture 结构：

```json
{
  "lithium": {
    "currency": "USD",
    "unit": "t",
    "points": [
      { "date": "2026-06-13", "price": 12850 }
    ]
  }
}
```

  - 可选 CSV 格式：

```csv
commodity,date,price,currency,unit
lithium,2026-06-13,12850,USD,t
```

- `FixturePriceProvider`
  - 数据：`data/fixtures/prices.json`。
  - 使用场景：配置源缺失、配置源失败、或测试显式要求 fixture。
  - 输出必须标记 `fallback_used=true`。

`tools.py` 规则：

- `get_price(commodity, date)`：
  - 标准化 commodity alias，如 `Li -> lithium`。
  - 优先读取 `ConfiguredPriceProvider`。
  - 如果指定日期没有精确价格，使用最近的 prior close 并给 warning。
  - 如果配置源失败，fallback 到 fixture 并披露。

- `get_trend(commodity, days)`：
  - 优先读取配置源。
  - 只返回 days 窗口内价格点。
  - 数据不足返回 `trend=insufficient_data`。
  - source 必须反映实际来源：文件路径、URL 或 fixture。

## 6. 配置

新增或完善 `.env.example`：

```env
MINING_NEWS_RSS_FEEDS=
MINERAL_PDF_DEFAULT_URL=
PRICE_DATA_FILE=
PRICE_DATA_URL=
USE_FIXTURES_ON_FAILURE=true
```

`USE_FIXTURES_ON_FAILURE=false` 时：

- 新闻 RSS 无结果不自动返回 fixture。
- 价格配置源失败不自动返回 fixture。
- PDF 不受该开关影响；PDF fixture 必须显式请求。

## 7. 错误处理

统一原则：

- 参数非法：返回结构化 warning 或由 Pydantic/FastMCP 校验阻断。
- 外部源失败：记录 warning，按配置决定是否 fallback。
- fallback 使用：`fallback_used=true`，warning 写清楚原因。
- 无数据：返回空结构，不伪造事实。
- PDF 无证据：`abstain=true`。
- 价格无证据：`price=None` 或 `trend=insufficient_data`。

## 8. 测试策略

### 单元测试

- 新闻：
  - 配置 RSS feed 时，`search()` 返回 RSS 项并 `fallback_used=false`。
  - RSS 失败且允许 fallback 时，返回 fixture 并带 warning。
  - blank query 不返回 fixture。
  - unsafe article URL 被拒绝。

- PDF：
  - 本地 PDF 可解析 Indicated/Inferred 并保留页码。
  - 没有 `pdf_url` 且没有 `MINERAL_PDF_DEFAULT_URL` 时，返回 `abstain=true`。
  - 显式 `fixture://...` 才返回 fixture resource。

- 价格：
  - `PRICE_DATA_FILE` JSON/CSV 可驱动 `get_price/get_trend`。
  - `PRICE_DATA_URL` JSON 可驱动 `get_price/get_trend`。
  - 配置源失败时 fallback 到 fixture 并披露。
  - `USE_FIXTURES_ON_FAILURE=false` 时不 fallback。

### 集成测试

- MCP stdio：
  - `list_tools` 仍暴露五个必需工具。
  - `call_tool` 对每个工具都返回结构化结果。

- Agent：
  - request `pdf_url` 会透传到 `mineral-pdf-mcp.extract_resources`。
  - 无 `pdf_url` 时报告不硬编样例资源量，而是披露缺失或 abstain。
  - price citation 跟随实际 provider source。

- TypeScript：
  - CLI `--pdf` 传入 `pdf_url`。
  - Web Dashboard PDF 输入传入 `pdf_url`。

## 9. 文档更新

需要更新：

- `README.md`
  - 说明如何配置 RSS、PDF 默认源、价格文件/URL。
  - 说明 fixture 是 fallback，不是主数据。

- `RUN.md`
  - 给出带真实源配置的运行示例。
  - 给出无真实源时的 fallback/abstain 预期。

- `DATA_NOTES.md`
  - 说明 provider 优先级、fallback 规则和数据可信度边界。

## 10. 验收标准

修复后必须满足：

1. 三个 MCP 的主逻辑不再直接把 fixture 当唯一数据源。
2. `lme-price-mcp` 能通过配置文件或 URL 返回非 fixture price/trend。
3. `mineral-pdf-mcp` 无 PDF 源时不默认样例 PDF。
4. fixture 使用必须可追踪、可披露。
5. MCP stdio、Python tests、TypeScript tests、TypeScript build 和 Docker Compose config 通过。

验收命令：

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
```

## 11. 风险

- RSS 源结构不稳定，可能导致新闻字段缺失；provider 需要容错并披露 warning。
- 公开价格 URL 格式不可控，本期只承诺项目定义的 JSON/CSV schema。
- PDF 表格解析仍只覆盖文本型 PDF 和有限表达式；扫描件或复杂表格需要后续 OCR/表格模型。
- 如果关闭 fixture fallback，演示输出可能缺少部分证据，这是符合生产语义的结果。

## 12. 实施顺序建议

1. 新增 provider 测试，先覆盖外部配置源和 no-fallback 行为。
2. 新增三个 `providers.py`。
3. 重构三个 `tools.py` 使用 provider 链。
4. 调整 Agent 默认 PDF 行为和 citation source。
5. 更新 CLI/Web/API 请求链路测试。
6. 更新 README/RUN/DATA_NOTES。
7. 跑完整验收命令。

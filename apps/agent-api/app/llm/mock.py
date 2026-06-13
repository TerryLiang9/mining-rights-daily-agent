from mining_agent_shared.models import EvidencePack


class MockLLMProvider:
    def generate_report(self, evidence: EvidencePack) -> str:
        commodity = evidence.topic.commodity
        region = evidence.topic.region
        fallback_note = "本报告使用了样例数据/fallback 数据。" if evidence.fallback_used else "本报告未使用 fallback 数据。"
        sources = "\n".join(f"- {citation.label}: {citation.url}" for citation in evidence.citations)
        news_lines = "\n".join(f"- {item.title}: {item.summary}" for item in evidence.news) or "- 暂无新闻证据。"
        resource_lines = (
            "\n".join(
                f"- {item.category}: {item.ore_tonnage} {item.ore_tonnage_unit}, "
                f"grade {item.grade} {item.grade_unit}"
                for item in evidence.resources
            )
            or "- 暂无资源量证据。"
        )
        trend = evidence.price_trend.trend if evidence.price_trend else "insufficient_data"

        return f"""# {region} {commodity} 矿权日报

## Executive Summary
- 当前简报基于新闻、资源量和价格三个工具的结构化证据生成。
- 价格趋势为 {trend}。
- 数据质量需要结合 fallback 标记判断。

## 新闻动态
{news_lines}

## 储量/资源量快照
{resource_lines}

## 价格趋势
- 近 30 天趋势：{trend}。

## 风险提示
- 外部数据源不可用时会使用样例数据。
- PDF 抽取证据不足时应进入人工复核。

## 数据质量说明
{fallback_note}

## Sources
{sources}
"""

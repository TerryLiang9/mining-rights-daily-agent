from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Topic(BaseModel):
    raw_query: str
    region: str = "global"
    commodity: str = "lithium"
    days: int = Field(default=7, ge=1, le=90)
    language: str = "zh"
    report_type: str = "daily_brief"


class Citation(BaseModel):
    label: str
    url: str
    source_type: Literal["news", "pdf", "price", "fixture"]
    retrieved_at: str | None = None


class ToolTrace(BaseModel):
    tool: str
    input: dict[str, Any]
    status: Literal["success", "partial", "fallback", "error"]
    duration_ms: int = Field(ge=0)
    fallback_used: bool = False
    message: str | None = None


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    published_at: str
    summary: str
    score: float = Field(ge=0, le=1)


class NewsSearchResult(BaseModel):
    items: list[NewsItem]
    fallback_used: bool = False
    retrieved_at: str
    warnings: list[str] = Field(default_factory=list)


class Article(BaseModel):
    url: str
    title: str
    text: str
    published_at: str | None = None
    source: str
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class ResourceItem(BaseModel):
    category: Literal["Measured", "Indicated", "Inferred", "Other"]
    ore_tonnage: float | None = None
    ore_tonnage_unit: str | None = None
    grade: float | None = None
    grade_unit: str | None = None
    contained_metal: float | None = None
    contained_metal_unit: str | None = None
    page: int | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class ResourceExtractionResult(BaseModel):
    project_name: str
    report_title: str
    resources: list[ResourceItem]
    abstain: bool = False
    fallback_used: bool = False
    source_url: str
    warnings: list[str] = Field(default_factory=list)


class PricePoint(BaseModel):
    date: str
    price: float


class PriceTrend(BaseModel):
    commodity: str
    days: int
    points: list[PricePoint]
    change_pct: float | None = None
    trend: Literal["up", "down", "flat", "insufficient_data"]
    currency: str = "USD"
    unit: str = "t"
    source: str
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class EvidencePack(BaseModel):
    topic: Topic
    news: list[NewsItem] = Field(default_factory=list)
    articles: list[Article] = Field(default_factory=list)
    resources: list[ResourceItem] = Field(default_factory=list)
    prices: list[PricePoint] = Field(default_factory=list)
    price_trend: PriceTrend | None = None
    citations: list[Citation] = Field(default_factory=list)
    tool_trace: list[ToolTrace] = Field(default_factory=list)
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class ReportRequest(BaseModel):
    query: str
    days: int = Field(default=7, ge=1, le=90)


class ReportResponse(BaseModel):
    markdown: str
    citations: list[Citation]
    tool_trace: list[ToolTrace]
    fallback_used: bool
    warnings: list[str] = Field(default_factory=list)

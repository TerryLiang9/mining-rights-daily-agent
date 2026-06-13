from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from mining_agent_shared.models import Article, NewsItem, NewsSearchResult

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "news.json"


def _load_fixture_items() -> list[NewsItem]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in raw]


def search(query: str, days: int = 7, limit: int = 5) -> NewsSearchResult:
    terms = [term.lower() for term in query.split() if term.strip()]
    items = _load_fixture_items()
    scored: list[NewsItem] = []

    for item in items:
        haystack = f"{item.title} {item.summary}".lower()
        matched = sum(1 for term in terms if term in haystack)
        score = max(item.score, min(1.0, 0.5 + matched * 0.2))
        scored.append(item.model_copy(update={"score": score}))

    scored.sort(key=lambda item: item.score, reverse=True)
    return NewsSearchResult(
        items=scored[:limit],
        fallback_used=True,
        retrieved_at=datetime.now(UTC).isoformat(),
        warnings=["Using fixture mining news for reproducible interview demo."],
    )


def fetch_article(url: str) -> Article:
    for item in _load_fixture_items():
        if item.url == url:
            return Article(
                url=item.url,
                title=item.title,
                text=(
                    f"{item.title}\n\n"
                    f"{item.summary}\n\n"
                    "This fixture article discusses Pilbara lithium project signals, "
                    "policy context, and execution risks."
                ),
                published_at=item.published_at,
                source=item.source,
                fallback_used=True,
                warnings=["Article body generated from fixture summary."],
            )

    return Article(
        url=url,
        title="Unavailable article",
        text="Article body unavailable. The Agent should disclose this partial evidence.",
        source="unknown",
        fallback_used=True,
        warnings=["Requested article URL was not found in fixture data."],
    )

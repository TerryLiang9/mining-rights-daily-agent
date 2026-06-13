from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import feedparser
from bs4 import BeautifulSoup

from mining_agent_shared.models import Article, NewsItem, NewsSearchResult

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "news.json"
GENERIC_QUERY_TERMS = {"mining", "mine", "minerals", "mineral", "global", "news"}


def retrieved_at() -> str:
    return datetime.now(UTC).isoformat()


def _scoring_terms(query: str) -> list[str]:
    terms = [term.lower() for term in query.split() if term.strip()]
    meaningful = [term for term in terms if term not in GENERIC_QUERY_TERMS]
    return meaningful or terms


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _filter_recent(items: list[NewsItem], days: int) -> list[NewsItem]:
    dated_items = [(item, _parse_iso_date(item.published_at)) for item in items]
    valid_dates = [published for _, published in dated_items if published is not None]
    if not valid_dates:
        return items

    cutoff = max(valid_dates) - timedelta(days=days - 1)
    return [
        item
        for item, published in dated_items
        if published is None or published >= cutoff
    ]


def _score_items(items: list[NewsItem], terms: list[str]) -> list[NewsItem]:
    scored: list[NewsItem] = []
    for item in items:
        haystack = f"{item.title} {item.summary} {item.source}".lower()
        matched = sum(1 for term in terms if term in haystack)
        if terms and matched == 0:
            continue
        score = min(1.0, max(item.score, 0.45 + matched * 0.2))
        scored.append(item.model_copy(update={"score": round(score, 3)}))

    return sorted(scored, key=lambda item: (item.score, item.published_at), reverse=True)


class RssNewsProvider:
    def __init__(self, feed_urls: list[str], http_get) -> None:
        self.feed_urls = feed_urls
        self.http_get = http_get

    def search(self, query: str, days: int, limit: int) -> NewsSearchResult:
        warnings: list[str] = []
        items: list[NewsItem] = []

        for feed_url in self.feed_urls:
            try:
                response = self.http_get(feed_url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
            except Exception as exc:
                warnings.append(f"RSS feed failed for {feed_url}: {exc}")
                continue

            source = urlparse(feed_url).netloc or "rss"
            for entry in feed.entries:
                parsed_time = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
                published_at = (
                    datetime(*parsed_time[:6], tzinfo=UTC).date().isoformat()
                    if parsed_time
                    else datetime.now(UTC).date().isoformat()
                )
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                items.append(
                    NewsItem(
                        title=(getattr(entry, "title", "") or "Untitled mining news").strip(),
                        url=(getattr(entry, "link", "") or feed_url).strip(),
                        source=source,
                        published_at=published_at,
                        summary=BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)[:600],
                        score=0.5,
                    )
                )

        return NewsSearchResult(
            items=_score_items(_filter_recent(items, days), _scoring_terms(query))[:limit],
            fallback_used=False,
            retrieved_at=retrieved_at(),
            warnings=warnings,
        )


class FixtureNewsProvider:
    def _items(self) -> list[NewsItem]:
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return [NewsItem(**item) for item in raw]

    def search(self, query: str, days: int, limit: int, warnings: list[str] | None = None) -> NewsSearchResult:
        return NewsSearchResult(
            items=_score_items(_filter_recent(self._items(), days), _scoring_terms(query))[:limit],
            fallback_used=True,
            retrieved_at=retrieved_at(),
            warnings=[*(warnings or []), "Using fixture mining news for reproducible interview demo."],
        )

    def fetch_article(self, url: str) -> Article | None:
        for item in self._items():
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
        return None

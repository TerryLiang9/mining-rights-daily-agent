from __future__ import annotations

from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from mining_agent_shared.config import get_settings
from mining_agent_shared.models import Article, NewsSearchResult
from mcp_servers.mining_news.providers import FixtureNewsProvider, RssNewsProvider, retrieved_at

MAX_ARTICLE_CHARS = 8000
REQUEST_TIMEOUT_SECONDS = 15


def _http_get(url: str):
    return httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True)


def _coerce_positive_int(value: int, *, field_name: str, maximum: int, warnings: list[str]) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        warnings.append(f"{field_name} must be an integer; using 1.")
        return 1

    if parsed < 1:
        warnings.append(f"{field_name} must be >= 1; using 1.")
        return 1
    if parsed > maximum:
        warnings.append(f"{field_name} must be <= {maximum}; using {maximum}.")
        return maximum
    return parsed


def search(query: str, days: int = 7, limit: int = 5) -> NewsSearchResult:
    warnings: list[str] = []
    normalized_query = query.strip()
    if not normalized_query:
        return NewsSearchResult(
            items=[],
            fallback_used=False,
            retrieved_at=retrieved_at(),
            warnings=["query must not be blank."],
        )

    days = _coerce_positive_int(days, field_name="days", maximum=90, warnings=warnings)
    limit = _coerce_positive_int(limit, field_name="limit", maximum=20, warnings=warnings)
    settings = get_settings()
    feed_urls = [url.strip() for url in settings.mining_news_rss_feeds.split(",") if url.strip()]

    if feed_urls:
        live_result = RssNewsProvider(feed_urls, _http_get).search(normalized_query, days, limit)
        if live_result.items or not settings.use_fixtures_on_failure:
            live_result.warnings = [*warnings, *live_result.warnings]
            return live_result
        warnings.extend(live_result.warnings)

    return FixtureNewsProvider().search(normalized_query, days, limit, warnings)


def _unsafe_url_warning(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return f"Unsupported URL scheme: {parsed.scheme or 'missing'}."
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return "Unsafe article URL host is not allowed."
    return None


def _article_text_from_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = (
        (soup.find("meta", property="og:title") or {}).get("content")
        or (soup.title.string.strip() if soup.title and soup.title.string else "")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
        or "Untitled article"
    )
    container = soup.find("article") or soup.body or soup
    paragraphs = [paragraph.get_text(" ", strip=True) for paragraph in container.find_all("p")]
    text = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
    if not text:
        text = container.get_text(" ", strip=True)
    return title.strip(), text[:MAX_ARTICLE_CHARS].strip()


def fetch_article(url: str) -> Article:
    fixture_article = FixtureNewsProvider().fetch_article(url)
    if fixture_article is not None:
        return fixture_article

    warning = _unsafe_url_warning(url)
    if warning:
        return Article(
            url=url,
            title="Unavailable article",
            text="",
            source="unknown",
            fallback_used=True,
            warnings=[warning],
        )

    parsed = urlparse(url)
    try:
        response = _http_get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if content_type and "html" not in content_type.lower():
            return Article(
                url=url,
                title="Unsupported article content",
                text="",
                source=parsed.netloc,
                fallback_used=True,
                warnings=[f"Unsupported article content type: {content_type}."],
            )
        title, text = _article_text_from_html(response.text)
        if not text:
            return Article(
                url=url,
                title=title,
                text="",
                source=parsed.netloc,
                fallback_used=True,
                warnings=["Article HTML did not contain extractable text."],
            )
        return Article(
            url=url,
            title=title,
            text=text,
            source=parsed.netloc,
            fallback_used=False,
            warnings=[],
        )
    except Exception as exc:
        return Article(
            url=url,
            title="Unavailable article",
            text="",
            source=parsed.netloc or "unknown",
            fallback_used=True,
            warnings=[f"Article fetch failed: {exc}"],
        )

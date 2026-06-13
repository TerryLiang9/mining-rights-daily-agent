from mining_agent_shared.config import Settings
from mcp_servers.mining_news import tools
from mcp_servers.mining_news.tools import fetch_article, search


def test_search_uses_fixture_news():
    result = search("Pilbara lithium", days=7, limit=2)
    assert result.items
    assert result.items[0].title
    assert result.fallback_used is True


def test_fetch_article_returns_text_for_fixture_url():
    result = fetch_article("https://example.com/pilbara-lithium-policy")
    assert result.url == "https://example.com/pilbara-lithium-policy"
    assert "Pilbara" in result.text


def test_search_rejects_blank_query_without_returning_fixture_noise():
    result = search("   ", days=7, limit=5)

    assert result.items == []
    assert result.fallback_used is False
    assert any("query" in warning.lower() for warning in result.warnings)


def test_search_respects_day_window_and_limit():
    result = search("Pilbara lithium", days=1, limit=10)

    assert [item.url for item in result.items] == ["https://example.com/pilbara-lithium-policy"]


def test_fetch_article_extracts_safe_http_article(monkeypatch):
    class FakeResponse:
        headers = {"content-type": "text/html; charset=utf-8"}
        text = """
        <html>
          <head><title>Pilbara lithium financing update</title></head>
          <body>
            <article>
              <p>Pilbara lithium developers secured new downstream financing.</p>
              <p>The article describes execution risk and permitting milestones.</p>
            </article>
          </body>
        </html>
        """

        def raise_for_status(self) -> None:
            return None

    def fake_http_get(url: str):
        assert url == "https://news.example.com/pilbara-lithium"
        return FakeResponse()

    monkeypatch.setattr(tools, "_http_get", fake_http_get, raising=False)

    result = fetch_article("https://news.example.com/pilbara-lithium")

    assert result.fallback_used is False
    assert result.title == "Pilbara lithium financing update"
    assert "downstream financing" in result.text
    assert result.source == "news.example.com"


def test_fetch_article_rejects_unsafe_url_scheme():
    result = fetch_article("file:///C:/Windows/win.ini")

    assert result.fallback_used is True
    assert result.text == ""
    assert any("unsupported url scheme" in warning.lower() for warning in result.warnings)


def test_search_uses_configured_rss_provider_before_fixture(monkeypatch):
    class FakeResponse:
        text = """
        <rss><channel>
          <item>
            <title>Pilbara lithium project advances</title>
            <link>https://news.example.com/pilbara-live</link>
            <description>Live RSS item about Pilbara lithium.</description>
            <pubDate>Sat, 13 Jun 2026 00:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(mining_news_rss_feeds="https://feeds.example.com/mining.xml"),
    )
    monkeypatch.setattr(tools, "_http_get", lambda url: FakeResponse(), raising=False)

    result = search("Pilbara lithium", days=7, limit=3)

    assert result.fallback_used is False
    assert [item.url for item in result.items] == ["https://news.example.com/pilbara-live"]
    assert result.items[0].source == "feeds.example.com"


def test_search_does_not_use_fixture_when_fallback_disabled(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(
            mining_news_rss_feeds="https://feeds.example.com/broken.xml",
            use_fixtures_on_failure=False,
        ),
    )
    monkeypatch.setattr(
        tools,
        "_http_get",
        lambda url: (_ for _ in ()).throw(RuntimeError("rss unavailable")),
        raising=False,
    )

    result = search("Pilbara lithium", days=7, limit=3)

    assert result.items == []
    assert result.fallback_used is False
    assert any("rss unavailable" in warning.lower() for warning in result.warnings)

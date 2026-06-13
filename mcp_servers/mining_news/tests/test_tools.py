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

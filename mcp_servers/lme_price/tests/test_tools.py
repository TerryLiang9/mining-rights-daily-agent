from mcp_servers.lme_price.tools import get_price, get_trend


def test_get_trend_returns_fixture_change():
    trend = get_trend("lithium", days=30)
    assert trend.commodity == "lithium"
    assert trend.points
    assert trend.trend == "up"
    assert trend.fallback_used is True


def test_get_price_returns_latest_point():
    price = get_price("lithium")
    assert price["commodity"] == "lithium"
    assert price["price"] == 12850

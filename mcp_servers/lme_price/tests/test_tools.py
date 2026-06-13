from mining_agent_shared.models import PriceQuote
from mcp_servers.lme_price.tools import get_price, get_trend


def test_get_trend_returns_fixture_change():
    trend = get_trend("lithium", days=30)
    assert trend.commodity == "lithium"
    assert trend.points
    assert trend.trend == "up"
    assert trend.fallback_used is True


def test_get_price_returns_latest_point():
    price = get_price("lithium")
    assert isinstance(price, PriceQuote)
    assert price.commodity == "lithium"
    assert price.price == 12850


def test_get_trend_respects_requested_day_window():
    trend = get_trend("lithium", days=10)

    assert [point.date for point in trend.points] == ["2026-06-05", "2026-06-13"]
    assert trend.change_pct == 0.86


def test_get_price_returns_prior_close_when_exact_date_missing():
    price = get_price("lithium", date="2026-06-01")

    assert price.date == "2026-05-29"
    assert price.price == 12620
    assert any("nearest prior" in warning.lower() for warning in price.warnings)


def test_get_price_normalizes_common_commodity_alias():
    price = get_price("Li")

    assert price.commodity == "lithium"
    assert price.price == 12850

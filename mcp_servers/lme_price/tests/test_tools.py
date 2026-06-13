import json

from mining_agent_shared.models import PriceQuote
from mining_agent_shared.config import Settings
import mcp_servers.lme_price.tools as tools
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


def test_get_price_uses_configured_json_file(tmp_path, monkeypatch):
    data_path = tmp_path / "prices.json"
    data_path.write_text(
        json.dumps(
            {
                "lithium": {
                    "currency": "USD",
                    "unit": "t",
                    "points": [{"date": "2026-06-13", "price": 13125}],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(price_data_file=str(data_path), use_fixtures_on_failure=True),
    )

    price = get_price("lithium")

    assert price.price == 13125
    assert price.source == str(data_path)
    assert price.fallback_used is False
    assert price.warnings == []


def test_get_trend_uses_configured_csv_file(tmp_path, monkeypatch):
    data_path = tmp_path / "prices.csv"
    data_path.write_text(
        "\n".join(
            [
                "commodity,date,price,currency,unit",
                "lithium,2026-06-10,12900,USD,t",
                "lithium,2026-06-13,13100,USD,t",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(price_data_file=str(data_path), use_fixtures_on_failure=True),
    )

    trend = get_trend("lithium", days=5)

    assert [point.price for point in trend.points] == [12900, 13100]
    assert trend.change_pct == 1.55
    assert trend.source == str(data_path)
    assert trend.fallback_used is False


def test_price_tools_do_not_use_fixture_when_fallback_disabled(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(use_fixtures_on_failure=False, price_data_file="", price_data_url=""),
    )

    price = get_price("lithium")
    trend = get_trend("lithium", days=30)

    assert price.price is None
    assert price.source == ""
    assert price.fallback_used is False
    assert trend.points == []
    assert trend.source == ""
    assert trend.fallback_used is False
    assert any("PRICE_DATA_FILE" in warning for warning in [*price.warnings, *trend.warnings])

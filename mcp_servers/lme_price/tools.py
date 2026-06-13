from __future__ import annotations

import json
from pathlib import Path

from mining_agent_shared.models import PricePoint, PriceTrend

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "prices.json"


def _load_prices() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def get_trend(commodity: str, days: int = 30) -> PriceTrend:
    data = _load_prices()
    key = commodity.lower()

    if key not in data:
        return PriceTrend(
            commodity=key,
            days=days,
            points=[],
            trend="insufficient_data",
            source="fixture",
            fallback_used=True,
            warnings=[f"Unsupported commodity: {commodity}"],
        )

    payload = data[key]
    points = [PricePoint(**point) for point in payload["points"]]
    if len(points) < 2:
        change_pct = None
        trend = "insufficient_data"
    else:
        first = points[0].price
        last = points[-1].price
        change_pct = round(((last - first) / first) * 100, 2)
        trend = "up" if change_pct > 1 else "down" if change_pct < -1 else "flat"

    return PriceTrend(
        commodity=key,
        days=days,
        points=points,
        change_pct=change_pct,
        trend=trend,
        currency=payload.get("currency", "USD"),
        unit=payload.get("unit", "t"),
        source="fixture",
        fallback_used=True,
        warnings=["Using fixture price data for reproducible demo."],
    )


def get_price(commodity: str, date: str | None = None) -> dict:
    trend = get_trend(commodity, days=30)
    if not trend.points:
        return {
            "commodity": commodity.lower(),
            "date": date,
            "price": None,
            "source": "fixture",
            "fallback_used": True,
            "warnings": trend.warnings,
        }

    point = next((item for item in trend.points if item.date == date), trend.points[-1])
    return {
        "commodity": trend.commodity,
        "date": point.date,
        "price": point.price,
        "currency": trend.currency,
        "unit": trend.unit,
        "source": trend.source,
        "fallback_used": trend.fallback_used,
    }

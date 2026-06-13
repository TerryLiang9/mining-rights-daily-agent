from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from mining_agent_shared.models import PricePoint, PriceQuote, PriceTrend

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "prices.json"
COMMODITY_ALIASES = {
    "li": "lithium",
    "lithium carbonate": "lithium",
    "lithium hydroxide": "lithium",
    "cu": "copper",
}


def _load_prices() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _normalize_commodity(commodity: str) -> str:
    key = commodity.strip().lower()
    return COMMODITY_ALIASES.get(key, key)


def _coerce_days(days: int) -> tuple[int, list[str]]:
    warnings: list[str] = []
    try:
        parsed = int(days)
    except (TypeError, ValueError):
        return 1, ["days must be an integer; using 1."]

    if parsed < 1:
        return 1, ["days must be >= 1; using 1."]
    if parsed > 365:
        return 365, ["days must be <= 365; using 365."]
    return parsed, warnings


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _points_for_payload(payload: dict) -> list[PricePoint]:
    return sorted(
        [PricePoint(**point) for point in payload["points"]],
        key=lambda point: point.date,
    )


def _window_points(points: list[PricePoint], days: int) -> list[PricePoint]:
    if not points:
        return []

    reference_date = _parse_date(points[-1].date)
    cutoff = reference_date - timedelta(days=days - 1)
    windowed = [point for point in points if _parse_date(point.date) >= cutoff]
    return windowed or [points[-1]]


def _trend_label(change_pct: float | None) -> str:
    if change_pct is None:
        return "insufficient_data"
    if change_pct > 1:
        return "up"
    if change_pct < -1:
        return "down"
    return "flat"


def get_trend(commodity: str, days: int = 30) -> PriceTrend:
    data = _load_prices()
    key = _normalize_commodity(commodity)
    days, warnings = _coerce_days(days)

    if key not in data:
        return PriceTrend(
            commodity=key,
            days=days,
            points=[],
            trend="insufficient_data",
            source="fixture",
            fallback_used=True,
            warnings=[*warnings, f"Unsupported commodity: {commodity}"],
        )

    payload = data[key]
    points = _window_points(_points_for_payload(payload), days)
    if len(points) < 2:
        change_pct = None
    else:
        first = points[0].price
        last = points[-1].price
        change_pct = round(((last - first) / first) * 100, 2)
    trend = _trend_label(change_pct)

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
        warnings=[*warnings, "Using fixture price data for reproducible demo."],
    )


def get_price(commodity: str, date: str | None = None) -> PriceQuote:
    data = _load_prices()
    key = _normalize_commodity(commodity)
    if key not in data:
        return PriceQuote(
            commodity=key,
            date=date,
            price=None,
            source="fixture",
            fallback_used=True,
            warnings=[f"Unsupported commodity: {commodity}"],
        )

    payload = data[key]
    points = _points_for_payload(payload)
    warnings = ["Using fixture price data for reproducible demo."]

    if not points:
        return PriceQuote(
            commodity=key,
            date=date,
            price=None,
            currency=payload.get("currency", "USD"),
            unit=payload.get("unit", "t"),
            source="fixture",
            fallback_used=True,
            warnings=[*warnings, f"No price points available for {key}."],
        )

    if date:
        try:
            requested_date = _parse_date(date)
        except ValueError:
            requested_date = _parse_date(points[-1].date)
            warnings.append(f"Invalid price date {date}; using latest available close.")
        exact = next((point for point in points if point.date == requested_date.isoformat()), None)
        if exact:
            point = exact
        else:
            prior_points = [point for point in points if _parse_date(point.date) <= requested_date]
            if prior_points:
                point = prior_points[-1]
                warnings.append(
                    f"No exact price for {date}; using nearest prior close {point.date}."
                )
            else:
                point = points[0]
                warnings.append(
                    f"No price on or before {date}; using earliest available close {point.date}."
                )
    else:
        point = points[-1]

    return PriceQuote(
        commodity=key,
        date=point.date,
        price=point.price,
        currency=payload.get("currency", "USD"),
        unit=payload.get("unit", "t"),
        source="fixture",
        fallback_used=True,
        warnings=warnings,
    )

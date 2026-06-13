from __future__ import annotations

from datetime import date, timedelta

from mining_agent_shared.config import get_settings
from mining_agent_shared.models import PricePoint, PriceQuote, PriceTrend
from mcp_servers.lme_price.providers import (
    ConfiguredPriceProvider,
    FixturePriceProvider,
    PriceDataset,
)

COMMODITY_ALIASES = {
    "li": "lithium",
    "lithium carbonate": "lithium",
    "lithium hydroxide": "lithium",
    "cu": "copper",
}


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
        [PricePoint(**point) for point in payload.get("points", [])],
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


def _load_dataset() -> PriceDataset:
    settings = get_settings()
    price_data_file = settings.price_data_file.strip()
    price_data_url = settings.price_data_url.strip()
    configured_source = price_data_file or price_data_url

    if configured_source:
        try:
            return ConfiguredPriceProvider(price_data_file, price_data_url).load()
        except Exception as exc:
            warning = f"Configured price data source failed: {exc}"
            if settings.use_fixtures_on_failure:
                return FixturePriceProvider().load([warning])
            return PriceDataset(
                data={},
                source=configured_source,
                fallback_used=False,
                warnings=[warning],
            )

    if settings.use_fixtures_on_failure:
        return FixturePriceProvider().load()

    return PriceDataset(
        data={},
        source="",
        fallback_used=False,
        warnings=["No price data source configured; set PRICE_DATA_FILE or PRICE_DATA_URL."],
    )


def get_trend(commodity: str, days: int = 30) -> PriceTrend:
    dataset = _load_dataset()
    data = dataset.data
    key = _normalize_commodity(commodity)
    days, warnings = _coerce_days(days)
    warnings = [*dataset.warnings, *warnings]

    if key not in data:
        return PriceTrend(
            commodity=key,
            days=days,
            points=[],
            trend="insufficient_data",
            source=dataset.source,
            fallback_used=dataset.fallback_used,
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
        source=dataset.source,
        fallback_used=dataset.fallback_used,
        warnings=warnings,
    )


def get_price(commodity: str, date: str | None = None) -> PriceQuote:
    dataset = _load_dataset()
    data = dataset.data
    key = _normalize_commodity(commodity)
    if key not in data:
        return PriceQuote(
            commodity=key,
            date=date,
            price=None,
            source=dataset.source,
            fallback_used=dataset.fallback_used,
            warnings=[*dataset.warnings, f"Unsupported commodity: {commodity}"],
        )

    payload = data[key]
    points = _points_for_payload(payload)
    warnings = list(dataset.warnings)

    if not points:
        return PriceQuote(
            commodity=key,
            date=date,
            price=None,
            currency=payload.get("currency", "USD"),
            unit=payload.get("unit", "t"),
            source=dataset.source,
            fallback_used=dataset.fallback_used,
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
        source=dataset.source,
        fallback_used=dataset.fallback_used,
        warnings=warnings,
    )

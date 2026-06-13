from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "prices.json"
REQUEST_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class PriceDataset:
    data: dict
    source: str
    fallback_used: bool
    warnings: list[str]


class FixturePriceProvider:
    def load(self, warnings: list[str] | None = None) -> PriceDataset:
        return PriceDataset(
            data=_normalize_json_payload(json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))),
            source="fixture",
            fallback_used=True,
            warnings=[*(warnings or []), "Using fixture price data for reproducible demo."],
        )


class ConfiguredPriceProvider:
    def __init__(self, file_path: str = "", url: str = "") -> None:
        self.file_path = file_path.strip()
        self.url = url.strip()

    def load(self) -> PriceDataset:
        if self.file_path:
            path = Path(self.file_path)
            if not path.is_absolute():
                path = ROOT_DIR / path
            text = path.read_text(encoding="utf-8")
            return PriceDataset(
                data=_parse_price_text(text, str(path), ""),
                source=str(path),
                fallback_used=False,
                warnings=[],
            )

        if self.url:
            response = httpx.get(self.url, timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            return PriceDataset(
                data=_parse_price_text(response.text, self.url, content_type),
                source=self.url,
                fallback_used=False,
                warnings=[],
            )

        raise ValueError("No configured price data source.")


def _parse_price_text(text: str, source: str, content_type: str) -> dict:
    if source.lower().endswith(".csv") or "csv" in content_type.lower():
        return _normalize_csv_payload(text)
    return _normalize_json_payload(json.loads(text))


def _normalize_json_payload(raw: dict | list[dict]) -> dict:
    if isinstance(raw, list):
        return _normalize_rows_payload(raw)

    normalized: dict = {}
    for commodity, payload in raw.items():
        key = str(commodity).strip().lower()
        normalized[key] = {
            "currency": payload.get("currency", "USD"),
            "unit": payload.get("unit", "t"),
            "points": [
                {"date": str(point["date"]), "price": float(point["price"])}
                for point in payload.get("points", [])
            ],
        }
    return normalized


def _normalize_csv_payload(text: str) -> dict:
    rows = list(csv.DictReader(text.splitlines()))
    return _normalize_rows_payload(rows)


def _normalize_rows_payload(rows: list[dict]) -> dict:
    normalized: dict = {}
    for row in rows:
        commodity = str(row.get("commodity") or row.get("symbol") or "").strip().lower()
        if not commodity:
            raise ValueError("Price row is missing commodity.")
        date = str(row.get("date") or "").strip()
        if not date:
            raise ValueError(f"Price row for {commodity} is missing date.")
        price = float(row["price"])
        payload = normalized.setdefault(
            commodity,
            {
                "currency": str(row.get("currency") or "USD").strip() or "USD",
                "unit": str(row.get("unit") or "t").strip() or "t",
                "points": [],
            },
        )
        payload["points"].append({"date": date, "price": price})
    return normalized

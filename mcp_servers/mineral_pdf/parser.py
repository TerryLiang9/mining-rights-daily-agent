from __future__ import annotations

from collections.abc import Iterable
import re

from mining_agent_shared.models import ResourceItem

RESOURCE_PATTERN = re.compile(
    r"\b(?P<category>Measured|Indicated|Inferred)\b"
    r"(?:\s+(?:mineral\s+)?resources?)?"
    r"[^;\n\r]{0,80}?"
    r"(?P<tonnage>\d+(?:\.\d+)?)\s*"
    r"(?P<tonnage_unit>million\s+tonnes?|Mt|kt|thousand\s+tonnes?|tonnes?|t)\b"
    r"[^;\n\r]{0,60}?"
    r"(?:at|@)?\s*"
    r"(?P<grade>\d+(?:\.\d+)?)\s*%?\s*"
    r"(?P<grade_unit>Li2O|Cu|Ni|Zn|Au|Ag)?"
    r"[^;\n\r]{0,80}?"
    r"(?P<metal>\d+(?:\.\d+)?)\s*"
    r"(?P<metal_unit>million\s+tonnes?|Mt|kt|thousand\s+tonnes?|tonnes?|t)\s*"
    r"(?P<metal_name>LCE|Li2O|Cu|Ni|Zn|Au|Ag)?",
    re.IGNORECASE,
)


def _normalize_text(text: str) -> str:
    normalized = text.replace("\xa0", " ")
    normalized = re.sub(r"(?<=[A-Za-z])(?=(?:Measured|Indicated|Inferred)\b)", " ", normalized)
    return re.sub(r"[ \t]+", " ", normalized)


def _normalize_unit(unit: str) -> str:
    normalized = unit.strip().lower()
    if normalized in {"mt", "million tonne", "million tonnes"}:
        return "Mt"
    if normalized in {"kt", "thousand tonne", "thousand tonnes"}:
        return "kt"
    return "t"


def _grade_unit(raw: str | None) -> str | None:
    return f"% {_normalize_symbol(raw)}" if raw else "%"


def _contained_unit(raw_unit: str, raw_name: str | None) -> str:
    unit = _normalize_unit(raw_unit)
    return f"{unit} {_normalize_symbol(raw_name)}" if raw_name else unit


def _normalize_symbol(raw: str | None) -> str:
    if raw is None:
        return ""
    symbols = {
        "li2o": "Li2O",
        "lce": "LCE",
        "cu": "Cu",
        "ni": "Ni",
        "zn": "Zn",
        "au": "Au",
        "ag": "Ag",
    }
    return symbols.get(raw.lower(), raw)


def parse_resource_pages(pages: Iterable[tuple[int | None, str]]) -> list[ResourceItem]:
    resources: list[ResourceItem] = []
    for page_number, text in pages:
        normalized_text = _normalize_text(text)
        for match in RESOURCE_PATTERN.finditer(normalized_text):
            resources.append(
                ResourceItem(
                    category=match.group("category").title(),
                    ore_tonnage=float(match.group("tonnage")),
                    ore_tonnage_unit=_normalize_unit(match.group("tonnage_unit")),
                    grade=float(match.group("grade")),
                    grade_unit=_grade_unit(match.group("grade_unit")),
                    contained_metal=float(match.group("metal")),
                    contained_metal_unit=_contained_unit(
                        match.group("metal_unit"),
                        match.group("metal_name"),
                    ),
                    page=page_number,
                    confidence=0.78,
                )
            )
    return resources


def parse_resource_lines(text: str) -> list[ResourceItem]:
    return parse_resource_pages([(None, text)])

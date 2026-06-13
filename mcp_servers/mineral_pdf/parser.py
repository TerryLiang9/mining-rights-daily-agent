from __future__ import annotations

import re

from mining_agent_shared.models import ResourceItem

RESOURCE_PATTERN = re.compile(
    r"(?P<category>Indicated|Inferred)\s+"
    r"(?P<tonnage>\d+(?:\.\d+)?)\s*Mt\s+"
    r"(?P<grade>\d+(?:\.\d+)?)\s*%\s*Li2O\s+"
    r"(?P<metal>\d+(?:\.\d+)?)\s*Mt\s*LCE",
    re.IGNORECASE,
)


def parse_resource_lines(text: str) -> list[ResourceItem]:
    resources: list[ResourceItem] = []
    for match in RESOURCE_PATTERN.finditer(text):
        resources.append(
            ResourceItem(
                category=match.group("category").title(),
                ore_tonnage=float(match.group("tonnage")),
                ore_tonnage_unit="Mt",
                grade=float(match.group("grade")),
                grade_unit="% Li2O",
                contained_metal=float(match.group("metal")),
                contained_metal_unit="Mt LCE",
                confidence=0.7,
            )
        )
    return resources

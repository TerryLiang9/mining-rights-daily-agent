from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from mining_agent_shared.models import Citation


def make_citation(label: str, url: str, source_type: Literal["news", "pdf", "price", "fixture"]) -> Citation:
    return Citation(
        label=label,
        url=url,
        source_type=source_type,
        retrieved_at=datetime.now(UTC).isoformat(),
    )

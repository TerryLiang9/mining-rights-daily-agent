from __future__ import annotations

from typing import Protocol

from mining_agent_shared.models import EvidencePack


class LLMProvider(Protocol):
    def generate_report(self, evidence: EvidencePack) -> str:
        """Generate a Markdown report from an evidence pack."""

from __future__ import annotations

import httpx

from mining_agent_shared.models import EvidencePack


class OllamaProvider:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_report(self, evidence: EvidencePack) -> str:
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": self._build_prompt(evidence), "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["response"]

    def _build_prompt(self, evidence: EvidencePack) -> str:
        return (
            "You are a mining intelligence analyst. Write a concise Markdown daily brief in Chinese. "
            "Use only the evidence below. Do not invent numbers, dates, URLs, or project names. "
            "If fallback data is used, explicitly mention it in 数据质量说明. "
            "Required sections: Executive Summary, 新闻动态, 储量/资源量快照, 价格趋势, 风险提示, 数据质量说明, Sources.\n\n"
            f"<evidence>{evidence.model_dump_json()}</evidence>"
        )

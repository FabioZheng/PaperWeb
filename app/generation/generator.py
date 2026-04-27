"""Grounded generation from evidence pack only."""

from __future__ import annotations

from app.extraction.llm_provider import build_provider
from app.models import EvidencePack, GeneratedAnswer


class GenerationService:
    def __init__(self):
        self.provider = build_provider("generator")

    def generate(self, pack: EvidencePack) -> GeneratedAnswer:
        lines = [f"- [{i.source_store}] {i.text}" for i in pack.items]
        prompt = "Use only evidence below.\n" + "\n".join(lines)
        text = self.provider.complete_text(prompt)
        citations = [f"{i.source_store}:{i.item_id}" for i in pack.items]
        return GeneratedAnswer(query=pack.query, answer=text + "\n\nEvidence:\n" + "\n".join(lines), citations=citations, mode=pack.plan.response_mode)

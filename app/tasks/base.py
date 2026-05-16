from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskResult:
    task_type: str
    answer: str
    evidence_used: list[dict] = field(default_factory=list)
    evidence_discarded: list[dict] = field(default_factory=list)
    generator_called: bool = False
    selected_source: str = "paper_cards"


class BaseTask:
    task_type = "base"

    def run(self, query: str, context: dict) -> TaskResult:
        raise NotImplementedError

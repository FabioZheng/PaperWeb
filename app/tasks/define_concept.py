from __future__ import annotations

from app.paper_cards.index import match_acronym_or_term
from app.tasks.base import BaseTask, TaskResult


class DefineConceptTask(BaseTask):
    task_type = "define_concept"

    def run(self, query: str, context: dict) -> TaskResult:
        cards = context.get("paper_cards", [])
        concept = query.replace("what is", "").strip(" ?").upper()
        matched = match_acronym_or_term(cards, concept)
        if not matched:
            return TaskResult(task_type=self.task_type, answer="No evidence found for concept definition.")
        c = matched[0]
        answer = f"{concept} means {c.title}. In this database, it is described as: {(c.abstract or 'No abstract available.')[:220]}"
        ev = [{"paper_id": c.paper_id, "title": c.title}]
        return TaskResult(task_type=self.task_type, answer=answer, evidence_used=ev, generator_called=False, selected_source="acronym_keyterm_index")

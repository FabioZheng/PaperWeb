from __future__ import annotations

from app.tasks.base import BaseTask, TaskResult


class PlaceholderTask(BaseTask):
    task_type = "placeholder"

    def run(self, query: str, context: dict) -> TaskResult:
        return TaskResult(task_type=self.task_type, answer="Task scaffolded. Implement task-specific logic.")

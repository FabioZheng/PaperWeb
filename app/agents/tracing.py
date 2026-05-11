from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


TRACE_PATH = Path("data/agent_traces.jsonl")


def log_trace(event: dict) -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": datetime.utcnow().isoformat(), **event}
    with open(TRACE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_last_trace() -> dict | None:
    if not TRACE_PATH.exists():
        return None
    lines = TRACE_PATH.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return None
    return json.loads(lines[-1])

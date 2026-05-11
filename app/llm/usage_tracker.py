from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.config import load_config

RUN_ID = uuid4().hex[:10]
USAGE_DB_PATH = "data/llm_usage.sqlite"


def set_usage_db_path(path: str) -> None:
    global USAGE_DB_PATH
    USAGE_DB_PATH = path


def _conn(path: str = USAGE_DB_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage(
            ts TEXT, run_id TEXT, script_name TEXT, role TEXT, provider TEXT, model TEXT,
            input_tokens INTEGER, output_tokens INTEGER, total_tokens INTEGER,
            estimated_input_cost_usd REAL, estimated_output_cost_usd REAL, estimated_total_cost_usd REAL,
            status TEXT, source_module TEXT, paper_id TEXT, field_name TEXT, error_message TEXT
        )
        """
    )
    c.commit()
    return c


def pricing_table() -> dict:
    cfg = load_config()
    from_cfg = (cfg.llm.pricing or {}).get("openai") if cfg.llm.pricing else None
    if from_cfg:
        return from_cfg
    return {"gpt-5.5": {"input_per_million": 5.0, "output_per_million": 30.0}, "gpt-5.4": {"input_per_million": 2.5, "output_per_million": 15.0}, "gpt-5.4-mini": {"input_per_million": 0.75, "output_per_million": 4.5}}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _cost(model: str, input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
    price = pricing_table().get(model)
    if not price:
        print(f"[usage] warning: no pricing for model {model}")
        return 0.0, 0.0, 0.0
    ci = (input_tokens / 1_000_000) * price["input_per_million"]
    co = (output_tokens / 1_000_000) * price["output_per_million"]
    return ci, co, ci + co


def record_llm_usage(role: str, provider: str, model: str, input_tokens: int, output_tokens: int, status: str = "success", source_module: str = "", script_name: str = "", paper_id: str | None = None, field_name: str | None = None, error_message: str | None = None, run_id: str = RUN_ID, usage_db_path: str = USAGE_DB_PATH) -> None:
    ci, co, ct = _cost(model, input_tokens, output_tokens)
    c = _conn(usage_db_path)
    c.execute("INSERT INTO llm_usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (datetime.now(UTC).isoformat(), run_id, script_name, role, provider, model, int(input_tokens), int(output_tokens), int(input_tokens)+int(output_tokens), ci, co, ct, status, source_module, paper_id, field_name, error_message))
    c.commit(); c.close()


def get_usage_summary(usage_db_path: str = USAGE_DB_PATH) -> dict:
    c = _conn(usage_db_path)
    rows = c.execute("SELECT role, COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(estimated_total_cost_usd) FROM llm_usage GROUP BY role").fetchall()
    c.close()
    return {r[0]: {"calls": r[1] or 0, "input_tokens": r[2] or 0, "output_tokens": r[3] or 0, "total_cost": r[4] or 0.0, "total_tokens": (r[2] or 0)+(r[3] or 0)} for r in rows}


def get_usage_by_role(usage_db_path: str = USAGE_DB_PATH):
    return get_usage_summary(usage_db_path)


def get_usage_by_model(usage_db_path: str = USAGE_DB_PATH):
    c = _conn(usage_db_path); rows = c.execute("SELECT model, COUNT(*), SUM(estimated_total_cost_usd) FROM llm_usage GROUP BY model").fetchall(); c.close(); return rows


def get_usage_by_run(usage_db_path: str = USAGE_DB_PATH):
    c = _conn(usage_db_path); rows = c.execute("SELECT run_id, COUNT(*), SUM(estimated_total_cost_usd) FROM llm_usage GROUP BY run_id ORDER BY run_id DESC").fetchall(); c.close(); return rows


def print_usage_summary(usage_db_path: str = USAGE_DB_PATH) -> None:
    s = get_usage_summary(usage_db_path)
    print("LLM usage summary:")
    print("Role                 Calls   Input tok   Output tok   Est. cost")
    total = 0.0
    for role in ["router", "extractor", "generator", "topic_extractor", "semantic_summarizer"]:
        r = s.get(role, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0.0})
        total += r["total_cost"]
        print(f"{role:20} {r['calls']:5d} {r['input_tokens']:11d} {r['output_tokens']:12d} ${r['total_cost']:.4f}")
    print(f"TOTAL{'':16} ${total:.4f}")

from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3

from app.config import VALID_LLM_ROLES, load_config


def build_html(db: str) -> str:
    conn = sqlite3.connect(db)
    role = conn.execute("SELECT role, COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(estimated_total_cost_usd) FROM llm_usage GROUP BY role").fetchall()
    model = conn.execute("SELECT model, COUNT(*), SUM(estimated_total_cost_usd) FROM llm_usage GROUP BY model").fetchall()
    runs = conn.execute("SELECT run_id, COUNT(*), SUM(estimated_total_cost_usd) FROM llm_usage GROUP BY run_id ORDER BY run_id DESC LIMIT 20").fetchall()
    recent = conn.execute("SELECT ts, run_id, role, model, input_tokens, output_tokens, estimated_total_cost_usd, status FROM llm_usage ORDER BY ts DESC LIMIT 50").fetchall()
    conn.close()
    cfg = load_config()
    lineup = "".join([f"<li>{r}: {cfg.llm.roles[r].provider} / {cfg.llm.roles[r].model} / in {cfg.llm.roles[r].max_input_tokens} / out {cfg.llm.roles[r].max_output_tokens} / enabled {cfg.llm.roles[r].enabled}</li>" for r in VALID_LLM_ROLES])
    def table(headers, rows):
        h="".join([f"<th>{x}</th>" for x in headers]); b="".join(["<tr>"+"".join([f"<td>{c}</td>" for c in row])+"</tr>" for row in rows]);
        return f"<table border='1' cellspacing='0' cellpadding='4'><tr>{h}</tr>{b}</table>"
    return f"""<html><body><h1>LLM Usage Dashboard</h1><h2>Current LLM config</h2><ul>{lineup}</ul>
    <h3>Cost limits</h3><pre>{cfg.llm.cost_limits}</pre>
    <h3>Role usage</h3>{table(['role','calls','input','output','cost'], role)}
    <h3>Model usage</h3>{table(['model','calls','cost'], model)}
    <h3>Run usage</h3>{table(['run_id','calls','cost'], runs)}
    <h3>Recent calls</h3>{table(['ts','run','role','model','in','out','cost','status'], recent)}
    </body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--usage-db", default="data/llm_usage.sqlite")
    ap.add_argument("--out", default="reports/llm_usage_dashboard.html")
    args = ap.parse_args()
    html = build_html(args.usage_db)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"Wrote dashboard to {args.out}")


if __name__ == "__main__":
    main()

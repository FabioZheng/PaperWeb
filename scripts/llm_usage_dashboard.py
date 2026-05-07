from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import os

from app.config import VALID_LLM_ROLES, load_config
from app.llm.usage_tracker import reset_llm_usage_history


def build_html(db: str) -> str:
    conn = sqlite3.connect(db)
    role = conn.execute("SELECT role, COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(estimated_total_cost_usd) FROM llm_usage WHERE is_real_api_call=1 GROUP BY role").fetchall()
    model = conn.execute("SELECT model, COUNT(*), SUM(estimated_total_cost_usd) FROM llm_usage WHERE is_real_api_call=1 GROUP BY model").fetchall()
    runs = conn.execute("SELECT run_id, COUNT(*), SUM(estimated_total_cost_usd) FROM llm_usage WHERE is_real_api_call=1 GROUP BY run_id ORDER BY run_id DESC LIMIT 20").fetchall()
    recent = conn.execute("SELECT ts, run_id, role, model, input_tokens, output_tokens, estimated_total_cost_usd, status, runtime_mode FROM llm_usage ORDER BY ts DESC LIMIT 50").fetchall()
    conn.close()
    cfg = load_config()
    rows = []
    for r in VALID_LLM_ROLES:
        rc = cfg.llm.roles[r]
        key_present = bool(cfg.llm.openai_api_key or os.getenv(rc.api_key_env or "OPENAI_API_KEY"))
        runtime = "real_api" if rc.enabled and rc.provider == "openai" and key_present else ("mock" if rc.provider == "mock" else "fallback/unavailable")
        rows.append((r, rc.provider, rc.model, rc.enabled, key_present, runtime))

    def table(headers, vals):
        h = "".join([f"<th>{x}</th>" for x in headers])
        b = "".join(["<tr>" + "".join([f"<td>{c}</td>" for c in row]) + "</tr>" for row in vals])
        return f"<table border='1' cellspacing='0' cellpadding='4'><tr>{h}</tr>{b}</table>"

    return f"""<html><body><h1>LLM Usage Dashboard</h1>
    <h2>Current runtime status</h2>{table(['role','configured provider','configured model','enabled','api key present','runtime mode'], rows)}
    <h3>Cost limits</h3><pre>{cfg.llm.cost_limits}</pre>
    <h3>Real API usage by role</h3>{table(['role','calls','input','output','cost'], role)}
    <h3>Real API usage by model</h3>{table(['model','calls','cost'], model)}
    <h3>Real API usage by run</h3>{table(['run_id','calls','cost'], runs)}
    <h3>Recent call records</h3>{table(['ts','run','role','model','in','out','cost','status','runtime_mode'], recent)}
    </body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--usage-db", default="data/llm_usage.sqlite")
    ap.add_argument("--out", default="reports/llm_usage_dashboard.html")
    ap.add_argument("--reset", action="store_true", help="Reset usage history")
    ap.add_argument("--yes", action="store_true", help="Confirm reset")
    args = ap.parse_args()

    if args.reset:
        if not args.yes:
            print("Are you sure you want to reset LLM usage history? This cannot be undone.")
            print("Re-run with --reset --yes to confirm.")
            return
        reset_llm_usage_history(args.usage_db)
        print("LLM usage history reset.")

    html = build_html(args.usage_db)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"Wrote dashboard to {args.out}")


if __name__ == "__main__":
    main()

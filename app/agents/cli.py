from __future__ import annotations

import argparse
import json

from app.agents.paperweb_agent import PaperWebResearchAgent
from app.agents.tracing import load_last_trace
from app.cli import print_cli_banner
from app.config import load_config


def main() -> None:
    print_cli_banner()
    cfg = load_config()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask")
    a.add_argument("query")
    r = sub.add_parser("report")
    r.add_argument("--topic", required=True)
    t = sub.add_parser("trace")
    t.add_argument("--last", action="store_true")
    args = ap.parse_args()

    if args.cmd == "trace":
        print(json.dumps(load_last_trace() or {}, indent=2, ensure_ascii=False))
        return

    role = "generator"
    agent = PaperWebResearchAgent(model_role=role, db_path=cfg.storage.db_path, usage_db_path=cfg.storage.usage_db_path)
    q = args.query if args.cmd == "ask" else f"Generate a literature review about {args.topic}"
    out = agent.run(q, route="agents_cli")
    print(f"Route: {out['route']}")
    print(f"Agent lineup: {out['model_role']} -> {out['provider']}/{out['model']}")
    print("Tool calls:")
    for c in out["tool_calls"]:
        print(f"- {c['tool']}: {c['count']}")
    print("\nFinal answer:\n")
    print(out["answer"])
    print("\nEvidence IDs:")
    print(json.dumps(out["evidence_ids"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from app.config import load_config
from app.intelligence.institution_ranking import rank_institutions_by_direction
from app.intelligence.lab_coverage import compute_lab_coverage
from app.intelligence.loader import load_intelligence_papers
from app.intelligence.report import build_field_intelligence_report
from app.intelligence.taxonomy import build_topic_taxonomy, load_taxonomy_json, save_taxonomy_json
from app.intelligence.topic_assignment import assign_papers_to_taxonomy, save_assignments_json
from app.intelligence.topic_stats import compute_topic_direction_stats
from app.llm.usage_tracker import get_usage_summary, print_usage_summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/paperweb.db")
    p.add_argument("--field", required=True)
    p.add_argument("--lab-name", required=True)
    p.add_argument("--out", default="reports/field_intelligence.md")
    p.add_argument("--top-k", type=int, default=15)
    p.add_argument("--current-year", type=int, default=datetime.utcnow().year)
    p.add_argument("--recent-years", type=int, default=3)
    p.add_argument("--historical-years", type=int, default=5)
    p.add_argument("--min-topic-papers", type=int, default=2)
    p.add_argument("--topic-k", type=int, default=8)
    p.add_argument("--taxonomy", default="")
    p.add_argument("--taxonomy-out", default="reports/intelligence_taxonomy.json")
    p.add_argument("--assignments-out", default="reports/topic_assignments.json")
    p.add_argument("--min-fit-score", type=float, default=0.45)
    p.add_argument("--llm-provider", default="")
    p.add_argument("--abstract-only-topics", action="store_true", default=True)
    p.add_argument("--dry-run-cost", action="store_true")
    p.add_argument("--max-papers", type=int, default=0)
    p.add_argument("--force", action="store_true")
    p.add_argument("--ignore-cost-limit", action="store_true")
    args = p.parse_args()

    cfg = load_config()
    print("LLM lineup:")
    for role in ["router", "extractor", "generator", "topic_extractor", "semantic_summarizer"]:
        rc = getattr(cfg.llm, role)
        print(f"- {role}: {rc.provider} / {rc.model} ({'enabled' if rc.enabled else 'disabled'})")

    papers = load_intelligence_papers(args.db)
    if args.max_papers:
        papers = papers[: args.max_papers]
    if args.dry_run_cost:
        print(f"Dry-run cost estimate (rough): ~{len(papers)+1} LLM calls; no API calls executed.")
        return

    if args.taxonomy:
        taxonomy = load_taxonomy_json(args.taxonomy)
    else:
        taxonomy = build_topic_taxonomy(papers, k=args.topic_k, field=args.field, llm_provider=args.llm_provider or None)
        Path(args.taxonomy_out).parent.mkdir(parents=True, exist_ok=True)
        save_taxonomy_json(taxonomy, args.taxonomy_out)

    assignments = assign_papers_to_taxonomy(papers, taxonomy, llm_provider=args.llm_provider or None, min_fit_score=args.min_fit_score)
    Path(args.assignments_out).parent.mkdir(parents=True, exist_ok=True)
    save_assignments_json(assignments, args.assignments_out)

    stats = compute_topic_direction_stats(papers, taxonomy, assignments, args.current_year, args.recent_years, args.historical_years, args.min_topic_papers)
    ranks = rank_institutions_by_direction(papers, assignments, args.current_year, args.recent_years)
    coverage = compute_lab_coverage(papers, assignments, stats, args.lab_name, args.current_year, args.recent_years, args.historical_years)
    report = build_field_intelligence_report(args.field, args.lab_name, taxonomy, assignments, stats, ranks, coverage, args.top_k)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(report, encoding="utf-8")

    summary = get_usage_summary()
    total_cost = sum(v.get("total_cost", 0.0) for v in summary.values())
    if cfg.llm.cost_limits.enabled and not args.ignore_cost_limit and total_cost >= cfg.llm.cost_limits.max_estimated_run_cost_usd and not args.force:
        raise SystemExit("Estimated cost limit reached. Use --force or --ignore-cost-limit to continue.")

    print(f"Wrote report to {args.out}")
    print_usage_summary()


if __name__ == "__main__":
    main()

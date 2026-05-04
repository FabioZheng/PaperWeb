from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from app.intelligence.institution_ranking import rank_institutions_by_direction
from app.intelligence.lab_coverage import compute_lab_coverage
from app.intelligence.loader import load_intelligence_papers
from app.intelligence.report import build_field_intelligence_report
from app.intelligence.taxonomy import build_topic_taxonomy, load_taxonomy_json, save_taxonomy_json
from app.intelligence.topic_assignment import assign_papers_to_taxonomy, save_assignments_json
from app.intelligence.topic_stats import compute_topic_direction_stats


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
    args = p.parse_args()

    papers = load_intelligence_papers(args.db)
    if args.taxonomy:
        taxonomy = load_taxonomy_json(args.taxonomy)
    else:
        taxonomy = build_topic_taxonomy(papers, k=args.topic_k, field=args.field, llm_provider=args.llm_provider or None)
        Path(args.taxonomy_out).parent.mkdir(parents=True, exist_ok=True)
        save_taxonomy_json(taxonomy, args.taxonomy_out)

    assignments = assign_papers_to_taxonomy(papers, taxonomy, llm_provider=args.llm_provider or None, min_fit_score=args.min_fit_score)
    Path(args.assignments_out).parent.mkdir(parents=True, exist_ok=True)
    save_assignments_json(assignments, args.assignments_out)

    stats = compute_topic_direction_stats(
        papers,
        taxonomy,
        assignments,
        current_year=args.current_year,
        recent_years=args.recent_years,
        historical_years=args.historical_years,
        min_topic_papers=args.min_topic_papers,
    )
    ranks = rank_institutions_by_direction(papers, assignments, current_year=args.current_year, recent_years=args.recent_years)
    coverage = compute_lab_coverage(papers, assignments, stats, args.lab_name, args.current_year, args.recent_years, args.historical_years)
    report = build_field_intelligence_report(args.field, args.lab_name, taxonomy, assignments, stats, ranks, coverage, args.top_k)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"Wrote report to {args.out}")


if __name__ == "__main__":
    main()

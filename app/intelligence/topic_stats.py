from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.intelligence.schema import IntelligencePaper
from app.intelligence.topic_assignment import TopicAssignment
from app.intelligence.taxonomy import TopicBucket


@dataclass
class TopicDirectionStat:
    topic_id: str
    topic_title: str
    total_paper_count: int
    recent_paper_count: int
    historical_paper_count: int
    recent_topic_share: float
    historical_topic_share: float
    growth_score: float
    citation_velocity: float
    influential_citation_velocity: float
    top_venue_score: float
    institution_diversity_score: float
    frontier_score: float
    established_impact_score: float


def compute_topic_direction_stats(papers: list[IntelligencePaper], taxonomy: list[TopicBucket], assignments: list[TopicAssignment], current_year: int | None = None, recent_years: int = 3, historical_years: int = 5, min_topic_papers: int = 2) -> list[TopicDirectionStat]:
    year = current_year or datetime.utcnow().year
    recent_start = year - recent_years + 1
    historical_start = recent_start - historical_years
    pmap = {p.paper_id: p for p in papers}
    tmap = {t.topic_id: t.title for t in taxonomy}
    buckets: dict[str, list[IntelligencePaper]] = {}
    recent_total = 0
    historical_total = 0
    for a in assignments:
        if a.primary_topic_id == "OTHER":
            continue
        p = pmap.get(a.paper_id)
        if not p:
            continue
        buckets.setdefault(a.primary_topic_id, []).append(p)
        if p.year and p.year >= recent_start:
            recent_total += 1
        elif p.year and p.year >= historical_start:
            historical_total += 1
    out=[]
    for tid, items in buckets.items():
        if len(items)<min_topic_papers:
            continue
        total=len(items); recent=[p for p in items if p.year and p.year>=recent_start]; hist=[p for p in items if p.year and historical_start<=p.year<recent_start]
        recent_share=len(recent)/max(1,recent_total); hist_share=len(hist)/max(1,historical_total); growth=recent_share/max(1e-6,hist_share)
        cvel=sum((p.citation_count or 0)/max(1,year-(p.year or year)+1) for p in items)/total
        ivel=sum((p.influential_citation_count or 0)/max(1,year-(p.year or year)+1) for p in items)/total
        venue_score=sum(1 for p in items if p.venue)/max(1,total)
        inst_div=min(1.0,len({i for p in items for i in (p.institutions or [])})/max(1,total))
        frontier=0.35*recent_share+0.25*growth+0.20*((cvel+ivel)/2)+0.10*venue_score+0.10*inst_div
        established=0.35*total+0.30*sum(p.citation_count for p in items)+0.20*sum(p.influential_citation_count for p in items)+0.15*venue_score
        out.append(TopicDirectionStat(tid,tmap.get(tid,tid),total,len(recent),len(hist),recent_share,hist_share,growth,cvel,ivel,venue_score,inst_div,frontier,established))
    return sorted(out,key=lambda x:x.frontier_score, reverse=True)

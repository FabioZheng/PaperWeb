from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.intelligence.schema import IntelligencePaper
from app.intelligence.topic_assignment import TopicAssignment


@dataclass
class InstitutionDirectionRank:
    topic_id: str
    institution: str
    recent_paper_count: int
    total_paper_count: int
    citation_velocity: float
    influential_citation_velocity: float
    citation_count: int
    influential_citation_count: int
    venue_score: float
    current_leader_score: float
    established_leader_score: float


def rank_institutions_by_direction(papers: list[IntelligencePaper], assignments: list[TopicAssignment], current_year: int | None = None, recent_years: int = 3) -> list[InstitutionDirectionRank]:
    year=current_year or datetime.utcnow().year
    recent_start=year-recent_years+1
    pmap={p.paper_id:p for p in papers}
    grouped: dict[tuple[str,str], list[IntelligencePaper]]={}
    for a in assignments:
        p=pmap.get(a.paper_id)
        if not p: continue
        topic=a.primary_topic_id
        insts=p.institutions or ["Unknown institution"]
        for i in insts:
            grouped.setdefault((topic,i),[]).append(p)
    out=[]
    for (topic,inst),items in grouped.items():
        total=len(items); recent=len([p for p in items if p.year and p.year>=recent_start])
        cites=sum(p.citation_count for p in items); infl=sum(p.influential_citation_count for p in items)
        cvel=sum((p.citation_count or 0)/max(1,year-(p.year or year)+1) for p in items)/max(1,total)
        ivel=sum((p.influential_citation_count or 0)/max(1,year-(p.year or year)+1) for p in items)/max(1,total)
        venue=sum(1 for p in items if p.venue)/max(1,total)
        current=0.35*recent+0.25*cvel+0.20*ivel+0.10*total+0.10*venue
        estab=0.35*total+0.30*cites+0.20*infl+0.15*venue
        out.append(InstitutionDirectionRank(topic,inst,recent,total,cvel,ivel,cites,infl,venue,current,estab))
    return sorted(out,key=lambda r:(r.topic_id,-r.current_leader_score,-r.established_leader_score))

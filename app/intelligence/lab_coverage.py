from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.intelligence.schema import IntelligencePaper
from app.intelligence.topic_assignment import TopicAssignment
from app.intelligence.topic_stats import TopicDirectionStat


@dataclass
class LabTopicCoverage:
    topic_id: str
    field_papers: int
    lab_papers: int
    recent_field_papers: int
    recent_lab_papers: int
    historical_field_papers: int
    historical_lab_papers: int
    raw_coverage: float
    recent_raw_coverage: float
    field_share: float
    lab_share: float
    recent_field_share: float
    recent_lab_share: float
    specialization_ratio: float
    recent_specialization_ratio: float
    classification: str


def compute_lab_coverage(papers: list[IntelligencePaper], assignments: list[TopicAssignment], topic_stats: list[TopicDirectionStat], lab_name: str, current_year: int | None = None, recent_years: int = 3, historical_years: int = 5) -> list[LabTopicCoverage]:
    year=current_year or datetime.utcnow().year
    recent_start=year-recent_years+1
    historical_start=recent_start-historical_years
    lab=lab_name.lower()
    pmap={p.paper_id:p for p in papers}
    by_topic: dict[str,list[IntelligencePaper]]={}
    for a in assignments:
        p=pmap.get(a.paper_id)
        if p: by_topic.setdefault(a.primary_topic_id,[]).append(p)
    total=len(papers); total_recent=len([p for p in papers if p.year and p.year>=recent_start])
    lab_all=[p for p in papers if any(lab in (i or '').lower() for i in (p.institutions or []))]
    total_lab=len(lab_all); total_lab_recent=len([p for p in lab_all if p.year and p.year>=recent_start])
    frontier={s.topic_id:s.frontier_score for s in topic_stats}
    out=[]
    for tid,items in by_topic.items():
        lab_items=[p for p in items if any(lab in (i or '').lower() for i in (p.institutions or []))]
        rf=[p for p in items if p.year and p.year>=recent_start]; rl=[p for p in lab_items if p.year and p.year>=recent_start]
        hf=[p for p in items if p.year and historical_start<=p.year<recent_start]; hl=[p for p in lab_items if p.year and historical_start<=p.year<recent_start]
        field_cnt=len(items); lab_cnt=len(lab_items); rfc=len(rf); rlc=len(rl)
        raw=lab_cnt/max(1,field_cnt); rraw=rlc/max(1,rfc)
        field_share=field_cnt/max(1,total); lab_share=lab_cnt/max(1,total_lab)
        rfshare=rfc/max(1,total_recent); rlshare=rlc/max(1,total_lab_recent)
        spec=lab_share/max(1e-6,field_share); rspec=rlshare/max(1e-6,rfshare)
        fr=frontier.get(tid,0.0)
        if raw>=0.3 and spec>=1.25: cls='core strength'
        elif fr>=1.0 and rraw>=0.2: cls='emerging alignment'
        elif fr>=1.0 and rraw<0.1: cls='strategic gap'
        elif spec>=1.5 and fr<1.0: cls='niche specialization'
        elif raw>=0.25 and rraw<0.1: cls='historical strength'
        else: cls='emerging alignment'
        out.append(LabTopicCoverage(tid,field_cnt,lab_cnt,rfc,rlc,len(hf),len(hl),raw,rraw,field_share,lab_share,rfshare,rlshare,spec,rspec,cls))
    return out

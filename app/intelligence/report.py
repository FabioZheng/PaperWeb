from __future__ import annotations

from collections import Counter

from app.intelligence.institution_ranking import InstitutionDirectionRank
from app.intelligence.lab_coverage import LabTopicCoverage
from app.intelligence.taxonomy import TopicBucket
from app.intelligence.topic_assignment import TopicAssignment
from app.intelligence.topic_stats import TopicDirectionStat


def build_field_intelligence_report(field_name: str, lab_name: str, taxonomy: list[TopicBucket], assignments: list[TopicAssignment], topic_stats: list[TopicDirectionStat], institution_ranks: list[InstitutionDirectionRank], lab_coverage: list[LabTopicCoverage], top_k: int = 15) -> str:
    ttitle={t.topic_id:t.title for t in taxonomy}
    counts=Counter(a.primary_topic_id for a in assignments)
    other_titles=Counter(a.other_topic_title for a in assignments if a.primary_topic_id=='OTHER' and a.other_topic_title)
    front=sorted(topic_stats,key=lambda x:x.frontier_score,reverse=True)[:top_k]
    estab=sorted(topic_stats,key=lambda x:x.established_impact_score,reverse=True)[:top_k]
    lines=[f"# Field Intelligence Report: {field_name}","",f"Target lab: **{lab_name}**","","Taxonomy and assignments were inferred from **abstracts only**.","","## Generated topic taxonomy",""]
    for t in taxonomy:
        lines.append(f"- {t.topic_id}: **{t.title}** — {t.description}")
    lines += ["", "## Assignment summary", "", "| Topic | Assigned Papers |", "|---|---:|"]
    for t in taxonomy:
        lines.append(f"| {t.topic_id} ({t.title}) | {counts.get(t.topic_id,0)} |")
    lines.append(f"| OTHER | {counts.get('OTHER',0)} |")
    if other_titles:
        lines += ["", "Most common OTHER topic titles:"]
        for title,n in other_titles.most_common(5):
            lines.append(f"- {title}: {n}")

    lines += ["", "## Current frontier directions", "", "| Topic | Frontier Score | Recent Papers | Growth |", "|---|---:|---:|---:|"]
    for s in front:
        lines.append(f"| {s.topic_id} ({s.topic_title}) | {s.frontier_score:.3f} | {s.recent_paper_count} | {s.growth_score:.2f} |")

    lines += ["", "## Established directions", "", "| Topic | Established Impact Score | Total Papers |", "|---|---:|---:|"]
    for s in estab:
        lines.append(f"| {s.topic_id} ({s.topic_title}) | {s.established_impact_score:.2f} | {s.total_paper_count} |")

    lines += ["", "## Institution leaders by direction"]
    for s in front[:8]:
        ranks=[r for r in institution_ranks if r.topic_id==s.topic_id]
        cur=sorted(ranks,key=lambda x:x.current_leader_score,reverse=True)[:3]
        est=sorted(ranks,key=lambda x:x.established_leader_score,reverse=True)[:3]
        lines += ["", f"### {s.topic_id} ({s.topic_title})", "Current leaders:"]
        lines += [f"- {r.institution} (score={r.current_leader_score:.2f})" for r in cur] or ["- None"]
        lines += ["Established leaders:"] + ([f"- {r.institution} (score={r.established_leader_score:.2f})" for r in est] or ["- None"])

    lines += ["", "## Target lab coverage", "", "| Topic | Raw Coverage | Recent Coverage | Specialization | Recent Specialization | Class |", "|---|---:|---:|---:|---:|---|"]
    for c in lab_coverage[:top_k]:
        lines.append(f"| {c.topic_id} ({ttitle.get(c.topic_id,c.topic_id)}) | {c.raw_coverage:.2f} | {c.recent_raw_coverage:.2f} | {c.specialization_ratio:.2f} | {c.recent_specialization_ratio:.2f} | {c.classification} |")

    for cls in ["strategic gap","emerging alignment","core strength","niche specialization","historical strength"]:
        items=[c for c in lab_coverage if c.classification==cls]
        lines += ["", f"## {cls.title()}s"]
        lines += [f"- {c.topic_id} ({ttitle.get(c.topic_id,c.topic_id)})" for c in items[:top_k]] or ["- None"]

    lines += ["", "## Limitations", "- Topic taxonomy is abstract-only and may miss nuance from full-text/method sections.", "- Sparse abstracts reduce assignment fidelity.", "- Missing affiliation/citation metadata reduces ranking confidence."]
    return "\n".join(lines)+"\n"

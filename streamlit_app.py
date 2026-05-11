from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from app.agents.config import parse_agents_config
from app.agents.paperweb_agent import PaperWebResearchAgent
from app.config import load_config
from app.agents.config import parse_agents_config
from app.agents.paperweb_agent import PaperWebResearchAgent
from app.ingest import run_ingest, run_multi_source_ingest
from app.llm.usage_tracker import get_usage_summary
from app.query import run_query
from app.runtime import build_runtime_paths

st.set_page_config(page_title="PaperWeb UI", layout="wide")

cfg = load_config()
agents_cfg = parse_agents_config(cfg, {"agents": cfg.agents or {}})
DB_DIR = Path("data/dbs")
DB_DIR.mkdir(parents=True, exist_ok=True)


def list_dbs() -> list[str]:
    return sorted([str(p) for p in DB_DIR.glob("*.db")])


def read_table(db_path: str, table: str) -> pd.DataFrame:
    con = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(f"SELECT * FROM {table}", con)
    finally:
        con.close()


def read_graph_structure(db_path: str) -> dict:
    con = sqlite3.connect(db_path)
    try:
        nodes = pd.read_sql_query("SELECT node_id, node_type, name FROM graph_nodes", con)
        edges = pd.read_sql_query("SELECT edge_id, source_id, target_id, relation_type FROM graph_edges", con)
    finally:
        con.close()
    degree: dict[str, int] = {}
    for _, r in edges.iterrows():
        degree[r["source_id"]] = degree.get(r["source_id"], 0) + 1
        degree[r["target_id"]] = degree.get(r["target_id"], 0) + 1
    return {
        "num_nodes": int(len(nodes)),
        "num_edges": int(len(edges)),
        "relation_types": edges["relation_type"].value_counts().to_dict() if not edges.empty else {},
        "top_degree_nodes": sorted(degree.items(), key=lambda x: x[1], reverse=True)[:15],
        "nodes": nodes,
        "edges": edges,
    }


def usage_counts_by_role(usage_db_path: str) -> dict[str, int]:
    con = sqlite3.connect(usage_db_path)
    try:
        rows = con.execute("SELECT role, COUNT(*) FROM llm_usage GROUP BY role").fetchall()
    except Exception:
        rows = []
    finally:
        con.close()
    return {r[0]: int(r[1]) for r in rows}


def render_model_lineup(active_roles: set[str] | None = None) -> None:
    active_roles = active_roles or set()
    st.subheader("Model lineup")
    cols = st.columns(5)
    roles = ["router", "extractor", "generator", "topic_extractor", "semantic_summarizer"]
    for i, role in enumerate(roles):
        rcfg = cfg.llm.roles[role]
        label = f"{rcfg.provider}:{rcfg.model}"
        if role in active_roles:
            cols[i].markdown(
                f"<div style='padding:8px;border:2px solid #22c55e;border-radius:8px;background:#ecfdf5'><b>{role}</b><br/>{label}<br/><span style='color:#15803d'>● running</span></div>",
                unsafe_allow_html=True,
            )
        else:
            cols[i].markdown(
                f"<div style='padding:8px;border:1px solid #d1d5db;border-radius:8px'><b>{role}</b><br/>{label}</div>",
                unsafe_allow_html=True,
            )


st.title("PaperWeb Streamlit UI")
with st.sidebar:
    st.header("Database / Collection")
    options = list_dbs()
    default_db = str(DB_DIR / "paperweb.db")
    if default_db not in options:
        options = [default_db] + options
    selected = st.selectbox("Existing DB", options=options, index=0)
    new_name = st.text_input("Create new DB", value="agentic_ir")
    if st.button("Create and switch"):
        selected = str(DB_DIR / f"{new_name}.db")
        Path(selected).touch()
    st.session_state["active_db"] = selected
    st.success(f"Active DB: {selected}")


if st.session_state.get("active_roles_until", 0) and time.time() > st.session_state.get("active_roles_until", 0):
    st.session_state["active_roles"] = []
    st.session_state["active_roles_until"] = 0
render_model_lineup(set(st.session_state.get("active_roles", [])))

if agents_cfg.enabled:
    st.subheader("Agent lineup")
    st.json({
        "default_model_role": agents_cfg.default_model_role,
        "research": agents_cfg.research.model_role,
        "evidence": agents_cfg.evidence.model_role,
        "report": agents_cfg.report.model_role,
    })

st.subheader("Pipeline runner")
with st.form("pipeline"):
    pipeline_mode = st.radio("pipeline mode", ["crawler pipeline", "multi-source discovery"], horizontal=True)
    source = st.selectbox("crawler source", ["mock", "openreview", "aclcvf"])
    discovery_sources = st.multiselect("discovery sources", ["arxiv", "semantic_scholar", "openalex"], default=["arxiv", "semantic_scholar"])
    search_query = st.text_input("query/search string", value=cfg.ingestion.search_query or "information retrieval OR dense retrieval OR neural IR")
    limit = st.number_input("limit", min_value=1, max_value=50, value=cfg.ingestion.limit)
    field = st.text_input("research field", value=cfg.ingestion.research_field)
    paper_type = st.text_input("paper type", value=cfg.ingestion.paper_type)
    extraction_enabled = st.checkbox("extraction on", value=True)
    topic_inference_enabled = st.checkbox("topic inference on", value=True)
    semantic_summary_enabled = st.checkbox("semantic summary on", value=True)
    dry_run = st.checkbox("dry run", value=False)
    submitted = st.form_submit_button("Run pipeline")

if submitted:
    logs: list[str] = []
    progress = st.progress(0.0)
    status = st.empty()

    def on_event(msg: str) -> None:
        logs.append(msg)
        status.info(msg)
        progress.progress(min(1.0, len(logs) / max(1, int(limit))))

    pre_usage = usage_counts_by_role(runtime.usage_db_path)
    st.session_state["active_roles"] = []
    try:
        if dry_run:
            st.warning("Dry run selected; no writes executed.")
        elif pipeline_mode == "multi-source discovery":
            if not search_query.strip():
                raise ValueError("Query is required for multi-source discovery mode.")
            if not discovery_sources:
                raise ValueError("Select at least one discovery source.")
            st.json(run_multi_source_ingest(search_query, discovery_sources, int(limit), db_path=runtime.db_path))
        else:
            run_ingest(source=source, limit=int(limit), research_field=field, paper_type=paper_type, search_query=search_query or None, db_path=runtime.db_path, usage_db_path=runtime.usage_db_path, extraction_enabled=extraction_enabled, topic_inference_enabled=topic_inference_enabled, semantic_summary_enabled=semantic_summary_enabled, on_event=on_event)
        progress.progress(1.0)
        post_usage = usage_counts_by_role(runtime.usage_db_path)
        active = {r for r, n in post_usage.items() if n > pre_usage.get(r, 0)}
        st.session_state["active_roles"] = sorted(active)
        st.session_state["active_roles_until"] = time.time() + 5
        st.success("Pipeline complete")
    except Exception as exc:
        st.error(f"Pipeline failed: {exc}")
    st.text_area("Activity logs", value="\n".join(logs), height=220)

st.subheader("Usage / cost")
st.json(get_usage_summary(runtime.usage_db_path))

st.subheader("Query knowledge base")
query_db = st.selectbox("Query DB", options=list_dbs() or [runtime.db_path], index=0)
q = st.text_input("Ask a question")
if st.button("Run query") and q:
    query_runtime = build_runtime_paths(query_db, cfg.storage.usage_db_path)
    pre_usage = usage_counts_by_role(query_runtime.usage_db_path)
    out = run_query(q, db_path=query_runtime.db_path, usage_db_path=query_runtime.usage_db_path)
    post_usage = usage_counts_by_role(query_runtime.usage_db_path)
    active = {r for r, n in post_usage.items() if n > pre_usage.get(r, 0)}
    st.session_state["active_roles"] = sorted(active)
    st.session_state["active_roles_until"] = time.time() + 5
    st.caption(f"Query route: {out.get('route', 'pipeline')} · DB: {query_runtime.db_path}")
    if out.get("agent_fallback_reason"):
        st.warning(f"Agent fallback reason: {out['agent_fallback_reason']}")
    st.markdown("### Final answer")
    st.write(out["answer"]["answer"])
    st.markdown("### Citations")
    st.json(out["answer"].get("citations", []))
    st.markdown("### Router plan")
    st.json(out["plan"])
    st.markdown("### Evidence")
    st.dataframe(pd.DataFrame(out.get("evidence_items", [])))

if st.button("Show graph structure"):
    try:
        g = read_graph_structure(query_db)
        st.markdown("### Graph summary")
        st.json({"num_nodes": g["num_nodes"], "num_edges": g["num_edges"], "relation_types": g["relation_types"], "top_degree_nodes": g["top_degree_nodes"]})
        st.markdown("### Graph nodes")
        st.dataframe(g["nodes"], use_container_width=True)
        st.markdown("### Graph edges")
        st.dataframe(g["edges"], use_container_width=True)
    except Exception as exc:
        st.error(f"Failed to load graph structure: {exc}")

st.subheader("Dataset explorer")
tabs = st.tabs(["papers", "chunks", "extracted", "graph_nodes", "graph_edges", "semantic", "query export"])
for tab, name in zip(tabs, ["papers", "chunks", "extracted", "graph_nodes", "graph_edges", "graph_semantic", "papers"]):
    with tab:
        try:
            df = read_table(runtime.db_path, name)
            term = st.text_input(f"Search {name}", key=f"search_{name}")
            if term:
                df = df[df.astype(str).apply(lambda c: c.str.contains(term, case=False, na=False)).any(axis=1)]
            st.dataframe(df, use_container_width=True)
            st.download_button(f"Export {name} JSON", data=df.to_json(orient="records", indent=2), file_name=f"{Path(runtime.db_path).stem}_{name}.json")
            st.download_button(f"Export {name} CSV", data=df.to_csv(index=False), file_name=f"{Path(runtime.db_path).stem}_{name}.csv")
            if name == "papers" and not df.empty:
                pid = st.selectbox("Paper details", options=df["paper_id"].tolist(), key="paper_select")
                row = df[df["paper_id"] == pid].iloc[0]
                st.json(json.loads(row["payload"]))
        except Exception as exc:
            st.info(f"Table not available yet: {exc}")

if agents_cfg.enabled:
    st.subheader("Agent Research")
    aq = st.text_input("Agent research query")
    if st.button("Run agent research") and aq:
        pre_usage = usage_counts_by_role(runtime.usage_db_path)
        out = PaperWebResearchAgent(model_role=agents_cfg.research.model_role, db_path=runtime.db_path, usage_db_path=runtime.usage_db_path, max_tool_calls=agents_cfg.research.max_tool_calls, trace_enabled=agents_cfg.trace_enabled).run(aq, route="agents_streamlit")
        post_usage = usage_counts_by_role(runtime.usage_db_path)
        active = {r for r, n in post_usage.items() if n > pre_usage.get(r, 0)}
        st.session_state["active_roles"] = sorted(active)
        st.session_state["active_roles_until"] = time.time() + 5
        st.write(f"Selected route: {out['route']}")
        st.json(out.get("tool_calls", []))
        st.json({"evidence_ids": out.get("evidence_ids", [])})
        st.markdown("### Final grounded answer")
        st.write(out["answer"])

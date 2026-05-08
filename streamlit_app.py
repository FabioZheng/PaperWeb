from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from app.config import load_config
from app.ingest import run_ingest, run_multi_source_ingest
from app.llm.usage_tracker import get_usage_summary
from app.query import run_query
from app.runtime import build_runtime_paths

st.set_page_config(page_title="PaperWeb UI", layout="wide")

cfg = load_config()
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

active_db = st.session_state.get("active_db", str(DB_DIR / "paperweb.db"))
runtime = build_runtime_paths(active_db, cfg.storage.usage_db_path)

st.subheader("Model lineup")
cols = st.columns(5)
for i, role in enumerate(["router", "extractor", "generator", "topic_extractor", "semantic_summarizer"]):
    rcfg = cfg.llm.roles[role]
    cols[i].metric(role, f"{rcfg.provider}:{rcfg.model}")

st.subheader("Pipeline runner")
with st.form("pipeline"):
    source = st.selectbox("source", ["mock", "openreview", "aclcvf", "arxiv", "semantic_scholar", "openalex"])
    search_query = st.text_input("query/search string", value=cfg.ingestion.search_query or "")
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
        denom = max(1, int(limit))
        progress.progress(min(1.0, len(logs) / denom))

    try:
        if dry_run:
            st.warning("Dry run selected; no writes executed.")
        else:
            if source in {"arxiv", "semantic_scholar", "openalex"} and search_query:
                summary = run_multi_source_ingest(search_query, [source], int(limit), db_path=runtime.db_path)
                st.json(summary)
            else:
                run_ingest(source=source, limit=int(limit), research_field=field, paper_type=paper_type, search_query=search_query or None, db_path=runtime.db_path, usage_db_path=runtime.usage_db_path, extraction_enabled=extraction_enabled, topic_inference_enabled=topic_inference_enabled, semantic_summary_enabled=semantic_summary_enabled, on_event=on_event)
            progress.progress(1.0)
            st.success("Pipeline complete")
    except Exception as exc:
        st.error(f"Pipeline failed: {exc}")
    st.text_area("Activity logs", value="\n".join(logs), height=220)

st.subheader("Usage / cost")
usage = get_usage_summary(runtime.usage_db_path)
st.json(usage)

st.subheader("Query knowledge base")
q = st.text_input("Ask a question")
if st.button("Run query") and q:
    out = run_query(q, db_path=runtime.db_path, usage_db_path=runtime.usage_db_path)
    st.markdown("### Final answer")
    st.write(out["answer"]["answer"])
    st.markdown("### Citations")
    st.json(out["answer"].get("citations", []))
    st.markdown("### Router plan")
    st.json(out["plan"])
    st.markdown("### Evidence")
    st.dataframe(pd.DataFrame(out["evidence_items"]))

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
                payload = json.loads(row["payload"])
                st.json(payload)
        except Exception as exc:
            st.info(f"Table not available yet: {exc}")

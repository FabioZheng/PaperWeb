from types import SimpleNamespace

from app.query_router.router import QueryRouter


class _RoleCfg:
    def __init__(self):
        self.provider = "mock"
        self.model = "gpt-5.4-mini"
        self.max_input_tokens = 2000
        self.max_output_tokens = 300
        self.temperature = 0.0
        self.enabled = True
        self.base_url = None
        self.api_key_env = "OPENAI_API_KEY"


def _cfg(agents_enabled: bool):
    roles = {k: _RoleCfg() for k in ["router", "extractor", "generator", "topic_extractor", "semantic_summarizer"]}
    return SimpleNamespace(llm=SimpleNamespace(roles=roles), agents={"enabled": agents_enabled}, storage=SimpleNamespace(db_path="data/paperweb.db", usage_db_path="data/llm_usage.sqlite"))


def test_route_pipeline_when_agents_disabled(monkeypatch):
    monkeypatch.setattr("app.query_router.router.load_config", lambda: _cfg(False))
    r = QueryRouter(use_llm=False)
    assert r.select_execution_route("Generate a literature review") == "pipeline"


def test_route_agents_for_complex_query_when_enabled(monkeypatch):
    monkeypatch.setattr("app.query_router.router.load_config", lambda: _cfg(True))
    r = QueryRouter(use_llm=False)
    assert r.select_execution_route("Find research gap and compare methods across papers") == "agents"


def test_route_pipeline_for_simple_query_when_enabled(monkeypatch):
    monkeypatch.setattr("app.query_router.router.load_config", lambda: _cfg(True))
    r = QueryRouter(use_llm=False)
    assert r.select_execution_route("List papers from 2025") == "pipeline"

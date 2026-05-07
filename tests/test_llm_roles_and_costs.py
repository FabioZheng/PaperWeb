from app.config import ROLE_DEFAULTS, VALID_LLM_ROLES, get_llm_role_config, load_config
from app.extraction.llm_provider import build_provider
from app.llm.usage_tracker import get_usage_by_model, get_usage_by_run, get_usage_summary, record_llm_usage


def test_config_supports_all_roles():
    cfg = load_config()
    for role in VALID_LLM_ROLES:
        assert role in cfg.llm.roles


def test_missing_role_fallback_defaults():
    assert ROLE_DEFAULTS["topic_extractor"].max_input_tokens == 8000


def test_unknown_role_errors():
    try:
        get_llm_role_config("bad")
        assert False
    except ValueError as e:
        assert "Valid" in str(e)


def test_provider_factory_all_roles():
    for role in VALID_LLM_ROLES:
        assert build_provider(role) is not None


def test_usage_persisted_and_aggregated(tmp_path):
    db = str(tmp_path / "usage.sqlite")
    record_llm_usage(role="router", provider="openai", model="gpt-5.4-mini", input_tokens=1000, output_tokens=200, usage_db_path=db)
    record_llm_usage(role="extractor", provider="openai", model="unknown-model", input_tokens=100, output_tokens=20, usage_db_path=db)
    s = get_usage_summary(db)
    assert s["router"]["calls"] == 1
    assert s["extractor"]["total_cost"] >= 0
    assert get_usage_by_model(db)
    assert get_usage_by_run(db)

from app.config import ROLE_DEFAULTS, VALID_LLM_ROLES, get_llm_role_config, load_config
from app.extraction.llm_provider import build_provider
from app.llm.usage_tracker import get_usage_by_model, get_usage_by_run, get_usage_summary, record_llm_usage, reset_llm_usage_history


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


def test_non_real_usage_not_counted(tmp_path):
    db = str(tmp_path / "usage.sqlite")
    record_llm_usage(role="router", provider="mock", model="gpt-5.4-mini", input_tokens=1000, output_tokens=200, usage_db_path=db, is_real_api_call=False, runtime_mode="mock")
    s = get_usage_summary(db)
    assert s == {}


def test_real_usage_and_reset(tmp_path):
    db = str(tmp_path / "usage.sqlite")
    record_llm_usage(role="router", provider="openai", model="gpt-5.4-mini", input_tokens=1000, output_tokens=200, usage_db_path=db, is_real_api_call=True, runtime_mode="real_api")
    s = get_usage_summary(db)
    assert s["router"]["calls"] == 1
    assert get_usage_by_model(db)
    assert get_usage_by_run(db)
    reset_llm_usage_history(db)
    assert get_usage_summary(db) == {}
    assert load_config().llm.roles["router"].model

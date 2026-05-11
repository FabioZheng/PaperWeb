from app.extraction.llm_provider import _safe_json_loads


def test_safe_json_loads_handles_wrapped_prose():
    raw = "hello before {\"intent\":\"qa\",\"filters\":{}} trailing"
    out = _safe_json_loads(raw)
    assert out["intent"] == "qa"


def test_safe_json_loads_handles_balanced_with_tail_garbage():
    raw = '{"ok": true, "nested": {"x": 1}} garbage here'
    out = _safe_json_loads(raw)
    assert out["ok"] is True

from __future__ import annotations

from app.config import VALID_LLM_ROLES, load_config


def print_cli_banner() -> None:
    cfg = load_config()
    print("PaperWeb CLI")
    print("LLM lineup:")
    for role in VALID_LLM_ROLES:
        rc = cfg.llm.roles[role]
        print(
            f"- {role}: {rc.provider} / {rc.model} / input {rc.max_input_tokens} / output {rc.max_output_tokens} / enabled {str(rc.enabled).lower()}"
        )
    cl = cfg.llm.cost_limits
    print(
        f"Cost limits: enabled={str(cl.enabled).lower()} warn_after=${cl.warn_after_estimated_cost_usd:.2f} max_run=${cl.max_estimated_run_cost_usd:.2f} max_calls_per_role={cl.max_calls_per_role}"
    )
    print("Usage dashboard: python scripts/llm_usage_dashboard.py --usage-db data/llm_usage.sqlite")

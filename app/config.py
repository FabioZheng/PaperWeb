"""Application configuration loaded from TOML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

VALID_LLM_ROLES = ("router", "extractor", "generator", "topic_extractor", "semantic_summarizer")


@dataclass(frozen=True)
class LLMRoleConfig:
    role: str
    provider: str = "openai"
    model: str = "gpt-5.4-mini"
    max_input_tokens: int = 2000
    max_output_tokens: int = 300
    temperature: float = 0.0
    enabled: bool = True
    base_url: str | None = None
    api_key_env: str | None = "OPENAI_API_KEY"


@dataclass(frozen=True)
class CostLimitsConfig:
    enabled: bool = True
    warn_after_estimated_cost_usd: float = 1.0
    max_estimated_run_cost_usd: float = 5.0
    max_calls_per_role: int = 1000


@dataclass(frozen=True)
class LLMConfig:
    roles: dict[str, LLMRoleConfig]
    openai_api_key: str | None = None
    pricing: dict[str, dict[str, dict[str, float]]] | None = None
    cost_limits: CostLimitsConfig = CostLimitsConfig()


@dataclass(frozen=True)
class IngestionConfig:
    source: str = "mock"
    limit: int = 5
    research_field: str = "nlp"
    paper_type: str = "recent"
    search_query: str | None = None


@dataclass(frozen=True)
class StorageConfig:
    db_path: str = "data/paperweb.db"
    usage_db_path: str = "data/llm_usage.sqlite"


class AppConfig:
    llm: LLMConfig
    ingestion: IngestionConfig = IngestionConfig()
    storage: StorageConfig = StorageConfig()


ROLE_DEFAULTS = {
    "router": LLMRoleConfig(role="router", model="gpt-5.4-mini", max_input_tokens=2000, max_output_tokens=300),
    "extractor": LLMRoleConfig(role="extractor", model="gpt-5.4-mini", max_input_tokens=12000, max_output_tokens=2000, temperature=0.1),
    "generator": LLMRoleConfig(role="generator", model="gpt-5.4", max_input_tokens=24000, max_output_tokens=3000, temperature=0.3),
    "topic_extractor": LLMRoleConfig(role="topic_extractor", model="gpt-5.4-mini", max_input_tokens=8000, max_output_tokens=1200, temperature=0.1),
    "semantic_summarizer": LLMRoleConfig(role="semantic_summarizer", model="gpt-5.4-mini", max_input_tokens=6000, max_output_tokens=900, temperature=0.2),
}


def _load_raw(path: str | None = None) -> dict:
    p = Path(path or os.getenv("PAPERWEB_CONFIG", "config/paperweb.toml"))
    if not p.exists():
        return {}
    return tomllib.loads(p.read_text())


def load_config(path: str | None = None) -> AppConfig:
    data = _load_raw(path)
    llm_data = data.get("llm", {})
    roles: dict[str, LLMRoleConfig] = {}
    for role in VALID_LLM_ROLES:
        d = llm_data.get(role, {})
        base = ROLE_DEFAULTS[role]
        roles[role] = LLMRoleConfig(
            role=role,
            provider=str(d.get("provider", base.provider)).lower(),
            model=str(d.get("model", base.model)),
            max_input_tokens=int(d.get("max_input_tokens", base.max_input_tokens)),
            max_output_tokens=int(d.get("max_output_tokens", base.max_output_tokens)),
            temperature=float(d.get("temperature", base.temperature)),
            enabled=bool(d.get("enabled", base.enabled)),
            base_url=d.get("base_url"),
            api_key_env=d.get("api_key_env", base.api_key_env),
        )

    cl = llm_data.get("cost_limits", {})
    ingest = data.get("ingestion", {})
    storage = data.get("storage", {})
    return AppConfig(
        llm=LLMConfig(
            roles=roles,
            openai_api_key=llm_data.get("openai_api_key"),
            pricing=llm_data.get("pricing") or None,
            cost_limits=CostLimitsConfig(
                enabled=bool(cl.get("enabled", True)),
                warn_after_estimated_cost_usd=float(cl.get("warn_after_estimated_cost_usd", 1.0)),
                max_estimated_run_cost_usd=float(cl.get("max_estimated_run_cost_usd", 5.0)),
                max_calls_per_role=int(cl.get("max_calls_per_role", 1000)),
            ),
        ),
        ingestion=IngestionConfig(
            source=str(ingest.get("source", "mock")),
            limit=int(ingest.get("limit", 5)),
            research_field=str(ingest.get("research_field", "nlp")),
            paper_type=str(ingest.get("paper_type", "recent")),
            search_query=ingest.get("search_query"),
        ),
        storage=StorageConfig(
            db_path=str(storage.get("db_path", "data/paperweb.db")),
            usage_db_path=str(storage.get("usage_db_path", "data/llm_usage.sqlite")),
        ),
    )


def get_llm_role_config(role: str) -> LLMRoleConfig:
    if role not in VALID_LLM_ROLES:
        raise ValueError(f"Unknown LLM role: {role}. Valid roles: {', '.join(VALID_LLM_ROLES)}")
    return load_config().llm.roles[role]

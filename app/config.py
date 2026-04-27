"""Application configuration loaded from TOML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib


@dataclass(frozen=True)
class RoleConfig:
    provider: str = "mock"
    model: str = "mock-model"


@dataclass(frozen=True)
class LLMConfig:
    router: RoleConfig = RoleConfig()
    extractor: RoleConfig = RoleConfig()
    generator: RoleConfig = RoleConfig()
    openai_api_key: str | None = None


@dataclass(frozen=True)
class IngestionConfig:
    source: str = "mock"
    limit: int = 5
    research_field: str = "nlp"
    paper_type: str = "recent"
    search_query: str | None = None


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig = LLMConfig()
    ingestion: IngestionConfig = IngestionConfig()


def load_config(path: str | None = None) -> AppConfig:
    config_path = Path(path or os.getenv("PAPERWEB_CONFIG", "config/paperweb.toml"))
    if not config_path.exists():
        return AppConfig()

    data = tomllib.loads(config_path.read_text())
    llm_data = data.get("llm", {})

    def _role(name: str, default_model: str) -> RoleConfig:
        role_data = llm_data.get(name, {})
        return RoleConfig(
            provider=str(role_data.get("provider", "mock")).lower(),
            model=str(role_data.get("model", default_model)),
        )

    llm = LLMConfig(
        router=_role("router", "gpt-4.1-mini"),
        extractor=_role("extractor", "gpt-4.1-mini"),
        generator=_role("generator", "gpt-4.1-mini"),
        openai_api_key=llm_data.get("openai_api_key"),
    )

    ingest_data = data.get("ingestion", {})
    ingestion = IngestionConfig(
        source=str(ingest_data.get("source", "mock")),
        limit=int(ingest_data.get("limit", 5)),
        research_field=str(ingest_data.get("research_field", "nlp")),
        paper_type=str(ingest_data.get("paper_type", "recent")),
        search_query=ingest_data.get("search_query"),
    )

    return AppConfig(llm=llm, ingestion=ingestion)

from __future__ import annotations

from dataclasses import dataclass

from app.config import AppConfig, get_llm_role_config


@dataclass(frozen=True)
class AgentModeConfig:
    enabled: bool = True
    model_role: str = "generator"
    max_tool_calls: int = 8


@dataclass(frozen=True)
class AgentsConfig:
    enabled: bool = False
    trace_enabled: bool = True
    default_model_role: str = "generator"
    max_tool_calls: int = 8
    max_run_cost_usd: float = 1.0
    research: AgentModeConfig = AgentModeConfig(enabled=True, model_role="generator", max_tool_calls=8)
    evidence: AgentModeConfig = AgentModeConfig(enabled=True, model_role="extractor", max_tool_calls=6)
    report: AgentModeConfig = AgentModeConfig(enabled=True, model_role="generator", max_tool_calls=5)


def parse_agents_config(cfg: AppConfig, raw: dict) -> AgentsConfig:
    agents = raw.get("agents", {})

    def _mode(name: str, defaults: AgentModeConfig) -> AgentModeConfig:
        d = (agents.get(name, {}) if isinstance(agents.get(name, {}), dict) else {})
        return AgentModeConfig(
            enabled=bool(d.get("enabled", defaults.enabled)),
            model_role=str(d.get("model_role", defaults.model_role)),
            max_tool_calls=int(d.get("max_tool_calls", defaults.max_tool_calls)),
        )

    out = AgentsConfig(
        enabled=bool(agents.get("enabled", False)),
        trace_enabled=bool(agents.get("trace_enabled", True)),
        default_model_role=str(agents.get("default_model_role", "generator")),
        max_tool_calls=int(agents.get("max_tool_calls", 8)),
        max_run_cost_usd=float(agents.get("max_run_cost_usd", 1.0)),
        research=_mode("research", AgentModeConfig(enabled=True, model_role="generator", max_tool_calls=8)),
        evidence=_mode("evidence", AgentModeConfig(enabled=True, model_role="extractor", max_tool_calls=6)),
        report=_mode("report", AgentModeConfig(enabled=True, model_role="generator", max_tool_calls=5)),
    )
    _ = get_llm_role_config(out.default_model_role)
    return out

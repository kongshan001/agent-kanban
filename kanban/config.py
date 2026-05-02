"""配置管理 (kanban.config.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

from .models import AgentConfig

CONFIG_FILE = "kanban.config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "project": "",
    "main_branch": "main",
    "agents": {
        "default": {
            "type": "claude-code",
            "model": "claude-sonnet-4-20250514",
            "capabilities": ["develop", "test", "review"],
        },
    },
    "evaluation": {
        "score_threshold": 9.0,
        "roles": ["tech_lead", "qa", "product", "design"],
    },
    "self_improve": {
        "max_iterations": 5,
    },
}


class Config:
    """配置管理器."""

    def __init__(self, project_dir: str | Path = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.config_path = self.project_dir / CONFIG_FILE
        self._data: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path) as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}
        return self._data

    def save(self, data: dict[str, Any]) -> None:
        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        self._data = data

    def init(self) -> dict[str, Any]:
        """初始化默认配置."""
        cfg = {**DEFAULT_CONFIG, "project": self.project_dir.name}
        self.save(cfg)
        return cfg

    @property
    def data(self) -> dict[str, Any]:
        if not self._data:
            self.load()
        return self._data

    def get_agents(self) -> dict[str, AgentConfig]:
        agents = {}
        for name, cfg in self.data.get("agents", {}).items():
            agents[name] = AgentConfig(name=name, **cfg)
        return agents

    def get_score_threshold(self) -> float:
        return self.data.get("evaluation", {}).get("score_threshold", 9.0)

    def get_max_iterations(self) -> int:
        return self.data.get("self_improve", {}).get("max_iterations", 5)

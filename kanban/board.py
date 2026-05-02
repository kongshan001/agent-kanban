"""看板核心: 任务CRUD, 状态机, JSON持久化."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import BoardData, Task, TaskStatus, VALID_TRANSITIONS

BOARD_FILE = "kanban-board.json"


class BoardError(Exception):
    """看板操作错误."""


class Board:
    """看板管理器."""

    def __init__(self, project_dir: str | Path = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.board_path = self.project_dir / BOARD_FILE
        self._data: Optional[BoardData] = None

    @property
    def data(self) -> BoardData:
        if self._data is None:
            self._data = self._load()
        return self._data

    def _load(self) -> BoardData:
        if not self.board_path.exists():
            raise BoardError(f"看板未初始化: {self.board_path} 不存在。请先运行 kanban init")
        with open(self.board_path) as f:
            return BoardData.model_validate_json(f.read())

    def save(self) -> None:
        with open(self.board_path, "w") as f:
            f.write(self.data.model_dump_json(indent=2))

    def init(self, project: str = "", main_branch: str = "main") -> BoardData:
        """初始化看板."""
        if self.board_path.exists():
            raise BoardError(f"看板已存在: {self.board_path}")
        self._data = BoardData(
            project=project or self.project_dir.name,
            repo_path=str(self.project_dir),
            main_branch=main_branch,
        )
        self.save()
        return self.data

    # ── Task CRUD ──

    def create_task(self, title: str, description: str = "", assignee: str = "") -> Task:
        """创建任务, 自动生成 TK-NNN ID."""
        existing = len(self.data.tasks)
        task_id = f"TK-{existing + 1:03d}"
        while task_id in self.data.tasks:
            num = int(task_id.split("-")[1]) + 1
            task_id = f"TK-{num:03d}"
        task = Task(id=task_id, title=title, description=description, assignee=assignee)
        self.data.tasks[task_id] = task
        self.save()
        return task

    def get_task(self, task_id: str) -> Task:
        if task_id not in self.data.tasks:
            raise BoardError(f"任务不存在: {task_id}")
        return self.data.tasks[task_id]

    def update_task(self, task_id: str, **kwargs: object) -> Task:
        task = self.get_task(task_id)
        for k, v in kwargs.items():
            if hasattr(task, k):
                setattr(task, k, v)
        from datetime import datetime
        task.updated_at = datetime.now()
        self.save()
        return task

    def list_tasks(self) -> list[Task]:
        return list(self.data.tasks.values())

    # ── 状态机 ──

    def transition(self, task_id: str, new_status: TaskStatus) -> Task:
        """执行状态转换 (强约束)."""
        task = self.get_task(task_id)
        current = task.status
        if new_status not in VALID_TRANSITIONS.get(current, []):
            allowed = [s.value for s in VALID_TRANSITIONS.get(current, [])]
            raise BoardError(
                f"非法状态转换: {current.value} → {new_status.value}\n"
                f"允许的转换: {allowed}"
            )
        task.status = new_status
        from .models import STATUS_PHASE_MAP
        task.phase = STATUS_PHASE_MAP.get(new_status, task.phase)
        from datetime import datetime
        task.updated_at = datetime.now()
        self.save()
        return task

    def assign_task(self, task_id: str, assignee: str) -> Task:
        return self.update_task(task_id, assignee=assignee)

    # ── Agent ──

    def register_agent(self, agent: "AgentConfig") -> None:
        from .models import AgentConfig
        assert isinstance(agent, AgentConfig)
        self.data.agents[agent.name] = agent
        self.save()

    def get_agent(self, name: str) -> "AgentConfig":
        if name not in self.data.agents:
            raise BoardError(f"Agent 不存在: {name}")
        return self.data.agents[name]

    def list_agents(self) -> list["AgentConfig"]:
        return list(self.data.agents.values())

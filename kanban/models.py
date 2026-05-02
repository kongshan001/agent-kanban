"""数据模型定义."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举."""
    DRAFT = "DRAFT"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    EVALUATING = "EVALUATING"
    SELF_IMPROVE = "SELF_IMPROVE"
    USER_REVIEW = "USER_REVIEW"
    MERGED = "MERGED"
    ARCHIVED = "ARCHIVED"


class Phase(str, Enum):
    """阶段枚举."""
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    EVALUATE = "EVALUATE"
    IMPROVE = "IMPROVE"
    USER_REVIEW = "USER_REVIEW"
    ARCHIVE = "ARCHIVE"


# 状态机转换表
VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.DRAFT: [TaskStatus.PLANNING],
    TaskStatus.PLANNING: [TaskStatus.EXECUTING, TaskStatus.DRAFT],
    TaskStatus.EXECUTING: [TaskStatus.EVALUATING, TaskStatus.PLANNING],
    TaskStatus.EVALUATING: [TaskStatus.SELF_IMPROVE, TaskStatus.USER_REVIEW, TaskStatus.PLANNING],
    TaskStatus.SELF_IMPROVE: [TaskStatus.EXECUTING],
    TaskStatus.USER_REVIEW: [TaskStatus.ARCHIVED, TaskStatus.PLANNING],
    TaskStatus.MERGED: [TaskStatus.ARCHIVED],
    TaskStatus.ARCHIVED: [],
}

# 状态 → 阶段映射
STATUS_PHASE_MAP: dict[TaskStatus, Phase] = {
    TaskStatus.DRAFT: Phase.PLAN,
    TaskStatus.PLANNING: Phase.PLAN,
    TaskStatus.EXECUTING: Phase.EXECUTE,
    TaskStatus.EVALUATING: Phase.EVALUATE,
    TaskStatus.SELF_IMPROVE: Phase.IMPROVE,
    TaskStatus.USER_REVIEW: Phase.USER_REVIEW,
    TaskStatus.MERGED: Phase.ARCHIVE,
    TaskStatus.ARCHIVED: Phase.ARCHIVE,
}


class EvaluationResult(BaseModel):
    """评估结果."""
    role: str
    score: float = Field(ge=1.0, le=10.0)
    passed: bool = False
    report_path: str = ""
    feedback: str = ""

    def model_post_init(self, __context: Any) -> None:
        if self.passed is False and self.score >= 9.0:
            self.passed = True


class AgentConfig(BaseModel):
    """Agent 配置."""
    name: str
    type: str  # claude-code, opencode, openclaw, hermes
    capabilities: list[str] = []
    model: str = ""


class Task(BaseModel):
    """任务模型."""
    id: str = ""  # TK-NNN
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.DRAFT
    assignee: str = ""
    worktree_path: str = ""
    branch: str = ""
    phase: Phase = Phase.PLAN
    iteration: int = 1
    scores: dict[str, float] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    documents: list[str] = []
    evaluation_results: list[EvaluationResult] = []
    skip_checks: list[str] = []  # 跳过的检查项: "test", "review" 等


class BoardData(BaseModel):
    """看板数据存储."""
    version: int = 1
    project: str = ""
    repo_path: str = ""
    main_branch: str = "main"
    tasks: dict[str, Task] = {}
    agents: dict[str, AgentConfig] = {}

"""Agent 调度器."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional

from .models import AgentConfig, Phase, Task
from .config import Config


class RunnerError(Exception):
    """Agent 运行错误."""


# 各阶段的 prompt 模板
PHASE_PROMPTS: dict[Phase, str] = {
    Phase.PLAN: (
        "你是一个高级架构师。请为以下任务创建:\n"
        "1. docs/requirements.md - 详细需求文档\n"
        "2. docs/task-breakdown.md - 任务拆解文档\n\n"
        "任务: {title}\n描述: {description}\n"
    ),
    Phase.EXECUTE: (
        "你是一个高级开发工程师。请根据以下规划文档实现代码:\n"
        "任务: {title}\n描述: {description}\n迭代轮次: {iteration}\n"
        "要求:\n"
        "1. 实现业务代码\n"
        "2. 编写单元测试和集成测试\n"
        "3. 生成 docs/execute-summary-{iteration}.md 执行复盘\n"
    ),
    Phase.EVALUATE: (
        "你是评估专家。请对以下任务的产出进行全面评估:\n"
        "任务: {title}\n迭代轮次: {iteration}\n"
    ),
    Phase.IMPROVE: (
        "根据评估反馈改进代码。任务: {title}\n"
        "迭代轮次: {iteration}\n"
        "评估反馈: {feedback}\n"
    ),
}


class AgentRunner:
    """Agent 调度器, 根据 agent type 分发执行."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def run(self, task: Task, agent: AgentConfig) -> str:
        """根据 agent 类型分发执行."""
        prompt = self._build_prompt(task)
        if agent.type == "claude-code":
            return self._run_claude_code(task, agent, prompt)
        elif agent.type == "opencode":
            return self._run_opencode(task, agent, prompt)
        elif agent.type == "openclaw":
            return self._run_openclaw(task, agent, prompt)
        else:
            raise RunnerError(f"不支持的 agent 类型: {agent.type}")

    def _build_prompt(self, task: Task) -> str:
        template = PHASE_PROMPTS.get(task.phase, "")
        feedback = ""
        if task.evaluation_results:
            feedback = "\n".join(
                f"- {r.role}: {r.feedback}" for r in task.evaluation_results
            )
        return template.format(
            title=task.title,
            description=task.description,
            iteration=task.iteration,
            feedback=feedback,
        )

    def _run_claude_code(self, task: Task, agent: AgentConfig, prompt: str) -> str:
        """在 worktree 中执行 claude CLI."""
        wt = task.worktree_path
        if not wt:
            raise RunnerError(f"任务 {task.id} 没有 worktree")
        cmd = ["claude", "--print", prompt]
        return self._exec_in_worktree(wt, cmd)

    def _run_opencode(self, task: Task, agent: AgentConfig, prompt: str) -> str:
        """在 worktree 中执行 opencode."""
        wt = task.worktree_path
        if not wt:
            raise RunnerError(f"任务 {task.id} 没有 worktree")
        cmd = ["opencode", "--prompt", prompt]
        return self._exec_in_worktree(wt, cmd)

    def _run_openclaw(self, task: Task, agent: AgentConfig, prompt: str) -> str:
        """通过 openclaw sessions spawn 执行."""
        cmd = ["openclaw", "sessions", "spawn", "--task", prompt]
        return self._exec(cmd)

    def _exec_in_worktree(self, worktree: str, cmd: list[str]) -> str:
        result = subprocess.run(
            cmd, cwd=worktree, capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise RunnerError(f"命令执行失败: {result.stderr[:500]}")
        return result.stdout

    def _exec(self, cmd: list[str]) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RunnerError(f"命令执行失败: {result.stderr[:500]}")
        return result.stdout

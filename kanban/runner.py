"""Agent 调度器: 真正执行 claude/opencode CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from .models import AgentConfig, Phase, Task
from .config import Config


class RunnerError(Exception):
    """Agent 运行错误."""


# 各阶段 prompt 模板
PHASE_PROMPTS: dict[Phase, str] = {
    Phase.PLAN: (
        "你是一个高级架构师。请在当前目录下完成以下工作：\n\n"
        "1. 创建 docs/requirements.md - 详细需求文档\n"
        "2. 创建 docs/task-breakdown.md - 任务拆解文档，包含子任务列表和状态\n\n"
        "## 任务信息\n"
        "- 标题: {title}\n"
        "- 描述: {description}\n\n"
        "## 要求\n"
        "- 需求文档要具体到可执行的粒度\n"
        "- 任务拆解要包含每个子任务的验收标准\n"
        "- 文档使用中文\n"
    ),
    Phase.EXECUTE: (
        "你是一个高级开发工程师。请根据规划文档实现代码。\n\n"
        "## 任务信息\n"
        "- 标题: {title}\n"
        "- 描述: {description}\n"
        "- 迭代轮次: {iteration}\n\n"
        "## 你需要做的\n"
        "1. 阅读 docs/requirements.md 和 docs/task-breakdown.md 了解需求\n"
        "2. 实现业务代码\n"
        "3. 编写单元测试和集成测试\n"
        "4. 更新 docs/task-breakdown.md 中的子任务状态\n"
        "5. 创建 docs/execute-summary-{iteration}.md 执行复盘，包含：\n"
        "   - 完成内容\n"
        "   - 踩坑经验\n"
        "   - 文件清单\n\n"
        "{feedback_section}"
    ),
    Phase.IMPROVE: (
        "你是一个高级开发工程师。根据评估反馈改进代码。\n\n"
        "## 任务信息\n"
        "- 标题: {title}\n"
        "- 迭代轮次: {iteration}\n\n"
        "## 评估反馈\n"
        "{feedback}\n\n"
        "请根据反馈改进代码，并更新 docs/execute-summary-{iteration}.md"
    ),
}


class AgentRunner:
    """Agent 调度器, 根据 agent type 分发执行."""

    def __init__(self, config: Optional[Config] = None) -> None:
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

    def run_phase(self, task: Task, phase: Phase, agent: AgentConfig) -> str:
        """直接执行指定阶段 (不依赖 task.phase)."""
        prompt = self._build_prompt_for_phase(task, phase)
        if agent.type == "claude-code":
            return self._run_claude_code(task, agent, prompt)
        elif agent.type == "opencode":
            return self._run_opencode(task, agent, prompt)
        else:
            raise RunnerError(f"不支持的 agent 类型: {agent.type}")

    def _build_prompt(self, task: Task) -> str:
        return self._build_prompt_for_phase(task, task.phase)

    def _build_prompt_for_phase(self, task: Task, phase: Phase) -> str:
        template = PHASE_PROMPTS.get(phase, "")
        feedback = ""
        feedback_section = ""
        if task.evaluation_results:
            feedback = "\n".join(
                f"- {r.role}: {r.feedback}" for r in task.evaluation_results
            )
            feedback_section = f"## 上一轮评估反馈\n{feedback}\n\n请重点针对以上反馈改进。"

        return template.format(
            title=task.title,
            description=task.description,
            iteration=task.iteration,
            feedback=feedback,
            feedback_section=feedback_section,
        )

    def _run_claude_code(self, task: Task, agent: AgentConfig, prompt: str) -> str:
        """在 worktree 中执行 claude CLI."""
        wt = task.worktree_path
        if not wt:
            raise RunnerError(f"任务 {task.id} 没有 worktree")

        # claude -p 是非交互模式，适合自动化
        cmd = ["claude", "-p", prompt, "--max-turns", "30"]
        return self._exec_in_worktree(wt, cmd, timeout=600)

    def _run_opencode(self, task: Task, agent: AgentConfig, prompt: str) -> str:
        """在 worktree 中执行 opencode."""
        wt = task.worktree_path
        if not wt:
            raise RunnerError(f"任务 {task.id} 没有 worktree")

        cmd = ["opencode", "run", prompt]
        return self._exec_in_worktree(wt, cmd, timeout=600)

    def _run_openclaw(self, task: Task, agent: AgentConfig, prompt: str) -> str:
        """通过 hermes CLI 执行 (openclaw 暂用 hermes 替代)."""
        wt = task.worktree_path
        hermes_bin = "/root/.hermes/hermes-agent/venv/bin/python"
        cmd = [hermes_bin, "-m", "hermes_cli.main", "chat", "-q", prompt, "--yolo"]
        return self._exec_in_worktree(wt, cmd, timeout=300) if wt else self._exec(cmd, timeout=300)

    def _exec_in_worktree(self, worktree: str, cmd: list[str], timeout: int = 600) -> str:
        """在 worktree 目录执行命令."""
        wt_path = Path(worktree)
        if not wt_path.exists():
            raise RunnerError(f"Worktree 不存在: {worktree}")

        result = subprocess.run(
            cmd, cwd=worktree, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            error_msg = result.stderr[:1000] if result.stderr else result.stdout[:1000]
            raise RunnerError(f"命令执行失败 (exit {result.returncode}): {error_msg}")
        return result.stdout

    def _exec(self, cmd: list[str], timeout: int = 600) -> str:
        """执行命令."""
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RunnerError(f"命令执行失败: {result.stderr[:500]}")
        return result.stdout

    @staticmethod
    def detect_available_agents() -> list[dict[str, str]]:
        """检测本地可用的 agent CLI."""
        agents = []
        checks = [
            ("claude-code", "claude"),
            ("opencode", "opencode"),
            ("hermes", "/root/.hermes/hermes-agent/venv/bin/python"),
        ]
        for name, cmd in checks:
            try:
                if cmd.startswith("/"):
                    test_cmd = [cmd, "-m", "hermes_cli.main", "--version"]
                else:
                    test_cmd = ["which", cmd]
                result = subprocess.run(
                    test_cmd, capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    agents.append({"name": name, "cli": cmd})
            except Exception:
                pass
        return agents

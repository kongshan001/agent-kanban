"""报告生成器."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import Task, TaskStatus
from .templates import TemplateRenderer


class Reporter:
    """报告生成器."""

    def __init__(self) -> None:
        self.renderer = TemplateRenderer()

    def generate_task_report(self, task: Task, output_dir: str | Path | None = None) -> Path:
        """生成任务报告."""
        out = Path(output_dir) if output_dir else Path(task.worktree_path or ".") / "docs"
        out.mkdir(parents=True, exist_ok=True)

        status_emoji = {
            TaskStatus.DRAFT: "📝",
            TaskStatus.PLANNING: "📋",
            TaskStatus.EXECUTING: "⚙️",
            TaskStatus.EVALUATING: "🔍",
            TaskStatus.SELF_IMPROVE: "🔄",
            TaskStatus.USER_REVIEW: "👁️",
            TaskStatus.MERGED: "✅",
            TaskStatus.ARCHIVED: "📦",
        }

        report_path = out / f"{task.id}-report.md"
        content = self._build_report(task, status_emoji)
        report_path.write_text(content)
        return report_path

    def generate_board_report(self, tasks: list[Task]) -> str:
        """生成看板总览报告."""
        lines = ["# 看板总览\n"]
        for status in TaskStatus:
            status_tasks = [t for t in tasks if t.status == status]
            if status_tasks:
                lines.append(f"\n## {status.value} ({len(status_tasks)})\n")
                for t in status_tasks:
                    lines.append(f"- **{t.id}**: {t.title} (迭代: {t.iteration})")
        return "\n".join(lines)

    def _build_report(self, task: Task, emoji_map: dict) -> str:
        scores_str = ", ".join(f"{k}: {v}" for k, v in task.scores.items()) if task.scores else "无"
        evals = "\n".join(
            f"- **{r.role}**: {r.score}/10 {'✅' if r.passed else '❌'} - {r.feedback}"
            for r in task.evaluation_results
        ) or "无评估结果"

        return f"""# 任务报告: {task.id}

**状态**: {emoji_map.get(task.status, '')} {task.status.value}
**阶段**: {task.phase.value}
**标题**: {task.title}
**描述**: {task.description or '无'}
**负责人**: {task.assignee or '未分配'}
**分支**: {task.branch or '无'}
**迭代轮次**: {task.iteration}/5
**创建时间**: {task.created_at.strftime('%Y-%m-%d %H:%M')}
**更新时间**: {task.updated_at.strftime('%Y-%m-%d %H:%M')}

## 评分
{scores_str}

## 评估结果
{evals}

## 产出文档
{chr(10).join(f'- {d}' for d in task.documents) or '无'}
"""

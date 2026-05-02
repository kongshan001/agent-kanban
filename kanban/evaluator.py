"""评估引擎: 4个角色评估."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .models import EvaluationResult, Task
from .config import Config
from .templates import TemplateRenderer


EVALUATION_ROLES: dict[str, dict[str, str]] = {
    "tech_lead": {
        "name": "程序组长",
        "prompt": (
            "你是资深代码审核专家。请对以下任务的代码实现进行审核，评估:\n"
            "1. 代码质量和规范性\n2. 架构合理性\n3. 安全性\n4. 性能\n"
            "请给出 1-10 分评分和详细反馈。\n"
        ),
        "output": "code-review-{iteration}.md",
    },
    "qa": {
        "name": "QA工程师",
        "prompt": (
            "你是质量保障专家。请评估:\n"
            "1. 测试覆盖率\n2. 边界条件处理\n3. 错误处理\n4. 集成测试完整性\n"
            "请给出 1-10 分评分和详细反馈。\n"
        ),
        "output": "qa-report-{iteration}.md",
    },
    "product": {
        "name": "产品经理",
        "prompt": (
            "你是产品验收专家。请评估:\n"
            "1. 功能完整性\n2. 用户体验\n3. 需求匹配度\n4. 文档完整性\n"
            "请给出 1-10 分评分和详细反馈。\n"
        ),
        "output": "product-review-{iteration}.md",
    },
    "design": {
        "name": "美术/交互设计",
        "prompt": (
            "你是交互设计专家。请评估:\n"
            "1. UI/UX 设计质量\n2. 交互流畅性\n3. 视觉一致性\n4. 可访问性\n"
            "请给出 1-10 分评分和详细反馈。\n"
        ),
        "output": "design-review-{iteration}.md",
    },
}


class Evaluator:
    """评估引擎."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.renderer = TemplateRenderer()
        self.threshold = config.get_score_threshold()

    def evaluate(self, task: Task) -> list[EvaluationResult]:
        """对任务运行全部4个角色评估."""
        results: list[EvaluationResult] = []
        wt = Path(task.worktree_path) if task.worktree_path else Path(".")
        reviews_dir = wt / "docs" / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)

        for role_key, role_info in EVALUATION_ROLES.items():
            # 生成评估报告模板
            report_name = role_info["output"].format(iteration=task.iteration)
            report_path = reviews_dir / report_name

            # 使用模板渲染评估报告框架
            self.renderer.render_to_file(
                f"{role_key}_review.md.j2",
                str(report_path),
                task=task,
                role=role_info,
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )

            # 标记到任务文档
            if str(report_path) not in task.documents:
                task.documents.append(str(report_path))

            # 生成占位评估结果 (实际场景中由 agent 填写)
            result = EvaluationResult(
                role=role_key,
                score=1.0,  # 占位, 需 agent 填入实际评分
                report_path=str(report_path),
                feedback=f"评估报告已生成: {report_name}, 待填写评分",
            )
            results.append(result)

        task.evaluation_results = results
        return results

    def check_all_passed(self, task: Task) -> bool:
        """检查所有评估是否通过."""
        required = set(EVALUATION_ROLES.keys())
        for r in task.evaluation_results:
            if r.role in required and (r.score < self.threshold or not r.passed):
                return False
        return len(task.evaluation_results) >= len(required)

    def get_failing_roles(self, task: Task) -> list[str]:
        """获取未通过的角色列表."""
        required = set(EVALUATION_ROLES.keys())
        results_by_role = {r.role: r for r in task.evaluation_results}
        return [
            role for role in required
            if role not in results_by_role or results_by_role[role].score < self.threshold
        ]

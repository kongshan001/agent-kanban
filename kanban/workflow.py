"""流程守卫: 阶段转换前的强制检查."""

from __future__ import annotations

from pathlib import Path

from .models import Task, TaskStatus


class GuardError(Exception):
    """流程守卫检查未通过."""


class PhaseGuard:
    """阶段转换守卫, 每个转换前强制检查前置条件."""

    @staticmethod
    def check(task: Task, target_status: TaskStatus) -> list[str]:
        """检查从当前状态转换到目标状态的前置条件. 返回缺失项列表."""
        checker = {
            TaskStatus.EXECUTING: PhaseGuard._check_plan_complete,
            TaskStatus.EVALUATING: PhaseGuard._check_execute_complete,
            TaskStatus.SELF_IMPROVE: PhaseGuard._check_evaluate_results,
            TaskStatus.USER_REVIEW: PhaseGuard._check_evaluate_results,
            TaskStatus.ARCHIVED: PhaseGuard._check_user_review,
        }
        fn = checker.get(target_status)
        if fn:
            return fn(task)
        return []

    @staticmethod
    def enforce(task: Task, target_status: TaskStatus) -> None:
        """强制检查, 不通过则抛出异常."""
        errors = PhaseGuard.check(task, target_status)
        if errors:
            raise GuardError(
                "流程守卫检查未通过, 缺失以下条件:\n"
                + "\n".join(f"  ❌ {e}" for e in errors)
            )

    @staticmethod
    def _check_plan_complete(task: Task) -> list[str]:
        """Plan → Execute: 检查规划阶段产出."""
        errors: list[str] = []
        wt = task.worktree_path or ""
        if not wt:
            errors.append("Git worktree 未创建 (worktree_path 为空)")
            return errors
        base = Path(wt)
        docs = base / "docs"
        if not (docs / "requirements.md").exists():
            errors.append("缺少需求文档: docs/requirements.md")
        if not (docs / "task-breakdown.md").exists():
            errors.append("缺少任务拆解文档: docs/task-breakdown.md")
        if not base.exists():
            errors.append(f"Worktree 目录不存在: {wt}")
        return errors

    @staticmethod
    def _check_execute_complete(task: Task) -> list[str]:
        """Execute → Evaluate: 检查执行阶段产出."""
        errors: list[str] = []
        wt = task.worktree_path or ""
        if not wt:
            errors.append("Worktree 未设置")
            return errors
        base = Path(wt)
        docs = base / "docs"
        summary = docs / f"execute-summary-{task.iteration}.md"
        if not summary.exists():
            errors.append(f"缺少执行复盘: docs/execute-summary-{task.iteration}.md")
        # 检查是否有测试文件（除非跳过）
        if "test" not in task.skip_checks:
            has_tests = False
            for pattern in ["**/test_*.py", "**/*_test.py", "**/tests/**"]:
                if list(base.glob(pattern)):
                    has_tests = True
                    break
            if not has_tests:
                errors.append("缺少测试代码文件 (可通过 skip_checks=['test'] 跳过)")
        return errors

    @staticmethod
    def _check_evaluate_results(task: Task) -> list[str]:
        """Evaluate → SelfImprove/UserReview: 检查评估结果."""
        errors: list[str] = []
        required_roles = {"tech_lead", "qa", "product", "design"}
        results_by_role = {r.role: r for r in task.evaluation_results}
        for role in required_roles:
            if role not in results_by_role:
                errors.append(f"缺少评估报告: {role}")
        if not errors:
            low_scores = [
                f"{r.role} (评分: {r.score})"
                for r in task.evaluation_results
                if r.role in required_roles and r.score < 9.0
            ]
            if low_scores:
                errors.append(f"以下角色评分未达标 (阈值 >= 9.0): {', '.join(low_scores)}")
        return errors

    @staticmethod
    def _check_user_review(task: Task) -> list[str]:
        """UserReview → Archive: 用户审核检查."""
        if task.status != TaskStatus.USER_REVIEW:
            return [f"当前状态不是 USER_REVIEW, 而是 {task.status.value}"]
        return []

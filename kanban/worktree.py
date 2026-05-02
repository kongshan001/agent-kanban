"""Git worktree 管理."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from .models import Task


class WorktreeError(Exception):
    """Worktree 操作错误."""


class WorktreeManager:
    """Git worktree 管理器."""

    def __init__(self, repo_path: str | Path, main_branch: str = "main") -> None:
        self.repo_path = Path(repo_path).resolve()
        self.main_branch = main_branch
        self.worktrees_dir = self.repo_path / ".worktrees"

    def _git(self, *args: str, cwd: Optional[Path] = None) -> str:
        cmd = ["git", "-C", str(cwd or self.repo_path)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise WorktreeError(f"git 错误: {result.stderr.strip()}")
        return result.stdout.strip()

    def create_worktree(self, task: Task) -> Task:
        """为任务创建 git worktree."""
        branch = f"task/{task.id}"
        wt_path = self.worktrees_dir / task.id
        if wt_path.exists():
            raise WorktreeError(f"Worktree 已存在: {wt_path}")
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        self._git("worktree", "add", "-b", branch, str(wt_path), self.main_branch)
        task.worktree_path = str(wt_path)
        task.branch = branch
        return task

    def merge_worktree(self, task: Task) -> str:
        """合并 worktree 分支到主干 (fast-forward 优先)."""
        if not task.branch:
            raise WorktreeError(f"任务 {task.id} 没有关联分支")
        # 先在 worktree 里提交所有变更
        wt = Path(task.worktree_path) if task.worktree_path else None
        if wt and wt.exists():
            self._git("add", "-A", cwd=wt)
            try:
                self._git("commit", "-m", f"feat({task.id}): {task.title}", cwd=wt)
            except WorktreeError:
                pass  # nothing to commit
        # 切回主分支合并
        self._git("checkout", self.main_branch)
        try:
            self._git("merge", "--ff-only", task.branch)
        except WorktreeError:
            self._git("merge", task.branch, "-m", f"merge: {task.branch}")
        return f"已合并 {task.branch} → {self.main_branch}"

    def remove_worktree(self, task: Task) -> str:
        """清理 worktree."""
        if task.worktree_path and Path(task.worktree_path).exists():
            self._git("worktree", "remove", task.worktree_path, "--force")
        if task.branch:
            try:
                self._git("branch", "-d", task.branch)
            except WorktreeError:
                pass
        task.worktree_path = ""
        task.branch = ""
        return f"已清理 worktree: {task.id}"

    def has_changes(self, task: Task) -> bool:
        """检查 worktree 中是否有代码变更."""
        wt = task.worktree_path
        if not wt:
            return False
        try:
            result = subprocess.run(
                ["git", "-C", wt, "status", "--porcelain"],
                capture_output=True, text=True,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

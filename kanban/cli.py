"""CLI 入口 (typer)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .board import Board, BoardError
from .config import Config
from .evaluator import Evaluator
from .models import AgentConfig, TaskStatus
from .reporter import Reporter
from .runner import AgentRunner
from .workflow import GuardError, PhaseGuard
from .worktree import WorktreeManager, WorktreeError

app = typer.Typer(name="kanban", help="Agent Kanban - 多Agent任务编排看板系统")
task_app = typer.Typer(name="task", help="任务管理")
git_app = typer.Typer(name="git", help="Git 操作")
agent_app = typer.Typer(name="agent", help="Agent 调度")

app.add_typer(task_app, name="task")
app.add_typer(git_app, name="git")
app.add_typer(agent_app, name="agent")

console = Console()


def _board() -> Board:
    return Board()


def _fail(msg: str) -> None:
    console.print(f"[red]错误:[/red] {msg}")
    raise typer.Exit(1)


# ── 看板管理 ──

@app.command()
def init(
    project: str = typer.Option("", help="项目名称"),
    main_branch: str = typer.Option("", help="主分支名 (默认自动检测当前分支)"),
) -> None:
    """初始化看板."""
    if not main_branch:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True,
        )
        main_branch = result.stdout.strip() or "main"
    board = _board()
    try:
        data = board.init(project=project, main_branch=main_branch)
        console.print(f"[green]✅ 看板已初始化[/green]: {board.board_path}")
    except BoardError as e:
        _fail(str(e))

    # 同时初始化配置
    cfg = Config()
    cfg.init()
    console.print("[green]✅ 配置已生成[/green]: kanban.config.yaml")


@app.command(name="status")
def status() -> None:
    """查看所有任务状态."""
    board = _board()
    try:
        data = board.data
    except BoardError as e:
        _fail(str(e))

    if not data.tasks:
        console.print("[yellow]暂无任务[/yellow]")
        return

    table = Table(title="看板状态")
    table.add_column("ID", style="cyan")
    table.add_column("标题")
    table.add_column("状态", style="green")
    table.add_column("阶段")
    table.add_column("负责人")
    table.add_column("迭代")

    for t in data.tasks.values():
        table.add_row(t.id, t.title, t.status.value, t.phase.value, t.assignee or "-", str(t.iteration))

    console.print(table)


@app.command(name="board")
def board_view() -> None:
    """看板视图."""
    board = _board()
    try:
        data = board.data
    except BoardError as e:
        _fail(str(e))

    reporter = Reporter()
    report = reporter.generate_board_report(list(data.tasks.values()))
    console.print(report)


# ── 任务管理 ──

@task_app.command(name="create")
def task_create(
    title: str = typer.Option(..., "--title", "-t", help="任务标题"),
    desc: str = typer.Option("", "--desc", "-d", help="任务描述"),
    assignee: str = typer.Option("", "--assignee", "-a", help="负责人"),
    skip_checks: str = typer.Option("", "--skip-checks", help="跳过的检查项，逗号分隔 (test,review)"),
) -> None:
    """创建任务."""
    board = _board()
    try:
        task = board.create_task(title=title, description=desc, assignee=assignee)
        if skip_checks:
            task.skip_checks = [s.strip() for s in skip_checks.split(",")]
            board.save()
        console.print(f"[green]✅ 任务已创建[/green]: {task.id} - {task.title}")
    except BoardError as e:
        _fail(str(e))


@task_app.command(name="show")
def task_show(task_id: str = typer.Argument(help="任务ID")) -> None:
    """查看任务详情."""
    board = _board()
    try:
        task = board.get_task(task_id)
    except BoardError as e:
        _fail(str(e))

    console.print(f"[cyan]任务 {task.id}[/cyan]")
    console.print(f"  标题: {task.title}")
    console.print(f"  描述: {task.description or '无'}")
    console.print(f"  状态: {task.status.value}")
    console.print(f"  阶段: {task.phase.value}")
    console.print(f"  负责人: {task.assignee or '未分配'}")
    console.print(f"  分支: {task.branch or '无'}")
    console.print(f"  Worktree: {task.worktree_path or '无'}")
    console.print(f"  迭代: {task.iteration}/5")
    if task.scores:
        console.print(f"  评分: {task.scores}")
    if task.documents:
        console.print("  文档:")
        for d in task.documents:
            console.print(f"    - {d}")
    if task.evaluation_results:
        console.print("  评估:")
        for r in task.evaluation_results:
            status = "✅" if r.passed else "❌"
            console.print(f"    {status} {r.role}: {r.score}/10 - {r.feedback}")


@task_app.command(name="assign")
def task_assign(
    task_id: str = typer.Argument(help="任务ID"),
    assignee: str = typer.Argument(help="Agent名称"),
) -> None:
    """分配任务."""
    board = _board()
    try:
        task = board.assign_task(task_id, assignee)
        console.print(f"[green]✅ 已分配[/green] {task.id} → {assignee}")
    except BoardError as e:
        _fail(str(e))


@task_app.command(name="start")
def task_start(task_id: str = typer.Argument(help="任务ID")) -> None:
    """启动任务: DRAFT → PLANNING, 创建 worktree."""
    board = _board()
    try:
        task = board.get_task(task_id)
        if task.status != TaskStatus.DRAFT:
            _fail(f"任务状态为 {task.status.value}, 只有 DRAFT 状态可以启动")
        # 创建 worktree
        wm = WorktreeManager(board.data.repo_path, board.data.main_branch)
        wm.create_worktree(task)
        board.transition(task_id, TaskStatus.PLANNING)
        console.print(f"[green]✅ 任务已启动[/green]: {task.id} (worktree: {task.worktree_path})")
    except (BoardError, WorktreeError) as e:
        _fail(str(e))


@task_app.command(name="plan-done")
def task_plan_done(task_id: str = typer.Argument(help="任务ID")) -> None:
    """规划完成: PLANNING → EXECUTING (校验规划文档)."""
    board = _board()
    try:
        task = board.get_task(task_id)
        PhaseGuard.enforce(task, TaskStatus.EXECUTING)
        board.transition(task_id, TaskStatus.EXECUTING)
        console.print(f"[green]✅ 规划完成, 进入执行阶段[/green]: {task.id}")
    except (BoardError, GuardError) as e:
        _fail(str(e))


@task_app.command(name="exec-done")
def task_exec_done(task_id: str = typer.Argument(help="任务ID")) -> None:
    """执行完成: EXECUTING → EVALUATING (校验执行产出)."""
    board = _board()
    try:
        task = board.get_task(task_id)
        PhaseGuard.enforce(task, TaskStatus.EVALUATING)
        board.transition(task_id, TaskStatus.EVALUATING)
        console.print(f"[green]✅ 执行完成, 进入评估阶段[/green]: {task.id}")
    except (BoardError, GuardError) as e:
        _fail(str(e))


@task_app.command(name="evaluate")
def task_evaluate(
    task_id: str = typer.Argument(help="任务ID"),
    single: bool = typer.Option(False, "--single", "-s", help="使用单次综合评估（1次LLM调用代替4次）"),
) -> None:
    """运行评估流程."""
    board = _board()
    try:
        task = board.get_task(task_id)
        if task.status != TaskStatus.EVALUATING:
            _fail(f"任务状态为 {task.status.value}, 只有 EVALUATING 状态可以评估")
        config = Config()
        config.load()
        evaluator = Evaluator(config)

        if single:
            console.print("[cyan]使用单次综合评估模式[/cyan]")
            results = evaluator.evaluate_single(task)
        else:
            results = evaluator.evaluate(task)
        board.save()

        all_passed = evaluator.check_all_passed(task)
        if all_passed:
            board.transition(task_id, TaskStatus.USER_REVIEW)
            console.print(f"[green]✅ 评估全部通过, 进入用户审核[/green]: {task.id}")
        else:
            failing = [r.role for r in task.evaluation_results if r.score < 9.0]
            console.print(f"[yellow]⚠️ 部分评估未通过: {', '.join(failing)}[/yellow]")
            max_iter = config.get_max_iterations()
            if task.iteration < max_iter:
                task.iteration += 1
                board.transition(task_id, TaskStatus.SELF_IMPROVE)
                console.print(f"[yellow]进入自迭代 (第 {task.iteration} 轮)[/yellow]")
            else:
                board.transition(task_id, TaskStatus.USER_REVIEW)
                console.print(f"[red]已达迭代上限 ({max_iter}), 进入用户审核[/red]")
    except (BoardError, GuardError) as e:
        _fail(str(e))


@task_app.command(name="approve")
def task_approve(
    task_id: str = typer.Argument(help="任务ID"),
    merge: bool = typer.Option(True, "--merge/--no-merge", help="是否自动合并到主干"),
) -> None:
    """批准任务: USER_REVIEW → MERGED → ARCHIVED (自动合并)."""
    board = _board()
    try:
        task = board.get_task(task_id)
        if task.status != TaskStatus.USER_REVIEW:
            _fail(f"任务状态为 {task.status.value}, 只有 USER_REVIEW 状态可以批准")

        # 先合并到主干
        if merge and task.worktree_path:
            try:
                wm = WorktreeManager(board.data.repo_path, board.data.main_branch)
                merge_msg = wm.merge_worktree(task)
                console.print(f"[green]✅ {merge_msg}[/green]")
            except WorktreeError as e:
                console.print(f"[yellow]⚠️ 合并失败: {e}, 继续归档[/yellow]")

        board.transition(task_id, TaskStatus.MERGED)
        board.transition(task_id, TaskStatus.ARCHIVED)
        console.print(f"[green]✅ 任务已批准并归档[/green]: {task.id}")
    except BoardError as e:
        _fail(str(e))


@task_app.command(name="reject")
def task_reject(
    task_id: str = typer.Argument(help="任务ID"),
    feedback: str = typer.Option("", "--feedback", "-f", help="拒绝反馈"),
) -> None:
    """拒绝任务: USER_REVIEW → PLANNING (带反馈)."""
    board = _board()
    try:
        task = board.get_task(task_id)
        board.transition(task_id, TaskStatus.PLANNING)
        if feedback:
            console.print(f"[yellow]⚠️ 任务已拒绝, 回到规划阶段[/yellow]: {task.id}")
            console.print(f"[dim]反馈: {feedback}[/dim]")
        else:
            console.print(f"[yellow]⚠️ 任务已拒绝, 回到规划阶段[/yellow]: {task.id}")
    except BoardError as e:
        _fail(str(e))


@task_app.command(name="auto")
def task_auto(
    task_id: str = typer.Argument(help="任务ID"),
    single_eval: bool = typer.Option(True, "--single-eval/--multi-eval", help="评估使用单次调用"),
) -> None:
    """一键推进任务: 从当前阶段自动推进到需要用户介入的节点."""
    board = _board()
    try:
        task = board.get_task(task_id)
    except BoardError as e:
        _fail(str(e))

    config = Config()
    config.load()
    evaluator = Evaluator(config)

    while True:
        task = board.get_task(task_id)
        console.print(f"\n[cyan]当前状态: {task.status.value} | 阶段: {task.phase.value} | 迭代: {task.iteration}[/cyan]")

        if task.status == TaskStatus.DRAFT:
            wm = WorktreeManager(board.data.repo_path, board.data.main_branch)
            wm.create_worktree(task)
            board.transition(task_id, TaskStatus.PLANNING)
            console.print("[green]→ 创建 worktree, 进入规划[/green]")

        elif task.status == TaskStatus.PLANNING:
            errors = PhaseGuard.check(task, TaskStatus.EXECUTING)
            if errors:
                console.print(f"[yellow]⚠️ 规划未完成, 缺失: {', '.join(errors)}[/yellow]")
                console.print("[dim]请手动完成规划后再次执行 kanban task auto[/dim]")
                break
            board.transition(task_id, TaskStatus.EXECUTING)
            console.print("[green]→ 规划完成, 进入执行[/green]")

        elif task.status == TaskStatus.EXECUTING:
            errors = PhaseGuard.check(task, TaskStatus.EVALUATING)
            if errors:
                console.print(f"[yellow]⚠️ 执行未完成, 缺失: {', '.join(errors)}[/yellow]")
                console.print("[dim]请手动完成执行后再次执行 kanban task auto[/dim]")
                break
            board.transition(task_id, TaskStatus.EVALUATING)
            console.print("[green]→ 执行完成, 进入评估[/green]")

        elif task.status == TaskStatus.EVALUATING:
            console.print("[cyan]⏳ 运行评估...[/cyan]")
            if single_eval:
                results = evaluator.evaluate_single(task)
            else:
                results = evaluator.evaluate(task)
            board.save()

            all_passed = evaluator.check_all_passed(task)
            if all_passed:
                board.transition(task_id, TaskStatus.USER_REVIEW)
                console.print(f"[green]✅ 评估全部通过, 进入用户审核[/green]")
                console.print("[dim]请执行 kanban task approve 或 kanban task reject[/dim]")
                break
            else:
                failing = [r.role for r in task.evaluation_results if r.score < 9.0]
                console.print(f"[yellow]⚠️ 评估未通过: {', '.join(failing)}[/yellow]")
                max_iter = config.get_max_iterations()
                if task.iteration < max_iter:
                    task.iteration += 1
                    board.transition(task_id, TaskStatus.SELF_IMPROVE)
                    board.transition(task_id, TaskStatus.EXECUTING)
                    console.print(f"[yellow]→ 进入自迭代第 {task.iteration} 轮[/yellow]")
                    console.print("[dim]请根据评估反馈改进后再次执行 kanban task auto[/dim]")
                    break
                else:
                    board.transition(task_id, TaskStatus.USER_REVIEW)
                    console.print(f"[red]已达迭代上限, 进入用户审核[/red]")
                    break

        elif task.status in (TaskStatus.USER_REVIEW, TaskStatus.MERGED, TaskStatus.ARCHIVED):
            console.print(f"[dim]任务处于 {task.status.value} 状态, 需要用户操作[/dim]")
            break
        else:
            console.print(f"[dim]任务处于 {task.status.value} 状态, 无需自动推进[/dim]")
            break

    console.print(f"\n[cyan]最终状态: {task.status.value}[/cyan]")


# ── Git 操作 ──

@git_app.command(name="merge")
def git_merge(task_id: str = typer.Argument(help="任务ID")) -> None:
    """合并 worktree 到主干."""
    board = _board()
    try:
        task = board.get_task(task_id)
        wm = WorktreeManager(board.data.repo_path, board.data.main_branch)
        msg = wm.merge_worktree(task)
        board.transition(task_id, TaskStatus.MERGED)
        console.print(f"[green]✅ {msg}[/green]")
    except (BoardError, WorktreeError) as e:
        _fail(str(e))


@git_app.command(name="cleanup")
def git_cleanup(task_id: str = typer.Argument(help="任务ID")) -> None:
    """清理 worktree."""
    board = _board()
    try:
        task = board.get_task(task_id)
        wm = WorktreeManager(board.data.repo_path, board.data.main_branch)
        msg = wm.remove_worktree(task)
        board.save()
        console.print(f"[green]✅ {msg}[/green]")
    except (BoardError, WorktreeError) as e:
        _fail(str(e))


# ── Agent 调度 ──

@agent_app.command(name="detect")
def agent_detect() -> None:
    """检测本地可用的 Agent CLI."""
    from .runner import AgentRunner
    agents = AgentRunner.detect_available_agents()
    if not agents:
        console.print("[yellow]未检测到可用的 Agent CLI[/yellow]")
        console.print("[dim]已支持: claude-code, opencode[/dim]")
        return
    for a in agents:
        console.print(f"[green]✅ {a['name']}[/green]: {a['path']}")


@agent_app.command(name="run")
def agent_run(task_id: str = typer.Argument(help="任务ID")) -> None:
    """启动 agent 执行当前阶段."""
    board = _board()
    try:
        task = board.get_task(task_id)
        if not task.assignee:
            _fail("任务未分配 agent, 请先 kanban task assign")
        config = Config()
        config.load()
        agents = config.get_agents()
        if task.assignee not in agents:
            _fail(f"Agent '{task.assignee}' 未在配置中注册")
        runner = AgentRunner(config)
        result = runner.run(task, agents[task.assignee])
        console.print(f"[green]✅ Agent 执行完成[/green]: {task.id}")
        if result:
            console.print(result[:500])
    except Exception as e:
        _fail(str(e))


@agent_app.command(name="list")
def agent_list() -> None:
    """列出可用 agent."""
    config = Config()
    config.load()
    agents = config.get_agents()
    if not agents:
        console.print("[yellow]暂无注册 agent[/yellow]")
        return

    table = Table(title="已注册 Agent")
    table.add_column("名称", style="cyan")
    table.add_column("类型")
    table.add_column("模型")
    table.add_column("能力")

    for a in agents.values():
        table.add_row(a.name, a.type, a.model, ", ".join(a.capabilities))

    console.print(table)


# ── 报告 ──

@app.command(name="report")
def report(task_id: str = typer.Argument(help="任务ID")) -> None:
    """生成任务报告."""
    board = _board()
    try:
        task = board.get_task(task_id)
        reporter = Reporter()
        path = reporter.generate_task_report(task)
        console.print(f"[green]✅ 报告已生成[/green]: {path}")
    except BoardError as e:
        _fail(str(e))


if __name__ == "__main__":
    app()

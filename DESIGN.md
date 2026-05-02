# Agent Kanban - 多Agent任务编排看板系统

## 设计目标

构建一个CLI驱动的多Agent任务编排看板，支持：
- 任务分配与进度跟踪
- Git worktree 隔离并行执行
- 强约束的流程模板（Plan → Execute → Evaluate → Self-improve → User Decision → Archive）
- 插件化集成 claude code / opencode / hermes-agent

## 架构设计

```
agent-kanban/
├── pyproject.toml              # Python项目配置
├── README.md                   # 使用文档
├── kanban/
│   ├── __init__.py
│   ├── cli.py                  # CLI入口 (typer)
│   ├── board.py                # 看板核心: 任务CRUD, 状态机
│   ├── workflow.py             # 流程模板引擎, 阶段守卫
│   ├── worktree.py             # Git worktree 管理
│   ├── runner.py               # Agent调度器 (claude-code/opencode/hermes/openclaw)
│   ├── evaluator.py            # 评估阶段: 代码审核/QA/产品验收/美术验收
│   ├── config.py               # 项目配置管理
│   ├── reporter.py             # 报告生成器
│   ├── models.py               # 数据模型 (pydantic)
│   └── templates.py            # 模板渲染
├── templates/                  # 各阶段文档模板
│   ├── requirements.md.j2
│   ├── task_breakdown.md.j2
│   ├── review_report.md.j2
│   ├── qa_report.md.j2
│   ├── product_review.md.j2
│   ├── design_review.md.j2
│   ├── execute_summary.md.j2
│   └── archive.md.j2
└── skills/                     # Claude Code skill集成
    └── agent-kanban/
        └── SKILL.md
```

## 核心数据模型

### Task (任务)
```python
class Task:
    id: str                    # 唯一ID (如 TK-001)
    title: str
    description: str
    status: TaskStatus         # 当前状态
    assignee: str              # agent名称
    worktree_path: str         # git worktree路径
    branch: str                # git分支名
    phase: Phase               # 当前阶段
    iteration: int             # 自迭代轮次 (1-5)
    scores: dict               # 各角色评分
    created_at: datetime
    updated_at: datetime
    documents: list[str]       # 产出文档列表
```

### TaskStatus (状态机)
```
DRAFT → PLANNING → EXECUTING → EVALUATING → SELF_IMPROVE → USER_REVIEW → MERGED → ARCHIVED
                        ↑                          │
                        └──────────────────────────┘
```

### Phase (阶段)
```
PLAN        = "plan"        # 规划阶段
EXECUTE     = "execute"     # 执行阶段
EVALUATE    = "evaluate"    # 评估阶段
IMPROVE     = "improve"     # 自迭代
USER_REVIEW = "user_review" # 用户决策
ARCHIVE     = "archive"     # 归档
```

## 状态机转换规则 (强约束)

```
VALID_TRANSITIONS = {
    DRAFT:      [PLANNING],
    PLANNING:   [EXECUTING, DRAFT],        # 规划完成→执行, 规划失败→回退
    EXECUTING:  [EVALUATING, PLANNING],     # 执行完成→评估, 执行失败→回退
    EVALUATING: [SELF_IMPROVE, USER_REVIEW, PLANNING],
                                              # 全部通过→用户审核
                                              # 有不通过→自迭代
                                              # 严重问题→回退规划
    SELF_IMPROVE: [EXECUTING],              # 重新执行
    USER_REVIEW: [ARCHIVE, PLANNING],       # 验收→归档, 拒绝→回退
    ARCHIVE:    [],                          # 终态
}
```

## 看板存储

使用 `kanban-board.json` 作为状态存储：
```json
{
  "version": 1,
  "project": "project-name",
  "repo_path": "/path/to/main/repo",
  "main_branch": "main",
  "tasks": {
    "TK-001": { ... },
    "TK-002": { ... }
  },
  "agents": {
    "developer-1": {
      "type": "claude-code",
      "capabilities": ["develop", "test"]
    }
  }
}
```

## CLI 命令设计

```bash
# 看板管理
kanban init                    # 初始化看板
kanban status                  # 查看所有任务状态
kanban board                   # 看板视图 (终端表格)

# 任务管理
kanban task create --title "xxx" --desc "xxx" --assignee agent-1
kanban task show TK-001        # 查看任务详情
kanban task assign TK-001 agent-1  # 分配任务

# 流程控制 (强约束 - 自动校验前置条件)
kanban task start TK-001       # DRAFT → PLANNING (创建worktree)
kanban task plan-done TK-001   # PLANNING → EXECUTING (校验规划文档)
kanban task exec-done TK-001   # EXECUTING → EVALUATING (校验执行产出)
kanban task evaluate TK-001    # 运行评估流程
kanban task approve TK-001     # USER_REVIEW → ARCHIVE
kanban task reject TK-001      # USER_REVIEW → PLANNING (带反馈)

# Git 操作
kanban git merge TK-001        # 合并worktree到主干
kanban git cleanup TK-001      # 清理worktree

# Agent 调度
kanban agent run TK-001        # 启动agent执行当前阶段
kanban agent list              # 列出可用agent

# 报告
kanban report TK-001           # 生成任务报告
```

## 阶段文档产出要求 (强约束)

### Plan 阶段必须产出:
- `docs/requirements.md` - 需求文档
- `docs/task-breakdown.md` - 任务拆解 (含子任务状态)

### Execute 阶段必须产出:
- 业务代码
- 单元测试代码
- 集成测试代码
- `docs/execute-summary-{N}.md` - 执行复盘 (N=迭代轮次)

### Evaluate 阶段必须产出:
- `docs/reviews/code-review-{N}.md` - 代码审核报告 + 评分
- `docs/reviews/qa-report-{N}.md` - QA测试报告 + 评分
- `docs/reviews/product-review-{N}.md` - 产品验收报告 + 评分
- `docs/reviews/design-review-{N}.md` - 美术/交互验收报告 + 评分

### Archive 阶段产出:
- `docs/archive/TK-001-summary.md` - 任务归档总结

## 流程检查器 (PhaseGuard)

每个阶段转换前强制执行检查:

```python
class PhaseGuard:
    def check_plan_complete(task) -> list[str]:
        """校验规划阶段是否完成"""
        errors = []
        if not exists(f"{task.worktree}/docs/requirements.md"):
            errors.append("缺少需求文档: docs/requirements.md")
        if not exists(f"{task.worktree}/docs/task-breakdown.md"):
            errors.append("缺少任务拆解文档: docs/task-breakdown.md")
        if not git_worktree_exists(task):
            errors.append("Git worktree 未创建")
        return errors

    def check_execute_complete(task) -> list[str]:
        """校验执行阶段是否完成"""
        errors = []
        # 检查是否有代码变更
        if not has_uncommitted_changes(task.worktree):
            errors.append("没有代码变更")
        # 检查是否有测试
        if not has_test_files(task.worktree):
            errors.append("缺少测试代码")
        # 检查复盘文档
        if not exists(f"{task.worktree}/docs/execute-summary-{task.iteration}.md"):
            errors.append(f"缺少执行复盘: docs/execute-summary-{task.iteration}.md")
        return errors

    def check_evaluate_complete(task) -> list[str]:
        """校验评估阶段是否完成"""
        # 检查所有评估报告和评分
        ...
```

## Agent Runner 设计

```python
class AgentRunner:
    def dispatch(task, agent_config):
        """根据agent类型分发任务"""
        if agent_config.type == "claude-code":
            return self._run_claude_code(task, agent_config)
        elif agent_config.type == "opencode":
            return self._run_opencode(task, agent_config)
        elif agent_config.type == "hermes":
            return self._run_hermes(task, agent_config)
        elif agent_config.type == "openclaw":
            return self._run_openclaw(task, agent_config)

    def _run_claude_code(task, config):
        """通过 sessions_spawn 或直接 claude CLI 执行"""
        prompt = self._build_prompt(task)
        cmd = f"claude --print '{prompt}'"
        # 在 worktree 目录执行
        result = exec_in_worktree(task.worktree, cmd)
        return result
```

## 评估角色定义

```python
EVALUATION_ROLES = {
    "tech_lead": {
        "name": "程序组长",
        "prompt": "你是代码审核专家...",
        "score_threshold": 9.0,
        "output": "code-review-{N}.md"
    },
    "qa": {
        "name": "QA工程师",
        "prompt": "你是质量保障专家...",
        "score_threshold": 9.0,
        "output": "qa-report-{N}.md"
    },
    "product": {
        "name": "产品经理",
        "prompt": "你是产品验收专家...",
        "score_threshold": 9.0,
        "output": "product-review-{N}.md"
    },
    "design": {
        "name": "美术/交互设计",
        "prompt": "你是交互设计专家...",
        "score_threshold": 9.0,
        "output": "design-review-{N}.md"
    }
}
```

## 自迭代循环逻辑

```python
def run_self_improve_loop(task):
    """自迭代循环, 最多5轮"""
    while task.iteration <= 5:
        # 收集本轮评估分数
        scores = get_evaluation_scores(task)

        # 检查是否全部通过
        all_passed = all(s >= 9.0 for s in scores.values())

        if all_passed:
            task.status = USER_REVIEW
            return

        # 归档本轮评估报告
        archive_evaluation_reports(task, task.iteration)

        # 增加迭代轮次
        task.iteration += 1

        # 回到执行阶段
        task.status = EXECUTING
        run_execute_phase(task)

    # 超过5轮, 进入用户决策
    task.status = USER_REVIEW
    notify_user(task, "自迭代已达上限, 需要人工介入")
```

## 技术栈

- Python 3.11+
- typer (CLI框架)
- pydantic (数据模型)
- jinja2 (模板渲染)
- rich (终端美化)
- gitpython (Git操作)
- 无外部服务依赖

## 使用流程示例

```bash
# 1. 初始化
cd /path/to/project
kanban init

# 2. 创建任务
kanban task create \
  --title "实现用户登录功能" \
  --desc "支持邮箱/手机号登录, JWT认证" \
  --assignee developer-1

# 3. 启动任务 (自动创建worktree, 进入规划阶段)
kanban task start TK-001

# 4. Agent自动执行规划
kanban agent run TK-001

# 5. 查看进度
kanban board
kanban task show TK-001

# 6. 逐步推进 (每步都有前置检查)
kanban task plan-done TK-001    # 自动检查规划文档
kanban task exec-done TK-001    # 自动检查代码和测试
kanban task evaluate TK-001     # 自动运行评估

# 7. 评估通过后用户审核
kanban task approve TK-001

# 8. 合并到主干
kanban git merge TK-001
```

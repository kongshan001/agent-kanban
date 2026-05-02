# Agent Kanban Skill

> 多Agent任务编排看板系统 — Claude Code / Hermes / OpenCode 通用

## 概述

Agent Kanban 是一个 CLI 驱动的多 Agent 任务编排系统，核心特性：

- **Git Worktree 隔离** — 每个任务独立 worktree，支持多 Agent 并行
- **流程强约束** — PhaseGuard 状态机，阶段转换必须满足前置条件
- **LLM 驱动评估** — 支持 claude / hermes / opencode，自动代码评审
- **自迭代循环** — 评估不通过自动进入下一轮，最多 5 轮
- **一键推进** — `kanban task auto --run-agent` 自动推进到需要用户介入的节点

## 安装

### 方式一：pip 安装（推荐）

```bash
pip install git+https://github.com/kongshan001/agent-kanban.git
```

### 方式二：本地开发安装

```bash
git clone https://github.com/kongshan001/agent-kanban.git
cd agent-kanban && pip install -e .
```

### 方式三：Claude Code Skill

将 `skills/agent-kanban` 目录复制到 Claude Code 的 skills 目录：

```bash
# Claude Code
cp -r skills/agent-kanban ~/.claude/skills/

# 或在项目的 .claude/skills/ 下
cp -r skills/agent-kanban /path/to/your-project/.claude/skills/
```

## 快速开始

```bash
# 1. 在项目目录初始化
cd your-project
kanban init

# 2. 配置 agent（编辑 kanban.config.yaml）
# agents:
#   dev1:
#     type: hermes
#     capabilities: [develop, test, review]

# 3. 创建任务
kanban task create -t "实现用户登录" -d "JWT认证" -a dev1

# 4. 一键全自动推进（规划→开发→评估→迭代）
kanban task auto TK-001 --run-agent

# 5. 审核验收
kanban task approve TK-001   # 自动合并到主干
# 或
kanban task reject TK-001 --feedback "需要补充单元测试"
```

## 流程说明

```
DRAFT → PLANNING → EXECUTING → EVALUATING → USER_REVIEW → MERGED → ARCHIVED
  ↑                   ↑              ↓              │
  └── (reject)        │     SELF_IMPROVE → EXECUTING│
                      └─────────────────────────────┘
```

### 各阶段产出要求

| 阶段 | 必须产出 |
|------|---------|
| Plan | `docs/requirements.md` + `docs/task-breakdown.md` |
| Execute | 业务代码 + 测试代码 + `docs/execute-summary-{N}.md` |
| Evaluate | 评估报告（代码/测试/需求/交互各维度评分） |
| Archive | 合并到主干 + 清理 worktree |

### PhaseGuard 强约束

每个阶段转换前自动检查前置条件，不满足则拒绝：

```bash
$ kanban task plan-done TK-001
❌ 流程守卫检查未通过, 缺失以下条件:
  ❌ 缺少需求文档: docs/requirements.md
  ❌ 缺少任务拆解文档: docs/task-breakdown.md
```

## 命令参考

### 看板管理
| 命令 | 说明 |
|------|------|
| `kanban init` | 初始化看板（自动检测主分支） |
| `kanban status` | 查看所有任务状态 |
| `kanban board` | 看板表格视图 |

### 任务管理
| 命令 | 说明 |
|------|------|
| `kanban task create -t TITLE -d DESC -a AGENT` | 创建任务 |
| `kanban task show TK-001` | 查看任务详情 |
| `kanban task assign TK-001 agent-name` | 分配任务 |
| `kanban task start TK-001` | 启动（创建 worktree） |
| `kanban task plan-done TK-001` | 规划完成 |
| `kanban task exec-done TK-001` | 执行完成 |
| `kanban task evaluate TK-001 [--single]` | 运行评估 |
| `kanban task approve TK-001` | 批准（自动合并） |
| `kanban task reject TK-001 -f "反馈"` | 拒绝 |
| `kanban task auto TK-001 [--run-agent]` | 一键推进 |
| `kanban task reset TK-001 [-f]` | 重置任务 |

### Git 操作
| 命令 | 说明 |
|------|------|
| `kanban git merge TK-001` | 合并 worktree 到主干 |
| `kanban git cleanup TK-001` | 清理 worktree |

### Agent
| 命令 | 说明 |
|------|------|
| `kanban agent detect` | 检测本地可用 Agent |
| `kanban agent run TK-001` | 手动启动 Agent |
| `kanban agent list` | 列出已配置 Agent |

### 报告
| 命令 | 说明 |
|------|------|
| `kanban report TK-001` | 生成任务报告 |

## 配置说明

`kanban.config.yaml`:

```yaml
project: my-project
main_branch: main  # 自动检测
agents:
  dev1:
    type: hermes          # hermes | claude-code | opencode
    model: ""             # 可选模型覆盖
    capabilities:
      - develop
      - test
      - review
evaluation:
  score_threshold: 9.0    # 满分10，>=9 通过
  roles: [tech_lead, qa, product, design]
self_improve:
  max_iterations: 5       # 最大自迭代轮次
```

## 支持的 Agent

| Agent | CLI | 状态 |
|-------|-----|------|
| Hermes Agent | `hermes_cli` | ✅ 已验证 |
| Claude Code | `claude` | 🟡 需 API key |
| OpenCode | `opencode` | 🟡 需配置模型 |

## 端到端验证

详见 [e2e-demo/string-utils/](../../e2e-demo/string-utils/) — 一条命令全自动完成的完整产出示例。

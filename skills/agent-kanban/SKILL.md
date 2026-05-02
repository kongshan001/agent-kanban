# Agent Kanban Skill

> 多Agent任务编排看板系统 — Claude Code / Hermes / OpenCode 通用

## 概述

Agent Kanban 是一个 CLI 驱动的多 Agent 任务编排系统，核心特性：

- **Git Worktree 隔离** — 每个任务独立 worktree，支持多 Agent 并行
- **流程强约束** — PhaseGuard 状态机，阶段转换必须满足前置条件
- **LLM 驱动评估** — 支持 claude / hermes / opencode，自动代码评审
- **自迭代循环** — 评估不通过自动进入下一轮，最多 5 轮
- **一键推进** — `kanban task auto` 自动推进到需要用户介入的节点

## 安装

```bash
# 从 GitHub 安装
pip install git+https://github.com/kongshan001/agent-kanban.git

# 或克隆后本地安装
git clone https://github.com/kongshan001/agent-kanban.git
cd agent-kanban && pip install -e .
```

## 快速开始

```bash
# 1. 在项目目录初始化
cd your-project
kanban init

# 2. 创建任务
kanban task create -t "实现用户登录" -d "JWT认证" -a developer-1

# 3. 一键推进（自动创建 worktree、检查文档、运行评估）
kanban task auto TK-001

# 4. 评估通过后审核
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

- 缺少文档 → **拒绝**进入下一阶段
- 缺少测试代码 → **拒绝**进入评估
- 评估分数 < 9.0 → **自动**进入自迭代
- 自迭代 > 5 轮 → **强制**进入用户审核

## 命令参考

### 看板管理

```bash
kanban init                    # 初始化（自动检测主分支）
kanban status                  # 查看所有任务
kanban board                   # 看板视图
```

### 任务管理

```bash
kanban task create -t TITLE -d DESC -a AGENT [--skip-checks test]
kanban task show TK-001
kanban task assign TK-001 agent-1
kanban task start TK-001       # 创建 worktree
kanban task plan-done TK-001   # 规划→执行
kanban task exec-done TK-001   # 执行→评估
kanban task evaluate TK-001 [--single]  # 评估（--single: 单次LLM调用）
kanban task approve TK-001 [--no-merge] # 批准（自动合并）
kanban task reject TK-001 -f "反馈"     # 拒绝（回退到规划）
kanban task auto TK-001        # 一键推进
```

### Git 操作

```bash
kanban git merge TK-001        # 合并到主干
kanban git cleanup TK-001      # 清理 worktree
```

### Agent 调度

```bash
kanban agent detect            # 检测可用 Agent CLI
kanban agent list              # 列出已注册 Agent
kanban agent run TK-001        # 启动 Agent 执行当前阶段
```

## 配置 (kanban.config.yaml)

```yaml
project: my-project
main_branch: main  # 自动检测
agents:
  developer-1:
    type: claude-code
    model: claude-sonnet-4-20250514
    capabilities: [develop, test, review]
  developer-2:
    type: hermes
    model: minimax-m2.7
    capabilities: [develop, test]
evaluation:
  score_threshold: 9.0
  mode: single  # single（1次调用）或 multi（4次调用）
self_improve:
  max_iterations: 5
```

## 评估模式

### 单次综合评估 (推荐)
```bash
kanban task evaluate TK-001 --single
```
一次 LLM 调用评估 4 个维度（代码质量、测试质量、需求完整性、交互体验），效率高。

### 多角色独立评估
```bash
kanban task evaluate TK-001
```
4 个角色独立评估，每个角色单独调用 LLM，结果更细但耗时 4 倍。

## 支持的 Agent

| Agent | CLI | 状态 |
|-------|-----|------|
| Claude Code | `claude -p` | ✅ 需要 API key |
| Hermes Agent | `hermes chat -q` | ✅ 已验证 |
| OpenCode | `opencode run` | ⚠️ 需要正确模型配置 |

## 扩展

作为 Claude Code Skill 安装：

```bash
# 复制到 Claude Code skills 目录
cp -r skills/agent-kanban ~/.claude/skills/
```

## 开发

```bash
git clone https://github.com/kongshan001/agent-kanban.git
cd agent-kanban
python -m venv venv && source venv/bin/activate
pip install -e .

# 运行测试
pytest tests/ -v
```

## 版本历史

- **v0.5** — 综合评估 + auto 一键推进 + LLM 调用统一化
- **v0.4** — Hermes 真实 Agent 接入 + 端到端验证
- **v0.3** — Agent Runner + 完整闭环 + LLM 评估器
- **v0.2** — PhaseGuard 可配置 + 主分支自动检测
- **v0.1** — MVP: 状态机 + 流程守卫 + worktree

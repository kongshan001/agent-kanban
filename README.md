# Agent Kanban

多Agent任务编排看板系统 — 支持 Git Worktree 并行、流程强约束、LLM 驱动评估。

## 特性

- 🔄 **完整流程闭环**: Plan → Execute → Evaluate → Self-improve → User Review → Archive
- 🌳 **Git Worktree 隔离**: 每个任务独立分支和工作空间，支持多 Agent 并行
- 🛡️ **流程强约束**: PhaseGuard 状态机，缺少文档拒绝进入下一阶段
- 🤖 **LLM 驱动评估**: 支持 Claude Code / Hermes / OpenCode，真实代码评审
- ⚡ **一键推进**: `kanban task auto --run-agent` 全自动执行
- 📊 **评分系统**: 多维度评分（代码/测试/需求/交互），阈值 9.0/10

## 安装

```bash
pip install git+https://github.com/kongshan001/agent-kanban.git
```

## 快速开始

```bash
# 1. 在项目目录初始化
cd your-project
kanban init

# 2. 创建任务
kanban task create -t "实现用户登录" -d "JWT认证" -a developer-1

# 3. 全自动推进（Agent 自动规划、开发、评估）
kanban task auto TK-001 --run-agent

# 4. 审核通过（自动合并到主干）
kanban task approve TK-001
```

## 手动流程控制

```bash
kanban task start TK-001       # 创建 worktree
kanban task plan-done TK-001   # 规划→执行（校验文档）
kanban task exec-done TK-001   # 执行→评估（校验代码）
kanban task evaluate TK-001 --single  # 单次综合评估
kanban task approve TK-001     # 批准（自动合并）
kanban task reject TK-001 -f "反馈"   # 拒绝（回退规划）
```

## 流程状态机

```
DRAFT → PLANNING → EXECUTING → EVALUATING → USER_REVIEW → MERGED → ARCHIVED
                       ↑              ↓
                       └── SELF_IMPROVE (最多5轮)
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `kanban init` | 初始化看板（自动检测主分支） |
| `kanban status` | 查看所有任务 |
| `kanban task create` | 创建任务 |
| `kanban task auto TK-001` | 一键推进 |
| `kanban task evaluate TK-001 --single` | 单次综合评估 |
| `kanban task approve TK-001` | 批准+合并 |
| `kanban task reject TK-001` | 拒绝+回退 |
| `kanban agent detect` | 检测可用 Agent CLI |
| `kanban report TK-001` | 生成任务报告 |

## 配置 (kanban.config.yaml)

```yaml
agents:
  developer-1:
    type: claude-code
    model: claude-sonnet-4-20250514
    capabilities: [develop, test, review]
evaluation:
  score_threshold: 9.0
self_improve:
  max_iterations: 5
```

## 支持的 Agent

| Agent | 状态 |
|-------|------|
| Hermes Agent | ✅ 已验证 |
| Claude Code | ✅ 需要API key |
| OpenCode | ⚠️ 需要正确模型配置 |

## 版本历史

- v0.5 — 综合评估 + auto 一键推进 + LLM 统一调用
- v0.4 — Hermes 真实接入 + 端到端验证
- v0.3 — Agent Runner + 完整闭环
- v0.2 — PhaseGuard 可配置 + 自动检测分支
- v0.1 — MVP 基础功能

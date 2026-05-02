# Agent Kanban

多Agent任务编排看板系统 - CLI 驱动的任务管理，支持 Git worktree 隔离和强约束流程。

## 安装

```bash
cd agent-kanban
pip install -e .
```

## 快速开始

```bash
# 初始化看板
kanban init

# 创建任务
kanban task create --title "实现用户登录" --desc "支持邮箱/手机号登录, JWT认证"

# 启动任务 (创建 worktree, 进入规划)
kanban task start TK-001

# 规划完成后推进
kanban task plan-done TK-001    # 校验规划文档
kanban task exec-done TK-001    # 校验执行产出
kanban task evaluate TK-001     # 运行4角色评估
kanban task approve TK-001      # 用户审核通过

# 合并到主干
kanban git merge TK-001
kanban git cleanup TK-001
```

## 流程

```
DRAFT → PLANNING → EXECUTING → EVALUATING → USER_REVIEW → ARCHIVED
                       ↑              ↓
                       └── SELF_IMPROVE
```

## 评估角色

| 角色 | 职责 |
|------|------|
| tech_lead | 代码审核 + 架构审核 |
| qa | 单元测试 + 集成测试 |
| product | 功能验收 |
| design | UI/UX 验收 |

每个角色评分 >= 9.0 (满分10) 才通过。

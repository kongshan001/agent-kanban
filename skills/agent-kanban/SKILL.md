# Agent Kanban Skill

## 描述
多Agent任务编排看板系统，支持强约束的 Plan → Execute → Evaluate → Self-improve → User Review → Archive 流程。

## 使用方式

```bash
# 初始化
kanban init

# 创建并启动任务
kanban task create --title "实现登录功能"
kanban task start TK-001

# 逐步推进
kanban task plan-done TK-001
kanban task exec-done TK-001
kanban task evaluate TK-001
kanban task approve TK-001
```

## 约束
- 每个阶段转换强制检查前置条件
- 评估阈值: 9.0/10
- 自迭代上限: 5轮

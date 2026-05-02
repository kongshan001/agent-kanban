# E2E Demo: 字符串工具函数

> 本目录保存了 agent-kanban v0.6 端到端验证的完整产出

## 验证场景

一条命令 `kanban task auto TK-001 --run-agent` 全自动完成：

```
DRAFT → PLANNING → EXECUTING → EVALUATING → SELF_IMPROVE
```

## 执行环境

- **Agent**: Hermes (hermes_cli v0.10.0)
- **任务**: 实现 is_palindrome(s) 和 reverse_string(s)
- **模式**: 单次综合评估 (--single-eval)

## 产出文件

```
string-utils/
├── string_utils.py          # Hermes 自动实现的业务代码
├── test_string_utils.py     # Hermes 自动实现的 16 个测试用例
├── kanban-board.json        # 看板状态快照
├── kanban.config.yaml       # 看板配置
└── docs/
    ├── requirements.md      # Hermes 自动生成的需求文档
    ├── task-breakdown.md    # Hermes 自动生成的任务拆解
    ├── execute-summary-1.md # Hermes 自动生成的执行复盘
    └── reviews/
        └── review-1.md      # LLM 综合评估报告
```

## 评估结果

| 维度 | 分数 | 通过 |
|------|------|------|
| 代码质量 (tech_lead) | 9.0/10 | ✅ |
| 测试质量 (qa) | 8.0/10 | ❌ |
| 需求完整性 (product) | 9.0/10 | ✅ |
| 交互体验 (design) | 10.0/10 | ✅ |

qa 评分 8.0 未达阈值，自动进入自迭代第 2 轮。

## 代码亮点

- 完整 docstring + 类型注解
- Unicode 支持（中文回文"上海自来水来自海上"）
- 边界处理（空字符串、单字符、超长字符串、emoji）
- 16 个测试用例覆盖所有场景

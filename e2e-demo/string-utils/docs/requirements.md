# 字符串工具函数 - 需求文档

## 1. 项目概述

- **项目名称**: 字符串工具函数库
- **项目类型**: Python 工具模块
- **核心功能**: 提供 `is_palindrome(s)` 和 `reverse_string(s)` 两个字符串处理函数
- **目标用户**: Python 开发者，需要字符串处理的应用程序

## 2. 功能需求

### 2.1 is_palindrome(s) 函数

**功能描述**: 判断给定字符串是否为回文串

**参数说明**:
- `s` (str): 待检测的字符串

**返回值**: 
- `bool`: 是回文返回 `True`，否则返回 `False`

**回文定义**: 从左到右读与从右到左读完全一致的字符串（忽略大小写），空字符串视为回文

**处理规则**:
1. 大小写不敏感：`"Abba"` 应返回 `True`
2. 仅检测字母数字字符，忽略空格、标点、特殊字符：`"A man a plan a canal Panama"` 应返回 `True`
3. 空字符串返回 `True`

**示例**:
```python
is_palindrome("")          # True
is_palindrome("abc")       # False
is_palindrome("aba")       # True
is_palindrome("Abba")      # True
is_palindrome("racecar")   # True
is_palindrome("hello")     # False
```

### 2.2 reverse_string(s) 函数

**功能描述**: 反转给定字符串

**参数说明**:
- `s` (str): 待反转的字符串

**返回值**:
- `str`: 反转后的新字符串，原字符串不变

**处理规则**:
1. 逐字符反转，包括空格和特殊字符
2. 返回新字符串，不修改原字符串
3. 空字符串返回空字符串

**示例**:
```python
reverse_string("")         # ""
reverse_string("abc")      # "cba"
reverse_string("hello")     # "olleh"
reverse_string("12345")    # "54321"
```

## 3. 技术约束

- **Python 版本**: Python 3.8+
- **依赖**: 仅使用 Python 标准库，无需外部依赖
- **编码**: UTF-8

## 4. 文件结构

```
project/
├── string_utils.py   # 核心函数实现
├── test_string_utils.py  # 单元测试
└── docs/
    ├── requirements.md   # 本文档
    └── task-breakdown.md # 任务拆解
```

## 5. 验收标准

### 5.1 is_palindrome 验收标准

| 用例 | 输入 | 期望输出 |
|------|------|----------|
| 空字符串 | `""` | `True` |
| 单字符 | `"a"` | `True` |
| 相同字符 | `"aa"` | `True` |
| 普通回文 | `"aba"` | `True` |
| 大小写回文 | `"Abba"` | `True` |
| 带空格回文 | `"a man a plan a canal Panama"` | `True` |
| 非回文 | `"abc"` | `False` |
| 非回文偶数 | `"abca"` | `False` |

### 5.2 reverse_string 验收标准

| 用例 | 输入 | 期望输出 |
|------|------|----------|
| 空字符串 | `""` | `""` |
| 单字符 | `"a"` | `"a"` |
| 普通字符串 | `"abc"` | `"cba"` |
| 对称回文 | `"racecar"` | `"racecar"` |
| 带空格 | `"hello world"` | `"dlrow olleh"` |

### 5.3 测试覆盖率要求

- 测试文件必须包含所有验收标准用例
- 使用 `unittest` 框架
- 测试类命名: `TestStringUtils`

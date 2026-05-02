# 字符串工具函数 - 任务拆解

## 任务概览

**任务 ID**: T1
**任务标题**: 实现字符串工具函数
**任务描述**: 实现 `is_palindrome(s)` 和 `reverse_string(s)` 函数，带完整测试

---

## 子任务列表

### T1.1 创建核心函数模块
**状态**: :white_check_mark: completed
**负责人**: 开发者
**预计工时**: 15 分钟

**任务描述**:
创建 `string_utils.py` 文件，实现以下函数：

1. `is_palindrome(s: str) -> bool`
   - 判断字符串是否为回文（忽略大小写、非字母数字字符）
   - 空字符串返回 True

2. `reverse_string(s: str) -> str`
   - 返回字符串的反转结果
   - 不修改原字符串

**验收标准**:
- [x] 文件 `string_utils.py` 存在
- [x] `is_palindrome` 函数签名正确，参数和返回值类型标注正确
- [x] `reverse_string` 函数签名正确，参数和返回值类型标注正确
- [x] `is_palindrome("")` 返回 `True`
- [x] `is_palindrome("aba")` 返回 `True`
- [x] `is_palindrome("Abba")` 返回 `True`
- [x] `is_palindrome("abc")` 返回 `False`
- [x] `is_palindrome("a man a plan a canal Panama")` 返回 `True`
- [x] `reverse_string("")` 返回 `""`
- [x] `reverse_string("abc")` 返回 `"cba"`
- [x] `reverse_string("racecar")` 返回 `"racecar"`

---

### T1.2 创建单元测试文件
**状态**: :white_check_mark: completed
**依赖**: T1.1
**预计工时**: 15 分钟

**任务描述**:
创建 `test_string_utils.py` 文件，使用 `unittest` 框架编写完整单元测试

**验收标准**:
- [x] 文件 `test_string_utils.py` 存在
- [x] 测试类命名为 `TestStringUtils`
- [x] 包含 `test_is_palindrome_empty` - 测试空字符串
- [x] 包含 `test_is_palindrome_single_char` - 测试单字符
- [x] 包含 `test_is_palindrome_simple` - 测试普通回文 "aba"
- [x] 包含 `test_is_palindrome_case_insensitive` - 测试大小写不敏感 "Abba"
- [x] 包含 `test_is_palindrome_with_spaces` - 测试带空格回文
- [x] 包含 `test_is_palindrome_not_palindrome` - 测试非回文 "abc"
- [x] 包含 `test_is_palindrome_not_palindrome_even` - 测试非回文偶数 "abca"
- [x] 包含 `test_reverse_string_empty` - 测试空字符串反转
- [x] 包含 `test_reverse_string_single` - 测试单字符反转
- [x] 包含 `test_reverse_string_normal` - 测试普通字符串反转
- [x] 包含 `test_reverse_string_palindrome` - 测试回文反转（结果相同）
- [x] 包含 `test_reverse_string_with_spaces` - 测试带空格反转
- [x] 所有测试用例通过（执行 `python -m pytest test_string_utils.py` 无失败）

---

### T1.3 验证完整功能
**状态**: :white_check_mark: completed
**依赖**: T1.1, T1.2
**预计工时**: 5 分钟

**任务描述**:
运行完整测试套件，验证所有功能正常

**验收标准**:
- [x] 执行 `python -m pytest test_string_utils.py -v` 所有测试通过
- [x] 测试覆盖率 100%（可选）
- [x] 代码无警告（使用 `python -m py_compile string_utils.py`）

---

## 任务状态汇总

|| 子任务 | 状态 | 依赖 | 验收标准数 | 完成标准数 |
|--------|------|------|-----------|-----------|
|| T1.1 创建核心函数模块 | :white_check_mark: completed | - | 11 | 11 |
|| T1.2 创建单元测试文件 | :white_check_mark: completed | T1.1 | 14 | 14 |
|| T1.3 验证完整功能 | :white_check_mark: completed | T1.1, T1.2 | 3 | 3 |

**总计**: 3 个子任务，28 个验收标准，全部完成

---

## 执行顺序

1. **T1.1** → 创建 `string_utils.py` 核心模块
2. **T1.2** → 创建 `test_string_utils.py` 测试文件
3. **T1.3** → 运行测试验证所有功能

---

## 备注

- 所有代码使用 Python 3.8+ 语法
- 遵循 PEP 8 代码风格
- 函数需包含完整的 docstring 文档

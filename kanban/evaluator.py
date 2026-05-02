"""评估引擎: 支持 LLM 驱动的代码/功能评估."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import EvaluationResult, Task


class EvaluatorError(Exception):
    """评估错误."""


# 评估角色配置
EVALUATION_ROLES = {
    "tech_lead": {
        "name": "程序组长",
        "prompt": """你是一位资深的技术负责人，负责审核代码变更。请从以下维度评估：

1. **代码质量**: 代码是否清晰、可维护、遵循最佳实践
2. **架构合理性**: 变更是否符合项目架构，是否引入不必要的耦合
3. **安全风险**: 是否存在安全隐患（注入、泄露等）
4. **性能影响**: 是否有明显的性能问题

请阅读 worktree 中的所有变更文件和文档，给出评估。

输出格式（严格遵守）：
## 评估报告 - 程序组长

### 总体评分: X/10

### 代码质量 (X/10)
- 评价...

### 架构合理性 (X/10)  
- 评价...

### 安全风险 (X/10)
- 评价...

### 改善建议
1. ...
2. ...

### 风险点
- ...
""",
        "output": "code-review-{N}.md",
    },
    "qa": {
        "name": "QA工程师",
        "prompt": """你是一位质量保障工程师，负责测试和验证代码变更。请从以下维度评估：

1. **测试覆盖**: 是否有充分的单元测试和集成测试
2. **边界条件**: 是否考虑了边界情况和异常场景
3. **回归风险**: 变更是否可能影响已有功能

请阅读 worktree 中的代码和测试文件，给出评估。

输出格式（严格遵守）：
## 评估报告 - QA工程师

### 总体评分: X/10

### 测试覆盖 (X/10)
- 评价...

### 边界条件 (X/10)
- 评价...

### 改善建议
1. ...

### 待补充测试
- ...
""",
        "output": "qa-report-{N}.md",
    },
    "product": {
        "name": "产品经理",
        "prompt": """你是一位产品经理，负责验收功能需求。请从以下维度评估：

1. **需求完整性**: 是否完整实现了需求文档中的所有功能点
2. **用户体验**: 使用方式是否直观、易用
3. **文档完整性**: 是否有充分的说明文档

请阅读需求文档和实际产出，给出评估。

输出格式（严格遵守）：
## 评估报告 - 产品经理

### 总体评分: X/10

### 需求完整性 (X/10)
- 评价...

### 用户体验 (X/10)
- 评价...

### 改善建议
1. ...

### 扩展需求补充
- ...
""",
        "output": "product-review-{N}.md",
    },
    "design": {
        "name": "美术/交互设计",
        "prompt": """你是一位交互设计专家，负责评估表现力和交互质量。请从以下维度评估：

1. **美观度**: 视觉呈现是否专业、一致
2. **交互质量**: 操作流程是否顺畅
3. **信息架构**: 信息组织是否清晰

如果本次变更不涉及 UI/交互，评分默认给 9/10 并说明原因。

输出格式（严格遵守）：
## 评估报告 - 交互设计

### 总体评分: X/10

### 美观度 (X/10)
- 评价...

### 交互质量 (X/10)
- 评价...

### 改善建议
1. ...
""",
        "output": "design-review-{N}.md",
    },
}


SINGLE_REVIEW_PROMPT = """你是一位全栈技术评审专家，请从以下 4 个维度对代码变更进行全面评估：

1. **代码质量** (程序组长视角): 代码清晰度、架构合理性、安全风险、性能影响
2. **测试质量** (QA视角): 测试覆盖、边界条件、回归风险
3. **需求完整性** (产品经理视角): 需求是否完整实现、文档是否充分
4. **交互体验** (设计视角): 美观度、交互质量、信息架构（如不涉及UI则此项默认满分）

## 任务信息
- 任务: {title}
- 描述: {description}
- 迭代轮次: {iteration}

## 项目上下文
{context}

请严格按以下格式输出评估报告：

# 综合评估报告

## 代码质量评分: X/10
（评价内容...）

## 测试质量评分: X/10
（评价内容...）

## 需求完整性评分: X/10
（评价内容...）

## 交互体验评分: X/10
（评价内容...）

## 总体评分: X/10

## 改善建议
1. ...

## 风险点
- ...
"""


class Evaluator:
    """评估引擎."""

    def __init__(self, config: Optional[object] = None) -> None:
        self.config = config
        self.score_pattern = re.compile(r"总体评分[:：]\s*(\d+(?:\.\d+)?)\s*/\s*10")

    def evaluate(self, task: Task, roles: Optional[list[str]] = None) -> list[EvaluationResult]:
        """执行评估."""
        if roles is None:
            roles = list(EVALUATION_ROLES.keys())

        results: list[EvaluationResult] = []
        wt = task.worktree_path

        for role_key in roles:
            role_config = EVALUATION_ROLES.get(role_key)
            if not role_config:
                continue

            report_name = role_config["output"].format(N=task.iteration)
            reports_dir = Path(wt) / "docs" / "reviews" if wt else Path("docs/reviews")
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / report_name

            # 尝试 LLM 评估
            report_content = self._llm_evaluate(task, role_key, role_config)

            if report_content:
                report_path.write_text(report_content, encoding="utf-8")
                score = self._extract_score(report_content)
            else:
                # fallback: 生成占位报告
                report_content = self._generate_placeholder_report(task, role_key, role_config)
                report_path.write_text(report_content, encoding="utf-8")
                score = 1.0

            if str(report_path) not in task.documents:
                task.documents.append(str(report_path))

            result = EvaluationResult(
                role=role_key,
                score=score,
                report_path=str(report_path),
                feedback=f"评估报告: {report_name}",
            )
            results.append(result)

        task.evaluation_results = results
        return results

    def evaluate_single(self, task: Task) -> list[EvaluationResult]:
        """单次 LLM 调用完成全部评估（合并 4 角色为 1 次调用）."""
        wt = task.worktree_path or "."
        context = self._collect_context(wt)
        prompt = SINGLE_REVIEW_PROMPT.format(
            title=task.title, description=task.description,
            iteration=task.iteration, context=context,
        )

        report_content = self._call_llm(prompt, wt)

        reports_dir = Path(wt) / "docs" / "reviews"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"review-{task.iteration}.md"

        if report_content:
            report_path.write_text(report_content, encoding="utf-8")
            overall_score = self._extract_score(report_content)
            # 也提取各维度分数
            dim_scores = self._extract_dimension_scores(report_content)
        else:
            report_content = f"# 综合评估报告 (占位)\n\n总体评分: 1/10\n\nLLM 不可用，请手动评分。"
            report_path.write_text(report_content, encoding="utf-8")
            overall_score = 1.0
            dim_scores = {}

        results = []
        for role_key in EVALUATION_ROLES:
            score = dim_scores.get(role_key, overall_score)
            results.append(EvaluationResult(
                role=role_key, score=score,
                report_path=str(report_path),
                feedback=f"综合评估 - {role_key}: {score}/10",
            ))

        task.evaluation_results = results
        if str(report_path) not in task.documents:
            task.documents.append(str(report_path))
        return results

    def _llm_evaluate(self, task: Task, role_key: str, role_config: dict) -> Optional[str]:
        """尝试通过 LLM 执行评估."""
        wt = task.worktree_path or "."
        context = self._collect_context(wt)
        prompt = f"""{role_config["prompt"]}

## 任务信息
- 任务: {task.title}
- 描述: {task.description}
- 迭代轮次: {task.iteration}

## 项目上下文
{context}

请严格按照输出格式给出评估。"""
        return self._call_llm(prompt, wt)

    def _call_llm(self, prompt: str, wt: str = ".") -> Optional[str]:
        """统一 LLM 调用入口，依次尝试 claude → hermes → opencode."""
        cwd = wt if Path(wt).exists() else None

        # 1. claude CLI
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--max-turns", "1"],
                capture_output=True, text=True, timeout=120, cwd=cwd,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 2. hermes CLI
        try:
            hermes_bin = "/root/.hermes/hermes-agent/venv/bin/python"
            result = subprocess.run(
                [hermes_bin, "-m", "hermes_cli.main", "chat", "-q", prompt, "--yolo"],
                capture_output=True, text=True, timeout=180, cwd=cwd,
            )
            if result.returncode == 0 and result.stdout.strip():
                content = self._clean_hermes_output(result.stdout)
                if content:
                    return content
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 3. opencode
        try:
            result = subprocess.run(
                ["opencode", "run", prompt],
                capture_output=True, text=True, timeout=120, cwd=cwd,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return None

    def _extract_dimension_scores(self, text: str) -> dict[str, float]:
        """从综合报告中提取各维度分数."""
        dim_map = {
            "代码质量": "tech_lead",
            "测试质量": "qa",
            "需求完整性": "product",
            "交互体验": "design",
        }
        scores = {}
        for cn_name, role_key in dim_map.items():
            pattern = re.compile(rf"{cn_name}评分[:：]\s*(\d+(?:\.\d+)?)\s*/\s*10")
            match = pattern.search(text)
            if match:
                scores[role_key] = min(float(match.group(1)), 10.0)
        return scores

    def _collect_context(self, worktree_path: str) -> str:
        """收集 worktree 中的文件内容."""
        wt = Path(worktree_path)
        if not wt.exists():
            return "(worktree 不存在)"

        parts = []
        # 收集文档
        for doc in wt.glob("docs/**/*.md"):
            try:
                content = doc.read_text(encoding="utf-8")[:2000]
                parts.append(f"### {doc.relative_to(wt)}\n{content}")
            except Exception:
                pass

        # 收集代码文件（最多 10 个）
        code_files = []
        for ext in ["*.py", "*.js", "*.ts", "*.yaml", "*.yml", "*.toml"]:
            code_files.extend(wt.glob(ext))
            code_files.extend(wt.rglob(ext))
        seen = set()
        for f in code_files[:15]:
            rel = str(f.relative_to(wt))
            if rel in seen or "venv" in rel or "__pycache__" in rel:
                continue
            seen.add(rel)
            try:
                content = f.read_text(encoding="utf-8")[:2000]
                parts.append(f"### {rel}\n{content}")
            except Exception:
                pass

        return "\n\n".join(parts[:20]) if parts else "(无文件内容)"

    def _extract_score(self, text: str) -> float:
        """从报告中提取评分."""
        match = self.score_pattern.search(text)
        if match:
            return min(float(match.group(1)), 10.0)
        return 1.0

    def _generate_placeholder_report(self, task: Task, role_key: str, role_config: dict) -> str:
        """生成占位评估报告."""
        return f"""# 评估报告 - {role_config["name"]} (占位)

> ⚠️ 此报告为自动生成占位，LLM 评估不可用。
> 请手动填写评估内容，或确保 claude/opencode CLI 可用。

## 任务: {task.title}

### 总体评分: 1/10

### 说明
LLM 评估器未连接，请手动评分。

### 改善建议
- 配置 LLM CLI (claude 或 opencode) 以启用自动评估
- 或手动修改此文件填写实际评分
"""

    def _clean_hermes_output(self, raw: str) -> Optional[str]:
        """清理 hermes TUI 输出，只保留评估报告正文."""
        import re as _re
        # 去掉 ANSI 转义码
        ansi_clean = _re.sub(r'\x1b\[[0-9;]*[a-zA-Z]?', '', raw)
        lines = ansi_clean.split("\n")
        
        # 策略：找到 hermes 真正的评估输出
        # hermes 的评估通常在 "Hermes" 标记之后，以 ## 开头
        # 关键标记：hermes 输出中会有 "⚕ Hermes" 或类似标志
        
        # 找到评估报告真正的开始（第二个 "## 评估报告" 出现的位置，第一个是 prompt 模板）
        report_starts = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## 评估报告"):
                report_starts.append(i)
        
        # 取最后一个 "## 评估报告" 开始的内容（hermes 的实际回复）
        if report_starts:
            start_idx = report_starts[-1]
            content_lines = []
            for line in lines[start_idx:]:
                stripped = line.strip()
                # 遇到 hermes 结束标记就停
                if "Resume this session" in stripped or "Session:" in stripped:
                    break
                # 跳过空行但保留有内容的行
                if stripped:
                    content_lines.append(stripped)
            if content_lines:
                return "\n".join(content_lines)
        
        # Fallback: 找 "总体评分" 所在段落
        for i, line in enumerate(lines):
            if "总体评分" in line:
                # 往前找到最近的 ## 标题
                start = i
                for j in range(i - 1, max(0, i - 20), -1):
                    if lines[j].strip().startswith("## "):
                        start = j
                        break
                content_lines = []
                for line in lines[start:]:
                    stripped = line.strip()
                    if "Resume this session" in stripped:
                        break
                    if stripped:
                        content_lines.append(stripped)
                if content_lines:
                    return "\n".join(content_lines)
        
        return None

    def check_all_passed(self, task: Task) -> bool:
        """检查所有评估是否通过."""
        return all(r.score >= 9.0 for r in task.evaluation_results)

    def get_failed_roles(self, task: Task) -> list[str]:
        """获取未通过的评估角色."""
        return [r.role for r in task.evaluation_results if r.score < 9.0]

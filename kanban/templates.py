"""Jinja2 模板渲染."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class TemplateRenderer:
    """Jinja2 模板渲染器."""

    def __init__(self, templates_dir: str | Path | None = None) -> None:
        tdir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(tdir)),
            keep_trailing_newline=True,
        )

    def render(self, template_name: str, **context: Any) -> str:
        """渲染模板."""
        tmpl = self.env.get_template(template_name)
        return tmpl.render(**context)

    def render_to_file(self, template_name: str, output_path: str | Path, **context: Any) -> Path:
        """渲染模板并写入文件."""
        content = self.render(template_name, **context)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content)
        return out

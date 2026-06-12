"""본문 문단(Paragraph)과 인라인 글조각(Run)."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Component, RenderContext


@dataclass
class Run:
    """문단 안의 글조각. 일부 서식만 지정하면 나머지는 테마 본문값을 따른다."""

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str | None = None
    font: str | None = None
    size: float | None = None
    highlight: str | None = None
    strike: bool = False


def _coerce_run(value) -> Run:
    if isinstance(value, Run):
        return value
    if isinstance(value, str):
        return Run(value)
    raise TypeError(f"Paragraph 의 run 은 str 또는 Run 이어야 합니다: {value!r}")


class Paragraph(Component):
    """하나 이상의 Run 으로 이루어진 본문 문단.

    사용 예::

        Paragraph("간단한 한 줄")
        Paragraph(Run("강조", bold=True, color="#1F4E79"), " 그리고 보통 글씨", align="JUSTIFY")
    """

    def __init__(self, *runs, align: str | None = None) -> None:
        self.runs: list[Run] = [_coerce_run(r) for r in runs]
        self.align = align

    def render(self, ctx: RenderContext) -> None:
        indent = ctx.current_depth if ctx.theme.indent_body else 0
        para_ref = ctx.styles.outline_para(indent_level=indent, align=self.align)
        paragraph = ctx.doc.add_paragraph(
            "",
            para_pr_id_ref=para_ref,
            include_run=False,
            inherit_style=False,
        )
        theme_body = ctx.theme.body
        if not self.runs:
            # 빈 문단(여백). 글자 모양은 본문 기본.
            paragraph.add_run("", char_pr_id_ref=ctx.styles.body_char_id())
            return
        for run in self.runs:
            cid = ctx.styles.char_id(
                font=run.font or theme_body.name,
                size=run.size or theme_body.size_pt,
                bold=run.bold,
                italic=run.italic,
                underline=run.underline,
                color=run.color,
                highlight=run.highlight,
                strike=run.strike,
            )
            paragraph.add_run(run.text, char_pr_id_ref=cid)

    def __repr__(self) -> str:  # pragma: no cover
        preview = "".join(r.text for r in self.runs)[:20]
        return f"Paragraph({preview!r})"

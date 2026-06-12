"""페이지 나누기(PageBreak)."""

from __future__ import annotations

from .base import Component, RenderContext


class PageBreak(Component):
    """다음 내용을 새 페이지에서 시작."""

    def render(self, ctx: RenderContext) -> None:
        ctx.doc.add_paragraph("", pageBreak="1", inherit_style=False)

"""글머리표 목록(BulletList)과 번호 목록(NumberedList)."""

from __future__ import annotations

from typing import Sequence

from .base import Component, RenderContext


class _ListBase(Component):
    kind = "bullet"

    def __init__(self, items: Sequence[str], *, level: int | None = None) -> None:
        self.items = list(items)
        #: 마커/번호 단계(0-기반). None 이면 현재 장 깊이에 맞춰 자동.
        self.level = level

    def _effective_level(self, ctx: RenderContext) -> int:
        if self.level is not None:
            return self.level
        return max(ctx.current_depth, 0)

    def _para_ref(self, ctx: RenderContext, level: int) -> str:
        raise NotImplementedError

    def render(self, ctx: RenderContext) -> None:
        level = self._effective_level(ctx)
        para_ref = self._para_ref(ctx, level)
        body = ctx.theme.body
        char_id = ctx.styles.char_id(font=body.name, size=body.size_pt)
        for item in self.items:
            ctx.doc.add_paragraph(
                str(item),
                para_pr_id_ref=para_ref,
                char_pr_id_ref=char_id,
                inherit_style=False,
            )

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({len(self.items)} items, level={self.level})"


class BulletList(_ListBase):
    """글머리표 목록(테마 마커 □/○/-/· 또는 •)."""

    kind = "bullet"

    def _para_ref(self, ctx: RenderContext, level: int) -> str:
        indent = level if ctx.theme.indent_body else min(level, 1)
        return ctx.styles.outline_para(indent_level=indent, marker_level=level)


class NumberedList(_ListBase):
    """번호 목록(1. 2. 3. …)."""

    kind = "number"

    def _para_ref(self, ctx: RenderContext, level: int) -> str:
        return ctx.styles.number_para(level)

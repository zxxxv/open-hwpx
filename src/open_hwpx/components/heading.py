"""제목(Heading) 컴포넌트.

표시 방식(개조식 마커/번호식/일반 굵은 제목)은 테마가 결정한다(StyleSheet.render_heading).
장(Chapter) 제목은 렌더러가 장 번호와 함께 직접 render_heading 을 호출한다.
"""

from __future__ import annotations

from .base import Component, RenderContext


class Heading(Component):
    """제목 한 줄. level 은 0-기반(0=문서 제목, 1=대제목, 2=중제목 …)."""

    def __init__(self, text: str, level: int = 1) -> None:
        self.text = text
        self.level = level

    def render(self, ctx: RenderContext) -> None:
        ctx.styles.render_heading(self.level, self.text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Heading(level={self.level}, {self.text!r})"

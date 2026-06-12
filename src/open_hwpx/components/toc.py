"""자동 목차(TableOfContents).

구조 트리(StructureTree)의 제목들을 모아 정적 목차를 생성한다. 렌더러가 본문보다
먼저 set_entries() 로 제목 목록을 주입한다.

한계: 한컴 없이 페이지 번호를 계산할 수 없어 v1 은 '번호 + 제목'만 출력한다
(page_numbers=True 여도 쪽번호는 생략하고 경고).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Component, RenderContext

if TYPE_CHECKING:  # pragma: no cover
    from ..structure import HeadingRef


class TableOfContents(Component):
    def __init__(
        self,
        *,
        title: str | None = "목  차",
        max_level: int = 3,
        page_numbers: bool = False,
    ) -> None:
        self.title = title
        self.max_level = max_level
        self.page_numbers = page_numbers
        self._entries: list["HeadingRef"] = []

    def set_entries(self, entries) -> None:
        """렌더러가 호출. max_level 이하 항목만 보관."""
        self._entries = [e for e in entries if e.level <= self.max_level]

    def render(self, ctx: RenderContext) -> None:
        from .paragraph import Paragraph, Run

        if self.page_numbers:
            import warnings

            warnings.warn(
                "한컴 없이 페이지 번호를 계산할 수 없어 목차의 쪽번호는 생략됩니다.",
                stacklevel=2,
            )

        if self.title:
            cap = ctx.theme.table_header or ctx.theme.body
            Paragraph(
                Run(self.title, font=cap.name, size=15.0, bold=True),
                align="CENTER",
            ).render(ctx)
            Paragraph().render(ctx)  # 한 줄 여백

        body = ctx.theme.body
        for entry in self._entries:
            indent = "  " * max(entry.level - 1, 0)
            label = f"{entry.number_label} {entry.title}".strip()
            Paragraph(
                Run(f"{indent}{label}", font=body.name, size=body.size_pt)
            ).render(ctx)

    def __repr__(self) -> str:  # pragma: no cover
        return f"TableOfContents(max_level={self.max_level})"

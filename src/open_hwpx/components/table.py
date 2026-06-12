"""표(Table) 컴포넌트."""

from __future__ import annotations

from typing import Sequence

from .base import Component, RenderContext


class Table(Component):
    """행/열 표.

    - header: 헤더 행(0행)의 셀 텍스트. 비우면 헤더 없는 표.
    - rows: 본문 행들.
    - column_widths: 열 너비 가중치(예: [2,3,1]).
    - header_shading: 헤더 행 배경색("#RRGGBB"). None 이면 테마 기본값 사용.
    - merges: 셀 병합 범위 목록(예: ["A2:A3", "B1:C1"]).
    - caption: 표 위에 붙는 설명(예: "<표 1> 추진 일정").
    """

    def __init__(
        self,
        *,
        header: Sequence[str] = (),
        rows: Sequence[Sequence[str]] = (),
        column_widths: Sequence[float] = (),
        header_shading: str | None = None,
        merges: Sequence[str] = (),
        caption: str | None = None,
    ) -> None:
        self.header = list(header)
        self.rows = [list(r) for r in rows]
        self.column_widths = list(column_widths)
        self.header_shading = header_shading
        self.merges = list(merges)
        self.caption = caption

    def _all_rows(self) -> list[list[str]]:
        all_rows: list[list[str]] = []
        if self.header:
            all_rows.append([str(c) for c in self.header])
        all_rows.extend([str(c) for c in r] for r in self.rows)
        return all_rows

    def render(self, ctx: RenderContext) -> None:
        all_rows = self._all_rows()
        if not all_rows:
            raise ValueError("Table 은 header 또는 최소 한 개의 row 가 필요합니다")

        if self.caption:
            from .paragraph import Paragraph, Run

            cap = ctx.theme.caption or ctx.theme.body
            Paragraph(
                Run(self.caption, font=cap.name, size=cap.size_pt, bold=True)
            ).render(ctx)

        col_count = max(len(r) for r in all_rows)
        table = ctx.doc.add_table(len(all_rows), col_count)
        for r, row in enumerate(all_rows):
            for c in range(col_count):
                table.cell(r, c).text = row[c] if c < len(row) else ""

        for merge in self.merges:
            table.merge_cells(merge)

        if self.header:
            shading = self.header_shading or ctx.theme.table_header_shading
            if shading:
                for c in range(col_count):
                    table.set_cell_shading(0, c, shading)

        if self.column_widths:
            table.set_column_widths(self.column_widths)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Table(rows={len(self.rows)}, header={bool(self.header)})"

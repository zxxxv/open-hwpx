"""Renderer: Report(구조 트리 + 컴포넌트)를 HwpxDocument 로 렌더링.

흐름: 문서 생성 → 페이지/머리말·꼬리말 → 표지 → 목차(front matter) → 본문(장 DFS).
컴포넌트는 RenderContext.doc 를 직접 조작한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._compat import A4_SIZE_HWP, HwpxDocument, check_version, mm_to_hwp_units
from ..components.base import RenderContext
from ..components.heading import Heading
from ..components.paragraph import Paragraph, Run
from ..components.toc import TableOfContents
from ..styles.theme import StyleSheet

if TYPE_CHECKING:  # pragma: no cover
    from ..layout import PageConfig
    from ..report import Report


class Renderer:
    def __init__(self, theme) -> None:
        self.theme = theme

    def render(self, report: "Report") -> HwpxDocument:
        check_version()
        doc = HwpxDocument.new()
        self._apply_page(doc, report.page)

        styles = StyleSheet(self.theme, doc)
        ctx = RenderContext(doc=doc, styles=styles)

        # 머리말/꼬리말(섹션 1회 설정)
        if report.header is not None:
            report.header.render(ctx)
        if report.footer is not None:
            report.footer.render(ctx)

        # 표지(메타데이터 제목)
        self._render_cover(ctx, report.metadata)

        # 구조 정규화 + 번호 부여
        report.tree.prepare()
        headings = report.tree.headings()

        # front matter (목차 등)
        for comp in report.front_matter:
            if isinstance(comp, TableOfContents):
                comp.set_entries(headings)
            comp.render(ctx)

        # 본문(장 DFS)
        for chapter in report.tree.root_chapters:
            self._render_chapter(ctx, chapter)

        return doc

    # ---- 내부 ---------------------------------------------------------------
    def _apply_page(self, doc: HwpxDocument, page: "PageConfig | None") -> None:
        if page is None:
            return
        width_mm, height_mm = page.dimensions_mm()
        if page.size.upper() == "A4" and page.width_mm is None:
            width, height = A4_SIZE_HWP
        else:
            width = mm_to_hwp_units(width_mm)
            height = mm_to_hwp_units(height_mm)
        orientation = (page.orientation or "PORTRAIT").upper()
        if orientation == "LANDSCAPE":
            width, height = height, width
        doc.set_page_size(width=width, height=height, orientation=orientation)

        m = page.margins
        doc.set_page_margins(
            left=mm_to_hwp_units(m.left_mm),
            right=mm_to_hwp_units(m.right_mm),
            top=mm_to_hwp_units(m.top_mm),
            bottom=mm_to_hwp_units(m.bottom_mm),
            header=mm_to_hwp_units(m.header_mm),
            footer=mm_to_hwp_units(m.footer_mm),
            gutter=mm_to_hwp_units(m.gutter_mm),
        )

    def _render_cover(self, ctx: RenderContext, metadata) -> None:
        if metadata is None or not getattr(metadata, "title", ""):
            return
        Paragraph().render(ctx)
        Heading(metadata.title, level=0).render(ctx)
        Paragraph().render(ctx)
        sub_lines = [
            getattr(metadata, "organization", ""),
            getattr(metadata, "author", ""),
            getattr(metadata, "date", ""),
        ]
        body = ctx.theme.body
        for line in sub_lines:
            if line:
                Paragraph(Run(line, font=body.name, size=body.size_pt), align="CENTER").render(ctx)

    def _render_chapter(self, ctx: RenderContext, chapter) -> None:
        ctx.current_depth = chapter.level
        # 장 번호를 함께 전달 → 번호식 프리셋은 "1.1 제목" 으로 렌더된다.
        ctx.styles.render_heading(chapter.level, chapter.title, chapter.number)
        for component in chapter.body:
            ctx.current_depth = chapter.level
            component.render(ctx)
        for child in chapter.children:
            self._render_chapter(ctx, child)

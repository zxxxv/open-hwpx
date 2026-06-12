"""머리말(Header)·꼬리말(Footer)·쪽번호(PageNumber).

머리말/꼬리말 content-spec 형식은 상위 빌더(Header/Footer/Paragraph/PageNumber)의
.lower(doc) 를 재사용해 처리한다. 정렬은 상위 구현상 적용되지 않을 수 있다(v1 한계).
"""

from __future__ import annotations

from .._compat import (
    BuilderFooter,
    BuilderHeader,
    BuilderPageNumber,
    BuilderParagraph,
    BuilderRun,
)
from .base import Component, RenderContext


class PageNumber:
    """꼬리말/머리말 안에 들어가는 쪽번호 표식.

    format: "page"(현재 쪽) 등 상위 빌더가 지원하는 값.
    align: 쪽번호 문단 정렬(기본 가운데).
    """

    def __init__(self, fmt: str = "page", align: str = "CENTER") -> None:
        self.fmt = fmt
        self.align = align


def _to_builder_children(items):
    children = []
    for item in items:
        if isinstance(item, PageNumber):
            # 쪽번호를 정렬된 문단으로 감싼다(content-spec 의 align 키가 정렬을 적용).
            children.append(
                BuilderParagraph(children=[BuilderPageNumber(format=item.fmt)], align=item.align)
            )
        elif isinstance(item, str):
            children.append(BuilderParagraph(children=[BuilderRun(text=item)]))
        else:
            raise TypeError(f"머리말/꼬리말 항목은 str 또는 PageNumber 여야 합니다: {item!r}")
    return children


class _BandBase(Component):
    """Header/Footer 공통."""

    _builder = BuilderHeader

    def __init__(self, *items, text: str | None = None, page_number: bool = False) -> None:
        collected = list(items)
        if text is not None:
            collected.append(text)
        if page_number:
            collected.append(PageNumber())
        if not collected:
            raise ValueError("Header/Footer 는 최소 한 개의 항목이 필요합니다")
        self.items = collected

    def render(self, ctx: RenderContext) -> None:
        band = type(self)._builder(children=_to_builder_children(self.items))
        band.lower(ctx.doc, section_index=0)


class Header(_BandBase):
    """문서 상단 머리말."""

    _builder = BuilderHeader


class Footer(_BandBase):
    """문서 하단 꼬리말. page_number=True 로 쪽번호를 넣을 수 있다."""

    _builder = BuilderFooter

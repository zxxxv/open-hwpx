"""open_hwpx.report.v1 스펙: 블록 타입 → 컴포넌트 변환과 검증.

빌더 API 와 동일한 컴포넌트를 만들어, 코드 경로와 JSON 경로가 같은 결과로 수렴한다.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..components.heading import Heading
from ..components.headerfooter import PageNumber
from ..components.image import Image
from ..components.lists import BulletList, NumberedList
from ..components.pagebreak import PageBreak
from ..components.paragraph import Paragraph, Run
from ..components.table import Table
from ..components.toc import TableOfContents

#: 지원 스키마 식별자
SCHEMA_VERSION = "open_hwpx.report.v1"

#: Run 에 전달 가능한 키
_RUN_KEYS = {"text", "bold", "italic", "underline", "color", "font", "size", "highlight", "strike"}

#: 본문 블록 타입(머리말/꼬리말 전용 page_number 제외)
BODY_BLOCK_TYPES = {
    "paragraph",
    "heading",
    "bullets",
    "numbered",
    "table",
    "image",
    "toc",
    "page_break",
}


class SpecError(ValueError):
    """스펙 형식 오류."""


def _run_from(value: Any) -> Run:
    if isinstance(value, str):
        return Run(value)
    if isinstance(value, Mapping):
        unknown = set(value) - _RUN_KEYS
        if unknown:
            raise SpecError(f"run 에 알 수 없는 키: {sorted(unknown)}")
        if "text" not in value:
            raise SpecError("run 에는 'text' 가 필요합니다")
        return Run(**{k: value[k] for k in value})
    raise SpecError(f"run 은 str 또는 객체여야 합니다: {value!r}")


def build_component(block: Mapping[str, Any]):
    """블록 dict 하나를 컴포넌트로 변환."""
    if not isinstance(block, Mapping) or "type" not in block:
        raise SpecError(f"블록에는 'type' 이 필요합니다: {block!r}")
    btype = block["type"]

    if btype == "paragraph":
        runs = block.get("runs")
        if runs is not None:
            parts = [_run_from(r) for r in runs]
        elif "text" in block:
            parts = [Run(block["text"])]
        else:
            parts = []
        return Paragraph(*parts, align=block.get("align"))

    if btype == "heading":
        return Heading(block["text"], block.get("level", 1))

    if btype == "bullets":
        return BulletList(block["items"], level=block.get("level"))

    if btype == "numbered":
        return NumberedList(block["items"], level=block.get("level"))

    if btype == "table":
        return Table(
            header=block.get("header", ()),
            rows=block.get("rows", ()),
            column_widths=block.get("column_widths", ()),
            header_shading=block.get("header_shading"),
            merges=block.get("merges", ()),
            caption=block.get("caption"),
        )

    if btype == "image":
        return Image(
            block["path"],
            width_mm=block.get("width_mm"),
            height_mm=block.get("height_mm"),
            align=block.get("align", "CENTER"),
            caption=block.get("caption"),
            image_format=block.get("image_format"),
        )

    if btype == "toc":
        return TableOfContents(
            title=block.get("title", "목  차"),
            max_level=block.get("max_level", 3),
            page_numbers=block.get("page_numbers", False),
        )

    if btype == "page_break":
        return PageBreak()

    raise SpecError(f"알 수 없는 블록 타입: {btype!r}")


def build_band_items(blocks):
    """머리말/꼬리말 블록 목록 → Header/Footer 가 받는 항목(str/PageNumber)."""
    items = []
    for block in blocks:
        btype = block.get("type")
        if btype == "page_number":
            items.append(PageNumber(block.get("format", "page")))
        elif btype == "paragraph":
            text = block.get("text")
            if text is None and block.get("runs"):
                text = "".join(r["text"] if isinstance(r, Mapping) else str(r) for r in block["runs"])
            items.append(text or "")
        elif btype == "text":
            items.append(block.get("text", ""))
        else:
            raise SpecError(f"머리말/꼬리말에 지원하지 않는 블록: {btype!r}")
    return items

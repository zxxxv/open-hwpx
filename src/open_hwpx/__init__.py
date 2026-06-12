"""open_hwpx — 한글(HWPX) 문서를 쉽게 생성·렌더링·편집하는 컴포넌트 기반 모듈.

빠른 시작::

    from open_hwpx import Report, Paragraph, Run, Table, Image, BulletList

    report = Report.new(title="2026년 사업 추진계획", organization="○○부", date="2026-06-04")
    report.add_toc()
    ch = report.add_chapter("추진 배경")
    ch.add(Paragraph(Run("본 계획은 "), Run("AI 융합교육", bold=True, color="#1F4E79"), Run(" 확산이 목표.")))
    ch.bullets(["디지털 전환 가속", "현장 수요 증가"])
    report.save("보고서.hwpx")

또는 dict/JSON 스펙으로::

    report = Report.from_json("plan.json")
    report.save("보고서.hwpx")
"""

from __future__ import annotations

from .components import (
    BulletList,
    Footer,
    Header,
    Heading,
    Image,
    NumberedList,
    PageBreak,
    PageNumber,
    Paragraph,
    Run,
    Table,
    TableOfContents,
)
from .layout import PageConfig, PageMargins
from .report import Metadata, Report
from .structure import Chapter, StructureTree
from .styles import (
    BUSINESS_REPORT,
    DEFAULT_THEME,
    GOV_KOREAN,
    PLAIN_DOC,
    FontSpec,
    HeadingLevelStyle,
    StyleTheme,
    get_theme,
    preset_names,
)
from .fonts import (
    available_ofl_fonts,
    embed_font,
    ensure_font,
    register_font_file,
    registered_fonts,
)
from .read import RDocument, load, load_document, read_document
from .render_html import render_html

__version__ = "0.1.0"

__all__ = [
    # 최상위
    "Report",
    "Metadata",
    "Chapter",
    "StructureTree",
    # 컴포넌트
    "Paragraph",
    "Run",
    "Heading",
    "Table",
    "Image",
    "BulletList",
    "NumberedList",
    "TableOfContents",
    "Header",
    "Footer",
    "PageNumber",
    "PageBreak",
    # 레이아웃/스타일
    "PageConfig",
    "PageMargins",
    "StyleTheme",
    "FontSpec",
    "HeadingLevelStyle",
    "GOV_KOREAN",
    "BUSINESS_REPORT",
    "PLAIN_DOC",
    "DEFAULT_THEME",
    "get_theme",
    "preset_names",
    # 읽기/렌더
    "load",
    "load_document",
    "read_document",
    "RDocument",
    "render_html",
    # 폰트
    "register_font_file",
    "registered_fonts",
    "embed_font",
    "ensure_font",
    "available_ofl_fonts",
]

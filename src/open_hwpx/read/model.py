"""읽기측 문서 모델.

.hwpx 를 사람이 다루기 쉬운 구조(속성 접근)로 표현한다. id_ref·HWPUNIT 같은
저수준 디테일은 :mod:`open_hwpx.read.reader` 가 흡수하고, 여기에는 깔끔한
dataclass 만 남긴다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class RRun:
    """인라인 텍스트 조각과 그 서식."""

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str | None = None  # "#RRGGBB" (기본 검정은 None)
    size_pt: float | None = None
    font: str | None = None


@dataclass
class RParagraph:
    runs: list[RRun] = field(default_factory=list)
    align: str | None = None  # "left"|"center"|"right"|"justify"

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class RHeading:
    level: int  # 1=문서 제목, 2=대제목, 3=중제목 …
    runs: list[RRun] = field(default_factory=list)
    align: str | None = None

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class RListItem:
    runs: list[RRun] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class RList:
    kind: str  # "bullet"|"number"
    items: list[RListItem] = field(default_factory=list)


@dataclass
class RCell:
    blocks: list[RParagraph] = field(default_factory=list)
    rowspan: int = 1
    colspan: int = 1
    background: str | None = None  # "#RRGGBB"
    header: bool = False

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)


@dataclass
class RTable:
    rows: list[list[RCell]] = field(default_factory=list)  # 행별 '앵커' 셀만(병합 반영)
    col_widths_px: list[int] = field(default_factory=list)


@dataclass
class RImage:
    data_uri: str
    width_px: int | None = None
    height_px: int | None = None
    alt: str = ""


RBlock = Union[RHeading, RParagraph, RList, RTable, RImage]


@dataclass
class RDocument:
    sections: list[list[RBlock]] = field(default_factory=list)
    title: str | None = None

    @property
    def blocks(self) -> list[RBlock]:
        out: list[RBlock] = []
        for sec in self.sections:
            out.extend(sec)
        return out

    @property
    def paragraphs(self) -> list[RParagraph | RHeading]:
        return [b for b in self.blocks if isinstance(b, (RParagraph, RHeading))]

    @property
    def tables(self) -> list[RTable]:
        return [b for b in self.blocks if isinstance(b, RTable)]

    def to_html(self, path=None, **kwargs) -> str:
        """이 문서를 HTML 로 렌더링한다. ``path`` 가 주어지면 파일로 저장."""
        from ..render_html import render_html

        html = render_html(self, **kwargs)
        if path is not None:
            from pathlib import Path

            Path(path).write_text(html, encoding="utf-8")
            return str(path)
        return html

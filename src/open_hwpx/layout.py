"""페이지 설정(크기·여백) report 와 renderer 가 공유"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageMargins:
    """페이지 여백(mm)"""

    top_mm: float = 20.0
    bottom_mm: float = 15.0
    left_mm: float = 20.0
    right_mm: float = 20.0
    header_mm: float = 15.0
    footer_mm: float = 15.0
    gutter_mm: float = 0.0


# 알려진 용지 크기(mm)
_NAMED_SIZES = {
    "A4": (210.0, 297.0),
    "B5": (176.0, 250.0),
    "A5": (148.0, 210.0),
    "LETTER": (215.9, 279.4),
}


@dataclass(frozen=True)
class PageConfig:
    """용지 크기/방향/여백"""

    size: str = "A4"  # "A4"/"B5"/"A5"/"LETTER" 또는 "CUSTOM"
    orientation: str = "PORTRAIT"  # "PORTRAIT" | "LANDSCAPE"
    width_mm: float | None = None  # size="CUSTOM" 일 때 사용
    height_mm: float | None = None
    margins: PageMargins = PageMargins()

    def dimensions_mm(self) -> tuple[float, float]:
        """(가로, 세로) mm. 방향 반영 전 원본 용지 크기"""
        if self.width_mm is not None and self.height_mm is not None:
            return self.width_mm, self.height_mm
        named = _NAMED_SIZES.get(self.size.upper())
        if named is None:
            raise ValueError(f"알 수 없는 용지 크기: {self.size}. width_mm/height_mm 를 지정하세요.")
        return named

"""스타일 기본 토큰: 폰트 사양과 제목 레벨 스타일."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FontSpec:
    """폰트 이름과 크기(pt).

    name 은 '문서에 등록된' face 여야 적용된다. 블랭크 템플릿 등록 face 는
    함초롬바탕 / 함초롬돋움 뿐이므로, 그 외 폰트는 렌더 시 경고 후 기본 폰트로 대체된다.
    """

    name: str
    size_pt: float


@dataclass(frozen=True)
class HeadingLevelStyle:
    """한 제목 레벨의 스타일.

    제목 표시 방식은 세 가지를 조합한다.
    - marker: 개요 글머리표 글자(□/○/-/·). 있으면 글머리표 paraPr 로 마커를 붙인다.
    - numbered: True 면 장 번호(1. / 1.1 …)를 제목 앞에 붙인다.
    - 둘 다 없으면 그냥 굵은 제목(일반 글쓰기).
    레벨 0(표지 제목)은 보통 marker/numbered 없이 align 정렬만 쓴다.
    """

    font: FontSpec
    bold: bool = True
    marker: str | None = None
    numbered: bool = False
    align: str | None = None  # "LEFT" | "CENTER" | "RIGHT" | "JUSTIFY"
    color: str | None = None  # "#RRGGBB"

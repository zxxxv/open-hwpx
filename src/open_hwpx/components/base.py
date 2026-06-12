"""컴포넌트 기반 클래스와 렌더 컨텍스트.

설계(스파이크 반영): 컴포넌트는 빌더 중간 노드를 거치지 않고 RenderContext.doc
(HwpxDocument)를 '직접' 조작한다. render() 는 부수효과로 문서에 내용을 추가한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .._compat import HwpxDocument
    from ..styles.theme import StyleSheet, StyleTheme


@dataclass
class RenderContext:
    """렌더링 동안 공유되는 상태."""

    doc: "HwpxDocument"
    styles: "StyleSheet"
    #: 현재 장(chapter)의 깊이(1-기반). 본문 컴포넌트의 기본 들여쓰기 기준.
    current_depth: int = 0
    #: 자동 캡션 번호 카운터
    figure_count: int = 0
    table_count: int = 0
    _counters: dict = field(default_factory=dict)

    @property
    def theme(self) -> "StyleTheme":
        return self.styles.theme

    def next_figure(self) -> int:
        self.figure_count += 1
        return self.figure_count

    def next_table(self) -> int:
        self.table_count += 1
        return self.table_count


class Component(ABC):
    """보고서 본문을 구성하는 단위(문단·표·그림 등)."""

    @abstractmethod
    def render(self, ctx: RenderContext) -> None:
        """ctx.doc 에 자신을 추가한다."""

    # 디버깅/테스트용 간단 표현
    def __repr__(self) -> str:  # pragma: no cover - 편의용
        return f"{type(self).__name__}()"

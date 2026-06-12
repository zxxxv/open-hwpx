"""문서 구조 트리: 장(Chapter)과 목차/번호 부여.

구조(목차)를 먼저 정하고, 각 장의 body 에 컴포넌트를 '주입'하는 2단계 워크플로의
뼈대다. fluent 빌더와 dict/JSON 스펙 로더가 모두 이 트리를 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:  # pragma: no cover
    from .components.base import Component


@dataclass
class HeadingRef:
    """목차 항목 한 줄."""

    level: int  # 1-기반
    title: str
    number: tuple[int, ...]  # 예: (1,), (1, 2)

    @property
    def number_label(self) -> str:
        """'1.2.' 형태의 번호 문자열(비어 있으면 '')."""
        return ".".join(str(n) for n in self.number) + ("." if self.number else "")


@dataclass
class Chapter:
    """목차의 한 장(章). 자식 장과 본문 컴포넌트를 가진다."""

    title: str
    level: int = 1
    number: tuple[int, ...] = ()
    children: list["Chapter"] = field(default_factory=list)
    body: list["Component"] = field(default_factory=list)

    # ---- 콘텐츠 주입(fluent) -------------------------------------------------
    def add(self, component: "Component") -> "Chapter":
        """본문 컴포넌트를 추가하고 self 를 반환(체이닝용)."""
        self.body.append(component)
        return self

    def extend(self, components) -> "Chapter":
        for c in components:
            self.body.append(c)
        return self

    def add_chapter(self, title: str, *, level: int | None = None) -> "Chapter":
        """하위 장을 추가하고 그 Chapter 를 반환."""
        child = Chapter(title=title, level=level if level is not None else self.level + 1)
        self.children.append(child)
        return child

    # ---- 본문 컴포넌트 sugar -------------------------------------------------
    def paragraph(self, *runs, **kwargs) -> "Chapter":
        from .components.paragraph import Paragraph

        return self.add(Paragraph(*runs, **kwargs))

    def heading(self, text: str, level: int) -> "Chapter":
        from .components.heading import Heading

        return self.add(Heading(text, level))

    def table(self, **kwargs) -> "Chapter":
        from .components.table import Table

        return self.add(Table(**kwargs))

    def image(self, path, **kwargs) -> "Chapter":
        from .components.image import Image

        return self.add(Image(path, **kwargs))

    def bullets(self, items, **kwargs) -> "Chapter":
        from .components.lists import BulletList

        return self.add(BulletList(items, **kwargs))

    def numbers(self, items, **kwargs) -> "Chapter":
        from .components.lists import NumberedList

        return self.add(NumberedList(items, **kwargs))

    def page_break(self) -> "Chapter":
        from .components.pagebreak import PageBreak

        return self.add(PageBreak())


class StructureTree:
    """최상위 장들의 모음. 레벨 정규화·번호 부여·목차 수집을 담당."""

    def __init__(self, root_chapters: list[Chapter] | None = None) -> None:
        self.root_chapters: list[Chapter] = root_chapters or []

    def add_chapter(self, title: str, *, level: int = 1) -> Chapter:
        ch = Chapter(title=title, level=level)
        self.root_chapters.append(ch)
        return ch

    def walk(self) -> Iterator[tuple[Chapter, int]]:
        """깊이우선 순회. (chapter, depth) 를 yield(depth 는 1-기반)."""

        def _walk(chapters: list[Chapter], depth: int):
            for ch in chapters:
                yield ch, depth
                yield from _walk(ch.children, depth + 1)

        yield from _walk(self.root_chapters, 1)

    def normalize_levels(self) -> None:
        """깊이에 맞춰 각 장의 level 을 1-기반으로 정규화."""
        for ch, depth in self.walk():
            ch.level = depth

    def assign_numbers(self) -> None:
        """장마다 계층 번호((1,), (1,1), …)를 매긴다."""

        def _assign(chapters: list[Chapter], prefix: tuple[int, ...]):
            for i, ch in enumerate(chapters, start=1):
                ch.number = prefix + (i,)
                _assign(ch.children, ch.number)

        _assign(self.root_chapters, ())

    def headings(self, max_level: int | None = None) -> list[HeadingRef]:
        """목차 항목 목록(번호 부여 이후 호출)."""
        refs: list[HeadingRef] = []
        for ch, depth in self.walk():
            if max_level is not None and depth > max_level:
                continue
            refs.append(HeadingRef(level=depth, title=ch.title, number=ch.number))
        return refs

    def prepare(self) -> None:
        """렌더 직전 정규화 + 번호 부여를 한 번에 수행."""
        self.normalize_levels()
        self.assign_numbers()

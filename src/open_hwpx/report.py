"""Report: 보고서의 최상위 퍼사드.

두 가지 주입 방식을 모두 지원한다.
1) fluent 빌더:  report.add_chapter("서론").add(Paragraph(...))
2) dict/JSON 스펙: Report.from_spec({...}) / Report.from_json("plan.json")

세팅·구조(테마/페이지/목차/장)를 먼저 정하고, 각 장에 컴포넌트를 주입한 뒤
save()/to_hwpx_document() 로 실제 .hwpx 파일을 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike

from .components.base import Component
from .components.headerfooter import Footer, Header
from .components.toc import TableOfContents
from .layout import PageConfig, PageMargins
from .render.renderer import Renderer
from .structure import Chapter, StructureTree
from .styles import DEFAULT_THEME, get_theme
from .styles.theme import StyleTheme


def _coerce_theme(theme: "StyleTheme | str | None") -> StyleTheme:
    """테마 인자를 StyleTheme 로 정규화(문자열이면 프리셋 이름으로 해석)."""
    if theme is None:
        return DEFAULT_THEME
    if isinstance(theme, str):
        return get_theme(theme)
    return theme


@dataclass
class Metadata:
    """문서 메타데이터(표지에 사용)."""

    title: str = ""
    author: str = ""
    organization: str = ""
    date: str = ""
    subject: str = ""


class Report:
    def __init__(
        self,
        *,
        theme: "StyleTheme | str | None" = None,
        metadata: Metadata | None = None,
        page: PageConfig | None = None,
    ) -> None:
        self.theme: StyleTheme = _coerce_theme(theme)
        self.metadata: Metadata = metadata or Metadata()
        self.page: PageConfig | None = page or PageConfig()
        self.tree = StructureTree()
        self.front_matter: list[Component] = []
        self.header: Header | None = None
        self.footer: Footer | None = None

    # 생성
    @classmethod
    def new(
        cls,
        *,
        title: str = "",
        author: str = "",
        organization: str = "",
        date: str = "",
        theme: "StyleTheme | str | None" = None,
    ) -> "Report":
        return cls(
            theme=theme,
            metadata=Metadata(title=title, author=author, organization=organization, date=date),
        )

    # 구조 세팅
    def set_theme(self, theme: "StyleTheme | str") -> "Report":
        self.theme = _coerce_theme(theme)
        return self

    def set_metadata(self, **fields) -> "Report":
        for key, value in fields.items():
            if not hasattr(self.metadata, key):
                raise AttributeError(f"Metadata 에 없는 항목: {key}")
            setattr(self.metadata, key, value)
        return self

    def set_page(
        self,
        *,
        size: str = "A4",
        orientation: str = "PORTRAIT",
        width_mm: float | None = None,
        height_mm: float | None = None,
        margins: PageMargins | dict | None = None,
        top_mm: float | None = None,
        bottom_mm: float | None = None,
        left_mm: float | None = None,
        right_mm: float | None = None,
        header_mm: float | None = None,
        footer_mm: float | None = None,
        gutter_mm: float | None = None,
    ) -> "Report":
        """용지 크기/방향/여백 설정.

        여백은 margins(PageMargins/dict)로 한 번에, 또는 top_mm/left_mm 등 개별 인자로
        지정할 수 있다. 개별 인자가 margins 보다 우선한다.
        """
        if isinstance(margins, dict):
            margins = PageMargins(**margins)
        base = margins or PageMargins()
        overrides = {
            k: v
            for k, v in {
                "top_mm": top_mm, "bottom_mm": bottom_mm, "left_mm": left_mm,
                "right_mm": right_mm, "header_mm": header_mm, "footer_mm": footer_mm,
                "gutter_mm": gutter_mm,
            }.items()
            if v is not None
        }
        from dataclasses import replace as _replace

        final_margins = _replace(base, **overrides) if overrides else base
        self.page = PageConfig(
            size="CUSTOM" if width_mm is not None else size,
            orientation=orientation,
            width_mm=width_mm,
            height_mm=height_mm,
            margins=final_margins,
        )
        return self

    def set_header(self, *items, text: str | None = None, page_number: bool = False) -> "Report":
        self.header = Header(*items, text=text, page_number=page_number)
        return self

    def set_footer(self, *items, text: str | None = None, page_number: bool = False) -> "Report":
        self.footer = Footer(*items, text=text, page_number=page_number)
        return self

    def add_front_matter(self, component: Component) -> "Report":
        self.front_matter.append(component)
        return self

    def add_toc(self, *, title: str | None = "목  차", max_level: int = 3) -> "Report":
        self.front_matter.append(TableOfContents(title=title, max_level=max_level))
        return self

    def add_chapter(self, title: str, *, level: int = 1) -> Chapter:
        """장을 추가하고 그 Chapter 를 반환(콘텐츠 주입은 Chapter.add 등으로)."""
        return self.tree.add_chapter(title, level=level)

    # 스펙(dict/JSON)
    @classmethod
    def from_spec(cls, spec: dict, *, base_dir=None) -> "Report":
        from .spec.loader import report_from_spec

        return report_from_spec(spec, base_dir=base_dir)

    @classmethod
    def from_json(cls, source: "str | PathLike[str]") -> "Report":
        """JSON 파일 경로 또는 JSON 문자열로부터 Report 생성.

        파일이면 그 파일이 있는 폴더를 기준으로 상대 이미지 경로를 해석한다.
        """
        import json
        from pathlib import Path

        text = source
        base_dir = None
        candidate = None
        try:
            candidate = Path(source)
        except (TypeError, ValueError):
            candidate = None
        if candidate is not None and candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            base_dir = candidate.parent
        return cls.from_spec(json.loads(text), base_dir=base_dir)

    # 출력
    def to_hwpx_document(self):
        """렌더링된 HwpxDocument 를 반환."""
        return Renderer(self.theme).render(self)

    def to_bytes(self) -> bytes:
        return self.to_hwpx_document().to_bytes()

    def save(self, path: "str | PathLike[str]"):
        """렌더링 후 .hwpx 로 저장하고 저장 경로를 반환."""
        return self.to_hwpx_document().save_to_path(path)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Report(title={self.metadata.title!r}, chapters={len(self.tree.root_chapters)})"

"""StyleTheme(선언적 테마)와 StyleSheet(살아있는 문서에 해석)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from .tokens import FontSpec, HeadingLevelStyle

if TYPE_CHECKING:  # pragma: no cover
    from .._compat import HwpxDocument


def number_label(number: tuple[int, ...]) -> str:
    """(1, 2) -> '1.2.' / () -> ''."""
    return ".".join(str(n) for n in number) + ("." if number else "")


@dataclass(frozen=True)
class StyleTheme:
    """보고서 전체의 스타일 정의(불변). override() 로 일부만 바꿔 새 테마를 만든다."""

    name: str
    body: FontSpec
    headings: tuple[HeadingLevelStyle, ...]
    bullet_markers: tuple[str, ...] = ("□", "○", "-", "·")
    #: 본문/제목을 깊이에 따라 좌측으로 들여쓸지(개조식=True, 일반 글쓰기=False)
    indent_body: bool = True
    #: 한 레벨당 들여쓰기 폭(글자 수 기준; 실제 폭 = body 크기 × 이 값)
    indent_chars_per_level: float = 2.0
    table_header: FontSpec | None = None
    table_header_shading: str | None = None
    caption: FontSpec | None = None
    colors: dict[str, str] = field(default_factory=dict)

    def heading_style(self, level: int) -> HeadingLevelStyle:
        """레벨(0=표지 제목, 1=대제목 …)의 제목 스타일. 범위를 넘으면 마지막을 반복."""
        if not self.headings:
            raise ValueError("theme 에 heading 스타일이 하나도 없습니다")
        idx = max(0, min(level, len(self.headings) - 1))
        return self.headings[idx]

    def override(self, **changes) -> "StyleTheme":
        return replace(self, **changes)


class StyleSheet:
    """StyleTheme 를 특정 HwpxDocument 에 해석한다(charPr/paraPr id 캐시·재사용)."""

    def __init__(self, theme: StyleTheme, document: "HwpxDocument") -> None:
        self.theme = theme
        self.doc = document
        self._header = document.headers[0]
        self._available_fonts = self._collect_fonts()
        self._char_cache: dict[tuple, str] = {}
        self._align_cache: dict[str, str] = {}
        self._para_cache: dict[tuple, str] = {}
        self._number_refs: list[str] | None = None
        self._warned_fonts: set[str] = set()
        # 한 레벨당 들여쓰기 폭(HWPUNIT) = body 크기(pt) × chars_per_level × 100
        self._indent_step = round(theme.body.size_pt * theme.indent_chars_per_level * 100)

    # ---- 폰트 ---------------------------------------------------------------
    def _collect_fonts(self) -> set[str]:
        faces: set[str] = set()
        for face in getattr(self._header, "font_faces", []) or []:
            name = getattr(face, "face", None) or getattr(face, "name", None)
            if name:
                faces.add(name)
        if not faces:
            faces = {"함초롬바탕", "함초롬돋움"}
        return faces

    def _resolve_font(self, name: str | None) -> str | None:
        if name is None or name in self._available_fonts:
            return name
        # 미등록 폰트는 헤더 fontface 에 '이름'으로 등록한다 → 뷰어에 그 폰트가 있으면 적용된다.
        # (바이너리 임베드=문서에 폰트 동봉은 별도 작업; OFL 폰트 파일이 있어야 한다.)
        if self._register_font_face(name):
            self._available_fonts.add(name)
            return name
        if name not in self._warned_fonts:  # 등록 실패 시에만 경고 후 기본 대체
            warnings.warn(
                f"폰트 '{name}'를 등록하지 못해 기본 폰트로 대체됩니다. "
                f"사용 가능 폰트: {sorted(self._available_fonts)}",
                stacklevel=3,
            )
            self._warned_fonts.add(name)
        return None

    def _register_font_face(self, name: str) -> bool:
        """헤더의 모든 ``<fontface>`` 에 ``<font face=name>`` 을 추가해 폰트를 등록한다.

        register_font_file 로 등록된 폰트 파일이 있으면 바이너리를 동봉(``isEmbedded="1"``)해
        이식성을 확보하고, 없으면 이름만 등록(``isEmbedded="0"``)한다.
        """
        element = getattr(self._header, "element", None)
        if element is None:
            return False
        from lxml import etree

        from ..fonts import embed_font_binary, font_file_for

        hh = "{http://www.hancom.co.kr/hwpml/2011/head}"
        faces = element.findall(f".//{hh}fontface")
        if not faces:
            return False

        embed_ref: str | None = None
        path = font_file_for(name)
        if path:
            try:
                from pathlib import Path

                data = Path(path).read_bytes()
                fmt = Path(path).suffix.lstrip(".").lower() or "ttf"
                embed_ref = embed_font_binary(self.doc, data, fmt)
            except Exception:  # pragma: no cover - 파일 문제 시 이름만 등록으로 폴백
                embed_ref = None

        for face in faces:
            fonts = face.findall(f"{hh}font")
            if any(f.get("face") == name for f in fonts):
                continue
            font_el = etree.SubElement(face, f"{hh}font")
            font_el.set("id", str(len(fonts)))
            font_el.set("face", name)
            font_el.set("type", "TTF")
            if embed_ref:
                font_el.set("isEmbedded", "1")
                font_el.set("binaryItemIDRef", embed_ref)
            else:
                font_el.set("isEmbedded", "0")
            face.set("fontCnt", str(len(fonts) + 1))
        return True

    # ---- 글자 모양 -----------------------------------------------------------
    def char_id(
        self,
        *,
        font: str | None = None,
        size: float | None = None,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        color: str | None = None,
        highlight: str | None = None,
        strike: bool = False,
    ) -> str:
        resolved = self._resolve_font(font)
        key = (resolved, size, bold, italic, underline, color, highlight, strike)
        cached = self._char_cache.get(key)
        if cached is not None:
            return cached
        cid = self.doc.ensure_run_style(
            bold=bold, italic=italic, underline=underline, color=color,
            font=resolved, size=size, highlight=highlight, strike=strike or None,
        )
        self._char_cache[key] = cid
        return cid

    def body_char_id(self, **overrides) -> str:
        params = {"font": self.theme.body.name, "size": self.theme.body.size_pt}
        params.update(overrides)
        return self.char_id(**params)

    # ---- 문단 모양(정렬/들여쓰기/마커) --------------------------------------
    def align_ref(self, align: str | None) -> str | None:
        if not align:
            return None
        norm = align.strip().upper()
        if norm in ("", "JUSTIFY"):
            return None
        cached = self._align_cache.get(norm)
        if cached is not None:
            return cached
        ref = self._header.ensure_paragraph_alignment(norm)
        self._align_cache[norm] = ref
        return ref

    def outline_para(
        self,
        *,
        indent_level: int = 0,
        marker_level: int | None = None,
        align: str | None = None,
    ) -> str | None:
        """좌측여백(indent_level 단계) + 선택적 마커/정렬을 가진 paraPr id.

        모두 기본값이면 None(=기본 paraPr 0)을 반환한다.
        """
        norm_align = (align or "").strip().upper() or None
        if norm_align == "JUSTIFY":
            norm_align = None
        if indent_level <= 0 and marker_level is None and norm_align is None:
            return None

        key = (indent_level, marker_level, norm_align)
        cached = self._para_cache.get(key)
        if cached is not None:
            return cached

        marker_char = None
        if marker_level is not None:
            markers = self.theme.bullet_markers or ("·",)
            marker_char = markers[max(0, min(marker_level, len(markers) - 1))]

        from ..render.paraprops import ensure_outline_para

        try:
            ref = ensure_outline_para(
                self._header,
                left=max(indent_level, 0) * self._indent_step,
                marker_char=marker_char,
                marker_level=marker_level or 0,
                align=norm_align,
            )
        except Exception:  # pragma: no cover - 내부 구조 변동 시 폴백
            ref = self.align_ref(norm_align)
        self._para_cache[key] = ref
        return ref

    def number_para(self, level: int) -> str:
        """번호 목록 paraPr id(자동 1.2.3. + 레벨 들여쓰기)."""
        if self._number_refs is None:
            count = max(level + 1, 4)
            self._number_refs = self.doc.ensure_numbering(
                kind="number", levels=[{} for _ in range(count)]
            )
            if self.theme.indent_body:
                from ..render.paraprops import patch_left_margin

                for lv, ref in enumerate(self._number_refs):
                    try:
                        patch_left_margin(self._header, ref, lv * self._indent_step)
                    except Exception:  # pragma: no cover
                        pass
        idx = max(0, min(level, len(self._number_refs) - 1))
        return self._number_refs[idx]

    # ---- 제목 렌더링(테마가 표시 방식을 결정) --------------------------------
    def render_heading(self, level: int, text: str, number: tuple[int, ...] | None = None) -> None:
        """제목 한 줄을 테마 규칙대로 문서에 추가한다."""
        style = self.theme.heading_style(level)
        display = text
        if style.numbered and number:
            display = f"{number_label(number)} {text}".strip()

        cid = self.char_id(
            font=style.font.name, size=style.font.size_pt,
            bold=style.bold, color=style.color or self.theme.colors.get("heading"),
        )

        if level <= 0:
            para_ref = self.align_ref(style.align)
        elif style.marker is not None:
            indent = (level - 1) if self.theme.indent_body else 0
            para_ref = self.outline_para(indent_level=indent, marker_level=level - 1, align=style.align)
        else:
            indent = (level - 1) if self.theme.indent_body else 0
            para_ref = self.outline_para(indent_level=indent, align=style.align)

        self.doc.add_paragraph(display, para_pr_id_ref=para_ref, char_pr_id_ref=cid, inherit_style=False)

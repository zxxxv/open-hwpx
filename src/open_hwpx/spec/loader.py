"""dict/JSON 스펙 → Report 로더."""

from __future__ import annotations

from dataclasses import fields as _dc_fields
from typing import Any, Mapping

from ..layout import PageConfig, PageMargins
from ..styles import DEFAULT_THEME, get_theme
from ..styles.theme import StyleTheme
from ..styles.tokens import FontSpec
from .schema import SCHEMA_VERSION, SpecError, build_band_items, build_component


def _theme_by_name(name: str) -> StyleTheme:
    try:
        return get_theme(name)
    except KeyError:
        return DEFAULT_THEME


def _resolve_theme(theme_spec: Any) -> StyleTheme:
    if theme_spec is None:
        return DEFAULT_THEME
    if isinstance(theme_spec, StyleTheme):
        return theme_spec
    if isinstance(theme_spec, str):
        return _theme_by_name(theme_spec)
    if isinstance(theme_spec, Mapping):
        base = _theme_by_name(theme_spec.get("name", "")) if theme_spec.get("name") else DEFAULT_THEME
        return _apply_theme_overrides(base, theme_spec.get("overrides") or {})
    raise SpecError(f"theme 형식 오류: {theme_spec!r}")


def _apply_theme_overrides(base: StyleTheme, overrides: Mapping[str, Any]) -> StyleTheme:
    changes: dict[str, Any] = {}
    if "body" in overrides:
        b = overrides["body"]
        changes["body"] = FontSpec(b.get("font", base.body.name), b.get("size_pt", base.body.size_pt))
    if "bullet_markers" in overrides:
        changes["bullet_markers"] = tuple(overrides["bullet_markers"])
    if "table_header_shading" in overrides:
        changes["table_header_shading"] = overrides["table_header_shading"]
    if "colors" in overrides:
        merged = dict(base.colors)
        merged.update(overrides["colors"])
        changes["colors"] = merged
    return base.override(**changes) if changes else base


def _build_metadata(report, meta_spec: Mapping[str, Any]) -> None:
    if not meta_spec:
        return
    known = {f.name for f in _dc_fields(report.metadata)}
    report.set_metadata(**{k: v for k, v in meta_spec.items() if k in known})


def _build_page(page_spec: Mapping[str, Any]) -> PageConfig:
    margins_spec = page_spec.get("margins")
    margins = PageMargins(**margins_spec) if isinstance(margins_spec, Mapping) else PageMargins()
    width_mm = page_spec.get("width_mm")
    return PageConfig(
        size="CUSTOM" if width_mm is not None else page_spec.get("size", "A4"),
        orientation=page_spec.get("orientation", "PORTRAIT"),
        width_mm=width_mm,
        height_mm=page_spec.get("height_mm"),
        margins=margins,
    )


def _resolve_image_path(path: Any, base_dir) -> Any:
    if base_dir is None or not isinstance(path, str):
        return path
    from pathlib import Path

    p = Path(path)
    if p.is_absolute() or path.startswith(("http://", "https://")):
        return path
    return str(Path(base_dir) / p)


def _add_body_block(chapter, block: Mapping[str, Any], base_dir) -> None:
    """본문 블록 하나를 장에 추가(markdown 은 여러 컴포넌트로 확장)."""
    btype = block.get("type")
    if btype in ("markdown", "md"):
        from ..markdown import md_to_components

        text = block.get("md") or block.get("text") or ""
        chapter.extend(md_to_components(text, base_dir=base_dir))
        return
    if btype == "image":
        block = {**block, "path": _resolve_image_path(block.get("path"), base_dir)}
    chapter.add(build_component(block))


def _build_chapter(node: Mapping[str, Any], add_chapter, base_dir) -> None:
    if "title" not in node:
        raise SpecError(f"chapter 에는 'title' 이 필요합니다: {node!r}")
    chapter = add_chapter(node["title"], level=node.get("level", 1))
    for block in node.get("body", []):
        _add_body_block(chapter, block, base_dir)
    # 장 단축 필드: md 문자열을 본문 끝에 덧붙인다
    if node.get("md"):
        from ..markdown import md_to_components

        chapter.extend(md_to_components(node["md"], base_dir=base_dir))
    for child in node.get("chapters", []):
        _build_chapter(child, chapter.add_chapter, base_dir)


def report_from_spec(spec: Mapping[str, Any], *, base_dir=None):
    """dict 스펙으로부터 Report 를 만든다. base_dir 은 상대 이미지/경로 해석 기준."""
    from ..report import Report  # 지연 import (순환 방지)

    if not isinstance(spec, Mapping):
        raise SpecError("스펙은 객체(dict)여야 합니다")
    declared = spec.get("schema")
    if declared is not None and declared != SCHEMA_VERSION:
        raise SpecError(f"지원하지 않는 schema: {declared!r} (기대값 {SCHEMA_VERSION!r})")

    report = Report(theme=_resolve_theme(spec.get("theme")))
    _build_metadata(report, spec.get("metadata") or {})

    if spec.get("page"):
        report.page = _build_page(spec["page"])

    header = spec.get("header")
    if header:
        report.set_header(*build_band_items(header.get("blocks", [])))
    footer = spec.get("footer")
    if footer:
        report.set_footer(*build_band_items(footer.get("blocks", [])))

    for block in spec.get("front_matter", []):
        report.add_front_matter(build_component(block))

    for node in spec.get("chapters", []):
        _build_chapter(node, report.add_chapter, base_dir)

    return report

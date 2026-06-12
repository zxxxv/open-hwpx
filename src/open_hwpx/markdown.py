"""Markdown 텍스트 → 컴포넌트 목록 변환.

JSON 으로 구조(장/테마/페이지)를 주고, 각 장의 본문은 Markdown 으로 빠르게 쓰는
하이브리드 워크플로를 지원한다. markdown-it-py 의 구문 트리를 컴포넌트로 매핑한다.

지원: 제목(#~####), 문단(**굵게**/*기울임*/`코드`/[링크]), 글머리표/번호 목록(중첩),
표(GFM), 이미지(![alt](src)), 코드블록, 인용. 수평선(---)은 무시한다.
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from .components.base import Component
from .components.heading import Heading
from .components.image import Image
from .components.lists import BulletList, NumberedList
from .components.paragraph import Paragraph, Run
from .components.table import Table

_MD = MarkdownIt("commonmark").enable("table")


def md_to_components(
    text: str,
    *,
    base_heading_level: int = 1,
    base_dir: "str | PathLike[str] | None" = None,
) -> list[Component]:
    """Markdown 문자열을 컴포넌트 목록으로 변환."""
    if not text or not text.strip():
        return []
    tree = SyntaxTreeNode(_MD.parse(text))
    out: list[Component] = []
    base = Path(base_dir) if base_dir is not None else None
    for node in tree.children:
        _emit_block(node, out, base_heading_level, base)
    return out


def markdown_to_report(
    text: str,
    *,
    theme=None,
    title: str = "",
    base_dir: "str | PathLike[str] | None" = None,
):
    """순수 Markdown 문서를 Report 로 변환.

    '# 제목' → 장, '## 제목' → 하위 장, 그 외는 현재 장의 본문이 된다.
    첫 제목 이전 내용은 기본 장에 담긴다.
    """
    from .report import Report

    report = Report(theme=theme)
    if title:
        report.metadata.title = title

    top = None
    sub = None
    for comp in md_to_components(text, base_dir=base_dir):
        if isinstance(comp, Heading) and comp.level == 1:
            top, sub = report.add_chapter(comp.text), None
        elif isinstance(comp, Heading) and comp.level == 2 and top is not None:
            sub = top.add_chapter(comp.text)
        else:
            target = sub or top
            if target is None:
                target = top = report.add_chapter(title or "본문")
            target.add(comp)
    return report


# 블록
def _emit_block(node, out: list[Component], base_level: int, base_dir: Path | None) -> None:
    t = node.type
    if t == "heading":
        level = int(node.tag[1:])  # h1 -> 1
        out.append(Heading(_plain(node), level=max(1, base_level + level - 1)))
    elif t == "paragraph":
        _emit_paragraph(node, out, base_dir)
    elif t == "bullet_list":
        _emit_list(node, out, level=0, ordered=False, base_dir=base_dir)
    elif t == "ordered_list":
        _emit_list(node, out, level=0, ordered=True, base_dir=base_dir)
    elif t == "table":
        _emit_table(node, out)
    elif t in ("fence", "code_block"):
        for line in node.content.rstrip("\n").splitlines() or [""]:
            out.append(Paragraph(Run(line)))
    elif t == "blockquote":
        for child in node.children:
            _emit_block(child, out, base_level, base_dir)
    # hr 등은 무시


def _emit_paragraph(node, out: list[Component], base_dir: Path | None) -> None:
    inline = node.children[0] if node.children else None
    if inline is None:
        return
    images = _collect_images(inline, base_dir)
    runs = _runs_from_inline(inline)
    if any(r.text.strip() for r in runs):
        out.append(Paragraph(*runs))
    out.extend(images)


def _emit_list(node, out: list[Component], *, level: int, ordered: bool, base_dir: Path | None) -> None:
    items: list[str] = []
    nested: list = []
    for item in node.children:  # list_item
        parts: list[str] = []
        for child in item.children:
            if child.type == "paragraph":
                parts.append(_plain(child))
            elif child.type in ("bullet_list", "ordered_list"):
                nested.append((child, child.type == "ordered_list"))
        items.append(" ".join(p for p in parts if p))
    if items:
        cls = NumberedList if ordered else BulletList
        out.append(cls(items, level=level))
    for child, child_ordered in nested:
        _emit_list(child, out, level=level + 1, ordered=child_ordered, base_dir=base_dir)


def _emit_table(node, out: list[Component]) -> None:
    header: list[str] = []
    rows: list[list[str]] = []
    for section in node.children:  # thead / tbody
        for tr in section.children:  # table_row
            cells = [_plain(cell) for cell in tr.children]
            if section.type == "thead":
                header = cells
            else:
                rows.append(cells)
    if header or rows:
        out.append(Table(header=header, rows=rows))


# 인라인
def _runs_from_inline(inline) -> list[Run]:
    runs: list[Run] = []

    def walk(nodes, bold: bool, italic: bool) -> None:
        for n in nodes:
            if n.type == "text":
                if n.content:
                    runs.append(Run(n.content, bold=bold, italic=italic))
            elif n.type == "strong":
                walk(n.children, True, italic)
            elif n.type == "em":
                walk(n.children, bold, True)
            elif n.type == "code_inline":
                if n.content:
                    runs.append(Run(n.content, bold=bold, italic=italic))
            elif n.type == "link":
                walk(n.children, bold, italic)  # 링크는 표시 텍스트만
            elif n.type in ("softbreak", "hardbreak"):
                runs.append(Run(" ", bold=bold, italic=italic))
            elif n.type == "image":
                pass  # 블록 단계에서 처리
            elif n.children:
                walk(n.children, bold, italic)
            elif getattr(n, "content", ""):
                runs.append(Run(n.content, bold=bold, italic=italic))

    walk(inline.children, False, False)
    return runs


def _collect_images(inline, base_dir: Path | None) -> list[Image]:
    images: list[Image] = []
    for n in inline.children:
        if n.type == "image":
            src = n.attrs.get("src", "")
            if base_dir is not None and src and not _is_absolute(src):
                src = str(base_dir / src)
            alt = n.content or None
            images.append(Image(src, caption=alt))
    return images


def _is_absolute(src: str) -> bool:
    return src.startswith(("http://", "https://", "/")) or (len(src) > 1 and src[1] == ":")


def _plain(node) -> str:
    """노드 하위의 모든 텍스트를 이어붙인 평문."""
    inline = None
    if node.type in ("paragraph", "heading", "th", "td", "table_cell"):
        inline = node.children[0] if node.children else None
    target = inline or node
    parts: list[str] = []

    def walk(nodes) -> None:
        for n in nodes:
            if n.type in ("text", "code_inline"):
                parts.append(n.content)
            elif n.type in ("softbreak", "hardbreak"):
                parts.append(" ")
            elif n.children:
                walk(n.children)
            elif getattr(n, "content", ""):
                parts.append(n.content)

    walk(getattr(target, "children", []) or [])
    return "".join(parts).strip()

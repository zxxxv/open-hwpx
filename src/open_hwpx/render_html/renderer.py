"""읽기측 모델(:class:`RDocument`) → 충실 HTML+CSS.

python-hwpx 내장 ``export_html`` 과 달리 다음을 보존한다:
- 제목 레벨(``<h1>``…``<h6>``), 런 서식(굵게·기울임·밑줄·색·글자크기)
- 표 셀 병합(``colspan``/``rowspan``)·셀 음영·열 너비
- 임베드 이미지(``data:`` URI)
"""

from __future__ import annotations

from ..read.model import (
    RDocument,
    RHeading,
    RImage,
    RList,
    RParagraph,
    RRun,
    RTable,
)

DEFAULT_CSS = """
:root { color-scheme: light dark; }
body {
  font-family: "함초롬바탕", "Noto Serif KR", "Malgun Gothic", "Apple SD Gothic Neo", serif;
  max-width: 820px; margin: 2rem auto; padding: 0 1rem;
  line-height: 1.7; color: #1a1a1a;
}
h1, h2, h3, h4, h5, h6 { font-family: "함초롬돋움", "Noto Sans KR", "Malgun Gothic", sans-serif; line-height: 1.3; }
h1 { font-size: 1.9em; text-align: center; margin: 1.2em 0 0.8em; }
h2 { font-size: 1.45em; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; margin-top: 1.4em; }
h3 { font-size: 1.2em; margin-top: 1.2em; }
h4, h5, h6 { font-size: 1.05em; margin-top: 1em; }
p { margin: 0.45em 0; }
ul, ol { margin: 0.45em 0 0.45em 1.5em; }
li { margin: 0.15em 0; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #555; padding: 5px 9px; vertical-align: top; text-align: left; }
th { background: #f0f0f0; font-weight: bold; }
img { max-width: 100%; height: auto; }
hr.section-break { border: none; border-top: 2px dashed #ccc; margin: 2.5em 0; }
""".strip()


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt_pt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _align_style(align: str | None) -> str:
    if align in ("center", "right", "justify"):
        return f' style="text-align:{align}"'
    return ""


def _render_span(run: RRun) -> str:
    styles: list[str] = []
    if run.bold:
        styles.append("font-weight:bold")
    if run.italic:
        styles.append("font-style:italic")
    if run.underline:
        styles.append("text-decoration:underline")
    if run.color:
        styles.append(f"color:{run.color}")
    if run.size_pt:
        styles.append(f"font-size:{_fmt_pt(run.size_pt)}pt")
    if run.font:
        styles.append(f"font-family:'{run.font}'")
    text = _escape(run.text)
    if not styles:
        return text
    return f'<span style="{";".join(styles)}">{text}</span>'


def _render_runs(runs: list[RRun]) -> str:
    return "".join(_render_span(r) for r in runs)


def _render_table(table: RTable) -> str:
    parts: list[str] = ["<table>"]
    widths = table.col_widths_px
    if widths and any(widths):
        cols = "".join(
            f'<col style="width:{w}px"/>' if w else "<col/>" for w in widths
        )
        parts.append(f"<colgroup>{cols}</colgroup>")
    for row in table.rows:
        parts.append("  <tr>")
        for cell in row:
            tag = "th" if cell.header else "td"
            attrs = ""
            if cell.rowspan > 1:
                attrs += f' rowspan="{cell.rowspan}"'
            if cell.colspan > 1:
                attrs += f' colspan="{cell.colspan}"'
            style = f' style="background:{cell.background}"' if cell.background else ""
            inner = "<br/>".join(_render_runs(b.runs) for b in cell.blocks)
            parts.append(f"    <{tag}{attrs}{style}>{inner}</{tag}>")
        parts.append("  </tr>")
    parts.append("</table>")
    return "\n".join(parts)


def _render_image(image: RImage) -> str:
    style = f' style="width:{image.width_px}px"' if image.width_px else ""
    return f'<img src="{image.data_uri}" alt="{_escape(image.alt)}"{style}/>'


def _render_block(block) -> str:
    if isinstance(block, RHeading):
        return f"<h{block.level}{_align_style(block.align)}>{_render_runs(block.runs)}</h{block.level}>"
    if isinstance(block, RParagraph):
        inner = _render_runs(block.runs)
        return f"<p{_align_style(block.align)}>{inner}</p>" if inner else ""
    if isinstance(block, RList):
        tag = "ol" if block.kind == "number" else "ul"
        items = "".join(f"<li>{_render_runs(it.runs)}</li>" for it in block.items)
        return f"<{tag}>{items}</{tag}>"
    if isinstance(block, RTable):
        return _render_table(block)
    if isinstance(block, RImage):
        return _render_image(block)
    return ""


def render_html(source, *, full_document: bool = True, fragment: bool = False, title: str | None = None) -> str:
    """``RDocument`` 또는 ``.hwpx`` 경로/바이트를 충실 HTML 로 렌더링한다.

    ``fragment=True`` 면 ``<html>`` 래퍼 없이 본문만 반환한다(webview 삽입용).
    """
    from ..read.reader import read_document

    doc = source if isinstance(source, RDocument) else read_document(source)
    if fragment:
        full_document = False

    parts: list[str] = []
    for index, blocks in enumerate(doc.sections):
        if index > 0:
            parts.append('<hr class="section-break"/>')
        for block in blocks:
            html = _render_block(block)
            if html:
                parts.append(html)
    body = "\n".join(parts)

    if not full_document:
        return body

    page_title = _escape(title or doc.title or "HWPX Document")
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '  <meta charset="utf-8"/>\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        f"  <title>{page_title}</title>\n"
        f"  <style>\n{DEFAULT_CSS}\n  </style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>"
    )

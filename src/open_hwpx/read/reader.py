"""`.hwpx` → 읽기측 문서 모델(:mod:`open_hwpx.read.model`).

python-hwpx 의 저수준 읽기 API(id_ref·HWPUNIT·child_attributes 등)를 이 한 곳에서
흡수하고, 바깥에는 깔끔한 :class:`RDocument` 만 내보낸다.

설계 근거(샘플로 경험적 확정):
- 런 서식: ``run.style`` 의 ``child_attributes`` 에 'bold'/'italic' 키 존재 = 적용,
  밑줄은 ``underline_type() != 'NONE'``, 색은 ``textColor``(#000000=기본), 크기 ``height/100``.
- 제목: 단일 속성이 없다. **굵게 + 본문보다 큰 글자**를 제목으로 보고, 개요 레벨은
  ``paragraph.heading.level`` 로 깊이를 매긴다(불릿 리스트 항목은 굵지 않아 제외됨).
- 표 병합: ``table.get_cell_map()`` 이 병합 인식 격자를 준다(앵커 셀에만 colspan/rowspan).
- 셀 음영: ``borderFillIDRef`` → ``border_fill`` → ``fillBrush/winBrush/@faceColor``.
"""

from __future__ import annotations

import base64
import io
from collections import Counter

from .._compat import HwpxDocument
from .model import (
    RCell,
    RDocument,
    RHeading,
    RImage,
    RList,
    RListItem,
    RParagraph,
    RRun,
    RTable,
)

_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_HC = "http://www.hancom.co.kr/hwpml/2011/core"

_ALIGN = {
    "LEFT": "left",
    "CENTER": "center",
    "RIGHT": "right",
    "JUSTIFY": "justify",
    "DISTRIBUTE": "justify",
}

# HWPUNIT(1/7200인치) → CSS px(96dpi)
_PX_PER_HWPUNIT = 96.0 / 7200.0


def _hwp_to_px(value) -> int | None:
    try:
        return round(int(value) * _PX_PER_HWPUNIT)
    except (TypeError, ValueError):
        return None


def _media_type(fmt: str) -> str:
    f = (fmt or "png").lower()
    return {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "bmp": "bmp"}.get(f, "png")


def _is_hex_color(value) -> bool:
    return isinstance(value, str) and value.startswith("#") and len(value) == 7


def _open(src) -> HwpxDocument:
    if isinstance(src, HwpxDocument):
        return src
    if isinstance(src, (bytes, bytearray)):
        return HwpxDocument.open(io.BytesIO(bytes(src)))
    return HwpxDocument.open(str(src))


# ---------------------------------------------------------------- run / paragraph


def _read_run(run) -> RRun | None:
    text = run.text or ""
    if text == "":
        return None
    st = run.style
    if st is None:
        return RRun(text=text)
    attrs = dict(getattr(st, "attributes", {}) or {})
    child = getattr(st, "child_attributes", {}) or {}
    bold = "bold" in child
    italic = "italic" in child
    try:
        underline = (st.underline_type() or "NONE") != "NONE"
    except Exception:
        underline = False
    color = attrs.get("textColor")
    if color in (None, "#000000", "none"):
        color = None
    height = attrs.get("height")
    size_pt = None
    if height is not None and str(height).isdigit():
        size_pt = int(height) / 100.0
    return RRun(text=text, bold=bold, italic=italic, underline=underline, color=color, size_pt=size_pt)


def _read_runs(paragraph) -> list[RRun]:
    out: list[RRun] = []
    for run in paragraph.runs:
        rr = _read_run(run)
        if rr is not None:
            out.append(rr)
    return out


def _para_align(doc, paragraph) -> str | None:
    ref = paragraph.para_pr_id_ref
    if ref is None:
        return None
    try:
        pp = doc.paragraph_property(ref)
    except Exception:
        return None
    horizontal = getattr(getattr(pp, "align", None), "horizontal", None)
    return _ALIGN.get(horizontal)


def _para_heading(doc, paragraph) -> tuple[str, int]:
    ref = paragraph.para_pr_id_ref
    if ref is None:
        return ("NONE", 0)
    try:
        pp = doc.paragraph_property(ref)
    except Exception:
        return ("NONE", 0)
    hd = getattr(pp, "heading", None)
    htype = getattr(hd, "type", None) or "NONE"
    try:
        hlevel = int(getattr(hd, "level", 0) or 0)
    except (TypeError, ValueError):
        hlevel = 0
    return (htype, hlevel)


# ---------------------------------------------------------------- table


def _find_face_color(element) -> str | None:
    for child in getattr(element, "children", []) or []:
        if getattr(child, "name", None) == "fillBrush":
            for brush in getattr(child, "children", []) or []:
                face = dict(getattr(brush, "attributes", {}) or {}).get("faceColor")
                if face:
                    return face
        found = _find_face_color(child)
        if found:
            return found
    return None


def _cell_background(doc, cell) -> str | None:
    bfi = cell.element.get("borderFillIDRef")
    if not bfi:
        return None
    try:
        bf = doc.border_fill(bfi)
    except Exception:
        bf = None
    if bf is None:
        return None
    color = _find_face_color(bf)
    if color and color.lower() != "none" and _is_hex_color(color):
        return color
    return None


def _read_cell_blocks(doc, cell) -> list[RParagraph]:
    blocks: list[RParagraph] = []
    for cp in cell.paragraphs:
        blocks.append(RParagraph(runs=_read_runs(cp), align=_para_align(doc, cp)))
    return blocks


def _read_table(doc, table) -> RTable:
    grid = table.get_cell_map()
    rows: list[list[RCell]] = []
    for r, grid_row in enumerate(grid):
        cells: list[RCell] = []
        for pos in grid_row:
            if not pos.is_anchor:
                continue
            cell = pos.cell
            cells.append(
                RCell(
                    blocks=_read_cell_blocks(doc, cell),
                    rowspan=pos.row_span,
                    colspan=pos.col_span,
                    background=_cell_background(doc, cell),
                    header=(r == 0),
                )
            )
        rows.append(cells)

    col_widths: list[int] = []
    if grid:
        for pos in grid[0]:
            if not pos.is_anchor:
                continue
            width = _hwp_to_px(getattr(pos.cell, "width", None)) or 0
            share = max(1, pos.col_span)
            for _ in range(share):
                col_widths.append(round(width / share) if width else 0)
    return RTable(rows=rows, col_widths_px=col_widths)


# ---------------------------------------------------------------- image


def _read_bin(doc, name: str) -> bytes | None:
    pkg = doc.package
    candidates = (f"BinData/{name}", f"Contents/BinData/{name}", name)
    for cand in candidates:
        try:
            if hasattr(pkg, "has_part") and pkg.has_part(cand):
                return pkg.read(cand)
        except Exception:
            pass
    try:
        names = pkg.part_names() if callable(getattr(pkg, "part_names", None)) else getattr(pkg, "part_names", [])
        for n in names:
            if n.endswith(name):
                return pkg.read(n)
    except Exception:
        pass
    return None


def _collect_images(doc) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in doc.list_images() or []:
        bindata = item.get("BinData")
        if not bindata:
            continue
        data = _read_bin(doc, bindata)
        if not data:
            continue
        fmt = (item.get("Format") or "png").lower()
        entry = {"bytes": data, "fmt": fmt}
        out[bindata.rsplit(".", 1)[0]] = entry  # 'BIN0001.png' -> 'BIN0001'
        if item.get("id"):
            out.setdefault(str(item["id"]), entry)
    return out


def _read_image(paragraph, images: dict[str, dict]) -> RImage | None:
    pic = paragraph.element.find(f".//{{{_HP}}}pic")
    if pic is None:
        return None
    img = pic.find(f".//{{{_HC}}}img")
    if img is None:
        return None
    ref = img.get("binaryItemIDRef")
    info = images.get(ref) if ref else None
    if info is None:
        return None
    uri = "data:image/{};base64,{}".format(
        _media_type(info["fmt"]), base64.b64encode(info["bytes"]).decode("ascii")
    )
    width = height = None
    sz = pic.find(f".//{{{_HP}}}sz")
    if sz is not None:
        width = _hwp_to_px(sz.get("width"))
        height = _hwp_to_px(sz.get("height"))
    return RImage(data_uri=uri, width_px=width, height_px=height)


# ---------------------------------------------------------------- classification

# 한 문단을 분류하기 전 모아두는 중간 표현.
class _Raw:
    __slots__ = ("runs", "align", "head_type", "head_level", "first_bold", "first_size", "table", "image", "text")

    def __init__(self, doc, paragraph, images):
        table = paragraph.tables[0] if getattr(paragraph, "tables", None) else None
        self.table = _read_table(doc, table) if table is not None else None
        self.image = _read_image(paragraph, images) if self.table is None else None
        self.runs = _read_runs(paragraph)
        self.align = _para_align(doc, paragraph)
        self.head_type, self.head_level = _para_heading(doc, paragraph)
        self.first_bold = self.runs[0].bold if self.runs else False
        self.first_size = self.runs[0].size_pt if self.runs else None
        self.text = "".join(r.text for r in self.runs)


def _modal_size(raws: list[_Raw]) -> float:
    counter = Counter(r.first_size for r in raws if r.text.strip() and r.first_size)
    if not counter:
        return 11.0
    return counter.most_common(1)[0][0]


def _max_size(raws: list[_Raw]) -> float:
    sizes = [r.first_size for r in raws if r.text.strip() and r.first_size]
    return max(sizes) if sizes else 11.0


def _heading_level(raw: _Raw, body_pt: float, max_pt: float) -> int:
    """제목이면 1~6, 아니면 0."""
    if not raw.runs or not raw.first_bold:
        return 0
    size = raw.first_size or body_pt
    if size <= body_pt + 0.5:  # 본문보다 크지 않으면 제목 아님(굵은 캡션·강조 제외)
        return 0
    if raw.head_type in ("BULLET", "NUMBER"):  # 개요 제목: 깊이로 레벨
        return min(6, raw.head_level + 2)  # L0→h2, L1→h3 …
    # 개요 아님(가운데 큰 제목): 최대 크기는 문서 제목(h1), 그 외 h2
    if max_pt and size >= max_pt - 0.01:
        return 1
    return 2


def _classify(raws: list[_Raw], body_pt: float, max_pt: float) -> list:
    blocks: list = []
    list_kind: str | None = None
    list_items: list[RListItem] = []

    def flush() -> None:
        nonlocal list_kind, list_items
        if list_items:
            blocks.append(RList(kind=list_kind, items=list_items))
        list_kind, list_items = None, []

    for raw in raws:
        if raw.table is not None:
            flush()
            blocks.append(raw.table)
            continue
        if raw.image is not None:
            flush()
            blocks.append(raw.image)
            continue
        if not raw.text.strip():
            flush()  # 빈 문단은 건너뛴다(목록 그룹은 끊음)
            continue

        level = _heading_level(raw, body_pt, max_pt)
        if level:
            flush()
            blocks.append(RHeading(level=level, runs=raw.runs, align=raw.align))
            continue

        if raw.head_type in ("BULLET", "NUMBER") and not raw.first_bold:
            kind = "number" if raw.head_type == "NUMBER" else "bullet"
            if list_kind is not None and list_kind != kind:
                flush()
            list_kind = kind
            list_items.append(RListItem(runs=raw.runs))
            continue

        flush()
        blocks.append(RParagraph(runs=raw.runs, align=raw.align))

    flush()
    return blocks


# ---------------------------------------------------------------- entry point


def read_document(src) -> RDocument:
    """``.hwpx`` 파일 경로/바이트/``HwpxDocument`` 를 읽어 :class:`RDocument` 로 변환."""
    doc = _open(src)
    images = _collect_images(doc)

    sections: list[list] = []
    for sec in doc.sections:
        raws = [_Raw(doc, p, images) for p in sec.paragraphs]
        body_pt = _modal_size(raws)
        max_pt = _max_size(raws)
        sections.append(_classify(raws, body_pt, max_pt))

    document = RDocument(sections=sections)
    for block in document.blocks:
        if isinstance(block, RHeading) and block.level == 1:
            document.title = block.text
            break
    return document


#: 사용하기 쉬운 별칭 — ``open_hwpx.load("a.hwpx")``
load = read_document
load_document = read_document

"""에이전트 tool-use 용 고수준 함수 모음.

각 함수는 LLM 도구로 바로 쓰기 좋은 **단순 시그니처 + JSON 직렬화 결과**를 돌려준다.
직접 SDK tool-use(예: Anthropic ``@beta_tool``), 임의 에이전트 프레임워크, 그리고
선택적 MCP 서버(:mod:`open_hwpx.mcp_server`)가 모두 이 함수들을 공유한다.

설계 원칙:
- 절대 예외를 밖으로 던지지 않는다 — 항상 ``{"ok": bool, ...}`` 를 반환해 에이전트가
  ``ok=False`` + ``error`` 를 보고 스스로 고칠 수 있게 한다(self-correct 루프).
- 생성(build) → 되먹임(read/render) → 검증(validate) 세 갈래로 품질 루프를 구성한다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from ._compat import HwpxDocument
from .markdown import markdown_to_report
from .read import load
from .read.model import RHeading
from .render_html import render_html as _render_html
from .report import Report
from .styles import get_theme, preset_names

#: HWPML paragraph 네임스페이스(표 행 XML 편집용).
_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"

#: 에이전트가 ``build_report`` 에 넘길 스펙 형식을 알려주는 짧은 도움말.
REPORT_SPEC_HELP = """\
open_hwpx.report.v1 스펙(JSON object):
{
  "schema": "open_hwpx.report.v1",
  "theme": "gov" | "business" | "plain",
  "metadata": {"title": "...", "organization": "...", "date": "YYYY-MM-DD"},
  "front_matter": [{"type": "toc", "max_level": 3}],
  "footer": {"blocks": [{"type": "page_number"}]},
  "chapters": [
    {"title": "장 제목", "md": "마크다운 본문"},
    {"title": "장", "body": [
        {"type": "paragraph", "runs": [{"text": "...", "bold": true, "color": "#1F4E79"}]},
        {"type": "table", "header": ["A","B"], "rows": [["1","2"]], "merges": ["A2:A3"], "caption": "<표 1>"},
        {"type": "bullets", "items": ["..."]},
        {"type": "page_break"}
     ],
     "chapters": [ ... 중첩 장 ... ]}
  ]
}
"""


def _ok(**fields: Any) -> dict:
    return {"ok": True, **fields}


def _err(exc: Exception) -> dict:
    return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _validate_file(path: str) -> dict:
    rep = HwpxDocument.open(str(path)).validate()
    return {"valid": bool(rep.ok), "issues": [] if rep.ok else [str(e) for e in rep.errors]}


def _open_doc(path: str):
    return HwpxDocument.open(str(path))


def _save_doc(doc, path: str, output_path: str | None) -> str:
    # raw XML 편집(표 행 등)은 section dirty 표시가 있어야 재직렬화된다.
    for section in getattr(doc, "sections", []):
        if hasattr(section, "mark_dirty"):
            section.mark_dirty()
    target = output_path or path
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    doc.save_to_path(str(target))
    return str(target)


def _all_tables(doc) -> list:
    return [t for p in doc.paragraphs for t in (getattr(p, "tables", None) or [])]


# --------------------------------------------------------------- 생성(build)


def build_report(spec: dict, output_path: str, validate: bool = True) -> dict:
    """JSON 스펙(open_hwpx.report.v1)으로 한글(HWPX) 보고서를 생성한다.

    spec 형식은 :data:`REPORT_SPEC_HELP` 참고(또는 ``report_spec_help`` 도구).
    반환: ``{ok, path, valid, issues}`` 또는 ``{ok: false, error}``.
    """
    try:
        if isinstance(spec, str):
            spec = json.loads(spec)
        report = Report.from_spec(spec)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        report.save(out)
    except Exception as exc:  # noqa: BLE001 - 에이전트에 에러를 그대로 전달
        return _err(exc)
    result = _ok(path=str(out))
    if validate:
        result.update(_validate_file(out))
    return result


def build_from_markdown(
    markdown: str,
    output_path: str,
    preset: str = "gov",
    title: str | None = None,
    toc: bool = False,
    page_number: bool = False,
    validate: bool = True,
) -> dict:
    """순수 Markdown(``#`` 제목 = 장)으로 한글(HWPX) 보고서를 생성한다.

    preset: ``gov``/``business``/``plain``. 반환은 :func:`build_report` 와 동일.
    """
    try:
        theme = get_theme(preset) if preset else None
        report = markdown_to_report(markdown, theme=theme, title=title or "문서")
        if toc:
            report.add_toc()
        if page_number:
            report.set_footer(page_number=True)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        report.save(out)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    result = _ok(path=str(out))
    if validate:
        result.update(_validate_file(out))
    return result


# --------------------------------------------------------------- 되먹임(read/render = 에이전트의 눈)


def read_as_markdown(hwpx_path: str) -> dict:
    """기존 .hwpx 의 내용을 Markdown(표 포함)으로 추출한다 — 에이전트가 결과를 검토할 때 사용."""
    try:
        md = HwpxDocument.open(str(hwpx_path)).export_markdown()
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(markdown=md)


def read_as_text(hwpx_path: str) -> dict:
    """기존 .hwpx 의 본문을 평문 텍스트로 추출한다(토큰 절약형 되먹임)."""
    try:
        text = HwpxDocument.open(str(hwpx_path)).export_text()
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(text=text)


def get_outline(hwpx_path: str) -> dict:
    """기존 .hwpx 의 제목 트리(개요)를 추출한다 — 구조 검토용."""
    try:
        doc = load(hwpx_path)
        outline = [
            {"level": b.level, "text": b.text}
            for b in doc.blocks
            if isinstance(b, RHeading)
        ]
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(title=doc.title, outline=outline)


def render_to_html(hwpx_path: str, output_path: str | None = None, fragment: bool = False) -> dict:
    """기존 .hwpx 를 표·서식 보존 HTML 로 렌더한다(미리보기/시각 검토용).

    output_path 가 있으면 파일로 저장하고 경로를 반환, 없으면 HTML 문자열을 반환한다.
    """
    try:
        html = _render_html(str(hwpx_path), fragment=fragment)
        if output_path:
            Path(output_path).write_text(html, encoding="utf-8")
            return _ok(path=output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(html=html)


# --------------------------------------------------------------- 편집 대상 나열(주소 부여)


def list_paragraphs(hwpx_path: str) -> dict:
    """문단을 ``index`` 와 함께 나열한다 — 편집 도구(edit_set_paragraph_text 등)의 index 기준."""
    try:
        doc = _open_doc(hwpx_path)
        items = [
            {"index": i, "text": p.text or "", "has_table": bool(getattr(p, "tables", None))}
            for i, p in enumerate(doc.paragraphs)
        ]
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(paragraphs=items)


def list_tables(hwpx_path: str) -> dict:
    """표를 ``table_index`` 와 셀 격자(텍스트)로 나열한다 — edit_set_cell 의 좌표에 사용.

    병합 셀은 좌상단(anchor)에 텍스트가 있고 가려진 칸은 ``null`` 로 표시된다.
    """
    try:
        doc = _open_doc(hwpx_path)
        out = []
        for ti, tbl in enumerate(_all_tables(doc)):
            rows = [
                [pos.cell.text if pos.is_anchor else None for pos in grid_row]
                for grid_row in tbl.get_cell_map()
            ]
            out.append({"table_index": ti, "rows": rows})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(tables=out)


# --------------------------------------------------------------- 편집(무손실 read-modify-write)


def edit_replace_text(
    hwpx_path: str, search: str, replacement: str, limit: int | None = None, output_path: str | None = None
) -> dict:
    """문서 전체에서 텍스트를 찾아 바꾼다(템플릿 채우기·문구 수정). 반환: ``{ok, path, replaced}``."""
    try:
        doc = _open_doc(hwpx_path)
        n = doc.replace_text_in_runs(search, replacement, limit=limit)
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target, replaced=int(n))


def edit_set_cell(
    hwpx_path: str, table_index: int, row: int, col: int, text: str, output_path: str | None = None
) -> dict:
    """특정 표의 (row, col) 셀 텍스트를 설정한다(0-기반, 0행=헤더). 병합 셀은 좌상단 좌표로."""
    try:
        doc = _open_doc(hwpx_path)
        tables = _all_tables(doc)
        if not 0 <= table_index < len(tables):
            return {"ok": False, "error": f"table_index {table_index} 범위 밖 (표 {len(tables)}개)"}
        tables[table_index].cell(row, col).text = text
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target)


def edit_set_paragraph_text(hwpx_path: str, index: int, text: str, output_path: str | None = None) -> dict:
    """``index`` 번째 문단의 텍스트를 통째로 교체한다(list_paragraphs 의 index 기준)."""
    try:
        doc = _open_doc(hwpx_path)
        paras = doc.paragraphs
        if not 0 <= index < len(paras):
            return {"ok": False, "error": f"index {index} 범위 밖 (문단 {len(paras)}개)"}
        para = paras[index]
        if para.runs:
            para.runs[0].text = text
            for run in para.runs[1:]:
                run.text = ""
        else:
            para.add_run(text)
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target)


def edit_append_paragraph(hwpx_path: str, text: str, output_path: str | None = None) -> dict:
    """문서 끝(마지막 구역)에 문단을 추가한다."""
    try:
        doc = _open_doc(hwpx_path)
        doc.sections[-1].add_paragraph(text)
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target)


def edit_delete_paragraph(hwpx_path: str, index: int, output_path: str | None = None) -> dict:
    """``index`` 번째 문단을 삭제한다(list_paragraphs 의 index 기준)."""
    try:
        doc = _open_doc(hwpx_path)
        paras = doc.paragraphs
        if not 0 <= index < len(paras):
            return {"ok": False, "error": f"index {index} 범위 밖 (문단 {len(paras)}개)"}
        doc.remove_paragraph(paras[index])
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target)


def edit_merge_cells(hwpx_path: str, table_index: int, cell_range: str, output_path: str | None = None) -> dict:
    """표의 셀 범위를 병합한다. ``cell_range`` 는 엑셀식(예: ``"A2:A3"``).

    참고: python-hwpx 는 표의 **행/열 삽입·삭제는 지원하지 않는다**(병합/분할만 가능).
    행 수 변경이 필요하면 build_report 로 표를 다시 생성하라.
    """
    try:
        doc = _open_doc(hwpx_path)
        tables = _all_tables(doc)
        if not 0 <= table_index < len(tables):
            return {"ok": False, "error": f"table_index {table_index} 범위 밖 (표 {len(tables)}개)"}
        tables[table_index].merge_cells(cell_range)
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target)


def _set_tc_text(tc, text: str) -> None:
    ts = tc.findall(f".//{_HP}t")
    if ts:
        ts[0].text = text
        for t in ts[1:]:
            t.text = ""


def edit_add_table_row(hwpx_path: str, table_index: int, cells: list, output_path: str | None = None) -> dict:
    """표 끝에 행을 추가한다(``cells`` = 칸별 텍스트). **병합 없는 표만 지원**.

    (python-hwpx 미지원분을 XML 레벨로 직접 구현 — 마지막 행 구조를 복제해 rowAddr/rowCnt 갱신.)
    """
    try:
        doc = _open_doc(hwpx_path)
        tables = _all_tables(doc)
        if not 0 <= table_index < len(tables):
            return {"ok": False, "error": f"table_index {table_index} 범위 밖 (표 {len(tables)}개)"}
        el = tables[table_index].element
        trs = el.findall(f"{_HP}tr")
        if not trs:
            return {"ok": False, "error": "표에 행이 없습니다"}
        col_cnt = int(el.get("colCnt") or len(trs[0].findall(f"{_HP}tc")))
        last = trs[-1]
        if len(last.findall(f"{_HP}tc")) != col_cnt:
            return {"ok": False, "error": "병합 셀이 있는 표는 행 추가 미지원(build_report 재생성 권장)"}
        new_index = int(el.get("rowCnt") or len(trs))
        new_tr = copy.deepcopy(last)
        for ci, tc in enumerate(new_tr.findall(f"{_HP}tc")):
            addr = tc.find(f"{_HP}cellAddr")
            if addr is not None:
                addr.set("rowAddr", str(new_index))
            span = tc.find(f"{_HP}cellSpan")
            if span is not None:
                span.set("rowSpan", "1")
                span.set("colSpan", "1")
            _set_tc_text(tc, str(cells[ci]) if ci < len(cells) else "")
        el.insert(list(el).index(last) + 1, new_tr)
        el.set("rowCnt", str(new_index + 1))
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target, rows=new_index + 1)


def edit_delete_table_row(hwpx_path: str, table_index: int, row: int, output_path: str | None = None) -> dict:
    """표의 ``row``(0-기반) 행을 삭제한다. **병합 없는 표만 지원**(병합 표는 재생성 권장)."""
    try:
        doc = _open_doc(hwpx_path)
        tables = _all_tables(doc)
        if not 0 <= table_index < len(tables):
            return {"ok": False, "error": f"table_index {table_index} 범위 밖 (표 {len(tables)}개)"}
        el = tables[table_index].element
        trs = el.findall(f"{_HP}tr")
        if not 0 <= row < len(trs):
            return {"ok": False, "error": f"row {row} 범위 밖 (행 {len(trs)}개)"}
        for span in el.findall(f".//{_HP}cellSpan"):
            if span.get("rowSpan") not in (None, "1") or span.get("colSpan") not in (None, "1"):
                return {"ok": False, "error": "병합 셀이 있는 표는 행 삭제 미지원(재생성 권장)"}
        el.remove(trs[row])
        for ri, tr in enumerate(el.findall(f"{_HP}tr")):
            for tc in tr.findall(f"{_HP}tc"):
                addr = tc.find(f"{_HP}cellAddr")
                if addr is not None:
                    addr.set("rowAddr", str(ri))
        el.set("rowCnt", str(len(trs) - 1))
        target = _save_doc(doc, hwpx_path, output_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(path=target, rows=len(trs) - 1)


# --------------------------------------------------------------- 검증/메타


def validate(hwpx_path: str) -> dict:
    """기존 .hwpx 가 유효한지 검증한다. 반환: ``{ok, valid, issues}``."""
    try:
        info = _validate_file(hwpx_path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return _ok(**info)


def list_presets() -> dict:
    """사용 가능한 테마 프리셋 목록을 반환한다."""
    return _ok(presets=list(preset_names()))


def report_spec_help() -> dict:
    """``build_report`` 스펙 형식 도움말을 반환한다."""
    return _ok(help=REPORT_SPEC_HELP)


#: 에이전트/MCP 서버에 일괄 노출할 도구 함수 목록.
TOOLS = [
    # 생성
    build_report,
    build_from_markdown,
    # 되먹임(읽기/렌더)
    read_as_markdown,
    read_as_text,
    get_outline,
    render_to_html,
    # 편집 대상 나열
    list_paragraphs,
    list_tables,
    # 편집(read-modify-write)
    edit_replace_text,
    edit_set_cell,
    edit_set_paragraph_text,
    edit_append_paragraph,
    edit_delete_paragraph,
    edit_merge_cells,
    edit_add_table_row,
    edit_delete_table_row,
    # 검증/메타
    validate,
    list_presets,
    report_spec_help,
]

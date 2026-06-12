"""읽기 → 충실 HTML 렌더: 표 병합·런 서식·이미지가 구조적으로 보존되는지."""

from __future__ import annotations

import base64
import re

from open_hwpx import Image, Paragraph, Report, Run, Table, load, render_html

# 1x1 PNG (이미지 임베드/추출 경로 검증용)
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _doc_bytes() -> bytes:
    r = Report.new(title="문서 제목", organization="○○부", date="2026-06-04")
    ch = r.add_chapter("첫 장")
    ch.add(Paragraph(Run("보통 "), Run("강조", bold=True, color="#FF0000", size=16)))
    ch.bullets(["항목 하나", "항목 둘"])
    ch.add(
        Table(
            header=["구분", "내용", "기한"],
            rows=[["병합", "x", "y"], ["", "z", "w"]],
            merges=["A2:A3"],
            header_shading="#EAF1FB",
            column_widths=[2, 3, 1],
        )
    )
    ch.add(Image(_PNG, width_mm=30, caption="[그림 1]"))
    return r.to_bytes()


def test_full_document_wrapper():
    html = render_html(_doc_bytes())
    assert html.startswith("<!DOCTYPE html>")
    assert "<style>" in html and "</html>" in html


def test_fragment_has_no_wrapper():
    body = render_html(_doc_bytes(), fragment=True)
    assert "<!DOCTYPE" not in body
    assert "<html" not in body
    assert "<table" in body  # 본문은 들어있음


def test_headings_not_plain_paragraphs():
    html = render_html(_doc_bytes())
    assert re.search(r"<h[1-3][ >]", html)  # 제목이 <h*> 로
    assert "첫 장" in html


def test_run_styling_preserved():
    html = render_html(_doc_bytes())
    assert "font-weight:bold" in html
    assert "color:#FF0000" in html
    assert "font-size:16pt" in html


def test_table_merge_rowspan_and_no_phantom_cell():
    html = render_html(_doc_bytes())
    # A2:A3 병합 → rowspan="2"; 병합으로 사라진 셀이 빈 <td> 로 새지 않아야(베이스라인 버그)
    assert 'rowspan="2"' in html
    assert "<td></td>" not in html


def test_anchor_cell_count():
    body = render_html(_doc_bytes(), fragment=True)
    # 헤더3 + (병합,x,y)=3 + (z,w)=2 = 8 (사라진 병합 셀 제외)
    assert body.count("<td") + body.count("<th") == 8
    assert body.count("<th") == 3  # 헤더 행


def test_table_header_shading_and_widths():
    html = render_html(_doc_bytes())
    assert "background:#EAF1FB" in html
    assert "<colgroup>" in html and "width:" in html


def test_bullets_become_list():
    html = render_html(_doc_bytes())
    assert "<ul>" in html and "<li>" in html
    assert "항목 하나" in html


def test_image_data_uri():
    html = render_html(_doc_bytes())
    assert '<img src="data:image/png;base64,' in html


def test_load_returns_friendly_model():
    doc = load(_doc_bytes())
    assert doc.title  # 문서 제목 자동 감지
    assert any(t.rows for t in doc.tables)
    # 표 안에 rowspan 셀이 존재
    assert any(c.rowspan == 2 for t in doc.tables for row in t.rows for c in row)
    html = doc.to_html()
    assert "<table" in html

"""end-to-end: 빌드 → 저장 → 재오픈 → validate + 구조 검증."""

from __future__ import annotations

import base64
import zipfile

from open_hwpx import BulletList, Image, Paragraph, Report, Run, Table
from open_hwpx._compat import HwpxDocument

# 1x1 PNG
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _read(path):
    with zipfile.ZipFile(path) as z:
        return z.read("Contents/section0.xml").decode("utf-8"), z.namelist()


def _full_report() -> Report:
    report = Report.new(title="2026년 추진계획", organization="○○부", date="2026-06-04")
    report.set_footer(page_number=True)
    report.add_toc(max_level=3)
    bg = report.add_chapter("추진 배경")
    bg.add(Paragraph(Run("본 계획은 "), Run("AI 융합교육", bold=True, color="#1F4E79"), Run(" 확산이 목표.")))
    bg.add(BulletList(["디지털 전환", "수요 증가"]))
    road = report.add_chapter("세부 계획").add_chapter("로드맵")
    road.add(Table(
        header=["구분", "내용"],
        rows=[["1단계", "기반 구축"], ["1단계", "시범 운영"]],
        merges=["A2:A3"],
        column_widths=[1, 2],
        caption="<표 1> 일정",
    ))
    road.add(Image(PNG, width_mm=40, caption="[그림 1] 로드맵"))
    road.page_break()
    return report


def test_fluent_roundtrip(tmp_path):
    out = tmp_path / "fluent.hwpx"
    _full_report().save(str(out))

    reopened = HwpxDocument.open(str(out))
    assert reopened.validate().ok

    section, names = _read(str(out))
    assert section.count("<hp:tbl") == 1
    assert section.count("<hp:pic") == 1
    assert any(n.startswith("BinData/") for n in names)

    text = reopened.export_text()
    for needle in ["2026년 추진계획", "추진 배경", "로드맵", "기반 구축"]:
        assert needle in text


def test_spec_roundtrip(tmp_path):
    spec = {
        "schema": "open_hwpx.report.v1",
        "metadata": {"title": "스펙 보고서"},
        "front_matter": [{"type": "toc", "max_level": 2}],
        "chapters": [
            {"title": "장1", "body": [
                {"type": "paragraph", "text": "문단"},
                {"type": "numbered", "items": ["하나", "둘"]},
            ]},
        ],
    }
    out = tmp_path / "spec.hwpx"
    Report.from_spec(spec).save(str(out))
    reopened = HwpxDocument.open(str(out))
    assert reopened.validate().ok
    assert "장1" in reopened.export_text()


def test_to_bytes_is_valid_zip():
    data = _full_report().to_bytes()
    assert data[:2] == b"PK"  # zip 시그니처

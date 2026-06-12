"""dict/JSON 스펙 로더 + 빌더/스펙 동치(parity)."""

from __future__ import annotations

import pytest

from open_hwpx import BulletList, Paragraph, Report, Run, Table
from open_hwpx.spec.schema import SpecError, build_component


def _snapshot(report: Report) -> dict:
    """Report 의 구조를 비교 가능한 형태로 직렬화."""
    report.tree.prepare()
    tree = [
        (depth, ch.title, tuple(type(c).__name__ for c in ch.body))
        for ch, depth in report.tree.walk()
    ]
    return {
        "title": report.metadata.title,
        "organization": report.metadata.organization,
        "front_matter": tuple(type(c).__name__ for c in report.front_matter),
        "tree": tree,
    }


def _fluent_report() -> Report:
    r = Report.new(title="제목", organization="○○부")
    r.add_toc(max_level=2)
    a = r.add_chapter("배경")
    a.add(Paragraph(Run("강조", bold=True), Run(" 보통")))
    a.bullets(["가", "나"])
    b = r.add_chapter("계획")
    b.add_chapter("로드맵").add(Table(header=["h"], rows=[["1"]]))
    return r


_SPEC = {
    "schema": "open_hwpx.report.v1",
    "metadata": {"title": "제목", "organization": "○○부"},
    "front_matter": [{"type": "toc", "max_level": 2}],
    "chapters": [
        {
            "title": "배경",
            "body": [
                {"type": "paragraph", "runs": [{"text": "강조", "bold": True}, {"text": " 보통"}]},
                {"type": "bullets", "items": ["가", "나"]},
            ],
        },
        {
            "title": "계획",
            "chapters": [
                {"title": "로드맵", "body": [{"type": "table", "header": ["h"], "rows": [["1"]]}]}
            ],
        },
    ],
}


def test_fluent_and_spec_produce_same_structure():
    assert _snapshot(_fluent_report()) == _snapshot(Report.from_spec(_SPEC))


def test_unknown_block_type_raises():
    with pytest.raises(SpecError):
        build_component({"type": "nope"})


def test_unknown_schema_raises():
    with pytest.raises(SpecError):
        Report.from_spec({"schema": "wrong.v9", "chapters": []})


def test_run_requires_text():
    with pytest.raises(SpecError):
        build_component({"type": "paragraph", "runs": [{"bold": True}]})


def test_paragraph_plain_text_block():
    comp = build_component({"type": "paragraph", "text": "한 줄"})
    assert isinstance(comp, Paragraph)
    assert comp.runs[0].text == "한 줄"

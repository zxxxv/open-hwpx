"""Markdown → 컴포넌트 / Report 변환."""

from __future__ import annotations

from open_hwpx import BulletList, Heading, NumberedList, Paragraph, Table
from open_hwpx.markdown import markdown_to_report, md_to_components


def test_inline_formatting_to_runs():
    comps = md_to_components("일반 **굵게** 그리고 *기울임* 끝")
    assert len(comps) == 1 and isinstance(comps[0], Paragraph)
    runs = comps[0].runs
    assert any(r.bold for r in runs)
    assert any(r.italic for r in runs)
    assert "굵게" in "".join(r.text for r in runs)


def test_block_types():
    md = "# 제목\n\n문단\n\n- 가\n- 나\n\n1. 하나\n2. 둘\n\n| h1 | h2 |\n| --- | --- |\n| a | b |"
    types = [type(c).__name__ for c in md_to_components(md)]
    assert "Heading" in types
    assert "BulletList" in types
    assert "NumberedList" in types
    assert "Table" in types


def test_nested_bullets_increase_level():
    comps = md_to_components("- a\n  - a1\n  - a2\n- b")
    bullets = [c for c in comps if isinstance(c, BulletList)]
    assert len(bullets) >= 2
    assert any(b.level == 1 for b in bullets)  # 중첩 목록은 한 단계 깊어짐


def test_table_header_and_rows():
    table = md_to_components("| 구분 | 값 |\n| --- | --- |\n| A | 1 |\n| B | 2 |")[0]
    assert isinstance(table, Table)
    assert table.header == ["구분", "값"]
    assert table.rows == [["A", "1"], ["B", "2"]]


def test_markdown_to_report_builds_chapter_tree():
    report = markdown_to_report("# 1장\n본문\n\n## 1-1 절\n세부\n\n# 2장\n끝")
    report.tree.prepare()
    nodes = {(depth, ch.title) for ch, depth in report.tree.walk()}
    assert (1, "1장") in nodes
    assert (2, "1-1 절") in nodes
    assert (1, "2장") in nodes

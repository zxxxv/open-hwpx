"""구조 트리: 레벨 정규화·번호 부여·목차 수집."""

from __future__ import annotations

from open_hwpx import Paragraph
from open_hwpx.structure import StructureTree


def _sample_tree() -> StructureTree:
    tree = StructureTree()
    a = tree.add_chapter("배경")
    a.add(Paragraph("내용"))
    b = tree.add_chapter("계획")
    b1 = b.add_chapter("로드맵")
    b1.add_chapter("세부")
    b.add_chapter("예산")
    return tree


def test_normalize_levels_uses_depth():
    tree = _sample_tree()
    tree.normalize_levels()
    levels = {ch.title: ch.level for ch, _ in tree.walk()}
    assert levels == {"배경": 1, "계획": 1, "로드맵": 2, "세부": 3, "예산": 2}


def test_assign_numbers():
    tree = _sample_tree()
    tree.assign_numbers()
    numbers = {ch.title: ch.number for ch, _ in tree.walk()}
    assert numbers["배경"] == (1,)
    assert numbers["계획"] == (2,)
    assert numbers["로드맵"] == (2, 1)
    assert numbers["세부"] == (2, 1, 1)
    assert numbers["예산"] == (2, 2)


def test_headings_and_labels():
    tree = _sample_tree()
    tree.prepare()
    refs = tree.headings(max_level=2)
    titles = [r.title for r in refs]
    assert "세부" not in titles  # max_level=2 로 제외
    road = next(r for r in refs if r.title == "로드맵")
    assert road.number_label == "2.1."

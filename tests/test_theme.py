"""테마 오버라이드와 StyleSheet 동작."""

from __future__ import annotations

import warnings

from open_hwpx import GOV_KOREAN, FontSpec
from open_hwpx._compat import HwpxDocument
from open_hwpx.styles.theme import StyleSheet


def test_theme_override_is_nondestructive():
    custom = GOV_KOREAN.override(body=FontSpec("함초롬바탕", 12.0))
    assert custom.body.size_pt == 12.0
    assert GOV_KOREAN.body.size_pt == 11.0  # 원본 불변
    assert custom.name == GOV_KOREAN.name


def test_heading_style_clamps_out_of_range():
    last = GOV_KOREAN.headings[-1]
    assert GOV_KOREAN.heading_style(99) is last


def test_stylesheet_char_id_dedup():
    doc = HwpxDocument.new()
    ss = StyleSheet(GOV_KOREAN, doc)
    a = ss.char_id(font="함초롬바탕", size=11, bold=True)
    b = ss.char_id(font="함초롬바탕", size=11, bold=True)
    c = ss.char_id(font="함초롬바탕", size=11, bold=False)
    assert a == b
    assert a != c


def test_unregistered_font_warns_and_falls_back():
    doc = HwpxDocument.new()
    ss = StyleSheet(GOV_KOREAN, doc)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ss.char_id(font="존재하지않는폰트", size=11)
    assert any("등록되어 있지 않" in str(w.message) for w in caught)


def test_outline_para_indents_per_level():
    doc = HwpxDocument.new()
    ss = StyleSheet(GOV_KOREAN, doc)
    r0 = ss.outline_para(indent_level=0, marker_level=0)
    r1 = ss.outline_para(indent_level=1, marker_level=1)
    assert r0 != r1            # 레벨마다 다른 paraPr
    assert ss.outline_para(indent_level=1, marker_level=1) == r1  # 캐시 재사용


def test_outline_para_default_is_none():
    doc = HwpxDocument.new()
    ss = StyleSheet(GOV_KOREAN, doc)
    # 들여쓰기/마커/정렬이 모두 기본이면 기본 paraPr(None)
    assert ss.outline_para(indent_level=0) is None


def test_indent_step_scales_with_body_size():
    doc = HwpxDocument.new()
    ss = StyleSheet(GOV_KOREAN, doc)
    assert ss._indent_step == round(GOV_KOREAN.body.size_pt * GOV_KOREAN.indent_chars_per_level * 100)

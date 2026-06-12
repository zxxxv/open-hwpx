"""프리셋 레지스트리와 각 프리셋의 빌드 검증."""

from __future__ import annotations

import pytest

from open_hwpx import (
    BUSINESS_REPORT,
    GOV_KOREAN,
    PLAIN_DOC,
    Paragraph,
    Report,
    Run,
    get_theme,
    preset_names,
)
from open_hwpx._compat import HwpxDocument


def test_aliases_resolve():
    assert get_theme("gov") is GOV_KOREAN
    assert get_theme("개조식") is GOV_KOREAN
    assert get_theme("business") is BUSINESS_REPORT
    assert get_theme("report") is BUSINESS_REPORT
    assert get_theme("plain") is PLAIN_DOC


def test_unknown_preset_raises():
    with pytest.raises(KeyError):
        get_theme("없는프리셋")


def test_preset_names_unique():
    names = preset_names()
    assert names == ["korean_gov_outline", "business_report", "plain"]


@pytest.mark.parametrize("preset", ["gov", "business", "plain"])
def test_each_preset_builds_and_validates(preset, tmp_path):
    report = Report.new(title=f"{preset} 보고서", theme=preset)
    report.add_toc()
    ch = report.add_chapter("배경")
    ch.add(Paragraph(Run("본문 "), Run("강조", bold=True)))
    ch.bullets(["가", "나"])
    report.add_chapter("계획").add_chapter("로드맵").numbers(["1단계", "2단계"])

    out = tmp_path / f"{preset}.hwpx"
    report.save(str(out))
    assert HwpxDocument.open(str(out)).validate().ok


def test_string_theme_in_constructor():
    assert Report(theme="business").theme is BUSINESS_REPORT
    assert Report.new(theme="plain").theme is PLAIN_DOC

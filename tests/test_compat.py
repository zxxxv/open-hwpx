"""_compat 계층과 패키지 import 스모크."""

from __future__ import annotations

import open_hwpx
from open_hwpx import _compat


def test_public_imports():
    for name in [
        "Report", "Paragraph", "Run", "Heading", "Table", "Image",
        "BulletList", "NumberedList", "TableOfContents", "Header", "Footer",
        "PageBreak", "PageConfig", "GOV_KOREAN",
    ]:
        assert hasattr(open_hwpx, name), name


def test_hwpx_available_and_versioned():
    assert _compat.hwpx_version() != "unknown"
    # 검증 범위 안이면 경고가 없어야 한다(범위 밖이면 경고만, 예외 아님)
    _compat.check_version()


def test_mm_to_hwp_units_a4():
    # A4 210x297mm 가 빌더 상수와 거의 일치
    w = _compat.mm_to_hwp_units(210)
    h = _compat.mm_to_hwp_units(297)
    assert abs(w - _compat.A4_SIZE_HWP[0]) <= 1
    assert abs(h - _compat.A4_SIZE_HWP[1]) <= 1


def test_detect_image_format():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 8
    assert _compat.detect_image_format(png) == "png"
    assert _compat.detect_image_format(jpg) == "jpg"
    assert _compat.detect_image_format(b"unknown") == "png"

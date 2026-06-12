"""스타일: 테마 정의와 문서 해석기, 내장 프리셋."""

from __future__ import annotations

from .gov_korean import GOV_KOREAN
from .presets import BUSINESS_REPORT, PLAIN_DOC, PRESETS, get_theme, preset_names
from .theme import StyleSheet, StyleTheme
from .tokens import FontSpec, HeadingLevelStyle

#: 기본 테마
DEFAULT_THEME = GOV_KOREAN

__all__ = [
    "FontSpec",
    "HeadingLevelStyle",
    "StyleTheme",
    "StyleSheet",
    "GOV_KOREAN",
    "BUSINESS_REPORT",
    "PLAIN_DOC",
    "DEFAULT_THEME",
    "PRESETS",
    "get_theme",
    "preset_names",
]

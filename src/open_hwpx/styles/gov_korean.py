"""기본 테마: 한국 공문서 개요식.

스파이크에서 확인된 '등록된' 폰트(함초롬바탕/함초롬돋움)만 사용하므로 어떤 환경에서도
폰트가 누락되지 않는다. 개요 마커는 □ → ○ → - → · 4단계.
"""

from __future__ import annotations

from .theme import StyleTheme
from .tokens import FontSpec, HeadingLevelStyle

#: 본문 폰트
_BODY = FontSpec("함초롬바탕", 11.0)
_GOTHIC = "함초롬돋움"
_SERIF = "함초롬바탕"

GOV_KOREAN = StyleTheme(
    name="korean_gov_outline",
    body=_BODY,
    headings=(
        # 레벨 0: 표지/문서 제목 — 마커 없음, 가운데, 큰 글씨
        HeadingLevelStyle(FontSpec(_GOTHIC, 20.0), bold=True, marker=None, align="CENTER"),
        # 레벨 1: 대제목 □
        HeadingLevelStyle(FontSpec(_GOTHIC, 14.0), bold=True, marker="□"),
        # 레벨 2: 중제목 ○
        HeadingLevelStyle(FontSpec(_GOTHIC, 12.0), bold=True, marker="○"),
        # 레벨 3: 소제목 -
        HeadingLevelStyle(FontSpec(_SERIF, 11.0), bold=True, marker="-"),
        # 레벨 4: 세부 ·
        HeadingLevelStyle(FontSpec(_SERIF, 11.0), bold=False, marker="·"),
    ),
    bullet_markers=("□", "○", "-", "·"),
    table_header=FontSpec(_GOTHIC, 11.0),
    table_header_shading="#EAF1FB",
    caption=FontSpec(_SERIF, 10.0),
    colors={"heading": "#000000", "accent": "#1F4E79", "caption": "#595959"},
)

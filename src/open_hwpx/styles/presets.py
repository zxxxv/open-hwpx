"""추가 내장 테마(프리셋)와 이름 레지스트리.

- gov_korean : 한국 공문서 개조식(□○-·, 들여쓰기). 기본값.
- business   : 일반 보고서 — 번호식 제목(1. / 1.1 …), 본문 왼쪽 정렬.
- plain      : 일반 글쓰기 — 굵은 제목만, 마커·번호·들여쓰기 없음.
"""

from __future__ import annotations

from .gov_korean import GOV_KOREAN
from .theme import StyleTheme
from .tokens import FontSpec, HeadingLevelStyle

_GOTHIC = "함초롬돋움"
_SERIF = "함초롬바탕"

# ── 일반 보고서: 번호식 제목 ────────────────────────────────────────────────
BUSINESS_REPORT = StyleTheme(
    name="business_report",
    body=FontSpec(_SERIF, 11.0),
    headings=(
        HeadingLevelStyle(FontSpec(_GOTHIC, 20.0), bold=True, align="CENTER"),       # 표지 제목
        HeadingLevelStyle(FontSpec(_GOTHIC, 15.0), bold=True, numbered=True),        # 1.
        HeadingLevelStyle(FontSpec(_GOTHIC, 13.0), bold=True, numbered=True),        # 1.1
        HeadingLevelStyle(FontSpec(_GOTHIC, 12.0), bold=True, numbered=True),        # 1.1.1
        HeadingLevelStyle(FontSpec(_SERIF, 11.0), bold=True, numbered=True),
    ),
    bullet_markers=("•", "-", "◦", "‣"),
    indent_body=False,
    table_header=FontSpec(_GOTHIC, 11.0),
    table_header_shading="#D9E2F3",
    caption=FontSpec(_SERIF, 10.0),
    colors={"heading": "#1F3864", "accent": "#2E74B5", "caption": "#595959"},
)

# ── 일반 글쓰기: 굵은 제목만 ────────────────────────────────────────────────
PLAIN_DOC = StyleTheme(
    name="plain",
    body=FontSpec(_SERIF, 11.0),
    headings=(
        HeadingLevelStyle(FontSpec(_GOTHIC, 20.0), bold=True, align="CENTER"),
        HeadingLevelStyle(FontSpec(_GOTHIC, 16.0), bold=True),
        HeadingLevelStyle(FontSpec(_GOTHIC, 13.0), bold=True),
        HeadingLevelStyle(FontSpec(_SERIF, 12.0), bold=True),
    ),
    bullet_markers=("•", "◦", "‣", "·"),
    indent_body=False,
    table_header=FontSpec(_GOTHIC, 11.0),
    table_header_shading="#F2F2F2",
    caption=FontSpec(_SERIF, 10.0),
    colors={"heading": "#000000", "accent": "#404040", "caption": "#595959"},
)

#: 이름 → 테마. 별칭을 여러 개 허용.
PRESETS: dict[str, StyleTheme] = {
    "gov": GOV_KOREAN,
    "gov_korean": GOV_KOREAN,
    "korean_gov_outline": GOV_KOREAN,
    "개조식": GOV_KOREAN,
    "business": BUSINESS_REPORT,
    "business_report": BUSINESS_REPORT,
    "report": BUSINESS_REPORT,
    "보고서": BUSINESS_REPORT,
    "plain": PLAIN_DOC,
    "article": PLAIN_DOC,
    "일반": PLAIN_DOC,
}


def get_theme(name: str) -> StyleTheme:
    """이름(또는 별칭)으로 내장 테마를 찾는다."""
    key = (name or "").strip().lower()
    # 한글 별칭은 lower 영향 없음
    theme = PRESETS.get(key) or PRESETS.get(name or "")
    if theme is None:
        raise KeyError(
            f"알 수 없는 프리셋: {name!r}. 사용 가능: {sorted(set(t.name for t in PRESETS.values()))}"
        )
    return theme


def preset_names() -> list[str]:
    """대표 프리셋 이름 목록(중복 테마 제거)."""
    seen, names = set(), []
    for theme in PRESETS.values():
        if theme.name not in seen:
            seen.add(theme.name)
            names.append(theme.name)
    return names

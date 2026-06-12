"""python-hwpx 의존성 격리 계층.

open_hwpx 모듈이 사용하는 상위 라이브러리(python-hwpx) 심볼을 이 한 곳에서만 import 한다.
상위 API가 바뀌면 여기만 고치면 되고, import 스모크 테스트로 조기에 감지한다.

스파이크(Step 0)로 확정한 사실:
- 글자크기 size 는 '포인트' 단위(저장 시 height = pt*100).
- 색상은 "#RRGGBB" 문자열.
- font 는 문서에 '이미 등록된' face 만 적용된다(블랭크 템플릿엔 함초롬바탕/함초롬돋움뿐).
- 정렬은 header.ensure_paragraph_alignment(align) 로 paraPrIDRef 를 얻는다.
- 개요 마커/들여쓰기는 doc.ensure_numbering(kind="bullet", levels=[{"char": ...}]) 로 얻는다.
"""

from __future__ import annotations

from importlib import metadata as _metadata

#: 검증된 python-hwpx 버전 범위
MIN_HWPX = (2, 10)
MAX_HWPX_EXCLUSIVE = (3, 0)

try:
    from hwpx.document import HwpxDocument
except ImportError as exc:  # pragma: no cover - 설치 누락 안내
    raise ImportError(
        "open_hwpx 모듈은 'python-hwpx'가 필요합니다. `uv add python-hwpx` 로 설치하세요."
    ) from exc

# 머리말/꼬리말은 상위 빌더의 dataclass + .lower(doc) 를 그대로 재사용한다
# (set_header_content/set_footer_content 의 content-spec 형식을 직접 짤 필요가 없음).
from hwpx.builder import (  # noqa: E402
    Footer as BuilderFooter,
    Header as BuilderHeader,
    Paragraph as BuilderParagraph,
    PageNumber as BuilderPageNumber,
    Run as BuilderRun,
)

__all__ = [
    "HwpxDocument",
    "BuilderHeader",
    "BuilderFooter",
    "BuilderParagraph",
    "BuilderPageNumber",
    "BuilderRun",
    "hwpx_version",
    "check_version",
    "HWP_UNITS_PER_MM",
    "A4_SIZE_HWP",
    "mm_to_hwp_units",
    "detect_image_format",
]

#: 1mm 당 HWPUNIT (7200 units/inch ÷ 25.4 mm/inch)
HWP_UNITS_PER_MM = 7200 / 25.4

#: A4 (210×297mm) 의 정확한 HWPUNIT 크기 (상위 빌더 상수와 일치)
A4_SIZE_HWP = (59528, 84188)


def hwpx_version() -> str:
    """설치된 python-hwpx 버전 문자열."""
    try:
        return _metadata.version("python-hwpx")
    except _metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


def check_version() -> None:
    """설치된 python-hwpx 가 검증 범위 안인지 확인하고, 벗어나면 경고."""
    import warnings

    raw = hwpx_version()
    try:
        parts = tuple(int(p) for p in raw.split(".")[:2])
    except ValueError:  # pragma: no cover
        return
    if not (MIN_HWPX <= parts < MAX_HWPX_EXCLUSIVE):
        warnings.warn(
            f"python-hwpx {raw} 는 검증된 범위"
            f"({MIN_HWPX[0]}.{MIN_HWPX[1]} 이상 {MAX_HWPX_EXCLUSIVE[0]}.0 미만) 밖입니다. "
            "동작이 다를 수 있습니다.",
            stacklevel=2,
        )


def mm_to_hwp_units(value_mm: float) -> int:
    """밀리미터를 HWPUNIT 정수로 변환."""
    return round(value_mm * HWP_UNITS_PER_MM)


_IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"BM": "bmp",
}


def detect_image_format(data: bytes, fallback: str = "png") -> str:
    """이미지 바이트의 시그니처로 포맷(png/jpg/gif/bmp)을 추정."""
    for sig, fmt in _IMAGE_SIGNATURES.items():
        if data.startswith(sig):
            return fmt
    return fallback

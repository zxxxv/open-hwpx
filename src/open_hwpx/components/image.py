"""그림(Image) 컴포넌트.

python-hwpx 의 add_picture 로 이미지를 임베드한다(BinData 등록 + hp:pic 생성).
스파이크에서 생성·재오픈·validate 통과를 확인했다.
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from .._compat import detect_image_format
from .base import Component, RenderContext


class Image(Component):
    """이미지 한 개(+ 선택적 캡션).

    - path: 파일 경로(str/Path) 또는 이미지 바이트.
    - width_mm / height_mm: 표시 크기(mm). 둘 다 None 이면 원본 비율로 들어간다.
    - align: "LEFT" | "CENTER" | "RIGHT" (기본 CENTER).
    - caption: 그림 아래 설명(예: "[그림 1] 추진 로드맵").
    - image_format: 강제 포맷(png/jpg/…). 없으면 확장자/시그니처로 자동 판별.
    """

    def __init__(
        self,
        path: "str | PathLike[str] | bytes",
        *,
        width_mm: float | None = None,
        height_mm: float | None = None,
        align: str = "CENTER",
        caption: str | None = None,
        image_format: str | None = None,
    ) -> None:
        self.path = path
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.align = align
        self.caption = caption
        self.image_format = image_format

    def _load(self) -> tuple[bytes, str]:
        if isinstance(self.path, (bytes, bytearray)):
            data = bytes(self.path)
            fmt = self.image_format or detect_image_format(data)
            return data, fmt
        p = Path(self.path)
        data = p.read_bytes()
        fmt = self.image_format or p.suffix.lstrip(".").lower() or detect_image_format(data)
        if fmt == "jpeg":
            fmt = "jpg"
        return data, fmt

    def render(self, ctx: RenderContext) -> None:
        data, fmt = self._load()
        ctx.doc.add_picture(
            data,
            fmt,
            width_mm=self.width_mm,
            height_mm=self.height_mm,
            align=(self.align or "CENTER").upper(),
        )
        if self.caption:
            from .paragraph import Paragraph, Run

            cap = ctx.theme.caption or ctx.theme.body
            color = ctx.theme.colors.get("caption")
            Paragraph(
                Run(self.caption, font=cap.name, size=cap.size_pt, color=color),
                align="CENTER",
            ).render(ctx)

    def __repr__(self) -> str:  # pragma: no cover
        src = "<bytes>" if isinstance(self.path, (bytes, bytearray)) else str(self.path)
        return f"Image({src})"

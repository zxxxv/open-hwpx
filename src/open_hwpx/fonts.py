"""폰트 레지스트리 & .hwpx 바이너리 임베드.

기본 동작: 미등록 폰트는 **이름만** 헤더에 등록된다(뷰어에 그 폰트가 있어야 적용).
이식성(다른 PC에서도 안 깨짐)을 원하면 폰트 **파일(.ttf/.otf)을 등록**하라 — 이후 생성되는
문서에 폰트 바이너리가 동봉(``isEmbedded="1"``)된다::

    import open_hwpx as hwpx
    hwpx.register_font_file("나눔고딕", "/path/NanumGothic.ttf")  # OFL 등 임베드 허용 폰트
    # 이제 본문/Run 에서 "나눔고딕" 을 쓰면 .hwpx 에 폰트가 동봉된다.

⚠️ 라이선스: 함초롬·맑은 고딕 등 독점 폰트는 임베드/재배포가 제한된다. 자유 임베드 가능한
OFL 폰트(나눔글꼴, 본고딕/본명조=Noto Sans/Serif KR, Pretendard 등)만 등록하라.
"""

from __future__ import annotations

import os
from pathlib import Path

_HH = "{http://www.hancom.co.kr/hwpml/2011/head}"
_MEDIA = {"ttf": "application/x-font-ttf", "otf": "application/x-font-otf"}

#: face 이름 → 폰트 파일 경로
_REGISTRY: dict[str, str] = {}

_GF = "https://github.com/google/fonts/raw/main/ofl"
#: 자동 다운로드 가능한 OFL(임베드 허용) 한글 폰트 — 요청 이름 → URL.
OFL_FONTS: dict[str, str] = {
    "나눔고딕": f"{_GF}/nanumgothic/NanumGothic-Regular.ttf",
    "NanumGothic": f"{_GF}/nanumgothic/NanumGothic-Regular.ttf",
    "나눔명조": f"{_GF}/nanummyeongjo/NanumMyeongjo-Regular.ttf",
    "NanumMyeongjo": f"{_GF}/nanummyeongjo/NanumMyeongjo-Regular.ttf",
    "본고딕": f"{_GF}/notosanskr/NotoSansKR%5Bwght%5D.ttf",
    "Noto Sans KR": f"{_GF}/notosanskr/NotoSansKR%5Bwght%5D.ttf",
    "본명조": f"{_GF}/notoserifkr/NotoSerifKR%5Bwght%5D.ttf",
    "Noto Serif KR": f"{_GF}/notoserifkr/NotoSerifKR%5Bwght%5D.ttf",
    "Gothic A1": f"{_GF}/gothica1/GothicA1-Regular.ttf",
    "도현": f"{_GF}/dohyeon/DoHyeon-Regular.ttf",
    "Do Hyeon": f"{_GF}/dohyeon/DoHyeon-Regular.ttf",
}
_FONT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf")


def register_font_file(face_name: str, font_path: str) -> None:
    """``face_name`` 폰트의 ``.ttf``/``.otf`` 경로를 등록한다(이후 생성물에 임베드)."""
    _REGISTRY[face_name] = str(font_path)


def font_file_for(face_name: str) -> str | None:
    return _REGISTRY.get(face_name)


def registered_fonts() -> dict[str, str]:
    return dict(_REGISTRY)


def clear_registry() -> None:
    _REGISTRY.clear()


def available_ofl_fonts() -> list[str]:
    """자동 다운로드 가능한 OFL 폰트 이름 목록."""
    return sorted(OFL_FONTS)


def _cache_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    path = Path(base) / "open_hwpx" / "fonts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _download(url: str, dst: Path) -> None:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "open-hwpx"})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - 고정 OFL URL
        data = resp.read()
    if not data[:4] in _FONT_MAGIC and not data[:4] == b"wOFF":
        raise ValueError(f"다운로드한 파일이 폰트(TTF/OTF)가 아닙니다: {url}")
    dst.write_bytes(data)


def ensure_font(name: str, *, register: bool = True) -> str:
    """OFL 폰트를 (캐시에) 다운로드하고 ``register_font_file`` 로 등록한다 → 경로 반환.

    ``register_font_file`` 로 직접 파일을 넣지 않아도, 목록(:func:`available_ofl_fonts`)에 있는
    폰트는 이 한 줄로 동봉까지 준비된다::

        import open_hwpx as hwpx
        hwpx.ensure_font("나눔고딕")     # 1회 다운로드+등록 → 이후 생성물에 임베드
    """
    url = OFL_FONTS.get(name)
    if url is None:
        raise KeyError(
            f"OFL 자동 다운로드 목록에 없습니다: {name!r}. "
            f"가능: {available_ofl_fonts()} — 또는 register_font_file 로 파일을 직접 등록하세요."
        )
    ext = ".otf" if url.lower().endswith(".otf") else ".ttf"
    safe = "".join(c for c in name if c.isalnum() or c in "-_") or "font"
    dst = _cache_dir() / f"{safe}{ext}"
    if not dst.exists() or dst.stat().st_size == 0:
        _download(url, dst)
    if register:
        register_font_file(name, str(dst))
    return str(dst)


def embed_font_binary(doc, data: bytes, fmt: str = "ttf") -> str:
    """폰트 바이너리를 패키지에 동봉하고 ``binaryItemIDRef`` 로 쓸 id 를 반환한다.

    이미지 임베드와 동일한 절차: BinData 기록 → manifest 등록 → ``<hh:binItem>`` 추가.
    """
    header = doc.headers[0]
    existing = {bi.get("id", "") for bi in header.list_bin_items()}
    n = len(existing) + 1
    while f"BIN{n:04d}" in existing:
        n += 1
    item_id = f"BIN{n:04d}"
    bin_data_name = f"{item_id}.{fmt}"
    bin_data_path = f"BinData/{bin_data_name}"

    pkg = doc.package
    writer = getattr(pkg, "write", None) or pkg.set_part
    writer(bin_data_path, data)
    pkg.add_manifest_item(item_id, bin_data_path, _MEDIA.get(fmt, "application/octet-stream"))
    header.add_bin_item(item_type="Embedding", bin_data_id=bin_data_name, format=fmt)
    return item_id


def embed_font(hwpx_path: str, face_name: str, font_path: str, output_path: str | None = None) -> dict:
    """기존 .hwpx 에 폰트를 동봉한다(이미 그 face 를 쓰는 런이 있으면 임베드로 승격).

    반환: ``{ok, path, face}`` 또는 ``{ok: false, error}``.
    """
    from lxml import etree

    from ._compat import HwpxDocument

    try:
        data = Path(font_path).read_bytes()
        fmt = Path(font_path).suffix.lstrip(".").lower() or "ttf"
        doc = HwpxDocument.open(str(hwpx_path))
        ref = embed_font_binary(doc, data, fmt)
        for face in doc.headers[0].element.findall(f".//{_HH}fontface"):
            fonts = face.findall(f"{_HH}font")
            existing = next((f for f in fonts if f.get("face") == face_name), None)
            if existing is not None:
                existing.set("type", "TTF")
                existing.set("isEmbedded", "1")
                existing.set("binaryItemIDRef", ref)
            else:
                font_el = etree.SubElement(face, f"{_HH}font")
                font_el.set("id", str(len(fonts)))
                font_el.set("face", face_name)
                font_el.set("type", "TTF")
                font_el.set("isEmbedded", "1")
                font_el.set("binaryItemIDRef", ref)
                face.set("fontCnt", str(len(fonts) + 1))
        target = output_path or hwpx_path
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        doc.save_to_path(str(target))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "path": str(target), "face": face_name}

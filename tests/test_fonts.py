"""사용자 지정 폰트가 헤더 fontface 에 자동 등록되어 적용되는지."""

from __future__ import annotations

import io
import os
import warnings
from pathlib import Path

from lxml import etree

import pytest

from open_hwpx import FontSpec, GOV_KOREAN, Paragraph, Report, Run, embed_font, register_font_file
from open_hwpx import fonts as _fonts
from open_hwpx._compat import HwpxDocument


@pytest.fixture(autouse=True)
def _clean_font_registry():
    _fonts.clear_registry()
    yield
    _fonts.clear_registry()


def _faces(data: bytes) -> set[str]:
    header = HwpxDocument.open(io.BytesIO(data)).headers[0].element
    return {f.get("face") for f in header.iter() if etree.QName(f).localname == "font"}


def _font_nodes(data: bytes, face: str):
    header = HwpxDocument.open(io.BytesIO(data)).headers[0].element
    return [
        (f.get("isEmbedded"), f.get("binaryItemIDRef"))
        for f in header.iter()
        if etree.QName(f).localname == "font" and f.get("face") == face
    ]


def _fake_ttf(tmp_path) -> str:
    p = tmp_path / "Fake.ttf"
    p.write_bytes(b"\x00\x01\x00\x00FAKEFONT" * 200)
    return str(p)


def test_custom_body_font_is_registered(tmp_path):
    theme = GOV_KOREAN.override(body=FontSpec("나눔고딕", 11.0))
    r = Report.new(title="T", organization="O", date="2026-01-01", theme=theme)
    r.add_chapter("장").add(Paragraph(Run("본문")))
    data = r.to_bytes()
    assert "나눔고딕" in _faces(data)
    assert HwpxDocument.open(io.BytesIO(data)).validate().ok


def test_run_level_font_registered_without_fallback_warning():
    r = Report.new(title="T", organization="O", date="2026-01-01")
    r.add_chapter("장").add(Paragraph(Run("강조", font="나눔명조")))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        data = r.to_bytes()
    # 이제 등록되므로 '기본 폰트로 대체' 폴백 경고가 없어야 한다.
    assert not any("기본 폰트로 대체" in str(w.message) for w in caught)
    assert "나눔명조" in _faces(data)


def test_default_fonts_still_work():
    r = Report.new(title="T", organization="O", date="2026-01-01")  # 기본 함초롬
    r.add_chapter("장").add(Paragraph(Run("본문")))
    data = r.to_bytes()
    faces = _faces(data)
    assert "함초롬바탕" in faces and HwpxDocument.open(io.BytesIO(data)).validate().ok


def test_registered_font_is_embedded(tmp_path):
    register_font_file("임베드체", _fake_ttf(tmp_path))
    theme = GOV_KOREAN.override(body=FontSpec("임베드체", 11.0))
    r = Report.new(title="T", organization="O", date="2026-01-01", theme=theme)
    r.add_chapter("장").add(Paragraph(Run("본문")))
    data = r.to_bytes()
    nodes = _font_nodes(data, "임베드체")
    assert nodes and nodes[0][0] == "1" and nodes[0][1]  # isEmbedded=1 + binaryItemIDRef
    ref = nodes[0][1]
    doc = HwpxDocument.open(io.BytesIO(data))
    assert doc.package.has_part(f"BinData/{ref}.ttf")  # 폰트 바이너리가 문서에 동봉됨
    assert doc.validate().ok


def test_unregistered_font_is_name_only():
    theme = GOV_KOREAN.override(body=FontSpec("이름만체", 11.0))
    r = Report.new(title="T", organization="O", date="2026-01-01", theme=theme)
    r.add_chapter("장").add(Paragraph(Run("본문")))
    nodes = _font_nodes(r.to_bytes(), "이름만체")
    assert nodes and nodes[0][0] == "0"  # 파일 등록 안 했으면 이름만(임베드 아님)


def test_embed_font_posthoc(tmp_path):
    r = Report.new(title="T", organization="O", date="2026-01-01")
    r.add_chapter("장").add(Paragraph(Run("hi")))
    path = str(tmp_path / "d.hwpx")
    r.save(path)
    res = embed_font(path, "동봉체", _fake_ttf(tmp_path))
    assert res["ok"]
    doc = HwpxDocument.open(path)
    nodes = [
        f.get("isEmbedded")
        for f in doc.headers[0].element.iter()
        if etree.QName(f).localname == "font" and f.get("face") == "동봉체"
    ]
    assert nodes and nodes[0] == "1"
    assert doc.validate().ok


def test_available_ofl_fonts_and_unknown_raises():
    names = _fonts.available_ofl_fonts()
    assert "나눔고딕" in names and "Noto Sans KR" in names
    import pytest as _pytest

    with _pytest.raises(KeyError):
        _fonts.ensure_font("존재하지않는폰트XYZ")  # 목록에 없으면(다운로드 전) 에러


@pytest.mark.skipif(
    not os.environ.get("OPEN_HWPX_NETWORK_TESTS"),
    reason="네트워크 테스트(OPEN_HWPX_NETWORK_TESTS=1 로 활성화)",
)
def test_ensure_font_downloads_and_embeds(tmp_path, monkeypatch):
    monkeypatch.setattr(_fonts, "_cache_dir", lambda: tmp_path)
    path = _fonts.ensure_font("나눔고딕")
    assert Path(path).exists() and Path(path).stat().st_size > 100_000
    assert _fonts.registered_fonts().get("나눔고딕") == path
    # 등록됐으니 생성물에 임베드된다
    theme = GOV_KOREAN.override(body=FontSpec("나눔고딕", 11.0))
    r = Report.new(title="T", organization="O", date="2026-01-01", theme=theme)
    r.add_chapter("장").add(Paragraph(Run("본문")))
    nodes = _font_nodes(r.to_bytes(), "나눔고딕")
    assert nodes and nodes[0][0] == "1"

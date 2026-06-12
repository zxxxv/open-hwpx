"""에이전트 tool-use 함수: 생성 → 되먹임 → 검증 루프."""

from __future__ import annotations

import json

import pytest

from open_hwpx import agent

_SPEC = {
    "schema": "open_hwpx.report.v1",
    "theme": "gov",
    "metadata": {"title": "테스트 보고서", "organization": "○○부", "date": "2026-06-12"},
    "chapters": [
        {"title": "추진 배경", "md": "본 계획은 **AI 융합**이 목표다.\n\n- 항목 하나\n- 항목 둘"},
        {
            "title": "표",
            "body": [{"type": "table", "header": ["구분", "값"], "rows": [["A", "1"], ["B", "2"]]}],
        },
    ],
}


def test_build_report_and_validate(tmp_path):
    out = tmp_path / "r.hwpx"
    res = agent.build_report(_SPEC, str(out))
    assert res["ok"] is True
    assert res["valid"] is True
    assert out.exists()


def test_build_report_accepts_json_string(tmp_path):
    res = agent.build_report(json.dumps(_SPEC), str(tmp_path / "r.hwpx"))
    assert res["ok"] and res["valid"]


def test_build_report_bad_spec_returns_error(tmp_path):
    res = agent.build_report({"schema": "wrong.v9", "chapters": []}, str(tmp_path / "x.hwpx"))
    assert res["ok"] is False
    assert "error" in res  # 예외 대신 에러 필드로 — 에이전트 self-correct


def test_build_from_markdown(tmp_path):
    res = agent.build_from_markdown("# 장\n본문", str(tmp_path / "m.hwpx"), preset="business", toc=True)
    assert res["ok"] and res["valid"]


def test_read_back_roundtrip(tmp_path):
    out = tmp_path / "r.hwpx"
    agent.build_report(_SPEC, str(out))
    md = agent.read_as_markdown(str(out))
    assert md["ok"] and "구분" in md["markdown"]  # 표 헤더가 되먹임에 보여야
    txt = agent.read_as_text(str(out))
    assert txt["ok"] and "추진 배경" in txt["text"]


def test_outline(tmp_path):
    out = tmp_path / "r.hwpx"
    agent.build_report(_SPEC, str(out))
    res = agent.get_outline(str(out))
    assert res["ok"]
    assert any("추진 배경" in o["text"] for o in res["outline"])


def test_render_to_html_string_and_file(tmp_path):
    out = tmp_path / "r.hwpx"
    agent.build_report(_SPEC, str(out))
    s = agent.render_to_html(str(out))
    assert s["ok"] and "<table" in s["html"]
    html_path = tmp_path / "r.html"
    f = agent.render_to_html(str(out), str(html_path))
    assert f["ok"] and html_path.exists()


def test_validate_presets_and_help(tmp_path):
    out = tmp_path / "r.hwpx"
    agent.build_report(_SPEC, str(out))
    assert agent.validate(str(out))["valid"] is True
    presets = agent.list_presets()
    assert presets["ok"] and "plain" in presets["presets"]
    assert "open_hwpx.report.v1" in agent.report_spec_help()["help"]


def test_mcp_server_registers_tools():
    pytest.importorskip("mcp")  # 선택 의존성 없으면 skip
    import asyncio

    from open_hwpx.mcp_server import build_server

    server = build_server()
    assert server.name == "open-hwpx"
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert {"build_report", "render_to_html", "read_as_markdown", "validate"} <= names

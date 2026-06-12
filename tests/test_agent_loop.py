"""도구들이 실제 에이전트 루프 모양(build→되먹임→편집→검증)으로 조합되는지 결정적으로 검증.

LLM 없이, 에이전트가 할 법한 도구 호출 시퀀스를 직접 수행한다.
"""

from __future__ import annotations

from open_hwpx import agent

# 에이전트가 나중에 고칠 자리표시자(placeholder)를 일부러 심은 초안.
_DRAFT = {
    "schema": "open_hwpx.report.v1",
    "theme": "gov",
    "metadata": {"title": "AI 융합교육 추진계획", "organization": "○○부", "date": "2026-06-12"},
    "chapters": [
        {"title": "추진 배경", "md": "본 계획은 **AI 융합교육** 확산이 목표다.\n\n- TODO_배경1\n- 현장 수요 증가"},
        {"title": "추진 일정", "body": [
            {"type": "table", "header": ["구분", "내용", "기한"],
             "rows": [["1단계", "기반 구축", "TODO_기한"], ["2단계", "전면 확산", "2026.12"]]},
        ]},
    ],
}


def test_build_readback_edit_validate_loop(tmp_path):
    path = str(tmp_path / "report.hwpx")

    # 1) 생성
    built = agent.build_report(_DRAFT, path)
    assert built["ok"] and built["valid"]

    # 2) 되먹임 — 에이전트가 결과를 "본다"
    seen = agent.read_as_markdown(path)
    assert seen["ok"]
    assert "TODO_배경1" in seen["markdown"]  # 자리표시자를 발견

    outline = agent.get_outline(path)
    assert outline["ok"]
    assert any("추진 배경" in o["text"] for o in outline["outline"])

    # 3) 편집 — 문구 자리표시자 치환 + 표 셀 자리표시자 수정
    assert agent.edit_replace_text(path, "TODO_배경1", "디지털 전환 가속")["ok"]
    tables = agent.list_tables(path)["tables"]
    # 기한 셀(헤더=0행, 1단계=1행, '기한'=2열)에 TODO_기한 이 있어야
    assert tables[0]["rows"][1][2] == "TODO_기한"
    assert agent.edit_set_cell(path, 0, 1, 2, "2026.03")["ok"]

    # 4) 재확인 + 검증
    final_text = agent.read_as_text(path)["text"]
    assert "TODO" not in final_text
    assert "디지털 전환 가속" in final_text
    assert agent.validate(path)["valid"] is True


def test_all_tools_have_docstrings():
    # tool-use 스키마 품질: 모든 도구는 LLM 이 읽을 설명(docstring)을 가져야 한다.
    for fn in agent.TOOLS:
        assert (fn.__doc__ or "").strip(), fn.__name__

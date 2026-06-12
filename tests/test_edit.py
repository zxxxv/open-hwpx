"""편집 도구: 무손실 read-modify-write (열기→수정→저장→재열기 보존)."""

from __future__ import annotations

from open_hwpx import agent


def _make(tmp_path) -> str:
    spec = {
        "schema": "open_hwpx.report.v1",
        "theme": "gov",
        "metadata": {"title": "원본제목", "organization": "○○부", "date": "2026-06-12"},
        "chapters": [
            {"title": "장하나", "body": [
                {"type": "paragraph", "runs": [{"text": "교체대상문구"}]},
                {"type": "table", "header": ["구분", "값"], "rows": [["A", "1"], ["B", "2"]]},
            ]},
        ],
    }
    out = tmp_path / "doc.hwpx"
    res = agent.build_report(spec, str(out))
    assert res["ok"] and res["valid"]
    return str(out)


def test_replace_text_persists(tmp_path):
    path = _make(tmp_path)
    res = agent.edit_replace_text(path, "교체대상문구", "바뀐문구")
    assert res["ok"] and res["replaced"] == 1
    md = agent.read_as_text(path)
    assert "바뀐문구" in md["text"] and "교체대상문구" not in md["text"]
    assert agent.validate(path)["valid"] is True  # 편집 후에도 유효


def test_set_cell_persists(tmp_path):
    path = _make(tmp_path)
    res = agent.edit_set_cell(path, 0, 1, 1, "변경값")
    assert res["ok"]
    tables = agent.list_tables(path)["tables"]
    assert tables[0]["rows"][1][1] == "변경값"


def test_set_cell_out_of_range(tmp_path):
    path = _make(tmp_path)
    res = agent.edit_set_cell(path, 9, 0, 0, "x")
    assert res["ok"] is False and "범위" in res["error"]


def test_set_paragraph_text(tmp_path):
    path = _make(tmp_path)
    paras = agent.list_paragraphs(path)["paragraphs"]
    target = next(p["index"] for p in paras if "교체대상문구" in p["text"])
    res = agent.edit_set_paragraph_text(path, target, "완전히새문단")
    assert res["ok"]
    assert "완전히새문단" in agent.read_as_text(path)["text"]


def test_append_paragraph(tmp_path):
    path = _make(tmp_path)
    res = agent.edit_append_paragraph(path, "맨끝에추가된문단")
    assert res["ok"]
    assert "맨끝에추가된문단" in agent.read_as_text(path)["text"]


def test_edit_to_separate_output_keeps_original(tmp_path):
    path = _make(tmp_path)
    out2 = str(tmp_path / "copy.hwpx")
    agent.edit_replace_text(path, "원본제목", "사본제목", output_path=out2)
    assert "사본제목" in agent.read_as_text(out2)["text"]
    assert "원본제목" in agent.read_as_text(path)["text"]  # 원본은 그대로


def test_list_paragraphs_and_tables_shape(tmp_path):
    path = _make(tmp_path)
    paras = agent.list_paragraphs(path)
    assert paras["ok"] and any(p["has_table"] for p in paras["paragraphs"])
    tables = agent.list_tables(path)
    assert tables["ok"] and tables["tables"][0]["rows"][0] == ["구분", "값"]


def test_delete_paragraph(tmp_path):
    path = _make(tmp_path)
    paras = agent.list_paragraphs(path)["paragraphs"]
    target = next(p["index"] for p in paras if "교체대상문구" in p["text"])
    res = agent.edit_delete_paragraph(path, target)
    assert res["ok"]
    assert "교체대상문구" not in agent.read_as_text(path)["text"]
    assert agent.validate(path)["valid"] is True


def test_merge_cells(tmp_path):
    # 헤더 + 2 데이터행 표에서 A2:A3(데이터 첫 칸 2개) 병합
    spec = {
        "schema": "open_hwpx.report.v1",
        "chapters": [{"title": "장", "body": [
            {"type": "table", "header": ["A", "B"], "rows": [["a1", "b1"], ["a2", "b2"]]}
        ]}],
    }
    path = str(tmp_path / "m.hwpx")
    assert agent.build_report(spec, path)["ok"]
    res = agent.edit_merge_cells(path, 0, "A2:A3")
    assert res["ok"]
    rows = agent.list_tables(path)["tables"][0]["rows"]
    assert rows[2][0] is None  # 병합으로 가려진 칸
    assert agent.validate(path)["valid"] is True


def test_add_table_row(tmp_path):
    path = _make(tmp_path)  # 표: 헤더 + 데이터 2행
    before = agent.list_tables(path)["tables"][0]["rows"]
    res = agent.edit_add_table_row(path, 0, ["C", "3"])
    assert res["ok"]
    rows = agent.list_tables(path)["tables"][0]["rows"]
    assert len(rows) == len(before) + 1
    assert rows[-1] == ["C", "3"]
    assert agent.validate(path)["valid"] is True


def test_delete_table_row(tmp_path):
    path = _make(tmp_path)
    before = agent.list_tables(path)["tables"][0]["rows"]
    res = agent.edit_delete_table_row(path, 0, 1)  # 첫 데이터행 삭제
    assert res["ok"]
    rows = agent.list_tables(path)["tables"][0]["rows"]
    assert len(rows) == len(before) - 1
    assert agent.validate(path)["valid"] is True


def test_delete_table_row_refuses_merged(tmp_path):
    spec = {
        "schema": "open_hwpx.report.v1",
        "chapters": [{"title": "장", "body": [
            {"type": "table", "header": ["A", "B"], "rows": [["a1", "b1"], ["a2", "b2"]], "merges": ["A2:A3"]}
        ]}],
    }
    path = str(tmp_path / "m.hwpx")
    agent.build_report(spec, path)
    res = agent.edit_delete_table_row(path, 0, 1)
    assert res["ok"] is False and "병합" in res["error"]

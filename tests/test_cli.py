"""CLI(build/presets/new/info) 동작."""

from __future__ import annotations

import json

from open_hwpx._compat import HwpxDocument
from open_hwpx.cli import main


def test_presets_command(capsys):
    rc = main(["presets"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "korean_gov_outline" in out
    assert "business_report" in out


def test_new_json_then_build(tmp_path, capsys):
    spec = tmp_path / "spec.json"
    assert main(["new", str(spec)]) == 0
    data = json.loads(spec.read_text(encoding="utf-8"))
    assert data["schema"] == "open_hwpx.report.v1"

    out = tmp_path / "out.hwpx"
    rc = main(["build", str(spec), "-o", str(out)])
    assert rc == 0
    assert out.exists()
    assert HwpxDocument.open(str(out)).validate().ok


def test_new_md_then_build(tmp_path):
    doc = tmp_path / "doc.md"
    assert main(["new", str(doc), "--md"]) == 0
    out = tmp_path / "doc.hwpx"
    rc = main(["build", str(doc), "-o", str(out), "--preset", "business", "--toc", "--page-number"])
    assert rc == 0
    assert HwpxDocument.open(str(out)).validate().ok


def test_build_default_output_path(tmp_path):
    doc = tmp_path / "report.md"
    doc.write_text("# 장\n본문 내용", encoding="utf-8")
    rc = main(["build", str(doc)])  # -o 생략 → report.hwpx
    assert rc == 0
    assert (tmp_path / "report.hwpx").exists()


def test_info_command(tmp_path, capsys):
    doc = tmp_path / "d.md"
    doc.write_text("# 제목장\n내용", encoding="utf-8")
    out = tmp_path / "d.hwpx"
    main(["build", str(doc), "-o", str(out)])
    capsys.readouterr()  # 비우기
    rc = main(["info", str(out)])
    assert rc == 0
    assert "정상" in capsys.readouterr().out

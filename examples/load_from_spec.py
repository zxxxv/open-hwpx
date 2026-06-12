"""예제: dict/JSON 스펙으로부터 보고서를 만든다.

실행::

    uv run python examples/load_from_spec.py

결과: examples/out/gov_report_spec.hwpx
"""

from __future__ import annotations

from pathlib import Path

from open_hwpx import Report

SPEC = Path(__file__).parent / "gov_report_spec.json"
OUT = Path(__file__).parent / "out" / "gov_report_spec.hwpx"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = Report.from_json(SPEC)
    path = report.save(OUT)
    print(f"저장 완료: {path}")

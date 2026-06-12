"""예제: fluent 빌더 API 로 공문서 스타일 보고서를 만든다.

실행::

    uv run python examples/gov_report_builder.py

결과: examples/out/gov_report_builder.hwpx (한글에서 열기)
"""

from __future__ import annotations

import base64
from pathlib import Path

from open_hwpx import BulletList, Image, NumberedList, Paragraph, Report, Run, Table

# 데모용 작은 PNG(파란 점). 실제로는 파일 경로를 주면 된다.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

OUT = Path(__file__).parent / "out" / "gov_report_builder.hwpx"


def build() -> Report:
    report = Report.new(
        title="2026년 AI 융합교육 추진계획",
        organization="○○부 기획조정실",
        date="2026-06-04",
    )
    report.set_footer(page_number=True)
    report.add_toc(max_level=3)

    # 1. 추진 배경
    bg = report.add_chapter("추진 배경")
    bg.add(Paragraph(
        Run("본 계획은 "),
        Run("AI 융합교육", bold=True, color="#1F4E79"),
        Run(" 확산을 통해 미래 인재를 양성하는 것을 목표로 한다."),
    ))
    bg.bullets(["디지털 전환 가속", "현장의 교육 수요 증가", "관련 법·제도 정비 필요"])

    # 2. 세부 추진계획
    plan = report.add_chapter("세부 추진계획")
    plan.add(Paragraph(Run("연차별로 단계적으로 추진한다.")))

    road = plan.add_chapter("단계별 로드맵")
    road.add(Table(
        header=["구분", "주요 내용", "기한"],
        rows=[
            ["1단계", "기반 구축 및 교원 연수", "2026.03"],
            ["1단계", "시범 학교 운영", "2026.06"],
            ["2단계", "전면 확산", "2026.12"],
        ],
        column_widths=[2, 4, 2],
        merges=["A2:A3"],
        caption="<표 1> 단계별 추진 일정",
    ))
    road.add(Image(_PNG, width_mm=60, caption="[그림 1] 추진 로드맵 개요"))

    budget = plan.add_chapter("소요 예산")
    budget.numbers(["인건비 12억원", "사업운영비 30억원", "기자재비 8억원"])

    # 3. 기대 효과
    report.add_chapter("기대 효과").add(
        Paragraph(Run("교육 격차 완화와 미래 역량 강화에 기여할 것으로 기대된다."))
    ).page_break()

    return report


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = build()
    path = report.save(OUT)
    print(f"저장 완료: {path}")

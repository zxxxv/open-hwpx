"""AI 보고서 자동화 — 직접 SDK tool-use 레퍼런스.

`open_hwpx.agent.TOOLS` 를 Anthropic tool-runner 에 그대로 꽂아, 모델이
**생성 → 되먹임(읽기) → 편집 → 검증** 루프를 자율 수행하게 한다. agentic RAG
서비스에서 "분석 자료 → 사람이 쓸 한글 보고서" 단계가 바로 이 패턴이다.

실행::

    pip install open-hwpx anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python examples/agent_report.py

MCP 없이 in-process 직접 호출이라, 멀티-AI/RAG 오케스트레이션을 당신 코드가 소유한 채
보고서 생성·편집·검증만 open_hwpx 에 위임할 수 있다.
"""

from __future__ import annotations

import os

import anthropic  # pip install anthropic

from open_hwpx import agent

# 실제 서비스에서는 RAG 검색·분석 결과가 여기에 들어온다(여기선 예시 자료).
RESEARCH = """\
[분석 자료]
- 2026년 AI 융합교육 확산이 정책 목표. 디지털 전환 가속, 현장 교육 수요 증가.
- 추진 일정: 1단계(기반 구축, 2026.03), 1단계(시범 운영, 2026.06), 2단계(전면 확산, 2026.12).
- 소요 예산: 인건비 12억, 사업운영비 30억, 기자재비 8억.
"""

SYSTEM = """\
너는 한국 정부 공문서를 작성하는 보고서 작가다. 도구로 한글(.hwpx) 보고서를 만든다.
작업 순서를 반드시 지켜라:
1) build_report(또는 build_from_markdown)로 gov 스타일 보고서를 생성한다(report_spec_help 로 스펙 확인).
2) read_as_markdown 으로 네가 만든 결과를 직접 검토한다 — 표·번호·누락 섹션을 점검.
3) 부족하면 list_paragraphs/list_tables 로 위치를 찾아 edit_* 도구로 외과적으로 고친다.
4) validate 로 유효성을 확인하고, 최종 파일 경로를 보고한다.
서식 plumbing 은 도구가 처리하니 너는 내용 품질에 집중하라."""

OUT = os.path.join(os.path.dirname(__file__), "out", "agent_report.hwpx")


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY 를 설정하세요.")

    client = anthropic.Anthropic()
    tools = [anthropic.beta_tool(fn) for fn in agent.TOOLS]  # 17개 도구 일괄 등록

    runner = client.beta.messages.tool_runner(
        model="claude-opus-4-8",            # 최신·최강
        max_tokens=16000,
        thinking={"type": "adaptive"},      # 에이전틱 작업 권장
        output_config={"effort": "high"},
        system=SYSTEM,
        tools=tools,
        messages=[{
            "role": "user",
            "content": f"{RESEARCH}\n위 자료로 보고서를 만들어 `{OUT}` 에 저장하라.",
        }],
    )

    for message in runner:  # tool-runner 가 build→read-back→edit 루프를 자동 처리
        for block in message.content:
            if block.type == "text":
                print(block.text)

    print(f"\n→ 산출물: {OUT}")
    print("검증:", agent.validate(OUT))


if __name__ == "__main__":
    main()

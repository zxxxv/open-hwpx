"""hwpx 명령줄 인터페이스.

  hwpx build <spec.json|doc.md> -o out.hwpx [--preset 이름] [--title ...] [--toc]
  hwpx presets
  hwpx new <out.json> [--md]
  hwpx info <file.hwpx>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .styles import get_theme, preset_names


def _build(args: argparse.Namespace) -> int:
    from .markdown import markdown_to_report
    from .report import Report

    src = Path(args.input)
    if not src.exists():
        print(f"입력 파일을 찾을 수 없습니다: {src}", file=sys.stderr)
        return 2

    theme = get_theme(args.preset) if args.preset else None
    suffix = src.suffix.lower()

    if suffix in (".md", ".markdown", ".txt"):
        report = markdown_to_report(
            src.read_text(encoding="utf-8"),
            theme=theme,
            title=args.title or src.stem,
            base_dir=src.parent,
        )
    elif suffix == ".json":
        report = Report.from_json(src)
        if theme is not None:
            report.set_theme(theme)
        if args.title:
            report.set_metadata(title=args.title)
    else:
        print(f"지원하지 않는 입력 형식: {suffix} (.json 또는 .md)", file=sys.stderr)
        return 2

    if args.toc and not any(type(c).__name__ == "TableOfContents" for c in report.front_matter):
        report.add_toc()
    if args.page_number:
        report.set_footer(page_number=True)

    out = Path(args.output) if args.output else src.with_suffix(".hwpx")
    out.parent.mkdir(parents=True, exist_ok=True)
    report.save(out)

    if args.validate:
        from ._compat import HwpxDocument

        rep = HwpxDocument.open(str(out)).validate()
        status = "정상" if rep.ok else f"오류 {list(rep.errors)}"
        print(f"저장: {out}  (검증: {status})")
        return 0 if rep.ok else 1
    print(f"저장: {out}")
    return 0


def _presets(_args: argparse.Namespace) -> int:
    print("사용 가능한 프리셋:")
    descriptions = {
        "korean_gov_outline": "한국 공문서 개조식 (□○-· 마커 + 들여쓰기)",
        "business_report": "일반 보고서 (번호식 제목 1. / 1.1 …)",
        "plain": "일반 글쓰기 (굵은 제목, 마커·번호 없음)",
    }
    for name in preset_names():
        print(f"  - {name:20s} {descriptions.get(name, '')}")
    return 0


_STARTER_SPEC = {
    "schema": "open_hwpx.report.v1",
    "theme": "gov",
    "metadata": {"title": "보고서 제목", "organization": "○○부", "date": "2026-06-04"},
    "page": {"size": "A4", "margins": {"top_mm": 20, "bottom_mm": 15, "left_mm": 20, "right_mm": 20}},
    "footer": {"blocks": [{"type": "page_number"}]},
    "front_matter": [{"type": "toc", "title": "목  차", "max_level": 3}],
    "chapters": [
        {
            "title": "추진 배경",
            "md": "본 계획은 **핵심 목표** 달성을 위한 것이다.\n\n- 배경 1\n- 배경 2",
        },
        {
            "title": "세부 추진계획",
            "chapters": [
                {
                    "title": "단계별 로드맵",
                    "body": [
                        {
                            "type": "table",
                            "header": ["구분", "내용", "기한"],
                            "rows": [["1단계", "기반 구축", "3월"], ["2단계", "확산", "12월"]],
                        }
                    ],
                }
            ],
        },
    ],
}

_STARTER_MD = """# 추진 배경

본 계획은 **핵심 목표** 달성을 위한 것이다.

- 배경 1
- 배경 2

# 세부 추진계획

## 단계별 로드맵

| 구분 | 내용 | 기한 |
| --- | --- | --- |
| 1단계 | 기반 구축 | 3월 |
| 2단계 | 확산 | 12월 |
"""


def _new(args: argparse.Namespace) -> int:
    out = Path(args.output)
    if out.exists() and not args.force:
        print(f"이미 존재합니다(덮어쓰려면 --force): {out}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.md:
        out.write_text(_STARTER_MD, encoding="utf-8")
    else:
        out.write_text(json.dumps(_STARTER_SPEC, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"템플릿 생성: {out}")
    return 0


def _info(args: argparse.Namespace) -> int:
    from ._compat import HwpxDocument

    path = Path(args.input)
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 2
    doc = HwpxDocument.open(str(path))
    rep = doc.validate()
    print(f"파일: {path}")
    print(f"검증: {'정상' if rep.ok else '오류'}  errors={list(rep.errors)}")
    lines = [l for l in doc.export_text().splitlines() if l.strip()]
    print(f"문단 수(텍스트 줄): {len(lines)}")
    for line in lines[:8]:
        print(f"   {line}")
    return 0 if rep.ok else 1


def _render(args: argparse.Namespace) -> int:
    from .render_html import render_html

    path = Path(args.input)
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 2
    html = render_html(str(path), fragment=args.fragment, title=args.title)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"렌더: {out}")
    else:
        sys.stdout.write(html)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hwpx", description="한글(HWPX) 문서 생성·렌더 CLI")
    parser.add_argument("--version", action="version", version=f"hwpx {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="JSON 스펙 또는 Markdown 으로 .hwpx 생성")
    b.add_argument("input", help="입력 파일(.json 또는 .md)")
    b.add_argument("-o", "--output", help="출력 .hwpx 경로(기본: 입력명.hwpx)")
    b.add_argument("-p", "--preset", help=f"프리셋 이름 {preset_names()}")
    b.add_argument("-t", "--title", help="문서 제목(덮어쓰기)")
    b.add_argument("--toc", action="store_true", help="자동 목차 추가")
    b.add_argument("--page-number", action="store_true", help="꼬리말에 쪽번호(가운데)")
    b.add_argument("--no-validate", dest="validate", action="store_false", help="저장 후 검증 생략")
    b.set_defaults(func=_build, validate=True)

    p = sub.add_parser("presets", help="사용 가능한 프리셋 목록")
    p.set_defaults(func=_presets)

    n = sub.add_parser("new", help="시작용 템플릿(JSON 또는 MD) 생성")
    n.add_argument("output", help="생성할 파일 경로")
    n.add_argument("--md", action="store_true", help="JSON 대신 Markdown 템플릿")
    n.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    n.set_defaults(func=_new)

    i = sub.add_parser("info", help="기존 .hwpx 검증/요약")
    i.add_argument("input", help=".hwpx 파일")
    i.set_defaults(func=_info)

    r = sub.add_parser("render", help="기존 .hwpx 를 HTML 로 렌더링(표·서식 보존)")
    r.add_argument("input", help=".hwpx 파일")
    r.add_argument("-o", "--output", help="출력 .html 경로(생략 시 stdout)")
    r.add_argument("--fragment", action="store_true", help="<html> 래퍼 없이 본문만(webview 용)")
    r.add_argument("-t", "--title", help="문서 제목")
    r.set_defaults(func=_render)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

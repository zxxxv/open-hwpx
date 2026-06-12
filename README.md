# open-hwpx

한글(HWPX) 문서를 **쉽게 생성·렌더링·편집**하는 컴포넌트 기반 파이썬 모듈. (`import open_hwpx`, CLI `hwpx`)

- 한컴 오피스 설치 불필요(순수 파이썬). **macOS·Linux·Windows·CI 어디서나** `.hwpx` 생성. 검증된 오픈소스 [`python-hwpx`](https://github.com/airmang/python-hwpx) 위에 얇게 올린 어댑터.
- **2단계 워크플로**: ① 세팅·구조(테마·페이지·목차·장)를 먼저 정하고 → ② 각 장에 컴포넌트(문단·표·그림 …)를 주입.
- **세 가지 주입 방식**: ① fluent 빌더 API, ② dict/JSON 스펙, ③ JSON 구조 + 본문 **Markdown** 하이브리드.
- **프리셋 3종**: `gov`(공문서 개조식 □○-·), `business`(번호식 1./1.1), `plain`(일반 글쓰기).
- **CLI 제공**: `hwpx build / presets / new / info`.

## 설치

```bash
uv sync                 # 런타임 의존성(python-hwpx)
uv sync --extra dev     # 테스트까지(pytest)
```

## 빠른 시작 — 빌더 API

```python
from open_hwpx import Report, Paragraph, Run, Table, Image, BulletList

report = Report.new(title="2026년 사업 추진계획", organization="○○부", date="2026-06-04")
report.set_footer(page_number=True)
report.add_toc(max_level=3)            # 자동 목차

bg = report.add_chapter("추진 배경")    # 대제목 □
bg.add(Paragraph(
    Run("본 계획은 "),
    Run("AI 융합교육", bold=True, color="#1F4E79"),
    Run(" 확산을 목표로 한다."),
))
bg.bullets(["디지털 전환 가속", "현장 수요 증가"])

road = report.add_chapter("세부 추진계획").add_chapter("단계별 로드맵")  # ○ → 중제목
road.add(Table(
    header=["구분", "내용", "기한"],
    rows=[["1단계", "기반 구축", "3월"], ["1단계", "시범 운영", "6월"]],
    column_widths=[2, 3, 1], merges=["A2:A3"], caption="<표 1> 추진 일정",
))
road.add(Image("assets/roadmap.png", width_mm=120, caption="[그림 1] 로드맵"))

report.save("보고서.hwpx")             # → 한글에서 바로 열림
```

## 빠른 시작 — JSON 구조 + Markdown 본문 (권장 하이브리드)

구조(장·테마·페이지·표)는 JSON 으로 정밀하게, 본문 글쓰기는 Markdown 으로 빠르게.

```json
{
  "schema": "open_hwpx.report.v1",
  "theme": "gov",
  "metadata": { "title": "2026년 추진계획" },
  "front_matter": [ { "type": "toc" } ],
  "chapters": [
    { "title": "추진 배경",
      "md": "본 계획은 **AI 융합교육** 확산이 목표다.\n\n- 디지털 전환\n- 수요 증가" },
    { "title": "세부 계획", "chapters": [
        { "title": "로드맵", "body": [
            { "type": "table", "header": ["구분","내용"], "rows": [["1단계","구축"]] } ] } ] }
  ]
}
```

```python
from open_hwpx import Report
Report.from_json("plan.json").save("보고서.hwpx")
```

장의 `md` 필드(또는 `{"type":"markdown","md":"..."}` 블록)는 **굵게/기울임, 목록, 표,
이미지, 소제목**을 자동으로 컴포넌트로 변환한다. 빌더·JSON·Markdown 세 경로는 동일한 구조
트리로 수렴하므로 결과가 같다. 스펙 전체 예시는 [`examples/gov_report_spec.json`](examples/gov_report_spec.json).

## 프리셋

| 이름 | 느낌 |
|---|---|
| `gov` (기본) | 한국 공문서 개조식 — □ ○ - · 마커 + 단계별 들여쓰기 |
| `business` | 일반 보고서 — 번호식 제목(1. / 1.1), 왼쪽 정렬 |
| `plain` | 일반 글쓰기 — 굵은 제목만, 마커·번호 없음 |

```python
report = Report.new(title="...", theme="business")   # 이름 문자열로 선택
```

## CLI

```bash
hwpx presets                                     # 프리셋 목록
hwpx new plan.json                               # 시작 템플릿(JSON) 생성  (--md 로 Markdown)
hwpx build plan.json -o 보고서.hwpx              # JSON → hwpx
hwpx build article.md  -o 글.hwpx --preset plain --toc --page-number
hwpx info 보고서.hwpx                            # 기존 파일 검증/요약
```

순수 Markdown(`.md`) 입력은 `#` → 장, `##` → 하위 장으로 구조를 잡는다([`examples/article.md`](examples/article.md)).

## 컴포넌트

| 컴포넌트 | 설명 |
|---|---|
| `Paragraph(*runs, align=)` / `Run(text, bold=, italic=, underline=, color=, font=, size=)` | 본문 문단과 인라인 서식 |
| `Heading(text, level)` | 제목(0=문서 제목, 1=대제목 …) |
| `Table(header=, rows=, column_widths=, header_shading=, merges=, caption=)` | 표(병합·음영·열너비) |
| `Image(path, width_mm=, align=, caption=)` | 그림(파일 경로 또는 bytes) |
| `BulletList(items, level=)` / `NumberedList(items, level=)` | 글머리표·번호 목록 |
| `TableOfContents(title=, max_level=)` | 자동 목차(장 트리에서 생성) |
| `Header/Footer(..., page_number=)` / `PageNumber` | 머리말·꼬리말·쪽번호 |
| `PageBreak()` | 페이지 나누기 |

## 테마 커스터마이즈 · 페이지/여백

```python
from open_hwpx import GOV_KOREAN, FontSpec
my_theme = GOV_KOREAN.override(
    body=FontSpec("함초롬바탕", 12.0),
    indent_chars_per_level=1.5,     # 레벨당 들여쓰기 폭(글자 수)
)

report = Report.new(title="...", theme=my_theme)
report.set_page(size="A4", orientation="PORTRAIT",
                top_mm=25, bottom_mm=20, left_mm=20, right_mm=20)  # 개별 여백 지정
report.set_footer(page_number=True)   # 쪽번호(가운데)
```

## 한계(v1)

- **폰트**: 블랭크 템플릿에 등록된 `함초롬바탕`/`함초롬돋움`만 안전하게 적용된다. 그 외 폰트는 경고 후 기본 폰트로 대체(폰트 임베드는 향후 과제).
- **목차 쪽번호**: 한컴 없이 페이지 수를 계산할 수 없어 v1 목차는 번호+제목만 출력한다.
- **머리말/꼬리말 텍스트 정렬**: 쪽번호는 가운데로 들어가지만, 임의 머리말/꼬리말 텍스트의 정렬은 상위 라이브러리 제약으로 제한적이다.

자세한 상위 API 동작은 [`docs/python-hwpx-api-notes.md`](docs/python-hwpx-api-notes.md) 참고.

## 개발

```bash
uv run pytest             # 테스트(빌드 → 재오픈 → validate 포함)
uv run python examples/gov_report_builder.py
uv run python examples/load_from_spec.py
```

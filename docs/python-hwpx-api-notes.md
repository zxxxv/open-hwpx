# Step 0 스파이크 결과 (python-hwpx 2.10.0, 휠 기준 확정)

## 확정 API (실제 호출 경로)
- `from hwpx.document import HwpxDocument`
- `HwpxDocument.new() / .open(src) / .save_to_path(path) / .validate() / .export_text()`
- `ValidationReport(validated_parts, issues)` — `issues` 비면 정상(`.ok == True`).
- `doc.add_paragraph(text="", *, para_pr_id_ref=, char_pr_id_ref=, include_run=True, inherit_style=True, **extra_attrs)`
  - `inherit_style=False`로 템플릿 스타일 간섭 방지.
  - `**extra_attrs` → `<hp:p>` 속성. 페이지나누기: `add_paragraph("", pageBreak="1", inherit_style=False)`.
  - 반환: `HwpxOxmlParagraph` (`.add_run(...)`, `.text`, `.runs`, `.element`). **`set_attribute` 없음.**
- `para.add_run(text="", *, char_pr_id_ref=, bold, italic, underline, color, font, size, highlight, strike)`
- `doc.ensure_run_style(*, bold, italic, underline, color, font, size, highlight, strike, base_char_pr_id) -> charPrIDRef(str)`
  - **size 단위 = 포인트.** 저장 시 `height = pt*100` (11pt→1100, 16pt→1600).
  - color="#RRGGBB" → `textColor`.
  - **font: 이미 등록된 face만 적용.** 블랭크 템플릿 등록 face = `함초롬바탕`, `함초롬돋움` 뿐. 그 외(굴림/맑은 고딕/HY헤드라인M 등) 조용히 무시(fontRef 미설정).
- `doc.add_table(rows, cols) -> HwpxOxmlTable`
  - `tbl.cell(r,c).text = "..."`, `tbl.merge_cells("A2:A3")`, `tbl.set_cell_shading(r,c,"#RRGGBB")`, `tbl.set_column_widths([w,...])`. 헤더 = 0행.
- `doc.add_picture(bytes, fmt, *, width_mm=, height_mm=, align="CENTER", section_index=) -> HwpxOxmlInlineObject`
  - hp:pic + BinData/BIN0001.png 임베드, validate 통과.
- `doc.ensure_numbering(kind="bullet"|"number", levels=[{"char":"□"}, ...]) -> list[paraPrIDRef]`
  - `refs[level]`을 `add_paragraph(para_pr_id_ref=refs[level])`로 사용 → 마커+레벨 들여쓰기.
- 헤더/푸터: `doc.set_header_text/set_footer_text(text, page_type="BOTH")`,
  rich: `doc.set_header_content/set_footer_content(content: Sequence[Mapping], page_type="BOTH")`.
- 페이지: `doc.set_page_size(width=, height=, orientation=, section_index=)`,
  `doc.set_page_margins(left,right,top,bottom,header,footer,gutter, section_index=)`. 단위 = HWPUNIT.
  mm→HWPUNIT ≈ `round(mm * 7200 / 25.4)`. (A4=210×297mm. 빌더 `_A4_HWP_SIZE` 상수와 대조 검증할 것.)

## builder 레이어 (참고용, 직접 구동에서는 미사용)
- `hwpx.builder`: Document/Section/Paragraph/Run/Heading/Bullet/NumberedList/Table/Image/PageBreak/Header/Footer/PageNumber/PageSize/Margins/Metadata.
- `Heading.lower`는 **레벨 1~3만, font=함초롬바탕, outlineLevel 미설정** → 개요식엔 부적합 → 우리가 직접 구현.
- `Document.lower()`의 메타데이터 처리는 "제목: ..." 평문 문단 → 사용 안 함(자체 표지 구성).

## 설계 반영(계획 대비 변경)
1. 렌더러는 builder 노드를 거치지 않고 **컴포넌트가 `HwpxDocument`를 직접 호출**. (deferred 큐 불필요)
2. outlineLevel 미사용. 목차는 Chapter 트리에서 정적 생성.
3. 개요식 마커/들여쓰기 = `ensure_numbering(kind="bullet", levels=[...])` paraPr 재사용.
4. 기본 테마 폰트 = 함초롬바탕(본문)/함초롬돋움(제목). 미등록 폰트 요청 시 경고 후 기본 사용.

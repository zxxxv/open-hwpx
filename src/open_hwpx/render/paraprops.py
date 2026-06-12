"""개요 들여쓰기용 paraPr 생성/패치 (python-hwpx 2.10 내부 사용).

상위 라이브러리에는 '좌측 들여쓰기 paraPr'를 만드는 공개 API가 없다. 그래서 헤더의
내부 헬퍼(_para_properties_element / _ensure_bullet_definition / _allocate_ref_id /
_update_item_count)를 이용해 base paraPr를 복제하고 [좌측여백 + (선택)글머리표 마커 +
(선택)정렬] 조합 paraPr를 만든다. 네임스페이스는 하드코딩하지 않고 기존 요소에서 끌어온다.

내부 구조가 바뀌면 호출부에서 우아하게 폴백할 수 있도록 실패 시 예외를 던진다.
"""

from __future__ import annotations

from copy import deepcopy


def _lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(parent, local: str):
    for c in parent:
        if isinstance(c.tag, str) and _lname(c.tag) == local:
            return c
    return None


def _base_para_pr(para_props):
    for c in para_props:
        if isinstance(c.tag, str) and _lname(c.tag) == "paraPr":
            return c
    return None


def _set_left_margin_value(node, left: int) -> bool:
    """node 하위의 모든 <margin>/<left>에 좌측 여백을 설정.

    paraPr 의 margin 은 호환성(<switch>) 안에 중첩돼 있을 수 있어 하위 전체를 훑는다.
    """
    found = False
    for el in node.iter():
        if isinstance(el.tag, str) and _lname(el.tag) == "margin":
            for c in el:
                if isinstance(c.tag, str) and _lname(c.tag) == "left":
                    c.set("value", str(int(left)))
                    found = True
    return found


def ensure_outline_para(
    header,
    *,
    left: int = 0,
    marker_char: str | None = None,
    marker_level: int = 0,
    align: str | None = None,
) -> str:
    """좌측여백/마커/정렬을 가진 paraPr id를 만들어 반환.

    left: 좌측 여백(HWPUNIT). marker_char: 글머리표 글자(없으면 마커 없음).
    align: "LEFT"|"CENTER"|"RIGHT"|"JUSTIFY"(None이면 base 정렬 유지).
    """
    para_props = header._para_properties_element(create=True)
    base = _base_para_pr(para_props)
    if base is None:
        raise RuntimeError("base paraPr를 찾지 못했습니다")

    node = deepcopy(base)
    node.attrib.pop("id", None)

    _set_left_margin_value(node, left)

    heading = _child(node, "heading")
    if heading is not None:
        if marker_char:
            bullet_id = header._ensure_bullet_definition(marker_char)
            heading.set("type", "BULLET")
            heading.set("idRef", str(bullet_id))
            heading.set("level", str(marker_level))
        else:
            heading.set("type", "NONE")
            heading.set("idRef", "0")
            heading.set("level", "0")

    if align:
        align_el = _child(node, "align")
        if align_el is not None:
            align_el.set("horizontal", align)

    new_id = header._allocate_ref_id(para_props, base.tag)
    node.set("id", new_id)
    para_props.append(node)
    header._update_item_count(para_props, base.tag)
    header.mark_dirty()
    return new_id


def patch_left_margin(header, para_pr_id: str, left: int) -> None:
    """이미 있는 paraPr의 좌측 여백만 바꾼다(번호 목록 들여쓰기용)."""
    para_props = header._para_properties_element(create=True)
    for para_pr in para_props:
        if not isinstance(para_pr.tag, str) or _lname(para_pr.tag) != "paraPr":
            continue
        if para_pr.get("id") != str(para_pr_id):
            continue
        _set_left_margin_value(para_pr, left)
        header.mark_dirty()
        return

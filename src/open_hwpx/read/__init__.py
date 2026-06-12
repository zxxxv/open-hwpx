"""읽기: ``.hwpx`` → 사람이 다루기 쉬운 :class:`RDocument`.

    import open_hwpx as hwpx
    doc = hwpx.load("a.hwpx")
    for p in doc.paragraphs:
        for r in p.runs:
            print(r.text, r.bold, r.color)
    doc.to_html("a.html")
"""

from __future__ import annotations

from .model import (
    RBlock,
    RCell,
    RDocument,
    RHeading,
    RImage,
    RList,
    RListItem,
    RParagraph,
    RRun,
    RTable,
)
from .reader import load, load_document, read_document

__all__ = [
    "read_document",
    "load",
    "load_document",
    "RDocument",
    "RBlock",
    "RParagraph",
    "RHeading",
    "RRun",
    "RList",
    "RListItem",
    "RTable",
    "RCell",
    "RImage",
]

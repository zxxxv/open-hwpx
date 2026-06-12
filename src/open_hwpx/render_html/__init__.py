"""렌더링: ``RDocument``/``.hwpx`` → 충실 HTML."""

from __future__ import annotations

from .renderer import DEFAULT_CSS, render_html

__all__ = ["render_html", "DEFAULT_CSS"]

"""dict/JSON 스펙 처리."""

from __future__ import annotations

from .loader import report_from_spec
from .schema import SCHEMA_VERSION, SpecError, build_component

__all__ = ["report_from_spec", "build_component", "SCHEMA_VERSION", "SpecError"]

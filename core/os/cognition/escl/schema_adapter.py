"""
core/os/cognition/escl/schema_adapter.py
E2 — Canonical Schema Adapter Layer.

Performs 3-tier translation:
Model Output Intent -> Canonical Action Schema -> Low-Level Engine Parameters.
Ensures zero parameter drop and absolute semantic continuity.
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class SchemaAdapter:
    """Adapts arbitrary model output formats to canonical tool execution schemas."""

    def adapt_office_intent(self, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """Translates raw LLM parameters to strict Office Suite Master input schema."""
        canonical = dict(raw_params)
        
        # 1. Normalize action & format
        action = str(canonical.get("action", "")).lower()
        fmt = str(canonical.get("format", "")).lower()
        file_type = str(canonical.get("file_type", "")).lower()

        if "excel" in fmt or "xlsx" in file_type or "excel" in action:
            canonical["format"] = "xlsx"
            canonical["action"] = "create_file"
        elif "word" in fmt or "docx" in file_type or "word" in action:
            canonical["format"] = "docx"
            canonical["action"] = "write_word"
        elif "pdf" in fmt or "pdf" in file_type or "pdf" in action:
            canonical["format"] = "pdf"
            canonical["action"] = "write_pdf"
        elif not action:
            canonical["action"] = "create_file"

        # 2. Normalize title & filename
        title = canonical.get("title") or canonical.get("filename") or "Document"
        canonical["title"] = title
        if not canonical.get("filename"):
            canonical["filename"] = title

        # 3. Detect embedded chart requirements
        if "charts" in canonical or "content_structure" in canonical:
            canonical["add_charts"] = True

        return canonical


schema_adapter = SchemaAdapter()

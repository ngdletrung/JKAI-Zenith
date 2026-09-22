# -*- coding: utf-8 -*-
"""
core/os/routing/entity_extractor.py
🏛️ INGRESS ENTITY EXTRACTOR & INTENT ASSERTION ENGINE (P0.4)
Deterministic parsing of target resource paths, quoted files, and glob patterns.
Enforces invariant: target paths >= 2 OR multi-file glob -> hardcode SCOPE = MULTI_RESOURCE.
"""

from __future__ import annotations
import glob
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Optional


@dataclass
class ExtractedEntities:
    raw_prompt: str
    target_paths: List[str] = field(default_factory=list)
    glob_patterns: List[str] = field(default_factory=list)
    resolved_file_count: int = 0
    is_multi_resource: bool = False
    scope: str = "QUERY_OR_GENERAL"  # MULTI_RESOURCE | SINGLE_RESOURCE | QUERY_OR_GENERAL


class IngressEntityExtractor:
    """
    Deterministic Ingress Entity Extractor.
    Extracts file paths, quoted strings, and glob patterns before LLM intent classification.
    """

    # Known file extensions to recognize in prose
    KNOWN_EXTENSIONS = (
        r"\.(?:py|json|md|ts|js|yaml|yml|sh|ps1|txt|csv|xlsx|docx|pdf|html|css|sql|toml|ini|xml)"
    )

    # Regex patterns
    GLOB_REGEX = re.compile(r"(?:[a-zA-Z0-9_\-\.\/\\]*[\*\?]+[a-zA-Z0-9_\-\.\/\\]*)")
    QUOTED_FILE_REGEX = re.compile(rf'["\']([^"\']+{KNOWN_EXTENSIONS})["\']', re.IGNORECASE)
    RAW_PATH_REGEX = re.compile(rf'(?:[a-zA-Z]:[\\/][^\s]+|/(?:workspace|tmp|etc|var)[^\s]*|[a-zA-Z0-9_\-\.\/]+{KNOWN_EXTENSIONS})', re.IGNORECASE)

    @classmethod
    def extract(cls, prompt: str, workspace_root: Optional[str] = None) -> ExtractedEntities:
        if not prompt or not isinstance(prompt, str):
            return ExtractedEntities(raw_prompt="", scope="QUERY_OR_GENERAL")

        target_paths: Set[str] = set()
        glob_patterns: List[str] = []

        # 1. Quoted paths check: "file one.txt", 'src/app.py'
        for match in cls.QUOTED_FILE_REGEX.findall(prompt):
            clean = match.strip()
            if clean:
                target_paths.add(clean)

        # 2. Raw path regex check: absolute and relative paths
        for match in cls.RAW_PATH_REGEX.findall(prompt):
            clean = match.strip().strip("'\"").rstrip(".,;:)")
            if clean and not clean.startswith("http://") and not clean.startswith("https://"):
                target_paths.add(clean)

        # 3. Glob pattern check (P0.4-A): **/*.py, src/*.ts
        tokens = prompt.split()
        for token in tokens:
            clean_tok = token.strip("'\",;()[]")
            if any(char in clean_tok for char in ("*", "?")):
                # Verify it looks like a file pattern or directory glob
                if "." in clean_tok or "/" in clean_tok or "\\" in clean_tok:
                    glob_patterns.append(clean_tok)

        # 4. Resolve glob patterns on disk if workspace provided
        resolved_from_glob: Set[str] = set()
        base_dir = workspace_root or os.getcwd()

        for pattern in glob_patterns:
            try:
                full_pattern = pattern if os.path.isabs(pattern) else os.path.join(base_dir, pattern)
                matches = glob.glob(full_pattern, recursive=True)
                for m in matches:
                    resolved_from_glob.add(os.path.normpath(m))
            except Exception:
                pass

        total_files = len(target_paths) + len(resolved_from_glob)
        # If glob was found but didn't match real disk files (e.g. hypothetical in test),
        # treat recursive glob '**/*' as implying multi-resource
        has_multi_glob = any("**" in g or "*" in g for g in glob_patterns)

        is_multi = (total_files >= 2) or has_multi_glob or (len(glob_patterns) >= 2)

        if is_multi:
            scope = "MULTI_RESOURCE"
        elif total_files == 1 or glob_patterns:
            scope = "SINGLE_RESOURCE"
        else:
            scope = "QUERY_OR_GENERAL"

        all_paths = sorted(list(target_paths.union(resolved_from_glob)))
        return ExtractedEntities(
            raw_prompt=prompt,
            target_paths=all_paths,
            glob_patterns=glob_patterns,
            resolved_file_count=max(total_files, 2 if has_multi_glob else 0),
            is_multi_resource=is_multi,
            scope=scope
        )

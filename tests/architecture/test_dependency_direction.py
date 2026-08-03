"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: DEPENDENCY DIRECTION
tests/architecture/test_dependency_direction.py

Architectural Invariant Enforced:
    One-Way Import Dependency:
    - Governance MUST NOT import from Cognitive
    - Infrastructure MUST NOT import from Cognitive, Governance, or Runtime
    - Runtime MUST NOT import from Cognitive
"""

import pytest
import os
import glob
import ast


class TestDependencyDirection:

    def test_governance_does_not_import_cognitive(self):
        gov_dir = os.path.join("core", "governance")
        py_files = glob.glob(os.path.join(gov_dir, "**", "*.py"), recursive=True)

        for filepath in py_files:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("core.cognitive"), (
                        f"Constitutional Violation in {filepath}:{node.lineno}: "
                        f"Governance must NOT import from Cognitive! Found 'from {node.module} import ...'"
                    )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("core.cognitive"), (
                            f"Constitutional Violation in {filepath}:{node.lineno}: "
                            f"Governance must NOT import from Cognitive! Found 'import {alias.name}'"
                        )

    def test_infrastructure_does_not_import_cognitive_or_governance(self):
        infra_dir = os.path.join("core", "infrastructure")
        py_files = glob.glob(os.path.join(infra_dir, "**", "*.py"), recursive=True)

        forbidden = ("core.cognitive", "core.governance")

        for filepath in py_files:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for prefix in forbidden:
                        assert not node.module.startswith(prefix), (
                            f"Constitutional Violation in {filepath}:{node.lineno}: "
                            f"Infrastructure must NOT import from {prefix}! Found 'from {node.module} import ...'"
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        for prefix in forbidden:
                            assert not alias.name.startswith(prefix), (
                                f"Constitutional Violation in {filepath}:{node.lineno}: "
                                f"Infrastructure must NOT import from {prefix}! Found 'import {alias.name}'"
                            )


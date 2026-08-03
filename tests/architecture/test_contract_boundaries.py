"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: CONTRACT BOUNDARIES
tests/architecture/test_contract_boundaries.py

Architectural Invariant Enforced:
    core.contracts MUST be a pure, zero-dependency data contract package.
    It MUST NOT import from any domain packages:
        - core.cognitive
        - core.knowledge
        - core.capabilities
        - core.governance
        - core.runtime
        - core.infrastructure
"""

import pytest
import os
import glob
import ast


class TestContractBoundaries:

    def test_contracts_package_has_zero_domain_imports(self):
        contracts_dir = os.path.join("core", "contracts")
        py_files = glob.glob(os.path.join(contracts_dir, "*.py"))

        forbidden_prefixes = (
            "core.cognitive",
            "core.knowledge",
            "core.capabilities",
            "core.governance",
            "core.runtime",
            "core.infrastructure",
        )

        for filepath in py_files:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for prefix in forbidden_prefixes:
                        assert not node.module.startswith(prefix), (
                            f"Architectural Violation in {filepath}:{node.lineno}: "
                            f"Contracts must NOT import domain code! Found 'from {node.module} import ...'"
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        for prefix in forbidden_prefixes:
                            assert not alias.name.startswith(prefix), (
                                f"Architectural Violation in {filepath}:{node.lineno}: "
                                f"Contracts must NOT import domain code! Found 'import {alias.name}'"
                            )


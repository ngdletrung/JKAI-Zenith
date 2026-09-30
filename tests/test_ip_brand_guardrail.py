# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: tests/test_ip_brand_guardrail.py
- Role: Automated IP & Brand Honesty Guardrail Test (.keywork.md Part V.2, V.5, V.6).
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.0
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import List, Set

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent

# Forbidden third-party brand tokens in sovereign identifiers per .keywork.md Part V.2
FORBIDDEN_BRAND_TOKENS: Set[str] = {
    "laya",
    "convai",
    "typesafe",
    "quyet",
}

# Strict target directories for sovereign reflex & cognitive bus modules
STRICT_SCAN_PATHS: List[Path] = [
    ROOT_DIR / "core" / "cognitive_bus",
    ROOT_DIR / "core" / "routing",
    ROOT_DIR / "core" / "security",
    ROOT_DIR / "core" / "verification",
    ROOT_DIR / "core" / "recovery",
    ROOT_DIR / "core" / "utils" / "intent_cortex.py",
    ROOT_DIR / "core" / "utils" / "cognitive_memory.py",
    ROOT_DIR / "core" / "utils" / "skill_selector.py",
    ROOT_DIR / "services" / "ai-brain" / "critic.py",
    ROOT_DIR / "services" / "ai-brain" / "experience_distiller.py",
]


def split_identifier_tokens(identifier: str) -> List[str]:
    """
    Splits snake_case and CamelCase identifiers into lowercase word tokens.
    Prevents substring false positives such as 'replayability' matching 'laya'.
    """
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", identifier)
    tokens = [tok.lower() for tok in re.split(r"[^a-zA-Z0-9]+", camel_split) if tok]
    return tokens


def collect_python_files(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if not p.exists():
            continue
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
    return files


class TestIPBrandGuardrail:
    """Enforces .keywork.md Part V IP & Brand Honesty invariants."""

    def test_word_boundary_tokenizer_no_false_positive_on_replayability(self):
        """Regression check per Opencode Turn 238: 'replayability' must not match 'laya'."""
        tokens = split_identifier_tokens("test_b_replayability")
        assert "laya" not in tokens
        assert "replayability" in tokens

        bad_tokens = split_identifier_tokens("LayaDecisionEngine")
        assert "laya" in bad_tokens

        bad_snake = split_identifier_tokens("laya_multilingual_router")
        assert "laya" in bad_snake

    def test_no_forbidden_brand_in_filenames_or_ast_identifiers(self):
        """
        Scans all Python files in target cognitive/reflex modules to verify zero
        file names, class names, function names, or variable names use forbidden brand tokens.
        """
        violations: List[str] = []
        py_files = collect_python_files(STRICT_SCAN_PATHS)
        assert len(py_files) > 0, "Expected Python files to scan"

        for py_file in py_files:
            rel_path = py_file.relative_to(ROOT_DIR)
            # 1. Check file stem tokens
            stem_tokens = split_identifier_tokens(py_file.stem)
            for bad in FORBIDDEN_BRAND_TOKENS:
                if bad in stem_tokens:
                    violations.append(f"{rel_path}: filename contains forbidden token '{bad}'")

            # 2. Check AST identifiers (classes, functions, args, assignments)
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(rel_path))
            for node in ast.walk(tree):
                names_to_check: List[str] = []
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names_to_check.append(node.name)
                elif isinstance(node, ast.Name):
                    names_to_check.append(node.id)
                elif isinstance(node, ast.arg):
                    names_to_check.append(node.arg)

                for ident in names_to_check:
                    ident_tokens = split_identifier_tokens(ident)
                    for bad in FORBIDDEN_BRAND_TOKENS:
                        if bad in ident_tokens:
                            lineno = getattr(node, "lineno", "?")
                            violations.append(
                                f"{rel_path}:{lineno} identifier '{ident}' contains forbidden token '{bad}'"
                            )

        assert not violations, "Forbidden brand identifiers detected:\n" + "\n".join(violations)

    def test_license_and_notice_attribution_present(self):
        """Verifies Apache-2.0 license and NOTICE.md/CREDITS.md nominative fair-use attribution."""
        apache_path = ROOT_DIR / "LICENSES" / "Apache-2.0.txt"
        notice_path = ROOT_DIR / "NOTICE.md"
        credits_path = ROOT_DIR / "CREDITS.md"
        manifest_path = ROOT_DIR / "models" / "reflex_checkpoint_manifest.json"

        assert apache_path.exists() and apache_path.stat().st_size > 1000
        assert notice_path.exists()
        assert credits_path.exists()
        assert manifest_path.exists()

        notice_text = notice_path.read_text(encoding="utf-8")
        assert "Apache License 2.0" in notice_text
        assert "NandhaKishorM" in notice_text

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["research_reference"]["license"] == "Apache-2.0"
        assert manifest["runtime_execution"]["egress_policy"] == "local-only"
        assert manifest["runtime_execution"]["allow_remote_hub_download"] is False
        assert "vi" in manifest["runtime_execution"]["supported_languages"]
        assert "en" in manifest["runtime_execution"]["supported_languages"]
        assert manifest["calibration_governance"]["min_gold_samples_required"] == 100
        assert manifest["calibration_governance"]["min_gold_fit_samples_required"] == 100
        assert manifest["calibration_governance"]["min_gold_promote_samples_required"] == 200
        assert manifest["calibration_governance"]["calibration_state"]["vi"] == "uncalibrated"
        assert manifest["calibration_governance"]["calibration_state"]["en"] == "uncalibrated"

    def test_dual_manifest_synchronization_and_requirements_pin(self):
        """
        Verifies models/reflex_checkpoint_manifest.json and models/reflex_engine/0.4.2/manifest.json
        are 2-way synchronized and requirements-reflex.txt pins runtime packages + USE_TF=0.
        """
        root_manifest_path = ROOT_DIR / "models" / "reflex_checkpoint_manifest.json"
        ver_manifest_path = ROOT_DIR / "models" / "reflex_engine" / "0.4.2" / "manifest.json"
        req_path = ROOT_DIR / "requirements-reflex.txt"

        assert root_manifest_path.exists()
        assert ver_manifest_path.exists()
        assert req_path.exists()

        root_m = json.loads(root_manifest_path.read_text(encoding="utf-8"))
        ver_m = json.loads(ver_manifest_path.read_text(encoding="utf-8"))

        assert root_m["linked_version_manifest"] == "models/reflex_engine/0.4.2/manifest.json"
        assert ver_m["linked_root_manifest"] == "models/reflex_checkpoint_manifest.json"

        for shared_key in ("component_id", "active_version", "architecture", "research_reference", "runtime_execution", "weights_provenance", "calibration_governance"):
            assert root_m[shared_key] == ver_m[shared_key], f"Manifest drift detected on key '{shared_key}'"

        for m_path in (root_manifest_path, ver_manifest_path):
            raw_m_text = m_path.read_text(encoding="utf-8").lower()
            assert "http://" not in raw_m_text and "https://" not in raw_m_text, (
                f"{m_path.name} must not contain any external URLs"
            )
            for bad_tok in FORBIDDEN_BRAND_TOKENS:
                assert bad_tok not in raw_m_text, (
                    f"{m_path.name} must not contain forbidden brand token '{bad_tok}'"
                )

        req_text = req_path.read_text(encoding="utf-8")
        for pkg in ("onnxruntime", "safetensors", "tokenizers", "transformers", "torch", "USE_TF"):
            assert pkg in req_text


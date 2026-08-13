"""
core/os/cognition/escl/tool_contract_registry.py
E1 — Tool Contract Registry for Execution Semantic Contract Layer.

Maintains authoritative, versioned Tool Contracts with strict input/output schemas,
required capability tokens, side-effects, and deterministic verification rules.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from core.os.cognition.escl.contracts import ToolContract


class ToolContractRegistry:
    """Central registry for all typed tool execution contracts."""

    def __init__(self):
        self._contracts: Dict[str, ToolContract] = {}
        self._register_default_contracts()

    def register(self, contract: ToolContract):
        self._contracts[contract.tool_id] = contract

    def get(self, tool_id: str) -> Optional[ToolContract]:
        return self._contracts.get(tool_id)

    def list_all(self) -> List[ToolContract]:
        return list(self._contracts.values())

    def _register_default_contracts(self):
        # 1. OFFICE_SUITE_MASTER (Excel / Word / PDF)
        self.register(ToolContract(
            tool_id="OFFICE_SUITE_MASTER",
            version="2.2.0",
            domain="OFFICE",
            purpose="Autonomous generation, styling, and editing of Excel, Word, and PDF artifacts.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create_file", "write_excel", "write_word", "write_pdf", "add_chart", "read_file"]},
                    "format": {"type": "string", "enum": ["excel", "xlsx", "word", "docx", "pdf"]},
                    "title": {"type": "string"},
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                    "data": {"type": "array"},
                    "columns": {"type": "array"},
                    "rows": {"type": "array"},
                    "content_structure": {"type": "array"},
                    "charts": {"type": "array"}
                },
                "required": ["action"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "need_info", "error"]},
                    "path": {"type": "string"},
                    "format": {"type": "string"},
                    "file": {"type": "string"}
                },
                "required": ["status", "path"]
            },
            required_capabilities={"OFFICE_SUITE", "FILE_CREATE", "SANDBOX_WRITE"},
            side_effects=True,
            idempotent=True,
            verification_rules=[
                "E1_FILE_EXISTS",
                "E2_FILE_READABLE",
                "E3_ROW_COUNT",
                "E4_FORMULAS_PRESENT",
                "E5_CHARTS_PRESENT"
            ]
        ))

        # 2. PYTHON_SANDBOX_RUNNER
        self.register(ToolContract(
            tool_id="PYTHON_SANDBOX_RUNNER",
            version="2.0.0",
            domain="CODE",
            purpose="Execute Python scripts in an isolated worktree sandbox with deterministic verification.",
            input_schema={
                "type": "object",
                "properties": {
                    "script_code": {"type": "string"},
                    "script_path": {"type": "string"},
                    "timeout_sec": {"type": "number", "default": 30.0}
                },
                "required": ["script_code"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "exit_code": {"type": "integer"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                    "duration_ms": {"type": "number"}
                },
                "required": ["exit_code", "stdout"]
            },
            required_capabilities={"SANDBOX_EXECUTE", "FILE_READ"},
            side_effects=False,
            idempotent=True,
            verification_rules=["SYNTAX_VALID", "EXIT_CODE_ZERO"]
        ))

        # 3. SEARCH_WEB_GLOBAL
        self.register(ToolContract(
            tool_id="SEARCH_WEB_GLOBAL",
            version="2.1.0",
            domain="RESEARCH",
            purpose="Real-time multi-engine search with claim extraction and source credibility filtering.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "credibility_score": {"type": "number"}
                },
                "required": ["results"]
            },
            required_capabilities={"WEB_SEARCH", "URL_FETCH"},
            side_effects=False,
            idempotent=True,
            verification_rules=["RESULTS_NON_EMPTY"]
        ))


tool_contract_registry = ToolContractRegistry()

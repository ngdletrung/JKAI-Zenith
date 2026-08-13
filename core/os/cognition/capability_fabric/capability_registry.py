"""
core/os/cognition/capability_fabric/capability_registry.py
Capability Registry & Graph of JKAI Zenith.

Maintains verified capabilities, their dependencies, boundaries, and verification contracts.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set
from core.os.cognition.capability_fabric.models import CapabilityCategory, CapabilitySpec


class CapabilityRegistry:
    """The central registry and graph of what JKAI can and cannot do."""

    def __init__(self):
        self._capabilities: Dict[str, CapabilitySpec] = {}
        self._register_default_capabilities()

    def _register_default_capabilities(self):
        # 1. CREATE_EXCEL
        self.register(CapabilitySpec(
            capability_id="xlsx.create_and_chart",
            name="Excel Workbook & Chart Creation",
            category=CapabilityCategory.DOCUMENT_OFFICE,
            can_do=[
                "create_xlsx", "create_sheet", "write_cells", "formulas",
                "conditional_formatting", "charts", "tables", "styles"
            ],
            cannot_do=["read_sharepoint", "send_email", "manipulate_pdf"],
            requires_prerequisites=["python", "openpyxl", "filesystem.write"],
            produces_artifacts=["xlsx"],
            verification_methods=["workbook_parse", "sheet_check", "formula_check", "chart_check"],
            primary_tool="OFFICE_SUITE_MASTER",
            fallback_tool="python_execute"
        ))

        # 2. CODE_REFACTOR_BATCH
        self.register(CapabilitySpec(
            capability_id="code.multi_file_transform",
            name="Multi-File Batch Code Transformation",
            category=CapabilityCategory.CODE_MANIPULATION,
            can_do=["read_file", "view_file", "replace_file_content", "batch_edit", "syntax_check"],
            cannot_do=["direct_production_push_without_auth"],
            requires_prerequisites=["filesystem.read", "filesystem.write", "ast_parser"],
            produces_artifacts=["source_files"],
            verification_methods=["git_diff_check", "pytest_runner", "syntax_validator"],
            primary_tool="replace_file_content",
            fallback_tool="python_execute"
        ))

        # 3. WEB_RESEARCH
        self.register(CapabilitySpec(
            capability_id="research.web_search_and_extract",
            name="Realtime Web Research and Extraction",
            category=CapabilityCategory.RESEARCH_RETRIEVAL,
            can_do=["search_web", "read_url_content", "extract_structured_citations"],
            cannot_do=["access_private_intranet_without_creds", "execute_client_side_spa_js"],
            requires_prerequisites=["internet_access", "easg_policy_gate"],
            produces_artifacts=["citation_records", "evidence_items"],
            verification_methods=["url_freshness_check", "authority_tier_check"],
            primary_tool="search_web",
            fallback_tool="read_url_content"
        ))

        # 4. PYTHON_SANDBOX_EXECUTION
        self.register(CapabilitySpec(
            capability_id="system.python_execute",
            name="Sandboxed Python Execution & Dynamic Scripting",
            category=CapabilityCategory.SYSTEM_AUTOMATION,
            can_do=["execute_python_script", "compute_math", "generate_data", "run_local_algorithms"],
            cannot_do=["root_system_wipe", "bypass_sovereign_auth"],
            requires_prerequisites=["python_interpreter"],
            produces_artifacts=["stdout", "stderr", "files"],
            verification_methods=["exit_code_check", "stdout_presence"],
            primary_tool="python_execute",
            fallback_tool="run_command"
        ))

    def register(self, spec: CapabilitySpec):
        self._capabilities[spec.capability_id] = spec

    def get(self, capability_id: str) -> Optional[CapabilitySpec]:
        return self._capabilities.get(capability_id)

    def find_by_action(self, action: str) -> List[CapabilitySpec]:
        """Finds all capabilities that declare they can perform a specific atomic action."""
        matches = []
        for cap in self._capabilities.values():
            if action.lower() in [a.lower() for a in cap.can_do]:
                matches.append(cap)
        return matches

    def check_prerequisites(self, capability_id: str) -> List[str]:
        """Returns missing prerequisites for a given capability."""
        cap = self.get(capability_id)
        if not cap:
            return [f"Unknown capability {capability_id}"]
        # In runtime, check if python/openpyxl/filesystem etc. are available
        missing = []
        for prereq in cap.requires_prerequisites:
            if prereq == "openpyxl":
                try:
                    import openpyxl
                except ImportError:
                    missing.append("openpyxl")
            elif prereq == "python":
                pass # Python runtime is active
        return missing


capability_registry = CapabilityRegistry()

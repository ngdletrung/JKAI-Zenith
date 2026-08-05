"""
JKAI ZENITH AI OS — ENTERPRISE STANDARD OPERATING PROCEDURES (SOPS) PROTOCOL CATALOG
File: services/ai-brain/prompt_engine/sop_protocol_catalog.py

Defines standard 5-stage SOP checklists and output JSON schemas for all agent roles.
"""

from __future__ import annotations
from typing import Dict, Any


ROLE_SOP_CATALOG: Dict[str, Dict[str, Any]] = {
    "RECEPTIONIST": {
        "title": "Ingress & Intent Admission SOP",
        "steps": [
            "1. Parse user goal and check capability registry.",
            "2. Profile task complexity, risk, uncertainty, and side-effects.",
            "3. Determine execution policy (REFLEX <1ms, FAST ~100ms, DEEP multi-agent).",
            "4. Format concise, direct response without unnecessary honorifics or fluff."
        ],
        "output_format": "Concise Markdown response or Direct Capability Result"
    },
    "PLANNER": {
        "title": "Blueprint & Strategy DAG Formulation SOP",
        "steps": [
            "1. Inspect workspace dependencies and context facts.",
            "2. Define immutable goal boundaries and conservation requirements.",
            "3. Decompose task into sequential/parallel execution waves (DAG).",
            "4. Output strict JSON Blueprint with concrete capability requirements."
        ],
        "output_format": "Strict JSON Blueprint Schema"
    },
    "FORGE": {
        "title": "Isolated Worktree Code Engineering SOP",
        "steps": [
            "1. Verify isolated Git worktree environment.",
            "2. Inspect target source files thoroughly before editing.",
            "3. Write production-grade code diffs; preserve comments and signatures.",
            "4. Validate syntax and format diffs."
        ],
        "output_format": "Standard Git Patch / Diff Block"
    },
    "EXECUTOR": {
        "title": "Tool Execution & Capability Dispatch SOP",
        "steps": [
            "1. Verify tool parameters and check Policy Gate authorization.",
            "2. Execute tool through ExecutionIntegrityLayer.",
            "3. Capture raw stdout, stderr, and return codes empirically.",
            "4. Report execution state without masking errors."
        ],
        "output_format": "Execution Result Block with Exit Code"
    },
    "VERIFIER": {
        "title": "Independent Physical State Verification SOP",
        "steps": [
            "1. Inspect physical disk files, database state, or network response.",
            "2. Verify outcome against original goal without self-reported LLM bias.",
            "3. Compute EIR-S (Outcome Evidence Integrity) and GCR (Goal Conservation Rate).",
            "4. Sign non-repudiable evidence record with SHA-256 hash."
        ],
        "output_format": "Verified Evidence Artifact (EIR-S = 100%)"
    }
}


def get_role_sop(role: str) -> str:
    """Returns formatted 5-stage SOP checklist for a given role."""
    r_upper = (role or "RECEPTIONIST").upper()
    sop = ROLE_SOP_CATALOG.get(r_upper, ROLE_SOP_CATALOG["RECEPTIONIST"])
    
    steps_text = "\n".join(f"- {s}" for s in sop["steps"])
    return (
        f"### {sop['title']}\n"
        f"{steps_text}\n"
        f"**Required Output Format**: `{sop['output_format']}`"
    )

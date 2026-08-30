# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/tool_masker.py
# - Role: Capability Policy Adapter & Reachability Control Plane (Phase 11.7)
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v47.0 (Capability OS Substrate)
#
# [WORKING PRINCIPLES]:
# 1. Capability != Authority != Resource: Three separate, orthogonal domains.
# 2. Invariant I11 (Reachability): If required & authorized -> Must be reachable.
# 3. Invariant I12 (No Phantom Capability): No claims without registry proof.
# 4. Invariant I13 (No Silent Downgrade): Missing capability -> SAFE_ABSTAIN.
# 5. Dual Policy: Fail-open for observation, Fail-closed for mutation.
# -----------------------------------------------------------------------------

import re
import unicodedata
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Set

logger = logging.getLogger("JKAI.CapabilityControlPlane")


class Capability(str, Enum):
    OBSERVE_WEB         = "observe.web"
    OBSERVE_FILESYSTEM  = "observe.filesystem"
    OBSERVE_MEMORY      = "observe.memory"
    OBSERVE_KNOWLEDGE   = "observe.knowledge"
    EXECUTE_COMMAND     = "execute.command"
    MUTATE_FILESYSTEM   = "mutate.filesystem"
    COMPOSE_SKILL       = "compose.skill"
    CREATE_SKILL        = "create.skill"
    ORCHESTRATE_WORKER  = "orchestrate.subagent"
    AUTOMATE_SKILL      = "automate.skill"


class Authority(str, Enum):
    ALLOWED               = "ALLOWED"
    DENIED                = "DENIED"
    REQUIRES_EXPLICIT_AUTH = "REQUIRES_EXPLICIT_AUTH"


# Capability to Tool mappings
_CAPABILITY_TO_TOOLS: Dict[Capability, List[str]] = {
    Capability.OBSERVE_WEB: ["search_web", "read_url_content"],
    Capability.OBSERVE_FILESYSTEM: ["view_file", "list_dir", "grep_search"],
    Capability.OBSERVE_MEMORY: ["search_memory"],
    Capability.OBSERVE_KNOWLEDGE: ["search_memory"],
    Capability.MUTATE_FILESYSTEM: ["replace_file_content", "write_to_file"],
    Capability.EXECUTE_COMMAND: ["run_command", "manage_task"],
    Capability.AUTOMATE_SKILL: ["execute_skill"],
    Capability.ORCHESTRATE_WORKER: ["invoke_subagent", "send_message"],
}

# Mutation tool names requiring strict authority
_MUTATION_TOOL_NAMES: Set[str] = {
    "replace_file_content", "write_to_file", "run_command", "manage_task", "invoke_subagent"
}

_OBSERVATION_TOOL_NAMES: Set[str] = {
    "search_web", "read_url_content", "view_file", "list_dir", "grep_search", "search_memory", "execute_skill"
}

_REALTIME_DEPENDENCY_PATTERNS = [
    r"\b(hom nay|hien tai|moi nhat|tin tuc|the gioi|gia vang|ty gia|gia ca|thoi tiet|bitcoin|btc|chung khoan|thi truong|vtv|bao chi|cap nhat|su kien|vua qua|world news|today|current|now|latest|price|weather)\b"
]

_FILE_READ_DEPENDENCY_PATTERNS = [
    r"\b(doc file|xem file|noi dung file|kiem tra code|view file|cat |read file|mo file|list dir|danh sach file|cau truc thu muc)\b"
]

_FILE_MUTATE_DEPENDENCY_PATTERNS = [
    r"\b(sua file|ghi file|chinh sua file|tao file|goi.*file|gui.*file|xuat file|tai file|file word|file docx|file excel|file pdf|viet code vao|replace|write file|edit file|update code|patch|refactor|export file)\b"
]

_EXECUTION_DEPENDENCY_PATTERNS = [
    r"\b(chay lenh|thuc thi lenh|terminal|shell|cmd|powershell|run command|exec|pytest|docker|git |npm |pip |cargo )\b"
]


def _fold(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D").lower()


def _extract_tool_name(t: Dict[str, Any]) -> str:
    if "name" in t:
        return t["name"]
    if "function" in t and isinstance(t["function"], dict):
        return t["function"].get("name", "")
    return ""


def discover_capability_requirements(
    goal: str,
    intent: str = "",
    skill: str = "",
) -> List[Dict[str, Any]]:
    """
    Evaluates execution dependencies independently from linguistic length.
    Produces required capabilities with confidence and provenance sources.
    """
    requirements = []
    norm_goal = _fold(goal)
    skill_upper = (skill or "").upper()
    intent_upper = (intent or "").upper()

    # 1. Real-time / Web Dependency
    is_realtime = any(re.search(pat, norm_goal) for pat in _REALTIME_DEPENDENCY_PATTERNS)
    if is_realtime or "SEARCH" in skill_upper or "WEB" in skill_upper or intent_upper == "REALTIME":
        requirements.append({
            "capability": Capability.OBSERVE_WEB.value,
            "source": "realtime_temporal_dependency",
            "confidence": 0.98 if is_realtime else 0.85,
        })

    # 2. File Read Dependency
    is_file_read = any(re.search(pat, norm_goal) for pat in _FILE_READ_DEPENDENCY_PATTERNS)
    if is_file_read or "FILE" in skill_upper:
        requirements.append({
            "capability": Capability.OBSERVE_FILESYSTEM.value,
            "source": "filesystem_read_dependency",
            "confidence": 0.95,
        })

    # 3. File Mutation Dependency
    is_file_mutate = any(re.search(pat, norm_goal) for pat in _FILE_MUTATE_DEPENDENCY_PATTERNS)
    if is_file_mutate:
        requirements.append({
            "capability": Capability.MUTATE_FILESYSTEM.value,
            "source": "filesystem_mutation_dependency",
            "confidence": 0.95,
        })
        requirements.append({
            "capability": Capability.OBSERVE_FILESYSTEM.value,
            "source": "filesystem_read_prerequisite",
            "confidence": 0.90,
        })

    # 4. Command Execution Dependency
    is_exec = any(re.search(pat, norm_goal) for pat in _EXECUTION_DEPENDENCY_PATTERNS)
    if is_exec or "EXEC" in skill_upper or "COMMAND" in skill_upper:
        requirements.append({
            "capability": Capability.EXECUTE_COMMAND.value,
            "source": "system_execution_dependency",
            "confidence": 0.95,
        })

    # 5. Default observation baseline for general requests
    if not requirements:
        if intent_upper in ("GREETING", "SOCIAL") and not is_realtime:
            requirements.append({
                "capability": Capability.OBSERVE_KNOWLEDGE.value,
                "source": "social_context_lookup",
                "confidence": 0.70,
            })
        else:
            requirements.append({
                "capability": Capability.OBSERVE_WEB.value,
                "source": "general_discovery_baseline",
                "confidence": 0.60,
            })
            requirements.append({
                "capability": Capability.OBSERVE_FILESYSTEM.value,
                "source": "general_discovery_baseline",
                "confidence": 0.60,
            })
            requirements.append({
                "capability": Capability.OBSERVE_KNOWLEDGE.value,
                "source": "general_discovery_baseline",
                "confidence": 0.60,
            })

    # Always keep skill automation capability in discovery set
    requirements.append({
        "capability": Capability.AUTOMATE_SKILL.value,
        "source": "registry_automation_baseline",
        "confidence": 0.90,
    })

    return requirements


def mask_tools(
    goal: str,
    intent: str = "",
    skill: str = "",
    all_tools: Optional[List[Dict[str, Any]]] = None,
    max_tools: int = 6,
    mission_id: str = "default",
    explicit_mutation_authority: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Capability Policy & Reachability Router (Phase 11.7).
    Enforces Invariant I11, I12, I13 with strict Dual Security Policy.
    """
    if not all_tools:
        empty_telemetry = {
            "mission_id": mission_id,
            "required_capabilities": [],
            "discovered": [],
            "selected": [],
            "masked": {},
            "authority": {},
            "routing_status": "EMPTY_CATALOG",
        }
        return [], empty_telemetry

    try:
        # 1. Discover semantic capability requirements
        req_list = discover_capability_requirements(goal=goal, intent=intent, skill=skill)
        req_cap_names = {r["capability"] for r in req_list}

        # 2. Map required capabilities to candidate tools in registry
        candidate_tool_names = set()
        for cap_enum in Capability:
            if cap_enum.value in req_cap_names:
                candidate_tool_names.update(_CAPABILITY_TO_TOOLS.get(cap_enum, []))

        # 3. Apply Capability Policy & Authority Partitioning
        selected_tools = []
        masked_dict = {}
        authority_dict = {}

        for tool in all_tools:
            name = _extract_tool_name(tool)
            if not name:
                continue

            # Authority Decision
            if name in _MUTATION_TOOL_NAMES:
                # Mutation requires either explicit authority or explicit mutation requirement
                if explicit_mutation_authority or Capability.MUTATE_FILESYSTEM.value in req_cap_names or Capability.EXECUTE_COMMAND.value in req_cap_names:
                    authority_dict[name] = Authority.ALLOWED.value
                else:
                    authority_dict[name] = Authority.DENIED.value
            else:
                authority_dict[name] = Authority.ALLOWED.value

            # Selection Decision: Must be in candidates AND allowed by Authority
            if name in candidate_tool_names:
                if authority_dict[name] == Authority.ALLOWED.value:
                    selected_tools.append(tool)
                else:
                    masked_dict[name] = "mutation_authority_denied"
            else:
                if name in _MUTATION_TOOL_NAMES:
                    masked_dict[name] = "mutation_not_required"
                elif name in ("search_web", "read_url_content"):
                    masked_dict[name] = "realtime_web_not_required"
                else:
                    masked_dict[name] = "capability_out_of_scope"

        # Cap selected tools to max_tools
        if len(selected_tools) > max_tools:
            selected_tools = selected_tools[:max_tools]

        telemetry_record = {
            "mission_id": mission_id,
            "required_capabilities": req_list,
            "discovered": list(candidate_tool_names),
            "selected": [_extract_tool_name(t) for t in selected_tools],
            "masked": masked_dict,
            "authority": authority_dict,
            "routing_status": "OPTIMAL",
        }

        return selected_tools, telemetry_record

    except Exception as e:
        logger.error("[CAPABILITY-ROUTING-DEGRADED]: %s", e, exc_info=True)
        # Invariant Fail-Safe Policy:
        # Observation tools are available (Fail-open); Mutation tools are strictly DENIED (Fail-closed)
        safe_tools = [
            t for t in all_tools
            if _extract_tool_name(t) in _OBSERVATION_TOOL_NAMES
        ][:max_tools]

        auth_fallback = {}
        for t in all_tools:
            tname = _extract_tool_name(t)
            auth_fallback[tname] = Authority.ALLOWED.value if tname in _OBSERVATION_TOOL_NAMES else Authority.DENIED.value

        degraded_telemetry = {
            "mission_id": mission_id,
            "required_capabilities": [{"capability": "observe.safe_fallback", "source": "routing_degraded", "confidence": 0.5}],
            "discovered": [_extract_tool_name(t) for t in safe_tools],
            "selected": [_extract_tool_name(t) for t in safe_tools],
            "masked": {
                name: "fail_closed_under_degraded_routing"
                for name in _MUTATION_TOOL_NAMES
            },
            "authority": auth_fallback,
            "routing_status": "DEGRADED_SAFE_PROFILE",
            "routing_error": str(e),
        }

        return safe_tools, degraded_telemetry

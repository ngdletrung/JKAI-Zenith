# -*- coding: utf-8 -*-
"""
core/kernel/tool_contracts.py
🏛️ TOOL CONTRACT REGISTRY & STRICT SCHEMA VALIDATOR (P0.2)
Provides Pydantic-based strict contract enforcement for all tools in JKAI Zenith.
Enforces Fail-Closed behavior: any malformed tool invocation is rejected at the Broker boundary.
"""

from __future__ import annotations
import inspect
import logging
from typing import Dict, Any, List, Optional, Tuple, Type
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("ToolContracts")


# =========================================================================
# 1. TOOL CONTRACT PYDANTIC MODELS
# =========================================================================

class WriteFileContract(BaseModel):
    TargetFile: str = Field(..., description="Absolute or normalized target file path")
    CodeContent: str = Field(..., description="File content to write")
    Overwrite: Optional[bool] = Field(default=True, description="Overwrite if file exists")


class ReplaceFileContentContract(BaseModel):
    TargetFile: str = Field(..., description="Path to the file to modify")
    TargetContent: str = Field(..., description="Exact snippet of code to be replaced")
    ReplacementContent: str = Field(..., description="New replacement content")
    StartLine: Optional[int] = Field(default=None, description="Starting line number")
    EndLine: Optional[int] = Field(default=None, description="Ending line number")
    AllowMultiple: Optional[bool] = Field(default=False, description="Allow replacing multiple matches")


class RunCommandContract(BaseModel):
    CommandLine: str = Field(..., description="The command line string to execute")
    Cwd: Optional[str] = Field(default=".", description="Current working directory")


class ViewFileContract(BaseModel):
    AbsolutePath: str = Field(..., description="Absolute path to file to view")
    StartLine: Optional[int] = Field(default=None, description="Start line 1-indexed")
    EndLine: Optional[int] = Field(default=None, description="End line 1-indexed")


class GrepSearchContract(BaseModel):
    SearchPath: str = Field(..., description="Path to directory or file to search")
    Query: str = Field(..., description="Search term or regex pattern")
    CaseInsensitive: Optional[bool] = Field(default=False, description="Case-insensitive match")
    IsRegex: Optional[bool] = Field(default=False, description="Treat query as regular expression")


class ListDirContract(BaseModel):
    DirectoryPath: str = Field(..., description="Path to directory to list")


class WebSearchContract(BaseModel):
    query: str = Field(..., description="Search query string")


class PythonExecuteContract(BaseModel):
    code: str = Field(..., description="Python source code to execute")


# =========================================================================
# 2. CONTRACT REGISTRY & FAIL-CLOSED VALIDATOR
# =========================================================================

class ToolContractRegistry:
    """
    Registry of strict tool schemas.
    Validates arguments before any I/O dispatch to infrastructure.
    """
    _registry: Dict[str, Type[BaseModel]] = {}
    _aliases: Dict[str, str] = {}

    @classmethod
    def register(cls, tool_name: str, model_cls: Type[BaseModel], aliases: Optional[List[str]] = None) -> None:
        canonical = tool_name.lower().strip()
        cls._registry[canonical] = model_cls
        if aliases:
            for alias in aliases:
                cls._aliases[alias.lower().strip()] = canonical

    @classmethod
    def get_canonical_name(cls, tool_name: str) -> Optional[str]:
        t_low = tool_name.lower().strip()
        if t_low in cls._registry:
            return t_low
        return cls._aliases.get(t_low)

    @classmethod
    def get_model(cls, tool_name: str) -> Optional[Type[BaseModel]]:
        canon = cls.get_canonical_name(tool_name)
        return cls._registry.get(canon) if canon else None

    @classmethod
    def normalize_args(cls, model_cls: Type[BaseModel], raw_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes snake_case, lowercase, or camelCase keys to model field names.
        E.g., target_file -> TargetFile, commandline -> CommandLine
        """
        if not isinstance(raw_args, dict):
            return {}

        fields = model_cls.__annotations__ if hasattr(model_cls, "__annotations__") else {}
        field_map = {f.lower().replace("_", ""): f for f in fields.keys()}

        normalized = {}
        for k, v in raw_args.items():
            k_key = k.lower().replace("_", "")
            if k_key in field_map:
                normalized[field_map[k_key]] = v
            else:
                normalized[k] = v
        return normalized

    @classmethod
    def validate_tool_call(
        cls,
        tool_name: str,
        args: Dict[str, Any],
        strict: bool = False
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[BaseModel]]:
        """
        P0.2 Contract Enforcement:
        Validates tool parameters against registered Pydantic contract.
        Returns: (is_valid, error_payload, parsed_model)
        """
        model_cls = cls.get_model(tool_name)
        if not model_cls:
            if strict:
                err = {
                    "error_type": "TOOL_CONTRACT_NOT_FOUND",
                    "tool": tool_name,
                    "message": f"Tool '{tool_name}' is not registered in ToolContractRegistry."
                }
                return False, err, None
            # If not in registry and non-strict, allow through
            return True, None, None

        if not isinstance(args, dict):
            err = {
                "error_type": "CONTRACT_VIOLATION",
                "tool": tool_name,
                "missing_fields": list(model_cls.__annotations__.keys()),
                "type_mismatches": {"args": f"Expected dict, got {type(args).__name__}"},
                "expected_schema": {k: getattr(v, "__name__", str(v)) for k, v in model_cls.__annotations__.items()}
            }
            return False, err, None

        norm_args = cls.normalize_args(model_cls, args)

        try:
            parsed = model_cls(**norm_args)
            return True, None, parsed
        except ValidationError as ve:
            missing_fields = []
            type_mismatches = {}
            for e in ve.errors():
                loc = e.get("loc", ["unknown"])
                field_name = str(loc[0]) if loc else "unknown"
                err_type = e.get("type", "")
                if "missing" in err_type:
                    missing_fields.append(field_name)
                else:
                    type_mismatches[field_name] = e.get("msg", "type error")

            err = {
                "error_type": "CONTRACT_VIOLATION",
                "tool": tool_name,
                "missing_fields": sorted(missing_fields),
                "type_mismatches": type_mismatches,
                "expected_schema": {k: getattr(v, "__name__", str(v)) for k, v in model_cls.__annotations__.items()},
                "raw_errors": ve.errors()
            }
            logger.warning("🚧 [P0.2-CONTRACT-VIOLATION] Tool '%s' rejected: missing=%s mismatches=%s",
                           tool_name, missing_fields, type_mismatches)
            return False, err, None


# Register standard tool contracts
ToolContractRegistry.register("write_to_file", WriteFileContract, ["write_code", "writefile", "write_file"])
ToolContractRegistry.register("replace_file_content", ReplaceFileContentContract, ["replace_content", "replace_file"])
ToolContractRegistry.register("run_command", RunCommandContract, ["execute_command", "run_cmd", "cmd"])
ToolContractRegistry.register("view_file", ViewFileContract, ["read_file", "read_code", "viewfile"])
ToolContractRegistry.register("grep_search", GrepSearchContract, ["grep", "search_files", "pattern"])
ToolContractRegistry.register("list_dir", ListDirContract, ["listdir", "ls"])
ToolContractRegistry.register("web_search", WebSearchContract, ["search_web", "tavily_search", "search_web_global"])
ToolContractRegistry.register("python_execute", PythonExecuteContract, ["py_exec", "run_python"])


# =========================================================================
# 3. MODULE-LEVEL SHORTCUT FUNCTIONS
# =========================================================================

_FIELD_ALIASES: Dict[str, Dict[str, str]] = {
    "grep_search": {
        "pattern": "query",
        "path": "SearchPath",
        "search_path": "SearchPath",
    },
}


def get_contract(tool_name: str) -> Optional[Type[BaseModel]]:
    """Return the Pydantic contract model for a tool, or None if not registered."""
    return ToolContractRegistry.get_model(tool_name)


def canonicalize(
    tool_name: str,
    args: Dict[str, Any],
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Canonicalize tool arguments:
    - Resolves field aliases (e.g., 'pattern' → 'query' for grep_search)
    - Returns (canonical_name, canonical_kwargs, issues_list)
    canonical_kwargs uses lowercase alias-resolved keys (before Pydantic capitalization).
    issues_list is empty on success; contains warning strings on soft mismatches.
    """
    canon_name = ToolContractRegistry.get_canonical_name(tool_name) or tool_name.lower().strip()
    alias_map = _FIELD_ALIASES.get(canon_name, {})

    # Step 1: Apply field aliases (e.g., pattern → query). Keys stay lowercase.
    canonical_kws: Dict[str, Any] = {}
    issues: List[str] = []

    for k, v in args.items():
        mapped_key = alias_map.get(k.lower(), k)
        canonical_kws[mapped_key] = v

    # Step 2: Validate (collect issues) but DO NOT overwrite canonical_kws with
    # normalize_args output — that would capitalize keys (Query, SearchPath, etc.)
    # and break callers who expect lowercase keys like canonical_kws.get("query").
    model_cls = ToolContractRegistry.get_model(canon_name)
    if model_cls:
        norm = ToolContractRegistry.normalize_args(model_cls, canonical_kws)
        is_valid, err, _ = ToolContractRegistry.validate_tool_call(canon_name, norm)
        if not is_valid and err:
            for mf in err.get("missing_fields", []):
                issues.append(f"Missing required field: '{mf}'")
            for field, msg in err.get("type_mismatches", {}).items():
                issues.append(f"Type mismatch on '{field}': {msg}")
        # canonical_kws intentionally NOT replaced — preserve lowercase alias keys

    return canon_name, canonical_kws, issues


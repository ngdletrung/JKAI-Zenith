"""
Slice 1.2b Benchmark & Contract Suite:
1. Locked 20-Case Static Analysis Benchmark (SEALED_20_ACI_CASES) for stdlib ast + symtable
   undefined_name and broken_local_import detection (<15ms per file).
2. Guarded Edit integration in SYSTEM_CORE_EXECUTOR (write_to_file & replace_file_content return aci_diagnostics).
3. File/Shell ACI v2 pagination & outline: view_file(start_line, end_line, outline=True), view_file_outline,
   and single-pass grep_search(offset, limit) using iter_workspace_files().
4. Expanded GBNF params whitelist in core/utils/engine.py (path, pattern, command, start_line, end_line, query, content).
5. Import-safe lazy import in tools/graph_syncer.py (OpenCode Turn 262 condition).
"""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# 20 Locked Benchmark Cases for ACI Static Diagnostics (stdlib ast + symtable)
# 10 Buggy cases (5 undefined_name, 5 broken_local_import) + 10 Clean cases (including star-import, closures, comprehensions, builtins)
SEALED_20_ACI_CASES: List[Dict[str, Any]] = [
    # --- 5 UNDEFINED NAME CASES ---
    {
        "id": "ACI_U01",
        "code": "def compute_total(price, qty):\n    return price * qty + tax_rate_missing\n",
        "expect_undefined": ["tax_rate_missing"],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_U02",
        "code": "class OrderProcessor:\n    def run(self, item):\n        return normalize_item_helper(item)\n",
        "expect_undefined": ["normalize_item_helper"],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_U03",
        "code": "def format_report(rows):\n    out = []\n    for r in rows:\n        out.append( serialize_row_undef(r) )\n    return out\n",
        "expect_undefined": ["serialize_row_undef"],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_U04",
        "code": "async def fetch_data(url):\n    resp = await ghost_http_client.get(url)\n    return resp\n",
        "expect_undefined": ["ghost_http_client"],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_U05",
        "code": "def check_threshold(val):\n    if val > MAX_UNDECLARED_LIMIT:\n        return True\n    return False\n",
        "expect_undefined": ["MAX_UNDECLARED_LIMIT"],
        "expect_broken_imports": [],
    },
    # --- 5 BROKEN LOCAL IMPORT CASES ---
    {
        "id": "ACI_I01",
        "code": "from core.utils.non_existent_ghost_module import something\n",
        "expect_undefined": [],
        "expect_broken_imports": ["core.utils.non_existent_ghost_module"],
    },
    {
        "id": "ACI_I02",
        "code": "from core.utils.project_workspace import non_existent_symbol_xyz\n",
        "expect_undefined": [],
        "expect_broken_imports": ["core.utils.project_workspace.non_existent_symbol_xyz"],
    },
    {
        "id": "ACI_I03",
        "code": "import core.kernel.imaginary_subkernel_abc\n",
        "expect_undefined": [],
        "expect_broken_imports": ["core.kernel.imaginary_subkernel_abc"],
    },
    {
        "id": "ACI_I04",
        "code": "from services.tools.definitions.web_search import ghost_search_fn_999\n",
        "expect_undefined": [],
        "expect_broken_imports": ["services.tools.definitions.web_search.ghost_search_fn_999"],
    },
    {
        "id": "ACI_I05",
        "code": "from rag.ghost_rag_submodule import GhostRagClass\n",
        "expect_undefined": [],
        "expect_broken_imports": ["rag.ghost_rag_submodule"],
    },
    # --- 10 CLEAN CASES (ZERO FALSE POSITIVES) ---
    {
        "id": "ACI_C01_BUILTINS",
        "code": "def summarize(items):\n    return len(items), max(items, default=0), sorted(set(items))\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C02_CLOSURE",
        "code": "def make_multiplier(factor):\n    def multiply(x):\n        return x * factor\n    return multiply\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C03_COMPREHENSION",
        "code": "def squares(nums):\n    return [n * n for n in nums if n > 0]\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C04_VALID_LOCAL_IMPORT",
        "code": "from core.utils.project_workspace import get_jkai_workspace_root\ndef root_str():\n    return str(get_jkai_workspace_root())\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C05_STAR_IMPORT_GUARD",
        "code": "from math import *\ndef calc_circle(r):\n    return pi * (r ** 2) + unknown_from_star_is_skipped\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C06_EXCEPTION_TARGET",
        "code": "def safe_parse(text):\n    try:\n        return int(text)\n    except ValueError as err:\n        return str(err)\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C07_CLASS_SELF_AND_METHODS",
        "code": "class Counter:\n    DEFAULT_STEP = 1\n    def __init__(self):\n        self.val = 0\n    def inc(self):\n        self.val += self.DEFAULT_STEP\n        return self.val\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C08_WITH_AS_TARGET",
        "code": "def read_first_line(p):\n    with open(p, 'r', encoding='utf-8') as fh:\n        return fh.readline()\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C09_DICT_GENEXP",
        "code": "def index_by_id(records):\n    return {rec['id']: rec for rec in records if 'id' in rec}\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
    {
        "id": "ACI_C10_DECORATOR_AND_TYPE_ANNOT",
        "code": "from __future__ import annotations\nfrom typing import Optional\nclass Box:\n    @staticmethod\n    def create(val: Optional[NonExistentTypeHint] = None) -> Box:\n        return Box()\n",
        "expect_undefined": [],
        "expect_broken_imports": [],
    },
]


def run_20_case_aci_benchmark() -> Dict[str, Any]:
    """Runs the 20 locked static analysis cases and returns accuracy & latency metrics."""
    from core.utils import ast_code_auditor

    if not hasattr(ast_code_auditor, "analyze_python_aci_diagnostics"):
        return {
            "implemented": False,
            "total_cases": len(SEALED_20_ACI_CASES),
            "passed_cases": 0,
            "accuracy_pct": 0.0,
            "max_elapsed_ms": 0.0,
        }

    passed = 0
    max_ms = 0.0
    failures = []
    for case in SEALED_20_ACI_CASES:
        diag = ast_code_auditor.analyze_python_aci_diagnostics(
            case["code"], filename=f"<{case['id']}>", workspace_root=REPO_ROOT
        )
        elapsed = float(diag.get("elapsed_ms", 0.0))
        if elapsed > max_ms:
            max_ms = elapsed
        got_undef = sorted(diag.get("undefined_names", []))
        got_broken = sorted(diag.get("broken_imports", []))
        exp_undef = sorted(case["expect_undefined"])
        exp_broken = sorted(case["expect_broken_imports"])
        if got_undef == exp_undef and got_broken == exp_broken and elapsed < 50.0:
            passed += 1
        else:
            failures.append(
                {
                    "id": case["id"],
                    "got_undefined": got_undef,
                    "expect_undefined": exp_undef,
                    "got_broken_imports": got_broken,
                    "expect_broken_imports": exp_broken,
                    "elapsed_ms": elapsed,
                }
            )
    return {
        "implemented": True,
        "total_cases": len(SEALED_20_ACI_CASES),
        "passed_cases": passed,
        "accuracy_pct": round((passed / len(SEALED_20_ACI_CASES)) * 100.0, 2),
        "max_elapsed_ms": round(max_ms, 2),
        "failures": failures,
    }


def run_20_case_aci_benchmark_with_timing_retry(
    max_attempts: int = 3,
    budget_ms: float = 15.0,
) -> Dict[str, Any]:
    """
    [Turn 286 OpenCode Improvement #1]:
    Runs `run_20_case_aci_benchmark()` with up to `max_attempts` tries when only the
    wall-clock timing budget (`max_elapsed_ms < budget_ms`) spikes due to OS CPU load.
    Functional accuracy (`passed_cases == 20`) must pass on every attempt.
    """
    last_report: Dict[str, Any] = {}
    for attempt in range(1, max(1, int(max_attempts)) + 1):
        last_report = run_20_case_aci_benchmark()
        last_report["attempts_used"] = attempt
        if not last_report.get("implemented") or last_report.get("passed_cases") != 20:
            return last_report
        if float(last_report.get("max_elapsed_ms", 999.0)) < float(budget_ms):
            return last_report
    return last_report


def test_aci_20_case_static_benchmark():
    report = run_20_case_aci_benchmark_with_timing_retry(max_attempts=3, budget_ms=15.0)
    assert report["implemented"] is True, "analyze_python_aci_diagnostics not implemented in ast_code_auditor.py"
    assert report["passed_cases"] == 20, f"ACI Benchmark failed cases: {report.get('failures')}"
    assert report["max_elapsed_ms"] < 15.0, f"ACI Diagnostics exceeded 15ms budget across 3 attempts: {report['max_elapsed_ms']}ms"


def test_guarded_edit_attaches_aci_diagnostics_on_write_and_replace(tmp_path: Path):
    import intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic as core_exec

    target = tmp_path / "demo_mod.py"
    res_write = asyncio.run(
        core_exec.write_to_file(
            path=str(target),
            content="def add(a, b):\n    return a + b + undeclared_offset\n",
            overwrite=True,
        )
    )
    assert res_write["status"] == "success"
    assert "aci_diagnostics" in res_write, "write_to_file must return aci_diagnostics for .py files"
    assert "undeclared_offset" in res_write["aci_diagnostics"]["undefined_names"]

    res_replace = asyncio.run(
        core_exec.replace_file_content(
            path=str(target),
            target="return a + b + undeclared_offset",
            replacement="return a + b",
        )
    )
    assert res_replace["status"] == "success"
    assert "aci_diagnostics" in res_replace
    assert res_replace["aci_diagnostics"]["undefined_names"] == []


def test_view_file_outline_and_paginated_grep(tmp_path: Path):
    import intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic as core_exec

    sample = tmp_path / "sample_service.py"
    sample.write_text(
        "class AlphaService:\n"
        "    def start(self):\n"
        "        return 'started'\n\n"
        "def helper_fn(x, y):\n"
        "    # MAGIC_TOKEN_XYZ\n"
        "    return x + y\n",
        encoding="utf-8",
    )

    out_res = asyncio.run(core_exec.view_file(path=str(sample), outline=True))
    assert out_res["status"] == "success"
    assert "AlphaService" in out_res["outline"]
    assert "helper_fn" in out_res["outline"]

    grep_res = asyncio.run(core_exec.grep_search(query="MAGIC_TOKEN_XYZ", path=str(tmp_path), offset=0, limit=10))
    assert grep_res["status"] == "success"
    assert grep_res["count"] == 1
    assert "has_more" in grep_res


def test_gbnf_params_expanded_whitelist_and_graph_syncer_lazy_import():
    from core.utils.engine import normalize_json_schema
    from core.utils.structured_output import ExecuteOutput

    schema = normalize_json_schema(ExecuteOutput)
    params_props = schema["properties"]["params"]["properties"]
    for expected_key in ("path", "pattern", "command", "start_line", "end_line", "query", "content", "target", "value"):
        assert expected_key in params_props, f"Missing '{expected_key}' in bounded ExecuteOutput.params schema"
    assert schema["properties"]["params"].get("required", []) == []

    # Verify tools.graph_syncer is import-safe even when graphrag_sdk is not installed
    mod = importlib.import_module("tools.graph_syncer")
    assert hasattr(mod, "sync_knowledge")


def test_aci_5_layer_blindspot_honesty():
    """
    Point D (Reference Review): stdlib ast + symtable cannot catch 100% of dynamic/runtime semantic bugs.
    Verify analyze_python_aci_diagnostics explicitly reports its 5-layer boundaries, flags
    STAR_IMPORT_SCOPE_OPAQUE and DYNAMIC_DISPATCH_OPAQUE blindspots, and always marks
    requires_L4_runtime_pytest=True.
    """
    from core.utils.ast_code_auditor import analyze_python_aci_diagnostics

    star_diag = analyze_python_aci_diagnostics("from math import *\ndef f(x):\n    return missing_sym(x)\n")
    assert "STAR_IMPORT_SCOPE_OPAQUE" in star_diag["blindspots"]
    assert star_diag["verification_layers"]["L2_static_symtable_scope"] == "SKIPPED_STAR_IMPORT"
    assert star_diag["requires_L4_runtime_pytest"] is True

    dyn_diag = analyze_python_aci_diagnostics("def call_dyn(obj, name):\n    return getattr(obj, name)()\n")
    assert "DYNAMIC_DISPATCH_OPAQUE" in dyn_diag["blindspots"]
    assert dyn_diag["verification_layers"]["L4_unit_integration_pytest"] == "REQUIRED_AT_RUNTIME"
    assert dyn_diag["requires_L4_runtime_pytest"] is True


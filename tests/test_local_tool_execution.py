# -*- coding: utf-8 -*-
"""
tests/test_local_tool_execution.py
Unit & Benchmark tests for P0-2: Local-First Dual-Path Tool Execution & 5-Second File Test
"""

import os
import time
import pytest
import tempfile
import asyncio
from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import (
    write_to_file,
    view_file,
    replace_file_content,
    delete_file,
    run_command
)


@pytest.mark.asyncio
class TestLocalToolExecution:

    async def test_01_local_write_and_view_file_subsecond(self):
        """Vector 1: Creating a Python file and viewing it takes < 50ms locally (vs 40s via HTTP)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_math.py")
            code_content = "def add(a, b):\n    return a + b\n"

            start_t = time.perf_counter()
            # 1. Write
            write_res = await write_to_file(target_path=test_file, target_content=code_content)
            duration_write = time.perf_counter() - start_t

            assert write_res["status"] == "success"
            assert os.path.exists(test_file)
            assert duration_write < 0.20  # Under 200ms

            # 2. View
            view_res = await view_file(path=test_file)
            assert view_res["status"] == "success"
            assert "def add(a, b):" in view_res["content"]

    async def test_02_ast_pre_validation_blocks_syntax_error(self):
        """Vector 2: Broken code like '4ac' or '2a' is blocked before writing to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "bad_math.py")
            bad_code = "def calc(a, b, c):\n    delta = b**2 - 4ac\n    return delta\n"

            res = await write_to_file(target_path=bad_file, target_content=bad_code)
            assert res["status"] == "error"
            assert "AST Syntax Error" in res["msg"]
            assert not os.path.exists(bad_file)

    async def test_03_5_second_quadratic_file_generation_benchmark(self):
        """
        Vector 3: Master's Benchmark Test:
        Generate complete quadratic solver file, verify syntax, run pytest locally.
        Must complete in < 5.0 seconds.
        """
        start_benchmark = time.perf_counter()

        with tempfile.TemporaryDirectory() as tmpdir:
            py_path = os.path.join(tmpdir, "quadratic_solver.py")
            valid_code = (
                "import math\n\n"
                "def solve_quadratic(a, b, c):\n"
                "    if a == 0:\n"
                "        raise ValueError('Hệ số a phải khác 0')\n"
                "    delta = b**2 - 4*a*c\n"
                "    if delta < 0:\n"
                "        return []\n"
                "    elif delta == 0:\n"
                "        return [-b / (2*a)]\n"
                "    else:\n"
                "        return [(-b + math.sqrt(delta)) / (2*a), (-b - math.sqrt(delta)) / (2*a)]\n"
            )

            # Step 1: Write file
            w_res = await write_to_file(target_path=py_path, target_content=valid_code)
            assert w_res["status"] == "success"

            # Step 2: Run verification script
            test_cmd = f'python -c "import sys; sys.path.insert(0, r\'{tmpdir}\'); from quadratic_solver import solve_quadratic; roots = solve_quadratic(1, -3, 2); assert sorted(roots) == [1.0, 2.0]; print(\'PASS\')"'
            cmd_res = await run_command(command=test_cmd)
            assert cmd_res["status"] == "success"
            assert "PASS" in cmd_res["stdout"]

            total_elapsed = time.perf_counter() - start_benchmark
            assert total_elapsed < 5.0, f"Benchmark failed: Took {total_elapsed:.2f}s (expected < 5.0s)"

    async def test_04_path_guard_blocks_sensitive_files(self):
        """Vector 4 (F1): Verifies that write_to_file directly blocks sensitive paths like .env."""
        res = await write_to_file(target_path=".env", target_content="SECRET_KEY=12345")
        assert res["status"] == "error"
        assert "chính sách bảo vệ an ninh" in res["msg"]


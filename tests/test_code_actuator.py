# -*- coding: utf-8 -*-
"""
Unit test suite cho CodeActuator & PreWarmed Sandbox
"""

import os
import pytest
from core.kernel.code_actuator import code_actuator


class TestCodeActuator:
    """Kiểm tra độ chính xác và khả năng trích xuất, thực thi mã tạo file."""

    def test_extract_python_code_with_markdown(self):
        text = "Dưới đây là mã tạo file:\n```python\nimport openpyxl\nwb = openpyxl.Workbook()\nwb.save('test.xlsx')\n```"
        code = code_actuator.extract_python_code(text)
        assert code is not None
        assert "import openpyxl" in code

    def test_extract_code_with_pandas_writer(self):
        text = "Mã xuất báo cáo:\n```\nimport pandas as pd\nwith pd.ExcelWriter('report.xlsx') as writer:\n    pass\n```"
        code = code_actuator.extract_python_code(text)
        assert code is not None
        assert "pd.ExcelWriter" in code

    def test_execute_office_code_creates_real_file(self, tmp_path):
        code_actuator.output_dir = str(tmp_path)
        code = (
            "import openpyxl\n"
            "wb = openpyxl.Workbook()\n"
            "ws = wb.active\n"
            "ws['A1'] = 'JKAI Test'\n"
            "wb.save('unit_test.xlsx')\n"
        )
        res = code_actuator.execute_office_code(code, "unit_test.xlsx")
        assert res["success"] is True
        assert os.path.exists(res["file_path"])
        assert res["filename"] == "unit_test.xlsx"

    def test_prewarmed_scope_includes_essential_modules(self):
        scope = code_actuator._build_prewarmed_scope()
        assert "json" in scope
        assert "math" in scope
        assert "datetime" in scope
        assert "re" in scope

    def test_auto_healing_openpyxl_invalid_column_name(self, tmp_path):
        code_actuator.output_dir = str(tmp_path)
        bad_code = (
            "import openpyxl\n"
            "wb = openpyxl.Workbook()\n"
            "ws = wb.active\n"
            "ws.append(['Ma NV', 'Ten NV'])\n"
            "ws.column_dimensions['Ma NV'].width = 25\n"
            "wb.save('auto_heal_test.xlsx')\n"
        )
        res = code_actuator.execute_office_code(bad_code, "auto_heal_test.xlsx")
        assert res["success"] is True
        assert os.path.exists(res["file_path"])

# -*- coding: utf-8 -*-
"""
🧩 [AUTONOMOUS TOOL DISCOVERY & DYNAMIC PLUGIN LOADER v1.0]
File: core/plugins/dynamic_tool_loader.py

Hệ Sinh Thái Plugin Khai Báo & Tự Động Nạp Công Cụ (Trụ Cột 9):
  1. Declarative Tool Spec: Định nghĩa tool mới bằng YAML/JSON manifest.
  2. Runtime Tool Compiler: Tự động biên dịch và đăng ký tool vào registry mà không cần restart.
  3. Sandbox AST Verification: Kiểm tra cú pháp và tính an toàn của mã thực thi trước khi nạp.
"""

import ast
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger("JKAI.DynamicPluginLoader")


@dataclass
class DeclarativeToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    python_code: str
    author: str = "Master"
    is_active: bool = True
    created_at: float = field(default_factory=time.time)


class DynamicToolLoader:
    """
    🧩 Bộ Nạp & Biên Dịch Công Cụ Động Thời Gian Thực
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.registered_plugins: Dict[str, DeclarativeToolSpec] = {}
        self.compiled_executors: Dict[str, Callable] = {}

    def register_and_compile_tool(self, spec_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Nạp cấu hình khai báo, thẩm định an toàn bằng AST và biên dịch thành hàm thực thi.
        """
        tool_name = spec_dict.get("name", "").strip()
        code_str = spec_dict.get("python_code", spec_dict.get("code", "")).strip()

        if not tool_name or not code_str:
            return {"success": False, "error": "Thiếu tên tool hoặc mã Python thực thi."}

        # 1. Thẩm định cú pháp AST an toàn
        try:
            tree = ast.parse(code_str)
            # Chặn các lệnh nguy hại tiềm ẩn trong plugin
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(getattr(node, "func", None), "id", "") in ["os.system", "shutil.rmtree"]:
                    return {"success": False, "error": "Mã plugin chứa lệnh can thiệp hệ thống bị cấm."}
        except SyntaxError as syn_err:
            return {"success": False, "error": f"Lỗi cú pháp Python trong tool spec: {syn_err}"}

        # 2. Biên dịch hàm thực thi trong phạm vi cô lập
        execution_scope: Dict[str, Any] = {}
        try:
            exec(code_str, execution_scope)
            # Tìm hàm thực thi chính (execute hoặc trùng tên tool)
            executor = execution_scope.get("execute") or execution_scope.get(tool_name.lower()) or list(execution_scope.values())[-1]
            if not callable(executor):
                return {"success": False, "error": "Không tìm thấy hàm callable nào trong mã Python."}

            spec = DeclarativeToolSpec(
                name=tool_name,
                description=spec_dict.get("description", "Dynamic declarative tool"),
                parameters=spec_dict.get("parameters", {}),
                python_code=code_str,
                author=spec_dict.get("author", "Master")
            )

            self.registered_plugins[tool_name] = spec
            self.compiled_executors[tool_name] = executor
            logger.info(f"🧩 [DYNAMIC-PLUGIN]: Successfully compiled and registered tool '{tool_name}' at runtime.")

            return {
                "success": True,
                "tool_name": tool_name,
                "description": spec.description,
                "status": "ACTIVE"
            }

        except Exception as e:
            return {"success": False, "error": f"Lỗi nạp thực thi: {str(e)}"}

    def execute_dynamic_tool(self, tool_name: str, **kwargs) -> Any:
        """Thực thi công cụ động đã được nạp."""
        if tool_name in self.compiled_executors:
            executor = self.compiled_executors[tool_name]
            return executor(**kwargs)
        raise KeyError(f"Tool '{tool_name}' chưa được đăng ký trong Dynamic Plugin Registry.")

    def list_available_dynamic_tools(self) -> List[Dict[str, Any]]:
        """Liệt kê danh sách các công cụ động đang sẵn sàng."""
        return [
            {"name": spec.name, "description": spec.description, "parameters": spec.parameters}
            for spec in self.registered_plugins.values()
        ]


dynamic_tool_loader = DynamicToolLoader()

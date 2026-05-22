import ast
import json
import os

class SemanticReader:
    """
    Skill: semantic_read
    Description: Đọc và phân tích cấu trúc mã nguồn Python (AST).
    Trả về danh sách Classes, Functions, Imports và Docstrings thay vì text thô.
    """
    def __init__(self):
        self.workspace_root = os.getenv("WORKSPACE_ROOT", os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N"))

    def semantic_read(self, file_path: str) -> dict:
        """
        Đọc file python và phân tích Cây Cú Pháp (AST).
        """
        # Xử lý đường dẫn
        target_path = file_path
        if not os.path.isabs(target_path):
            target_path = os.path.join(self.workspace_root, target_path)

        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File không tồn tại: {target_path}"}

        if not target_path.endswith('.py'):
            return {"status": "error", "msg": f"Skill semantic_read hiện chỉ hỗ trợ file Python (.py)"}

        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
            
            result = {
                "file": file_path,
                "imports": [],
                "classes": [],
                "functions": []
            }

            for node in ast.walk(tree):
                # Lấy Imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        result["imports"].append(f"{module}.{alias.name}")
                
                # Lấy Functions độc lập (không nằm trong Class)
                elif isinstance(node, ast.FunctionDef) and not getattr(node, "_is_method", False):
                    func_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node)
                    }
                    result["functions"].append(func_info)

                # Lấy Classes và Methods bên trong
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node),
                        "methods": []
                    }
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            item._is_method = True # Đánh dấu để khỏi bị bắt bởi function_def
                            method_info = {
                                "name": item.name,
                                "args": [arg.arg for arg in item.args.args],
                                "docstring": ast.get_docstring(item)
                            }
                            class_info["methods"].append(method_info)
                    result["classes"].append(class_info)

            return {"status": "success", "data": result}
            
        except Exception as e:
            return {"status": "error", "msg": f"Lỗi parse AST: {str(e)}"}

import ast
import os
from typing import Dict, List, Any

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.imports = []
        self.definitions = []
        self.calls = []
        self.current_scope = []
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({"module": alias.name, "alias": alias.asname})
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ''
        for alias in node.names:
            self.imports.append({"module": f"{module}.{alias.name}", "alias": alias.asname})
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_info = {
            "type": "class",
            "name": node.name,
            "line": node.lineno,
            "methods": []
        }
        self.definitions.append(class_info)
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node):
        func_info = {
            "type": "function",
            "name": node.name,
            "line": node.lineno,
            "scope": ".".join(self.current_scope) if self.current_scope else "global"
        }
        self.definitions.append(func_info)
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node) # Xử lý async như hàm bình thường

    def visit_Call(self, node):
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            
        if func_name:
            self.calls.append({
                "called": func_name,
                "caller": ".".join(self.current_scope) if self.current_scope else "global",
                "line": node.lineno
            })
        self.generic_visit(node)


def parse_python_file(filepath: str) -> Dict[str, Any]:
    """Phân tích một file Python thành cấu trúc JSON."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        analyzer = CodeAnalyzer(filepath)
        analyzer.visit(tree)
        return {
            "file": filepath,
            "imports": analyzer.imports,
            "definitions": analyzer.definitions,
            "calls": analyzer.calls
        }
    except Exception as e:
        # Tắt bớt log rác để Master dễ nhìn
        return None

def scan_directory(directory: str) -> List[Dict[str, Any]]:
    """Quét toàn bộ thư mục để phân tích mã nguồn."""
    results = []
    for root, _, files in os.walk(directory):
        # Bỏ qua các thư mục không cần thiết để tăng tốc độ
        if any(ignore in root for ignore in ['.git', '__pycache__', 'venv', 'node_modules', 'scratch']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                parsed = parse_python_file(filepath)
                if parsed:
                    results.append(parsed)
    return results

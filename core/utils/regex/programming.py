import re

__all__ = [
    "PYTHON_FUNC", "PYTHON_CLASS", "PYTHON_IMPORT",
    "JS_FUNC", "ARROW_FUNC",
    "JAVA_CLASS",
    "GO_FUNC",
    "RUST_FUNC",
    "CPP_INCLUDE",
    "SNAKE_CASE_CALL",
]

PYTHON_FUNC = re.compile(r"def\s+\w+\(")
PYTHON_CLASS = re.compile(r"class\s+\w+")
PYTHON_IMPORT = re.compile(r"^(?:from|import)\s+[\w.]+", re.MULTILINE)
JS_FUNC = re.compile(r"function\s+\w+\(")
ARROW_FUNC = re.compile(r"\w+\s*=\s*\(?.*?\)?\s*=>")
JAVA_CLASS = re.compile(r"public\s+class")
GO_FUNC = re.compile(r"func\s+\w+")
RUST_FUNC = re.compile(r"fn\s+\w+")
CPP_INCLUDE = re.compile(r"#include\s*<")
SNAKE_CASE_CALL = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+){1,})\s*\(")

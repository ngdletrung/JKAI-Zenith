import re

__all__ = [
    "LOG_LEVEL", "LOG_TIMESTAMP", "PYTHON_TRACEBACK",
    "ERROR_LINE", "STACK_TRACE_LINE",
]

LOG_LEVEL = re.compile(r"\b(INFO|DEBUG|WARNING|ERROR|CRITICAL)\b")
LOG_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\b")
PYTHON_TRACEBACK = re.compile(r"Traceback \(most recent call last\)")
ERROR_LINE = re.compile(r'^\s*File ".*", line \d+, in .+$', re.MULTILINE)
STACK_TRACE_LINE = re.compile(r"^\s{4,}\w+.*$", re.MULTILINE)

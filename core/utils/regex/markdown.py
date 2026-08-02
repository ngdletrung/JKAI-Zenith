import re

__all__ = [
    "HEADING", "BOLD", "ITALIC", "CODE_INLINE", "CODE_BLOCK",
    "TABLE", "LIST_ITEM", "HORIZONTAL_RULE",
]

HEADING = re.compile(r"^#{1,6}\s.+$", re.MULTILINE)
BOLD = re.compile(r"\*\*(.*?)\*\*")
ITALIC = re.compile(r"\*(.*?)\*")
CODE_INLINE = re.compile(r"`([^`]+)`")
CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)
TABLE = re.compile(r"^\|.*\|$", re.MULTILINE)
LIST_ITEM = re.compile(r"^[\s]*[-*+]\s", re.MULTILINE)
HORIZONTAL_RULE = re.compile(r"^---+\s*$", re.MULTILINE)

import re

__all__ = ["MULTI_SPACE", "ZERO_WIDTH", "NON_PRINTABLE", "clean_text", "TOKEN_RE"]

MULTI_SPACE = re.compile(r"\s+")
ZERO_WIDTH = re.compile(r"[\u200B-\u200D\uFEFF]")
NON_PRINTABLE = re.compile(r"[^\S\r\n]+")


def clean_text(text: str) -> str:
    text = ZERO_WIDTH.sub("", text)
    text = NON_PRINTABLE.sub(" ", text)
    return MULTI_SPACE.sub(" ", text).strip()

TOKEN_RE = re.compile(r"[\w\u00C0-\u024F\u1E00-\u1EFF]+", re.UNICODE)

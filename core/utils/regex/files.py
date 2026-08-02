import re

__all__ = [
    "PDF", "WORD", "EXCEL", "IMAGE", "VIDEO", "AUDIO",
    "CODE", "ARCHIVE", "CONFIG",
]

PDF = re.compile(r"\.pdf$", re.IGNORECASE)
WORD = re.compile(r"\.(doc|docx)$", re.IGNORECASE)
EXCEL = re.compile(r"\.(xls|xlsx)$", re.IGNORECASE)
IMAGE = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|bmp)$", re.IGNORECASE)
VIDEO = re.compile(r"\.(mp4|avi|mkv|mov|wmv)$", re.IGNORECASE)
AUDIO = re.compile(r"\.(mp3|wav|flac|ogg)$", re.IGNORECASE)
CODE = re.compile(r"\.(py|js|ts|jsx|tsx|java|go|rs|cpp|c|h|hpp|rb|php|swift)$", re.IGNORECASE)
ARCHIVE = re.compile(r"\.(zip|tar|gz|bz2|7z|rar)$", re.IGNORECASE)
CONFIG = re.compile(r"\.(json|yaml|yml|toml|ini|cfg|env)$", re.IGNORECASE)

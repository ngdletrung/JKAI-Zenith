import re

__all__ = [
    "DATE_DMY", "DATE_MDY", "DATE_ISO",
    "TIME", "DATETIME_ISO", "DATETIME_VI",
    "RELATIVE_TIME", "YEAR_RECENT",
]

DATE_DMY = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](\d{4})\b")
DATE_MDY = re.compile(r"\b(0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])[-/](\d{4})\b")
DATE_ISO = re.compile(r"\b(\d{4})-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])\b")
TIME = re.compile(r"\b([01][0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?\b")
DATETIME_ISO = re.compile(
    r"\b(\d{4})-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])[T ]"
    r"([01][0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?\b"
)
DATETIME_VI = re.compile(
    r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE
)
RELATIVE_TIME = re.compile(
    r"\b(\d+)\s*(giờ|phút|ngày|hour|day|minute|min)s?\s*(trước|ago)\b", re.IGNORECASE
)
YEAR_RECENT = re.compile(r"\b(202[4-9])\b")

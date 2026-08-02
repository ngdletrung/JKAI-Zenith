import re
from typing import Any


class FactSet:
    def __init__(self):
        self.facts: list[dict] = []

    def add(self, fact_type: str, value: str, field: str = "", source: str = "", confidence: float = 0.8):
        self.facts.append({"type": fact_type, "value": value, "field": field, "source": source, "confidence": confidence})

    def to_list(self) -> list[dict]:
        return self.facts


class FactExtractor:
    _MONEY_PATTERN = re.compile(r"(\d+[.,]?\d*)\s*(triệu|tỉ|tỷ|nghìn|đồng|USD|usd|\$)", re.IGNORECASE)
    _TREND_PATTERN = re.compile(r"(tăng|giảm|lên|xuống|dao động|biến động|ổn định)\s*(.*?)(\d+[.,]?\d*\s*(triệu|tỉ|tỷ|nghìn|%|đồng|USD|usd|\$|điểm))?", re.IGNORECASE)
    _PERCENT_PATTERN = re.compile(r"(\d+[.,]?\d*)\s*%")
    _SOURCE_PATTERN = re.compile(r"(theo|nguồn|từ)\s+(\w+(?:\s+\w+)*)", re.IGNORECASE)
    _SUBJECT_PATTERN = re.compile(r"(giá\s+\w+|vàng|chứng\s+khoán|tỷ\s+giá|lãi\s+suất|bitcoin|eth|dầu|USD|VN-Index)", re.IGNORECASE)
    _DATE_PATTERN = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(hôm nay|hôm qua|ngày mai|tuần này|tuần trước|tháng này|tháng trước)", re.IGNORECASE)

    def extract(self, text: str, source: str = "") -> FactSet:
        facts = FactSet()
        if not text:
            return facts
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            for m in self._MONEY_PATTERN.finditer(line):
                facts.add("money", m.group(0), source=source)
            for m in self._TREND_PATTERN.finditer(line):
                facts.add("trend", m.group(0), source=source)
            for m in self._PERCENT_PATTERN.finditer(line):
                facts.add("percent", m.group(0), source=source)
            for m in self._SUBJECT_PATTERN.finditer(line):
                facts.add("subject", m.group(1), source=source)
        return facts

    def extract_subject(self, text: str) -> str:
        m = self._SUBJECT_PATTERN.search(text)
        return m.group(1) if m else ""

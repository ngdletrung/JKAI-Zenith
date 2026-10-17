# -*- coding: utf-8 -*-
"""
JKAI Trigger Parser (Deterministic Policy Gate).
Zero-LLM implementation enforcing source isolation, negation defense,
and deterministic intent extraction.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List


@dataclass
class TriggerResult:
    allowed: bool
    models: List[str] = field(default_factory=list)
    reason: str = "ok"
    raw_intent: str = ""


def strip_accents(text: str) -> str:
    """Normalize and strip diacritics for deterministic Vietnamese text matching."""
    text = text.replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


class TriggerParser:
    """
    Deterministic Parser for Master Direct Commands.
    Ensures policy gate invariant: Zero System 1 / LLMs involved in gating.
    """

    ALLOWED_SOURCES = {"master_cli", "master_ui", "master_voice"}

    # Check accented Vietnamese negations BEFORE stripping diacritics so "đúng" != "đừng"
    ACCENTED_NEGATION_PATTERNS = [
        r"\b(đừng|dừng lại|dừng thảo luận|chỉ chạy cục bộ|chỉ phân tích local|cấm thảo luận)\b",
        r"\b(đừng|không|cấm|dừng)\b.*(thảo luận|discuss|gọi cloud|call cloud|chatgpt|gemini|deepseek|grok)",
        r"\b(không được|không cho phép|cấm tuyệt đối)\b",
    ]

    # Unaccented negation patterns (safe from "dung roi" = "đúng rồi" collision)
    NEGATION_PATTERNS = [
        r"\b(dung lai|dung thao luan|cuc bo|chi local|only local)\b",
        r"\b(khong|cam|never|don'?t|stop)\b.*(thao luan|discuss|goi cloud|call cloud|chatgpt|gemini|deepseek|grok)",
        r"\b(khong duoc|khong cho phep|cam tuyet doi)\b",
    ]

    TRIGGER_PATTERNS = [
        r"hay thao luan voi (group|nhom) ai",
        r"thao luan voi (group|nhom) ai",
        r"thao luan voi (gemini|chatgpt|deepseek|grok|openai)",
        r"discuss with (group|gemini|chatgpt|deepseek|grok|openai)",
        r"please discuss with (group|gemini|chatgpt|deepseek|grok|openai)",
    ]

    KNOWN_MODELS = ["gemini", "chatgpt", "openai", "deepseek", "grok"]

    def parse(self, input_text: str, source: str) -> TriggerResult:
        if not input_text or not isinstance(input_text, str):
            return TriggerResult(allowed=False, reason="empty_input")

        # 1. Source Isolation: ONLY accept commands directly issued by Master
        if source not in self.ALLOWED_SOURCES:
            return TriggerResult(
                allowed=False,
                reason="source_not_master",
                raw_intent=input_text,
            )

        raw_lower = unicodedata.normalize("NFC", input_text.strip()).lower()

        # 2. Accented Vietnamese Negation Defense (Distinguishes "đừng"/"dừng" from "đúng"/"dùng")
        for acc_pat in self.ACCENTED_NEGATION_PATTERNS:
            if re.search(acc_pat, raw_lower):
                return TriggerResult(
                    allowed=False,
                    reason="negation_detected",
                    raw_intent=input_text,
                )

        # 3. Unicode & Diacritic Normalization
        normalized = strip_accents(raw_lower)

        # 4. Unaccented Negation Defense
        for neg_pat in self.NEGATION_PATTERNS:
            if re.search(neg_pat, normalized):
                return TriggerResult(
                    allowed=False,
                    reason="negation_detected",
                    raw_intent=input_text,
                )

        # 4. Trigger Matching: Must explicitly match positive discussion intent
        matched = False
        for trig_pat in self.TRIGGER_PATTERNS:
            if re.search(trig_pat, normalized):
                matched = True
                break

        if not matched:
            return TriggerResult(
                allowed=False,
                reason="no_trigger",
                raw_intent=input_text,
            )

        # 5. Model Target Extraction
        extracted_models = []
        for model in self.KNOWN_MODELS:
            if re.search(rf"\b{model}\b", normalized):
                extracted_models.append(model)

        if "group" in normalized or "nhom" in normalized or not extracted_models:
            if "default_group" not in extracted_models:
                extracted_models.append("default_group")

        return TriggerResult(
            allowed=True,
            models=extracted_models,
            reason="authorized_trigger",
            raw_intent=input_text,
        )

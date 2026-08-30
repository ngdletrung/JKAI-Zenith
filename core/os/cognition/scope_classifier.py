# -*- coding: utf-8 -*-
"""
core/os/cognition/scope_classifier.py
JKAI DEMS v1.0 — Deterministic Scope Classifier & Applicability Assessor.

Classifies incoming textual segments/URLs into typed epistemic scopes:
- POLITICS / GEOPOLITICS
- ECONOMY / FINANCIAL
- TECHNICAL / CODE
- HEALTH / SCIENCE
- ENTERTAINMENT / HOROSCOPE
- GENERAL
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Set, Tuple


@dataclass(frozen=True)
class ClassifiedScope:
    primary_scope: str
    secondary_scopes: List[str]
    applicability_to_world_news: float
    is_noise: bool
    reasons: List[str]


class ScopeClassifier:
    """Fast Dynamic Scope Classifier (< 1ms). Loads from scopes.yaml with hot-reload support."""

    def __init__(self, yaml_path: str = "core/os/routing/lexicons/scopes.yaml"):
        self.yaml_path = yaml_path
        self._scopes_config: dict = {}
        self._compiled_regexes: dict = {}
        self._noise_regex = None
        self._load_lexicon()

    def _load_lexicon(self):
        import os, yaml
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        full_path = os.path.join(base_dir, self.yaml_path) if not os.path.isabs(self.yaml_path) else self.yaml_path
        
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    self._scopes_config = data.get("scopes", {})
            except Exception:
                self._scopes_config = {}

        # Compile regexes for ultra-fast matching
        self._compiled_regexes = {}
        noise_kws = []
        for scope_name, conf in self._scopes_config.items():
            kws = conf.get("keywords", [])
            if conf.get("is_noise", False):
                noise_kws.extend(kws)
            elif kws:
                escaped = [re.escape(k) for k in kws]
                pattern = r"\b(" + "|".join(escaped) + r")\b"
                self._compiled_regexes[scope_name] = (re.compile(pattern, re.IGNORECASE), conf.get("applicability_to_world_news", 0.5))

        if noise_kws:
            escaped_noise = [re.escape(k) for k in noise_kws]
            self._noise_regex = re.compile(r"\b(" + "|".join(escaped_noise) + r")\b", re.IGNORECASE)
        else:
            self._noise_regex = re.compile(r"\b(tử vi|con giáp|cung hoàng đạo|chiêm tinh|bói toán|lịch vạn niên)\b", re.IGNORECASE)

    def classify(self, text: str, url: str = "") -> ClassifiedScope:
        combined = f"{url} {text}".lower()
        
        # 1. Check Noise / Horoscope first
        if self._noise_regex and self._noise_regex.search(combined):
            return ClassifiedScope(
                primary_scope="HOROSCOPE",
                secondary_scopes=["ENTERTAINMENT"],
                applicability_to_world_news=0.01,
                is_noise=True,
                reasons=["Matched dynamic horoscope/astrology/noise patterns"]
            )

        detected_scopes: List[Tuple[str, int, float]] = []

        # 2. Match against dynamically configured scopes
        for scope_name, (rgx, app_score) in self._compiled_regexes.items():
            matches = len(rgx.findall(combined))
            if matches > 0:
                detected_scopes.append((scope_name, matches, app_score))

        if not detected_scopes:
            return ClassifiedScope(
                primary_scope="GENERAL",
                secondary_scopes=[],
                applicability_to_world_news=0.4,
                is_noise=False,
                reasons=["General news content without strong topical domain"]
            )

        detected_scopes.sort(key=lambda x: x[1], reverse=True)
        primary = detected_scopes[0][0]
        primary_app = detected_scopes[0][2]
        secondaries = [s[0] for s in detected_scopes[1:]]

        return ClassifiedScope(
            primary_scope=primary,
            secondary_scopes=secondaries,
            applicability_to_world_news=primary_app,
            is_noise=False,
            reasons=[f"Dominant topic matches {primary} with score {detected_scopes[0][1]}"]
        )


scope_classifier = ScopeClassifier()

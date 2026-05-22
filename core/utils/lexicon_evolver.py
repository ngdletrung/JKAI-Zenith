import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class LLMVerdict:
    """Kết quả phân loại từ LLM — nguồn ground truth để học."""
    goal:           str
    normalized:     str
    primary_intent: str
    domain:         str
    confidence:     float
    tokens_used:    int = 0
    timestamp:      float = field(default_factory=time.time)

@dataclass
class LearnedPattern:
    """Một pattern đã được học từ LLM verdicts."""
    token:          str
    normalized:     str
    intent:         str
    domain:         str
    evidence_count: int  = 0
    confidence_sum: float = 0.0
    first_seen:     float = field(default_factory=time.time)
    last_seen:      float = field(default_factory=time.time)
    promoted:       bool  = False

    @property
    def avg_confidence(self) -> float:
        if self.evidence_count == 0: return 0.0
        return round(self.confidence_sum / self.evidence_count, 4)

    @property
    def is_ready_to_promote(self) -> bool:
        return (not self.promoted and self.evidence_count >= PatternMiner.MIN_EVIDENCE and self.avg_confidence >= PatternMiner.MIN_AVG_CONFIDENCE)

class PatternMiner:
    MIN_EVIDENCE:      int   = 3
    MIN_AVG_CONFIDENCE: float = 0.75
    _STOPWORDS: frozenset[str] = frozenset({"và", "hoặc", "nhưng", "với", "của", "cho", "về", "từ", "trong", "ngoài", "trên", "dưới", "này", "đó", "thì", "là", "có", "được", "không", "tôi", "bạn", "anh", "chị", "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or", "but", "in", "on", "at", "for", "with", "it", "this", "that", "i", "you", "he", "she", "we", "they"})
    _TOKEN_RE = re.compile(r"[\w\u00C0-\u024F\u1E00-\u1EFF]+", re.UNICODE)

    def extract(self, verdict: LLMVerdict) -> list[tuple[str, str]]:
        words = self._TOKEN_RE.findall(verdict.normalized)
        candidates = []
        for w in words:
            if len(w) >= 4 and w not in self._STOPWORDS: candidates.append((w, w.lower()))
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            norm = bigram.lower()
            if not all(w in self._STOPWORDS for w in bigram.split()): candidates.append((bigram, norm))
        return candidates

class LexiconStore:
    def __init__(self, store_path: str | Path = "lexicon_store.json"):
        self.path = Path(store_path)
        if not self.path.parent.exists(): self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return {"patterns": {}, "promoted_rules": []}

    def _save(self) -> None:
        try:
            with self.path.open("w", encoding="utf-8") as f: json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e: logger.error(f"LexiconStore save failed: {e}")

    def get_pattern(self, normalized: str) -> LearnedPattern | None:
        raw = self._data["patterns"].get(normalized)
        return LearnedPattern(**raw) if raw else None

    def upsert_pattern(self, pattern: LearnedPattern) -> None:
        self._data["patterns"][pattern.normalized] = asdict(pattern)
        self._save()

    def write_rule(self, pattern: LearnedPattern) -> None:
        rule = {"token": pattern.token, "normalized": pattern.normalized, "intent": pattern.intent, "domain": pattern.domain, "avg_confidence": pattern.avg_confidence, "evidence_count": pattern.evidence_count, "promoted_at": time.time()}
        self._data["promoted_rules"].append(rule)
        pattern.promoted = True
        self.upsert_pattern(pattern)
        logger.info(f"💎 [EVOLVE]: Rule promoted: '{pattern.token}' -> {pattern.intent}")

    def exported_rules(self) -> list[dict[str, Any]]:
        return list(self._data["promoted_rules"])

class LexiconEvolver:
    def __init__(self, store_path: str | Path = "lexicon_store.json", on_rule_promoted: Any = None):
        self.store = LexiconStore(store_path)
        self.miner = PatternMiner()
        self._on_promoted = on_rule_promoted
        self._pending: dict[str, LearnedPattern] = {}

    def observe(self, verdict: LLMVerdict) -> list[LearnedPattern]:
        candidates = self.miner.extract(verdict)
        for token, normalized in candidates:
            self._accumulate(token, normalized, verdict.primary_intent, verdict.domain, verdict.confidence)
        return self._promote_ready()

    def _accumulate(self, token, normalized, intent, domain, confidence):
        pattern = self._get_pattern(normalized) or LearnedPattern(token=token, normalized=normalized, intent=intent, domain=domain)
        pattern.evidence_count += 1
        pattern.confidence_sum += confidence
        pattern.last_seen = time.time()
        self.store.upsert_pattern(pattern)
        self._pending[normalized] = pattern

    def _get_pattern(self, normalized: str) -> LearnedPattern | None:
        return self._pending.get(normalized) or self.store.get_pattern(normalized)

    def _promote_ready(self) -> list[LearnedPattern]:
        promoted = []
        for pattern in list(self._pending.values()):
            if pattern.is_ready_to_promote:
                self.store.write_rule(pattern)
                promoted.append(pattern)
                if callable(self._on_promoted): self._on_promoted(self.store.exported_rules()[-1])
        return promoted

    def export_rules_for_lexicon(self) -> list[dict[str, Any]]:
        return self.store.exported_rules()

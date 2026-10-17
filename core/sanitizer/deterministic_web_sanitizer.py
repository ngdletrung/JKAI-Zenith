# -*- coding: utf-8 -*-
"""
core/sanitizer/deterministic_web_sanitizer.py
=============================================
Phase A7.2 & A7.3: Deterministic Web Sanitizer & Verbatim Passage Selector.
- Pure function, zero-model-in-the-loop sanitization for retrieved web content.
- Layer 1: Strips script, style, comments, and CSS-hidden/stealth elements.
- Layer 2: Strips invisible/bidi/tag characters while strictly PRESERVING ZWNJ (U+200C),
  ZWJ (U+200D), Emoji sequences, and NFC-normalized Vietnamese diacritics.
- Layer 3: Strips fake LLM delimiters (<|im_start|>, [INST], etc.) and neutralizes Base64 injections.
- VerbatimPassageSelector: Pure-Python BM25-CP scoring to select exact verbatim passages
  with character offsets and SHA-256 hashes without LLM paraphrasing.
"""

from __future__ import annotations

import base64
import hashlib
import html as html_lib
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.security.taint_tracking_warden import (
    ProvenanceLevel,
    TaintedValue,
    TaintTrackingWarden,
)

# Preserve ZWNJ (\u200c) and ZWJ (\u200d) for Indic/Persian and Emoji sequences!
# Strip zero-width space (\u200b), LRM/RLM (\u200e, \u200f), bidi overrides (\u202a-\u202e, \u2066-\u2069),
# word joiner/invisible math (\u2060-\u2064), BOM (\ufeff), soft hyphen (\u00ad), Arabic letter mark (\u061c),
# and Unicode tags (\U000e0000-\U000e007f).
INVISIBLE_CHARS_RE = re.compile(
    "[\u200b\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
    "\u2060\u2061\u2062\u2063\u2064\ufeff\u00ad\u061c\U000e0000-\U000e007f]"
)

# Stealth CSS patterns used to hide prompt injection payloads
STEALTH_TAG_RE = re.compile(
    r"""<(?P<tag>[a-zA-Z0-9]+)\b[^>]*(?:"""
    r"""\bhidden\b"""
    r"""|\baria-hidden\s*=\s*["']?true["']?"""
    r"""|\bstyle\s*=\s*["'][^"']*(?:"""
    r"""display\s*:\s*none"""
    r"""|visibility\s*:\s*hidden"""
    r"""|opacity\s*:\s*0(?:\.0+)?\b"""
    r"""|font-size\s*:\s*0(?:px|pt|em|rem)?\b"""
    r"""|color\s*:\s*transparent\b"""
    r"""|left\s*:\s*-\d{3,}(?:px|em)?\b"""
    r"""|top\s*:\s*-\d{3,}(?:px|em)?\b"""
    r"""|clip\s*:\s*rect\(\s*0"""
    r""")[^"']*["']"""
    r""")[^>]*>.*?</(?P=tag)>""",
    re.DOTALL | re.IGNORECASE,
)

CONTAINER_STRIP_RE = re.compile(
    r"<!--.*?-->"
    r"|<script\b[^>]*>.*?</script>"
    r"|<style\b[^>]*>.*?</style>"
    r"|<noscript\b[^>]*>.*?</noscript>"
    r"|<iframe\b[^>]*>.*?</iframe>"
    r"|<svg\b[^>]*>.*?</svg>"
    r"|<canvas\b[^>]*>.*?</canvas>"
    r"|<object\b[^>]*>.*?</object>",
    re.DOTALL | re.IGNORECASE,
)

TAG_STRIP_RE = re.compile(r"<[^>]+>")

# Fake LLM and chat template delimiters
FAKE_DELIMITERS_RE = re.compile(
    r"(?:<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|"
    r"<\|system\|>|<\|user\|>|<\|assistant\|>)",
    re.IGNORECASE,
)

# Potential base64 strings containing instructions
BASE64_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{20,}={0,2}(?![A-Za-z0-9+/=])")
SUSPICIOUS_PAYLOAD_KEYWORDS = (
    "ignore previous instructions",
    "ignore all previous",
    "previous instructions",
    "system prompt",
    "new instructions",
    "you are now",
    "dan mode",
    "developer mode",
    "reveal secret",
    "delete file",
)


@dataclass(frozen=True)
class VerbatimPassage:
    passage_id: str
    text: str
    char_start: int
    char_end: int
    sha256: str
    bm25_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "sha256": self.sha256,
            "bm25_score": round(self.bm25_score, 4),
        }


@dataclass
class WebRetrievalResult:
    contract_version: str = "1.0.0"
    url: str = ""
    status: str = "success"
    clean_text: str = ""
    total_chars: int = 0
    canonical_sha256: str = ""
    passages: List[VerbatimPassage] = field(default_factory=list)
    tainted_envelope: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "url": self.url,
            "status": self.status,
            "clean_text": self.clean_text,
            "total_chars": self.total_chars,
            "canonical_sha256": self.canonical_sha256,
            "passages": [p.to_dict() for p in self.passages],
            "tainted_envelope": self.tainted_envelope,
            "metadata": dict(self.metadata),
        }


class DeterministicWebSanitizer:
    """
    Three-layer deterministic sanitizer with strict UTF-8 NFC preservation
    and zero-model-in-the-loop guarantees.
    """

    @classmethod
    def strip_invisible_characters(cls, text: str) -> str:
        """Strips zero-width/bidi/tag characters while keeping ZWNJ/ZWJ and NFC."""
        if not text:
            return ""
        norm_text = unicodedata.normalize("NFC", str(text))
        return INVISIBLE_CHARS_RE.sub("", norm_text)

    @classmethod
    def strip_stealth_and_tags(cls, html_content: str) -> str:
        """Strips HTML comments, scripts, styles, and CSS-hidden stealth elements."""
        if not html_content:
            return ""
        # 1. Remove hidden/stealth DOM containers (display:none, aria-hidden, etc.)
        content = STEALTH_TAG_RE.sub(" ", html_content)
        # 2. Remove script/style/comment containers
        content = CONTAINER_STRIP_RE.sub(" ", content)
        # 3. Remove remaining HTML tags
        content = TAG_STRIP_RE.sub(" ", content)
        # 4. Unescape HTML entities
        content = html_lib.unescape(content)
        return content

    @classmethod
    def neutralize_delimiters_and_encoded(cls, text: str) -> str:
        """Removes fake delimiters and scans/defuses base64 prompt injection blocks."""
        if not text:
            return ""
        # 1. Strip fake delimiters
        cleaned = FAKE_DELIMITERS_RE.sub(" ", text)

        # 2. Scan for base64 instruction payloads
        def _check_base64_match(match: re.Match[str]) -> str:
            token = match.group(0)
            try:
                decoded = base64.b64decode(token, validate=True).decode("utf-8", errors="ignore").lower()
                if any(kw in decoded for kw in SUSPICIOUS_PAYLOAD_KEYWORDS):
                    return "[DEFUSED_ENCODED_PAYLOAD]"
            except Exception:
                pass
            return token

        cleaned = BASE64_TOKEN_RE.sub(_check_base64_match, cleaned)
        return cleaned

    @classmethod
    def sanitize(cls, raw_html: str, max_chars: int = 20000) -> str:
        """Full 3-layer deterministic sanitization pipeline."""
        if not raw_html:
            return ""
        step1 = cls.strip_stealth_and_tags(raw_html)
        step2 = cls.strip_invisible_characters(step1)
        step3 = cls.neutralize_delimiters_and_encoded(step2)

        # Normalize whitespace
        collapsed = " ".join(step3.split())
        final_text = unicodedata.normalize("NFC", collapsed)[:max_chars]
        return final_text


class VerbatimPassageSelector:
    """
    Pure-Python BM25-CP (Contiguous Phrase-Aware) passage selector.
    Adheres strictly to the principle: 'Page text is only ever scored, never followed'.
    """

    @staticmethod
    def tokenize(text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", str(text or "").lower())
        return [w for w in cleaned.split() if len(w) > 0]

    @classmethod
    def split_passages(
        cls,
        text: str,
        target_chunk_words: int = 60,
        overlap_words: int = 15,
    ) -> List[VerbatimPassage]:
        raw_words = text.split()
        if not raw_words:
            return []

        passages: List[VerbatimPassage] = []
        step = max(1, target_chunk_words - overlap_words)
        idx = 0
        p_num = 1

        while idx < len(raw_words):
            chunk_words = raw_words[idx : idx + target_chunk_words]
            chunk_str = " ".join(chunk_words)

            # Find exact character offsets within the sanitized text
            start_pos = text.find(chunk_str)
            if start_pos == -1:
                start_pos = 0
            end_pos = start_pos + len(chunk_str)

            p_digest = hashlib.sha256(chunk_str.encode("utf-8")).hexdigest()
            passages.append(
                VerbatimPassage(
                    passage_id=f"P_{p_num:03d}",
                    text=chunk_str,
                    char_start=start_pos,
                    char_end=end_pos,
                    sha256=p_digest,
                    bm25_score=0.0,
                )
            )
            p_num += 1
            idx += step
            if idx >= len(raw_words):
                break

        return passages

    @classmethod
    def score_and_select(
        cls,
        passages: Sequence[VerbatimPassage],
        query: str,
        top_k: int = 3,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> List[VerbatimPassage]:
        """
        Pure-Python BM25-CP with contiguous bigram/trigram boosts (1.5x / 2.0x).
        """
        if not passages:
            return []

        q_tokens = cls.tokenize(query)
        if not q_tokens:
            return list(passages[:top_k])

        # Generate bigrams and trigrams from query
        q_bigrams = [f"{q_tokens[i]} {q_tokens[i+1]}" for i in range(len(q_tokens) - 1)]
        q_trigrams = [f"{q_tokens[i]} {q_tokens[i+1]} {q_tokens[i+2]}" for i in range(len(q_tokens) - 2)]

        doc_tokens = [cls.tokenize(p.text) for p in passages]
        doc_lens = [len(dt) for dt in doc_tokens]
        avg_dl = sum(doc_lens) / max(1, len(doc_lens))
        total_docs = len(passages)

        # Document frequencies for query terms
        df_unigram: Dict[str, int] = {}
        for q in set(q_tokens):
            df_unigram[q] = sum(1 for dt in doc_tokens if q in dt)

        scored: List[VerbatimPassage] = []
        for p, tokens, d_len in zip(passages, doc_tokens, doc_lens):
            token_counts: Dict[str, int] = {}
            for t in tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            p_text_lower = p.text.lower()
            score = 0.0

            # 1. Unigram BM25 score
            for q in q_tokens:
                tf = token_counts.get(q, 0)
                if tf == 0:
                    continue
                df = df_unigram.get(q, 0)
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                denom = tf + k1 * (1.0 - b + b * (d_len / max(1.0, avg_dl)))
                score += idf * (tf * (k1 + 1.0)) / max(0.0001, denom)

            # 2. Contiguous Phrase Boosts
            for bg in q_bigrams:
                if bg in p_text_lower:
                    score += 1.5
            for tg in q_trigrams:
                if tg in p_text_lower:
                    score += 2.0

            scored.append(
                VerbatimPassage(
                    passage_id=p.passage_id,
                    text=p.text,
                    char_start=p.char_start,
                    char_end=p.char_end,
                    sha256=p.sha256,
                    bm25_score=score,
                )
            )

        scored.sort(key=lambda x: x.bm25_score, reverse=True)
        return scored[:top_k]


def build_retrieval_contract_result(
    url: str,
    raw_html: str,
    query: Optional[str] = None,
    max_chars: int = 20000,
    top_k_passages: int = 3,
) -> WebRetrievalResult:
    """End-to-end builder returning structured WebRetrievalResult with taint wrapping."""
    clean_text = DeterministicWebSanitizer.sanitize(raw_html, max_chars=max_chars)
    sha_digest = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    all_passages = VerbatimPassageSelector.split_passages(clean_text)

    if query and query.strip():
        selected_passages = VerbatimPassageSelector.score_and_select(all_passages, query, top_k=top_k_passages)
    else:
        selected_passages = all_passages[:top_k_passages]

    tainted = TaintTrackingWarden.tag_external(
        content=clean_text,
        source_uri=url,
        metadata={"canonical_sha256": sha_digest, "passages_count": len(selected_passages)},
    )

    return WebRetrievalResult(
        contract_version="1.0.0",
        url=url,
        status="success",
        clean_text=clean_text,
        total_chars=len(clean_text),
        canonical_sha256=sha_digest,
        passages=selected_passages,
        tainted_envelope=tainted.to_envelope(),
        metadata={"selected_passages_count": len(selected_passages)},
    )

# [ZENITH FILE DIRECTIVE]
# - File: logic.py
# - Role: Core Cognitive Logic for OMNI_SEARCH_ENGINE
# - Status: Optimized | Version: Zenith v9.9
# - Author: Antigravity AI thieu Master

import os
import re
import json
import logging
import asyncio
import hashlib
import time
import math
from enum import Enum
from typing import Any, List, Dict, Optional
import httpx
import sys

# Dam bao nap duoc cac module tu core
SYS_PATH_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if SYS_PATH_DIR not in sys.path:
    sys.path.append(SYS_PATH_DIR)

from core.qdrant_client import qdrant_client
from core.utils.embed import embed
from core.utils import path_manager
from core.utils.engine import engine
from core.utils import report_formatter as rf

logger = logging.getLogger("JKAI.OmniSearch")


class QueryIntent(Enum):
    CODE = "code"
    NEWS = "news"
    FACT = "fact"
    GENERAL = "general"


def classify_query_intent(query: str) -> QueryIntent:
    """
    Phan loai y dinh truy van (Query Intent Classifier) de thiet lap trong so rerank phu hop thua Master.
    """
    q_lower = query.lower()
    
    # 1. Code Intent Keywords
    code_keywords = [
        "code", "program", "function", "class", "syntax", "error", "exception",
        "api", "install", "docker", "python", "javascript", "react", "golang",
        "bash", "command", "git", "config", "build", "compile", "const ", "def "
    ]
    if any(kw in q_lower for kw in code_keywords):
        return QueryIntent.CODE
        
    # 2. News / Time Sensitive Intent Keywords
    time_keywords = [
        "tuan nay", "tuần này", "hom nay", "hôm nay", "moi nhat", "mới nhất",
        "trend", "trending", "gia vang", "giá vàng", "thoi tiet", "thời tiết",
        "tin tuc", "tin tức", "crypto", "bitcoin", "ty gia", "tỷ giá", "github"
    ]
    if any(kw in q_lower for kw in time_keywords):
        return QueryIntent.NEWS
        
    # 3. Factual Query Intent Keywords
    factual_keywords = [
        "la gi", "là gì", "dinh nghia", "định nghĩa", "what is", "who is",
        "ai la", "ai là", "lich su", "lịch sử", "khai niem", "khái niệm"
    ]
    if any(kw in q_lower for kw in factual_keywords):
        return QueryIntent.FACT
        
    return QueryIntent.GENERAL


def is_time_sensitive(query: str) -> bool:
    return classify_query_intent(query) == QueryIntent.NEWS


def split_long_text(text: str, max_len: int = 1500, overlap: int = 150) -> List[str]:
    """
    Phan ra cac khoi van ban cuc ky dai (vi du nhu mot paragraph qua dai khong co dau xuong dong) thua Master.
    Dam bao moi khoi con luon nho hon hoac bang max_len.
    """
    if len(text) <= max_len:
        return [text]
        
    lines = text.split("\n")
    sub_chunks = []
    current = []
    current_len = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if len(line) > max_len:
            if current:
                sub_chunks.append("\n".join(current))
                current = []
                current_len = 0
                
            sentences = re.split(r"(?<=[.!?])\s+", line)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(sentence) > max_len:
                    words = sentence.split(" ")
                    word_chunk = []
                    word_len = 0
                    for word in words:
                        if word_len + len(word) + 1 > max_len:
                            if word_chunk:
                                sub_chunks.append(" ".join(word_chunk))
                            overlap_words = []
                            overlap_len = 0
                            for w in reversed(word_chunk):
                                if overlap_len + len(w) + 1 < overlap:
                                    overlap_words.insert(0, w)
                                    overlap_len += len(w) + 1
                                else:
                                    break
                            word_chunk = overlap_words + [word]
                            word_len = overlap_len + len(word) + 1
                        else:
                            word_chunk.append(word)
                            word_len += len(word) + 1
                    if word_chunk:
                        sub_chunks.append(" ".join(word_chunk))
                else:
                    if current_len + len(sentence) + 1 > max_len:
                        sub_chunks.append(" ".join(current))
                        overlap_s = []
                        overlap_len = 0
                        for s in reversed(current):
                            if overlap_len + len(s) + 1 < overlap:
                                overlap_s.insert(0, s)
                                overlap_len += len(s) + 1
                            else:
                                break
                        current = overlap_s + [sentence]
                        current_len = overlap_len + len(sentence) + 1
                    else:
                        current.append(sentence)
                        current_len += len(sentence) + 1
        else:
            if current_len + len(line) + 1 > max_len:
                sub_chunks.append("\n".join(current))
                overlap_l = []
                overlap_len = 0
                for l in reversed(current):
                    if overlap_len + len(l) + 1 < overlap:
                        overlap_l.insert(0, l)
                        overlap_len += len(l) + 1
                    else:
                        break
                current = overlap_l + [line]
                current_len = overlap_len + len(line) + 1
            else:
                current.append(line)
                current_len += len(line) + 1
                
    if current:
        sub_chunks.append("\n".join(current))
        
    return [sc.strip() for sc in sub_chunks if sc.strip()]


def chunk_content_advanced(content: str, max_chunk_len: int = 1500, overlap: int = 150) -> List[str]:
    """
    Phan doan nhan thuc nang cao (Markdown, Code and Token-aware Chunker with Sliding Overlap) thua Master.
    - Bao toan nguyen ven khoi ma nguon (Code block preservation).
    - Su dung sliding overlap de giu lien mach tuyen tinh cho thong tin (Sliding window context).
    - Tu dong phan ra cac khoi paragraph co kich thuoc vuot nguong max_chunk_len de tieu diet lam lon thong tin.
    """
    if not content:
        return []
        
    paragraphs = re.split(r"\n\s*\n", content)
    chunks = []
    current_chunk = []
    current_len = 0
    in_code_block = False
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
            
        if "```" in p:
            in_code_block = (in_code_block != (p.count("```") % 2 != 0))
            
        p_len = len(p)
        
        # Neu paragraph hien tai qua to, phai su dung phuong phap phan ra phan cap thua Master
        if p_len > max_chunk_len and not in_code_block:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            
            sub_p_list = split_long_text(p, max_chunk_len, overlap)
            for sub_p in sub_p_list:
                chunks.append(sub_p)
            continue
            
        if current_len + p_len > max_chunk_len and not in_code_block:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                
                overlap_size = 0
                overlap_p = []
                for prev_p in reversed(current_chunk):
                    if overlap_size + len(prev_p) < overlap:
                        overlap_p.insert(0, prev_p)
                        overlap_size += len(prev_p)
                    else:
                        break
                current_chunk = overlap_p + [p]
                current_len = overlap_size + p_len
            else:
                chunks.append(p)
                current_chunk = []
                current_len = 0
        else:
            current_chunk.append(p)
            current_len += p_len
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return [c.strip() for c in chunks if len(c.strip().split()) > 5]


def extract_date_info(text: str, url: str, api_date: str = None) -> Optional[str]:
    """
    Trích xuất ngày đăng tin từ API date, URL hoặc nội dung văn bản thưa Master.
    Đảm bảo luôn trả về định dạng chuẩn DD/MM/YYYY hoặc tính toán chính xác từ thời gian tương đối.
    """
    import datetime
    today = datetime.date.today()
    
    # 0. Nếu có API date, ưu tiên hàng đầu và chuẩn hóa
    if api_date:
        api_date_str = str(api_date).strip()
        # Thử khớp ISO: 2026-05-29T15:44:38Z hoặc 2026-05-29
        iso_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", api_date_str)
        if iso_match:
            y, m, d = iso_match.group(1), iso_match.group(2).zfill(2), iso_match.group(3).zfill(2)
            return f"{d}/{m}/{y}"
        # Thử khớp DD/MM/YYYY
        dmy_match = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", api_date_str)
        if dmy_match:
            d, m, y = dmy_match.group(1).zfill(2), dmy_match.group(2).zfill(2), dmy_match.group(3)
            return f"{d}/{m}/{y}"

    # 1. Thử trích xuất từ URL
    if url:
        url_clean = url.lower()
        # Mẫu 1: YYYY/MM/DD hoặc YYYY-MM-DD hoặc YYYY/M/D
        url_ymd = re.search(r"\b(202[4-9])[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b", url_clean)
        if url_ymd:
            y, m, d = url_ymd.group(1), url_ymd.group(2).zfill(2), url_ymd.group(3).zfill(2)
            return f"{d}/{m}/{y}"
            
        # Mẫu 2: DD-MM-YYYY hoặc DD/MM/YYYY hoặc D-M-YYYY
        url_dmy = re.search(r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](202[4-9])\b", url_clean)
        if url_dmy:
            d, m, y = url_dmy.group(1).zfill(2), url_dmy.group(2).zfill(2), url_dmy.group(3)
            return f"{d}/{m}/{y}"

        # Mẫu 3: Dạng chuỗi số liên tục chứa ngày YYYYMMDD (ví dụ: ...20260529... hoặc ...192260529...)
        url_digits = re.search(r"\b\d*(202[4-9])(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d*\b", url_clean)
        if url_digits:
            y, m, d = url_digits.group(1), url_digits.group(2), url_digits.group(3)
            return f"{d}/{m}/{y}"
            
        # Mẫu 4: Dạng chuỗi số không biên tự do (ví dụ trong tên file htm: 192260529065038422)
        url_free_digits = re.search(r"(202[4-9])(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", url_clean)
        if url_free_digits:
            y, m, d = url_free_digits.group(1), url_free_digits.group(2), url_free_digits.group(3)
            return f"{d}/{m}/{y}"

    # 2. Thử trích xuất từ nội dung văn bản (text)
    text_clean = text.strip()
    if text_clean:
        # Mẫu A: ngày DD tháng MM năm YYYY (tiếng Việt)
        text_vn = re.search(r"ngày\s+([1-9]|0[1-9]|[12]\d|3[01])\s+tháng\s+([1-9]|0[1-9]|1[0-2])\s+năm\s+(202[4-9])", text_clean, re.IGNORECASE)
        if text_vn:
            d = text_vn.group(1).zfill(2)
            m = text_vn.group(2).zfill(2)
            y = text_vn.group(3)
            return f"{d}/{m}/{y}"

        # Mẫu B: DD/MM/YYYY hoặc DD-MM-YYYY hoặc DD.MM.YYYY (với ngày/tháng có hoặc không có số 0)
        text_dmy = re.search(r"\b(0?[1-9]|[12]\d|3[01])[-/\.](0?[1-9]|1[0-2])[-/\.](202[4-9])\b", text_clean)
        if text_dmy:
            d = text_dmy.group(1).zfill(2)
            m = text_dmy.group(2).zfill(2)
            y = text_dmy.group(3)
            return f"{d}/{m}/{y}"

        # Mẫu C: YYYY-MM-DD hoặc YYYY/MM/DD
        text_ymd = re.search(r"\b(202[4-9])[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b", text_clean)
        if text_ymd:
            y = text_ymd.group(1)
            m = text_ymd.group(2).zfill(2)
            d = text_ymd.group(3).zfill(2)
            return f"{d}/{m}/{y}"

        # Mẫu D: Relative time tiếng Việt & tiếng Anh
        relative_match = re.search(r"\b(\d+)\s*(giờ|phút|ngày|hour|day|minute|min)\s*(trước|ago)\b", text_clean, re.IGNORECASE)
        if relative_match:
            num = int(relative_match.group(1))
            unit = relative_match.group(2).lower()
            if "ngày" in unit or "day" in unit:
                target_date = today - datetime.timedelta(days=num)
                return target_date.strftime("%d/%m/%Y")
            elif "giờ" in unit or "hour" in unit or "phút" in unit or "minute" in unit or "min" in unit:
                return today.strftime("%d/%m/%Y")

        if re.search(r"\b(hôm qua|yesterday)\b", text_clean, re.IGNORECASE):
            target_date = today - datetime.timedelta(days=1)
            return target_date.strftime("%d/%m/%Y")

        if re.search(r"\b(hôm nay|today|vừa xong|vừa đăng|mới đăng)\b", text_clean, re.IGNORECASE):
            return today.strftime("%d/%m/%Y")

    # 3. Mặc định dự phòng nếu có năm 2026/2025 trong text hoặc URL nhưng không rõ ngày tháng cụ thể,
    # chúng ta lấy ngày hôm nay làm mặc định nếu bài viết chứa từ khóa mang tính thời sự "mới nhất", "hôm nay".
    if text_clean and any(kw in text_clean.lower() for kw in ["mới nhất", "hôm nay", "tin tức", "news", "thời sự"]):
        return today.strftime("%d/%m/%Y")

    if "2026" in text_clean or (url and "2026" in url):
        return today.strftime("%d/%m/%Y")
    if "2025" in text_clean or (url and "2025" in url):
        return "31/12/2025"

    return today.strftime("%d/%m/%Y")


def deduplicate_candidates(candidates: List[Dict], similarity_threshold: float = 0.85) -> List[Dict]:
    """
    Khu trung lap ngu nghia de tranh cac trang mirror, tin rac hay lap lai thua Master.
    Su dung Jaccard Similarity tren tap hop cac unigrams tu vung duoc chuan hoa.
    """
    if not candidates:
        return []
        
    unique_candidates = []
    seen_contents = []
    
    # Sap xep theo do dai hoac trust score truoc neu co san de giu lai ban chat luong nhat
    for cand in candidates:
        content = cand.get("content", "")
        if not content:
            continue
            
        words = set(_normalize_text(content).split())
        if len(words) < 5:
            continue
            
        is_duplicate = False
        for seen_words in seen_contents:
            if not seen_words:
                continue
            intersection = len(words.intersection(seen_words))
            union = len(words.union(seen_words))
            jaccard = intersection / union if union > 0 else 0.0
            
            if jaccard > similarity_threshold:
                is_duplicate = True
                break
                
        if not is_duplicate:
            unique_candidates.append(cand)
            seen_contents.append(words)
            
    return unique_candidates


class SourceCredibilityScorer:
    """
    Phan he tham dinh nguon tin nang cao thua Master:
    - Xep hang uy tin ten mien (Domain Reputation)
    - Loc thu rac va quang cao (Anti-Spam Filter)
    - Tinh toan do tuoi moi tri thuc (Freshness Decay)
    """
    def __init__(self):
        self.elite_domains = [
            "github.com", "stackoverflow.com", "python.org", "pypi.org",
            "npmjs.com", "docs.microsoft.com", "w3schools.com", "wikipedia.org",
            "medium.com/engineering", "developer.mozilla.org", "arxiv.org"
        ]
        self.doc_domains = [
            "docs.", "api.", "git", "blog.", "tech."
        ]
        self.spam_domains = [
            "seo-farm", "cheap-promos", "crack-", "discount", "offer-",
            "ad-click", "spam", "click-here", "quang-cao", "khuyen-mai"
        ]
        self.spam_keywords_regex = re.compile(
            r"(gia re|quang cao|click here|affiliate|mua ngay|gia tot|khuyen mai|chinh hang|voucher|discount|coupon|buy now)",
            re.IGNORECASE
        )

    def calculate_reputation(self, url: str) -> float:
        if not url:
            return 0.5
        url_lower = url.lower()
        score = 0.5
        for domain in self.elite_domains:
            if domain in url_lower:
                score = 1.0
                return score
                
        for domain in self.doc_domains:
            if domain in url_lower:
                score = 0.8
                return score
                
        for domain in self.spam_domains:
            if domain in url_lower:
                score = 0.2
                return score
                
        return score

    def calculate_spam_penalty(self, text: str) -> float:
        if not text:
            return 1.0
        matches = self.spam_keywords_regex.findall(text)
        if not matches:
            return 1.0
        word_count = len(text.split())
        if word_count == 0:
            return 1.0
        density = len(matches) / word_count
        if density > 0.02:
            return 0.4
        elif density > 0.005:
            return 0.7
        return 1.0

    def calculate_freshness_score(self, text: str, url: str) -> float:
        score = 0.5
        year_matches = re.findall(r"\b(2025|2026)\b", text + " " + url)
        if year_matches:
            score = 1.0
        elif "2024" in text or "2024" in url:
            score = 0.8
        elif any(yr in text or yr in url for yr in ["2023", "2022", "2021"]):
            score = 0.6
        else:
            old_year_matches = re.findall(r"\b(201\d|200\d)\b", text + " " + url)
            if old_year_matches:
                score = 0.3
        return score

    def score_source(self, url: str, text: str) -> float:
        reputation = self.calculate_reputation(url)
        penalty = self.calculate_spam_penalty(text)
        freshness = self.calculate_freshness_score(text, url)
        return reputation * penalty * freshness


def clean_scraped_content(text: str) -> str:
    """
    Lam sach ma nguon tho va loai bo nhieu quang cao, cookie, dieu khoan dich vu.
    """
    if not text:
        return ""
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"style\s*\{[^}]*\}", " ", text)
    noise_patterns = [
        r"(accept cookies|privacy policy|terms of service|cookie policy|all rights reserved|dang ky|dang nhap|menu|navigation)",
        r"(ban quyen thuoc ve|chinh sach bao mat|dieu khoan su dung)"
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_text(t: str) -> str:
    if not t:
        return ""
    t = t.lower()
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def _extract_ngrams(text: str, max_n: int = 3) -> list[str]:
    words = text.split()
    ngrams = []
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            ngrams.append(ngram)
    return ngrams


class HybridReranker:
    """
    Bo tai xep hang ket hop thong minh (Adaptive Hybrid Reranker) thua Master:
    - Tong hop diem so BM25-CP voi IDF dong thoi gian thuc tren Local Corpus.
    - Tang cuong cosine embeddings ngu nghia (Semantic Cosine).
    - Trong so tu dong thich ung (Dynamic Query Intent Weighting) phu hop theo ngu canh thua Master.
    """
    def __init__(self, query: str, candidates: List[Dict] = None):
        self.query = query
        self.intent = classify_query_intent(query)
        
        clean_query = _normalize_text(query)
        self.query_terms = list(set(_extract_ngrams(clean_query, max_n=3)))
        if not self.query_terms:
            self.query_terms = [t for t in query.lower().split() if len(t) > 1]
        if not self.query_terms:
            self.query_terms = query.lower().split()
            
        self.idf = {}
        if candidates:
            self._precompute_idf(candidates)
        else:
            self.idf = {t: 1.0 for t in self.query_terms}

    def _precompute_idf(self, candidates: List[Dict]):
        num_docs = len(candidates)
        for term in self.query_terms:
            padded_term = f" {term} "
            df = 0
            for c in candidates:
                clean_content = _normalize_text(c.get("content", ""))
                padded_content = f" {clean_content} "
                if padded_term in padded_content:
                    df += 1
            self.idf[term] = math.log(max((num_docs - df + 0.5) / (df + 0.5), 0.0001) + 1.0) if num_docs > 0 else 1.0

    def compute_bm25_lite(self, text: str, url: str = "") -> float:
        if not text:
            return 0.0
        clean_text = _normalize_text(text)
        doc_len = len(clean_text.split())
        if doc_len == 0:
            return 0.0
            
        score = 0.0
        padded_chunk = f" {clean_text} "
        
        for term in self.query_terms:
            padded_term = f" {term} "
            tf = padded_chunk.count(padded_term)
            if tf > 0:
                term_word_count = len(term.split())
                phrase_boost = 1.0
                if term_word_count == 2:
                    phrase_boost = 1.5
                elif term_word_count >= 3:
                    phrase_boost = 2.0
                    
                idf = self.idf.get(term, 1.0)
                score += phrase_boost * idf * (tf * 2.5) / (tf + 1.5 * (0.25 + 0.75 * (doc_len / 250.0)))
                
        # Phrase boost
        query_clean = self.query.lower().strip()
        text_lower = text.lower()
        if query_clean in text_lower:
            score += 4.0
            
        # Code block boost
        if "```" in text or "const " in text_lower or "def " in text_lower or "import " in text_lower or "class " in text_lower:
            score += 1.5
            
        # URL match boost
        if url:
            url_lower = url.lower()
            original_terms = [t for t in self.query.lower().split() if len(t) > 1]
            for term in original_terms:
                if term in url_lower:
                    score += 0.3
                    
        return score

    def compute_semantic_sim(self, text: str, text_embedding: list = None, query_embedding: list = None) -> float:
        if query_embedding and text_embedding:
            dot_product = sum(a * b for a, b in zip(query_embedding, text_embedding))
            norm_q = math.sqrt(sum(a * a for a in query_embedding))
            norm_t = math.sqrt(sum(b * b for b in text_embedding))
            if norm_q > 0 and norm_t > 0:
                return dot_product / (norm_q * norm_t)
        
        # Jaccard similarity fallback
        text_terms = set(text.lower().split())
        query_set = set(self.query_terms)
        if not text_terms or not query_set:
            return 0.0
        intersection = query_set.intersection(text_terms)
        union = query_set.union(text_terms)
        return len(intersection) / len(union)

    def rerank(self, candidates: List[Dict], query_embedding: list = None) -> List[Dict]:
        if not self.idf or len(self.idf) != len(self.query_terms):
            self._precompute_idf(candidates)
            
        # Dynamic Weighting theo y dinh cau hoi thua Master
        if self.intent == QueryIntent.CODE:
            weights = {"bm25": 0.15, "semantic": 0.55, "trust": 0.20, "recency": 0.10}
        elif self.intent == QueryIntent.NEWS:
            weights = {"bm25": 0.25, "semantic": 0.25, "trust": 0.15, "recency": 0.35}
        elif self.intent == QueryIntent.FACT:
            weights = {"bm25": 0.30, "semantic": 0.40, "trust": 0.20, "recency": 0.10}
        else:
            weights = {"bm25": 0.30, "semantic": 0.30, "trust": 0.25, "recency": 0.15}
            
        reranked = []
        for cand in candidates:
            content = cand.get("content", "")
            url = cand.get("url", "")
            trust_score = cand.get("trust_score", 0.5)
            recency_score = cand.get("recency_score", 0.5)
            cand_embedding = cand.get("embedding", None)
            
            bm25 = self.compute_bm25_lite(content, url)
            semantic = self.compute_semantic_sim(content, cand_embedding, query_embedding)
            
            scaled_bm25 = min(bm25 / (len(self.query_terms) * 3.0 + 1e-9), 1.0)
            
            # Tinh diem composite lay tu Dynamic Weights thua Master
            hybrid_score = (
                (weights["bm25"] * scaled_bm25) + 
                (weights["semantic"] * semantic) + 
                (weights["trust"] * trust_score) + 
                (weights["recency"] * recency_score)
            )
            
            cand_copy = dict(cand)
            cand_copy["bm25_score"] = scaled_bm25
            cand_copy["semantic_score"] = semantic
            cand_copy["hybrid_score"] = hybrid_score
            reranked.append(cand_copy)
            
        reranked.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return reranked


class FactVerifier:
    """
    Bo kiem chung su that nang cao (Consensus-based Technical Fact Verifier) thua Master:
    - Trich xuat va xac minh thong so ky thuat: ports, versions, commands, configs.
    - Tinh toan diem dong thuan (Consensus Score) giua cac nguon tin khac nhau de luu vao sieu tri thuc.
    - Phat hien maut thuan va dua ra canh bao khi phat hien bat dong thuan ky thuat giua cac trang web.
    """
    def __init__(self):
        self.port_pattern = re.compile(r"\b(?:port|localhost:|127\.0\.0\.1:)(\d{3,5})\b", re.IGNORECASE)
        self.version_pattern = re.compile(r"\b([\w\-]{3,20})\s+(?:v\d+\.\d+(?:\.\d+)?|\bversion\s+\d+\.\d+)\b", re.IGNORECASE)
        self.cmd_pattern = re.compile(r"\b(?:npm run|python|pip install|docker run|docker-compose|git clone|npx|uv pip|uv run)\b", re.IGNORECASE)
        self.negation_pattern = re.compile(r"\b(?:not|never|deprecated|avoid|error|failed|blocked|issue|warning|mau thuan|loi|khong nen|bi chan)\b", re.IGNORECASE)
        self.config_pattern = re.compile(r"\b([\w\_]{3,20})\s*[:=]\s*([\w\-]{1,15}|\d+)\b")

    def extract_technical_facts(self, text: str) -> Dict[str, Dict[str, str]]:
        facts = {
            "ports": {},
            "versions": {},
            "commands": {},
            "configs": {}
        }
        for match in self.port_pattern.finditer(text):
            facts["ports"]["port"] = match.group(1)
        for match in self.version_pattern.finditer(text):
            lib_name = match.group(1).lower()
            if lib_name not in ["the", "a", "an", "this", "my", "version", "with", "at", "by", "release"]:
                facts["versions"][lib_name] = match.group(0).lower()
        for match in self.cmd_pattern.finditer(text):
            cmd = match.group(0).lower()
            facts["commands"][cmd] = "present"
        for match in self.config_pattern.finditer(text):
            key = match.group(1).lower()
            val = match.group(2).lower()
            if key not in ["http", "https", "port", "version", "class", "def", "import", "const", "let", "var", "npm", "pip", "docker"]:
                facts["configs"][key] = val
        return facts

    def verify_and_detect_contradictions(self, candidates: List[Dict]) -> Dict[str, Any]:
        registry = {
            "ports": {},
            "versions": {},
            "commands": {},
            "configs": {}
        }
        for idx, cand in enumerate(candidates):
            content = cand.get("content", "")
            url = cand.get("url", "")
            facts = self.extract_technical_facts(content)
            for category, entity_dict in facts.items():
                for entity, val in entity_dict.items():
                    registry[category].setdefault(entity, {}).setdefault(val, []).append((idx, url))
                    
        verified_facts = {
            "ports": [],
            "versions": [],
            "commands": [],
            "configs": []
        }
        contradiction_warnings = []
        
        for category, entities in registry.items():
            for entity, val_dict in list(entities.items()):
                if len(val_dict) > 1:
                    conflicts = []
                    total_mentions = 0
                    for val, sources in val_dict.items():
                        total_mentions += len(sources)
                        src_urls = list(set(src[1] for src in sources))
                        conflicts.append(f"'{val}' tu {', '.join(src_urls[:1])}")
                    warning_msg = f"Xung dot ky thuat {category} cho '{entity}': Co nhieu thong tin trai chieu ({'; '.join(conflicts)})"
                    contradiction_warnings.append(warning_msg)
                    best_val = max(val_dict.keys(), key=lambda v: len(val_dict[v]))
                    supporting_sources = list(set(src[1] for src in val_dict[best_val]))
                    consensus_score = len(val_dict[best_val]) / total_mentions
                    verified_facts[category].append({
                        "entity": entity,
                        "value": best_val,
                        "confidence": "medium" if consensus_score >= 0.5 else "low",
                        "consensus_score": round(consensus_score, 2),
                        "sources": supporting_sources
                    })
                else:
                    val = list(val_dict.keys())[0]
                    sources = val_dict[val]
                    src_urls = list(set(src[1] for src in sources))
                    confidence = "high" if len(src_urls) >= 2 else "medium"
                    verified_facts[category].append({
                        "entity": entity,
                        "value": val,
                        "confidence": confidence,
                        "consensus_score": 1.0,
                        "sources": src_urls
                    })
                    
        for cand in candidates:
            content = cand.get("content", "")
            url = cand.get("url", "")
            if self.negation_pattern.search(content):
                sentences = re.split(r"[.!?]", content)
                for sentence in sentences:
                    sentence_strip = sentence.strip()
                    if len(sentence_strip) > 10 and self.negation_pattern.search(sentence_strip):
                        contradiction_warnings.append(f"Canh bao phat hien tu nguon {url}: '{sentence_strip}'")
                        
        return {
            "verified_facts": verified_facts,
            "contradiction_warnings": list(set(contradiction_warnings)),
            "is_consistent": len(contradiction_warnings) == 0
        }


class InMemoryLRUCache:
    """
    Sieu toc do nho dem nho nhe LRU Cache trong RAM de tranh doc o dia/Qdrant cho cac cau truy van hot-query thuong gap thua Master.
    """
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache = {}
        self.order = []

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest_key = self.order.pop(0)
            del self.cache[oldest_key]
        self.cache[key] = value
        self.order.append(key)

_lru_cache = InMemoryLRUCache(capacity=100)


class KnowledgePersistenceLoop:
    """
    Chu ky dong hoa tri thuc thong minh hai tang thua Master:
    - Tra cuu sieu toc LRU Cache trong RAM (0ms latency cho hot-queries)
    - Tra cuu o dia cuc bo va Qdrant Vector DB (Semantic Cache)
    - Luu tru va phuc hoi cache thoi gian thuc co ho tro mtime-validation
    """
    def __init__(self):
        self.cache_dir = path_manager.get("NEURAL_CACHE_DIR") or os.path.join(path_manager.get_root(), "intelligence", "knowledge", "neural_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_query_key(self, query: str) -> str:
        clean_query = re.sub(r"[^a-zA-Z0-9_]", "_", query)[:50].strip("_")
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()[:10]
        return f"{clean_query}_{query_hash}"

    async def get_cached_knowledge(self, query: str) -> Optional[Dict[str, Any]]:
        time_sensitive = is_time_sensitive(query)
        ttl = 3600 if time_sensitive else 43200
        
        # 1. Tra cuu RAM LRU Cache truoc de dat phan hoi gan nhu tuc thi thua Master
        mem_cached = _lru_cache.get(query)
        if mem_cached:
            cached_time = mem_cached.get("timestamp", 0)
            age = time.time() - cached_time
            if age < ttl:
                logger.info(f"[NEURAL-CACHE]: Trung dich RAM LRU Cache (Age: {age:.0f}s < TTL: {ttl}s)")
                return {
                    "status": "success",
                    "source": "memory_lru_cache",
                    "output": mem_cached.get("output", {})
                }
                
        logger.info(f"[NEURAL-CACHE]: Tra cuu tri thuc cho '{query}'...")
        
        # 2. Truy van Qdrant (Semantic Cache Match)
        try:
            query_emb = await embed.get_embedding_async(query)
            if query_emb:
                results = await qdrant_client.search_similar(
                    query_embedding=query_emb,
                    limit=1,
                    collection="jkai_zenith_intel",
                    filter_dict={"namespace": "neural_cache"}
                )
                if results:
                    best_match = results[0]
                    score = best_match.get("score", 0.0)
                    if score >= 0.88:
                        payload = best_match.get("payload", {})
                        cached_time = payload.get("timestamp", 0)
                        age = time.time() - cached_time
                        
                        if age < ttl:
                            logger.info(f"[NEURAL-CACHE]: Trung dich Qdrant Semantic Cache (Score: {score:.2f}, Age: {age:.0f}s < TTL: {ttl}s)")
                            res_payload = {
                                "content": payload.get("text", ""),
                                "metadata": payload
                            }
                            # Dong thoi dua nguoc len RAM Cache de thuc hien Hot promotion thua Master
                            _lru_cache.put(query, {
                                "timestamp": cached_time,
                                "output": res_payload
                            })
                            return {
                                "status": "success",
                                "source": "qdrant_cache",
                                "score": score,
                                "output": res_payload
                            }
                        else:
                            logger.info(f"[NEURAL-CACHE]: Cache Qdrant het han (Age: {age:.0f}s >= TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"[NEURAL-CACHE]: Qdrant cache error ({e})")

        # 3. Khoi phuc tu dia cuc bo
        try:
            key = self._get_query_key(query)
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cached_time = data.get("timestamp", 0)
                age = time.time() - cached_time
                
                if age < ttl:
                    logger.info(f"[NEURAL-CACHE]: Trung dich o dia: {cache_file} (Age: {age:.0f}s < TTL: {ttl}s)")
                    # Promotion len RAM LRU Cache
                    _lru_cache.put(query, {
                        "timestamp": cached_time,
                        "output": data
                    })
                    return {
                        "status": "success",
                        "source": "local_cache",
                        "output": data
                    }
                else:
                    logger.info(f"[NEURAL-CACHE]: Cache o dia het han (Age: {age:.0f}s >= TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"[NEURAL-CACHE]: Disk cache error ({e})")
            
        return None

    async def persist_knowledge(self, query: str, content: str, metadata: dict = None) -> bool:
        key = self._get_query_key(query)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        payload = {
            "query": query,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        # Luu vao RAM Cache ngay lap tuc
        _lru_cache.put(query, {
            "timestamp": time.time(),
            "output": payload
        })
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
            logger.info(f"[NEURAL-CACHE]: Luu cache o dia: {cache_file}")
        except Exception as e:
            logger.warning(f"[NEURAL-CACHE]: Loi ghi cache o dia ({e})")
            
        try:
            text_to_embed = f"Query: {query}\nAnswer: {content}"
            emb = await embed.get_embedding_async(text_to_embed)
            if emb:
                qdrant_meta = {
                    "namespace": "neural_cache",
                    "original_query": query,
                    "timestamp": time.time(),
                    **(metadata or {})
                }
                success = await qdrant_client.upsert_intel(
                    text=content,
                    embedding=emb,
                    metadata=qdrant_meta,
                    collection="jkai_zenith_intel",
                    vector_size=len(emb)
                )
                if success:
                    logger.info("[NEURAL-CACHE]: Day vector tri thuc vao Qdrant.")
                    return True
        except Exception as e:
            logger.warning(f"[NEURAL-CACHE]: Loi ghi vector vao Qdrant ({e})")
            
        return False


def _clean_query(query) -> str:
    if not query:
        return ""
    if isinstance(query, dict):
        for key in ["query", "q", "extracted_params", "description", "value"]:
            if val := query.get(key):
                return _clean_query(val)
        if len(query) == 1:
            return _clean_query(list(query.values())[0])
        return json.dumps(query)
    if isinstance(query, list):
        if len(query) > 0:
            return _clean_query(query[0])
        return ""
    if isinstance(query, str):
        query_str = query.strip()
        if query_str.startswith("{") and query_str.endswith("}"):
            try:
                parsed = json.loads(query_str)
                return _clean_query(parsed)
            except Exception:
                pass
        return query_str
    return str(query)


class OmniSearchEngine:
    """
    Skill: omni_search
    Bo may tim kiem dong thoi va chieu chieu chong chap Zenith v9.9.
    """
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self._embed_semaphore = asyncio.Semaphore(4)  # Gioi han 4 luong tao embeddings song song tranh loi nghẽn VRAM thua Master
        
    async def optimize_query(self, query: str) -> str:
        """
        Toi uu hoa cau truy van: Dich va mo rong thuat ngu ky thuat sang tieng Anh de tim kiem toan cau tot nhat.
        """
        q_lower = query.lower()
        if "trending github tuần này" in q_lower or "github trending" in q_lower:
            return "trending github this week"
            
        # [LOCAL-BYPASS]: Giu nguyen tieng Viet cho cac chu de dan sinh/local thieu Master
        local_keywords = ["giá vàng", "thời tiết", "tỷ giá", "xổ số", "giá xăng", "tin tức việt nam"]
        if any(kw in q_lower for kw in local_keywords):
            return query
            
        try:
            prompt = (
                "Ban la Query Planner cua JKAI Zenith. "
                "Hay dich va toi uu hoa cau truy van sau thanh mot tu khoa tim kiem tieng Anh ngan gon, hieu qua nhat.\n"
                "Quy tac:\n"
                "- Chi tra ve dung tu khoa tieng Anh toi uu, khong co bat ky van ban giai thich nao.\n"
                "- Neu cau truy van da la tieng Anh hoac ten rieng thi giu nguyen.\n"
                "- Tuyet doi khong dung emoji.\n\n"
                f"Query: '{query}'"
            )
            optimized = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="SUMMARIZER",
                task_id="query_optimization",
                trace_id="system"
            )
            if isinstance(optimized, dict) and "answer" in optimized:
                optimized = optimized["answer"]
            optimized_clean = optimized.strip().strip('"').strip("'").strip()
            
            if len(optimized_clean.split()) <= 6 and len(optimized_clean) > 2:
                logger.info(f"[QUERY-PLANNER]: Toi uu hoa truy van: '{query}' -> '{optimized_clean}'")
                return optimized_clean
        except Exception as e:
            logger.warning(f"[QUERY-PLANNER]: Loi toi uu hoa truy van bang LLM ({e}), su dung truy van goc.")
            
        return query

    async def omni_search(self, query: str, mode: str = "fast", **kwargs) -> dict:
        query = _clean_query(query)
        task_id = kwargs.get("task_id", "unknown")
        is_raw = kwargs.get("raw", False)
        
        # 0. Giai quyet che do hoat dong tu dong (auto mode) thieu Master
        resolved_mode = mode
        if mode == "auto":
            intent = classify_query_intent(query)
            if intent in (QueryIntent.NEWS, QueryIntent.GENERAL):
                resolved_mode = "fast"
            else:
                resolved_mode = "deep"
            logger.info(f"[OMNI-SEARCH-AUTO]: Da tu dong dinh tuyen y dinh {intent.value} -> mode: {resolved_mode} thieu Master.")

        # 1. Tra cuu cache truoc
        persistence = KnowledgePersistenceLoop()
        if not kwargs.get("bypass_cache", False):
            cached = await persistence.get_cached_knowledge(query)
            if cached:
                return cached

        # 2. Xac dinh truy van tim kiem (Search Query Optimization)
        if resolved_mode == "deep":
            search_query = await self.optimize_query(query)
        else:
            search_query = query

        # 3. THUC THI CHUOI TIM KIEM SONG SONG (CONCURRENT PARALLEL SEARCH CHAIN) thua Master!
        # Chay song song tat ca nguon tin va thu thap ket qua dong thoi de dat Latency nho nhat.
        logger.info(f"[OMNI-SEARCH-CONCURRENT]: Bat dau tim kiem dong thoi tren tat ca cac kenh cho '{search_query}'...")
        
        tasks = []
        source_indices = {}
        idx = 0
        
        # Kenh 1: Tavily API (Neu co Key)
        if self.tavily_api_key:
            tasks.append(self._search_tavily(search_query, resolved_mode))
            source_indices[idx] = "tavily"
            idx += 1
            
        # Kenh 2: DuckDuckGo Native (Free search)
        tasks.append(self._search_ddg(search_query))
        source_indices[idx] = "duckduckgo"
        idx += 1
        
        # Kenh 3: AI-Browse (Physical browser scraping fallback)
        try:
            from core.utils.registry import registry
            executor_url = registry.get_service_url("executor")
            if executor_url:
                tasks.append(self._search_browse(search_query, executor_url))
                source_indices[idx] = "ai_browse"
                idx += 1
        except Exception:
            pass
            
        # Kenh 4: Cloud LLM fallback
        tasks.append(self._search_cloud_llm(search_query))
        source_indices[idx] = "cloud_llm"
        idx += 1

        # Kich hoat dong thoi toan bo cac tieu tien trinh tim kiem thua Master!
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Tap hop va chiet xuat toan bo cac candidate tu cac nguon tim kiem thanh cong thua Master
        raw_candidates = []
        source_success = []
        
        for i, res in enumerate(search_results):
            if isinstance(res, Exception):
                logger.warning(f"[OMNI-SEARCH-CONCURRENT-FAIL]: Kenh '{source_indices[i]}' loi ({res})")
                continue
                
            if not res:
                continue
                
            source_name = source_indices[i]
            source_success.append(source_name)
            
            # Khop cau truc de tao thanh structured search results
            formatted_res = None
            if source_name == "tavily":
                formatted_res = {"output": res}
            elif source_name == "duckduckgo":
                formatted_res = {"output": {"results": res}}
            else:
                formatted_res = {"output": {"content": res}}
                
            # Trich xuat canidates tung phan
            extracted = self._extract_candidates(formatted_res, source_name)
            if extracted:
                raw_candidates.extend(extracted)
                
        if not raw_candidates:
            return {
                "status": "error",
                "msg": "Tim kiem dong thoi that bai tren tat ca cac kenh thua Master."
            }
            
        logger.info(f"[OMNI-SEARCH-CONCURRENT]: Thu thap thanh cong {len(raw_candidates)} phan doan thong tin tu: {', '.join(source_success)}")

        # Khu trung lap ngu nghia ngay truoc khi di vao cac khoi loc sau de tiet kiem tai nguyen thua Master
        candidates = deduplicate_candidates(raw_candidates, similarity_threshold=0.82)
        if not candidates:
            return {
                "status": "error",
                "msg": "Toan bo du lieu tim kiem bi trung lap va loc sach thua Master."
            }

        # 🧪 [ZENITH-V2-STRATEGY]: Tra ve RAW Data ngay lap tuc neu mode=fast thua Master
        if is_raw:
            engine.publish_mission_log("SEARCH", f"Trinh dien {len(candidates)} phan doan da khu trung lap tu {', '.join(source_success)}. Dang day ve Zenith...", task_id)
            raw_output = []
            for c in candidates[:5]: 
                content = c.get("content", "")[:2500] 
                raw_output.append(f"Source: {c.get('url')}\nContent: {content}")
            
            final_raw = "\n\n---\n\n".join(raw_output)
            if not final_raw.strip():
                return {"status": "error", "msg": "Du lieu tho rong thua Master."}
                
            return {
                "status": "success",
                "source": "+".join(source_success),
                "output": final_raw
            }

        # 4. CHU TRINH LOC PHAN TICH CHUYEN SAU (DEEP COGNITIVE PIPELINE)
        scorer = SourceCredibilityScorer()
        processed_candidates = []
        for cand in candidates:
            url = cand.get("url", "")
            raw_content = cand.get("content", "")
            clean_content = clean_scraped_content(raw_content)
            
            if len(clean_content.split()) < 3:
                continue
                
            trust_score = scorer.score_source(url, clean_content)
            recency_score = scorer.calculate_freshness_score(clean_content, url)
            
            processed_candidates.append({
                "url": url,
                "content": clean_content,
                "trust_score": trust_score,
                "recency_score": recency_score
            })

        if not processed_candidates:
            return {
                "status": "error",
                "msg": "Noi dung thong tin phan doan qua kem va da bi bo loc sach thua Master."
            }

        query_embedding = None
        if resolved_mode == "fast":
            logger.info("[OMNI-SEARCH]: Dang chay o che do FAST, bo qua buoc sinh embeddings de giam thoi gian tre thieu Master.")
            processed_candidates = processed_candidates[:12]
        else:
            # Tao embeddings song song co kiem soat Semaphore de tranh lam tre thong tin hay qua tai phan cung
            embedding_targets = processed_candidates[:12] # Toi uu: Chi lay top 12 ung vien tot nhat truoc khi rerank de tranh overhead
            
            async def get_embedding_safely(text: str):
                async with self._embed_semaphore:
                    try:
                        return await embed.get_embedding_async(text[:2000])
                    except Exception as ex:
                        logger.warning(f"[OMNI-SEARCH]: Loi tao embedding vector cho ung vien ({ex})")
                        return None
                        
            logger.info(f"[OMNI-SEARCH]: Bat dau tien trinh sinh vector nhung han che semaphore cho {len(embedding_targets)} ung vien...")
            embeddings = await asyncio.gather(*[get_embedding_safely(c["content"]) for c in embedding_targets])
            
            for cand, emb in zip(embedding_targets, embeddings):
                if emb:
                    cand["embedding"] = emb
            processed_candidates = embedding_targets

            try:
                query_embedding = await embed.get_embedding_async(query)
            except Exception as e:
                logger.warning(f"[OMNI-SEARCH]: Loi sinh vector truy van goc ({e})")

        # Rerank hybrid voi trong so dong thich ung thua Master
        reranker = HybridReranker(query)
        ranked_candidates = reranker.rerank(processed_candidates, query_embedding)
        
        # Kiem trung su that va canh bao xich dong dong nghia
        verifier = FactVerifier()
        verification_data = verifier.verify_and_detect_contradictions(ranked_candidates)
        
        # Tong hop nhan thuc 2-Pass grounded citation thua Master
        logger.info("[OMNI-SEARCH]: Bat dau tien trinh Tong hop Tri thuc Grounded va Citation thua Master...")
        synthesized_answer = await self._synthesize_knowledge(query, ranked_candidates, verification_data, mode=resolved_mode)
        
        metadata = {
            "source_type": "+".join(source_success),
            "verification_data": {
                "is_consistent": verification_data["is_consistent"],
                "contradiction_warnings": verification_data["contradiction_warnings"],
                "verified_facts": {k: list(v) if isinstance(v, set) else v for k, v in verification_data["verified_facts"].items()}
            }
        }
        await persistence.persist_knowledge(query, synthesized_answer, metadata)
        
        return {
            "status": "success",
            "source": f"internet_" + "+".join(source_success),
            "output": {
                "content": synthesized_answer,
                "metadata": metadata
            }
        }

    def _extract_candidates(self, search_result: dict, source_type: str) -> List[Dict]:
        candidates = []
        if source_type == "tavily":
            results = search_result.get("output", {}).get("results", [])
            for r in results:
                url = r.get("url", "https://tavily.com")
                raw_content = r.get("content", "")
                api_date = r.get("published_date") or r.get("date")
                extracted_date = extract_date_info(raw_content, url, api_date)
                date_prefix = f"[Ngày {extracted_date}] " if extracted_date else ""
                
                chunks = chunk_content_advanced(raw_content)
                for chunk in chunks:
                    chunk_content = chunk.strip()
                    if date_prefix and not chunk_content.startswith("[Ngày"):
                        chunk_content = f"{date_prefix}{chunk_content}"
                    candidates.append({
                        "url": url,
                        "content": chunk_content
                    })
        elif source_type == "duckduckgo":
            results = search_result.get("output", {}).get("results", [])
            for r in results:
                url = r.get("href", "https://duckduckgo.com")
                raw_content = r.get("body", "")
                api_date = r.get("published_date") or r.get("date")
                extracted_date = extract_date_info(raw_content, url, api_date)
                date_prefix = f"[Ngày {extracted_date}] " if extracted_date else ""
                
                chunks = chunk_content_advanced(raw_content)
                for chunk in chunks:
                    chunk_content = chunk.strip()
                    if date_prefix and not chunk_content.startswith("[Ngày"):
                        chunk_content = f"{date_prefix}{chunk_content}"
                    candidates.append({
                        "url": url,
                        "content": chunk_content
                    })
        else:
            content = ""
            if source_type == "cloud_llm":
                content = search_result.get("output", {}).get("content", "")
                url = "https://cloud-llm-search.internal"
            else:
                content = search_result.get("output", {}).get("content", "")
                url = "https://duckduckgo.com"
                
            extracted_date = extract_date_info(content, url)
            date_prefix = f"[Ngày {extracted_date}] " if extracted_date else ""
            
            chunks = chunk_content_advanced(content)
            for chunk in chunks:
                chunk_content = chunk.strip()
                if date_prefix and not chunk_content.startswith("[Ngày"):
                    chunk_content = f"{date_prefix}{chunk_content}"
                candidates.append({
                    "url": url,
                    "content": chunk_content
                })
        return candidates

    async def _search_tavily(self, query: str, mode: str) -> dict:
        query = _clean_query(query)
        search_depth = "advanced" if mode == "deep" else "basic"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": search_depth,
                    "include_answer": True,
                    "max_results": 5
                }
            )
            if resp.status_code == 429:
                raise Exception("429 Quota Exceeded")
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Tavily API failed with status {resp.status_code}: {resp.text}")
                raise e
            return resp.json()
            
    async def _search_ddg(self, query: str) -> List[Dict]:
        """[FREE-SEARCH]: Sử dụng thư viện duckduckgo_search thưa Master."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=5)]
                return results
        except Exception as e:
            logger.error(f"[DDG-ERR]: {e}")
            return []

    async def _search_cloud_llm(self, query: str) -> str:
        from core.utils.engine import engine
        prompt = (
            f"Vui long tim kiem tren Internet thong tin moi nhat ve: '{query}'. "
            "Tra loi ngan gon, chi tiet va chua cac thong tin thoi su/thuc te."
        )
        answer = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="PLANNER",
            task_id="omni_search_internal",
            trace_id="system"
        )
        if isinstance(answer, dict) and "answer" in answer:
            return answer["answer"]
        return str(answer)

    async def _search_browse(self, query: str, executor_url: str) -> str:
        from core.utils.engine import engine
        engine.publish_progress(92, f"[BROWSER] Dang khoi dong trinh duyet ao de tim kiem: `{query}`...", "browser", "omni")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{executor_url}/call_tool",
                json={
                    "name": "ai_browse",
                    "args": {
                        "url": f"https://duckduckgo.com/html/?q={query}",
                        "action": "extract_text"
                    }
                }
            )
            if resp.status_code == 200:
                engine.publish_progress(95, "[BROWSER] Da ket noi. Dang trich xuat DNA du lieu tu trang web...", "browser", "omni")
                data = resp.json()
                if data.get("status") == "success":
                    return str(data.get("output", ""))[:3000]
        raise Exception("Browser automation failed")

    def _append_citations_footer(self, text: str, sources: List[tuple], confidence_level: str) -> str:
        """
        Dinh dang chan trang de trinh bay cac nguon trich dan va do tin cay mot cach tinh xao nhat thua Master.
        """
        header = ""
        if "Độ tự tin tổng hợp" not in text and "Độ tin cậy" not in text:
            header = rf.section(f"Muc do tu tin nhan thuc: {confidence_level}", 3) + "\n\n"
            
        seen_urls = set()
        citation_items = []
        for idx, url, trust in sources:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            trust_label = "Cao" if trust >= 0.8 else "Trung bình" if trust >= 0.5 else "Thấp"
            citation_items.append(f"**[{idx}]** [{url}]({url}) *(Do uy tin: {trust_label})*")
            
        footer = rf.build([
            "",
            rf.section("Nguon trich dan thong tin", 3),
            rf.bullet(citation_items),
        ])
        return header + text.strip() + footer

    async def _synthesize_knowledge(self, query: str, ranked_snippets: List[Dict], verification_data: dict, mode: str = "fast") -> str:
        from core.utils.engine import engine
        
        # 1. Tinh toan do tin cay tong hop (Overall Confidence Score) thua Master
        avg_trust = sum(s.get("trust_score", 0.5) for s in ranked_snippets[:5]) / min(len(ranked_snippets), 5) if ranked_snippets else 0.5
        warnings = verification_data.get("contradiction_warnings", [])
        fact_penalty = min(0.3, len(warnings) * 0.05)
        overall_confidence = max(0.1, avg_trust * (1.0 - fact_penalty))
        confidence_percentage = int(overall_confidence * 100)
        
        if confidence_percentage >= 85:
            confidence_level = f"CAO ({confidence_percentage}%) thưa Master"
        elif confidence_percentage >= 60:
            confidence_level = f"TRUNG BÌNH ({confidence_percentage}%) thưa Master"
        else:
            confidence_level = f"THẤP ({confidence_percentage}%) thưa Master"
            
        # 2. Xay dung van ban cac Snippet trich dan
        limit = 3 if mode == "fast" else 5
        citation_sources = []
        snippets_rows = []
        for i, r in enumerate(ranked_snippets[:limit]):
            content_preview = r.get('content', '')[:200].replace('\n', ' ')
            snippets_rows.append([str(i+1), f"{r.get('trust_score', 0.5):.2f}", content_preview])
            citation_sources.append((i+1, r.get('url', 'Unknown'), r.get('trust_score', 0.5)))
        snippets_text = rf.table(["Nguon", "Do tin cay", "Trich xuat"], snippets_rows)
            
        warnings_text = ""
        if warnings:
            warnings_text = rf.build([
                rf.section("Canh bao mau thuan va xung dot ky thuat"),
                rf.bullet(warnings),
            ])
                
        # 3. Pass 1: Soan thao ban nhap tong hop
        draft_prompt = (
            f"Bạn là Hệ thống Tổng hợp Nhận thức Cao cấp của JKAI Zenith.\n"
            f"Hãy trả lời câu hỏi sau dựa trên dữ liệu tìm kiếm được cung cấp: '{query}'\n\n"
            f"KẾT QUẢ ĐÁNH GIÁ ĐỘ TIN CẬY:\n"
            f"- Mức độ tự tin tổng hợp: {confidence_level}\n"
            f"{warnings_text}\n"
            f"DỮ LIỆU TÌM KIẾM CÓ SẴN (Bắt buộc dùng trích dẫn):\n"
            f"{snippets_text}\n"
            f"CÁC QUY TẮC TỔNG HỢP CỰC KỲ NGHIÊM NGẶT THỪA MASTER:\n"
            f"1. CHỈ sử dụng thông tin có trực tiếp từ dữ liệu tìm kiếm. Tuyệt đối không tự suy diễn hay bịa đặt.\n"
            f"2. Con số '89.500' hoặc '157.500' trong giá vàng đại diện cho TRIỆU ĐỒNG/lượng (ví dụ: 89,5 triệu đồng/lượng).\n"
            f"3. Bắt buộc chèn trích dẫn dạng số thứ tự nguồn ngay sau các thông tin quan trọng hoặc cuối câu, ví dụ: '[1]', '[1, 3]'.\n"
            f"4. Nếu có mâu thuẫn hay điểm chưa chắc chắn (độ tin cậy trung bình/thấp), hãy nêu rõ các luồng ý kiến khác nhau một cách khách quan.\n"
            f"5. Văn phong súc tích, cực kỳ chính xác, khoa học và lễ phép với Master. Không chào hỏi rườm rà."
        )
        
        # Neu la FAST mode, chay 1 Pass duy nhat de toi uu thoi gian thua Master
        if mode == "fast":
            engine.publish_mission_log("SEARCH", f"⚡ Sử dụng Single-Pass Synthesis để tối ưu thời gian thưa Master. Độ tự tin: {confidence_percentage}%", "unknown")
            final_res = await engine.call_chat(
                messages=[{"role": "user", "content": draft_prompt}],
                role="SUMMARIZER",
                task_id="omni_synthesis_fast",
                trace_id="system"
            )
            ans = final_res["answer"] if isinstance(final_res, dict) and "answer" in final_res else str(final_res)
            return self._append_citations_footer(ans, citation_sources, confidence_level)
            
        # DEEP MODE: Chay 2 Pass de dam bao chat luong cao nhat thua Master
        draft_res = await engine.call_chat(
            messages=[{"role": "user", "content": draft_prompt}],
            role="SUMMARIZER",
            task_id="omni_synthesis_draft",
            trace_id="system"
        )
        draft_content = draft_res["answer"] if isinstance(draft_res, dict) and "answer" in draft_res else str(draft_res)
        
        refine_prompt = (
            f"Hãy tinh chỉnh bản nháp này thành câu trả lời hoàn hảo thưa Master, sửa đổi văn phong trôi chảy, "
            f"đảm bảo các thông số kỹ thuật (đặc biệt là giá vàng đơn vị triệu đồng/lượng) cực kỳ chuẩn xác, "
            f"giữ nguyên vẹn tất cả các trích dẫn dạng [1], [2] và độ tin cậy của thông tin.\n\n"
            f"BẢN NHÁP BAN ĐẦU:\n{draft_content}\n"
        )
        
        final_res = await engine.call_chat(
            messages=[{"role": "user", "content": refine_prompt}],
            role="SUMMARIZER",
            task_id="omni_synthesis_refine",
            trace_id="system"
        )
        ans = final_res["answer"] if isinstance(final_res, dict) and "answer" in final_res else str(final_res)
        return self._append_citations_footer(ans, citation_sources, confidence_level)


# Instantiation
_instance = OmniSearchEngine()

async def omni_search(**kwargs) -> dict:
    query = kwargs.pop("query", None) or kwargs.pop("q", None)
    mode = kwargs.pop("mode", "fast")
    if not query:
        return {"status": "error", "msg": "Missing query parameter"}
    return await _instance.omni_search(query, mode, **kwargs)

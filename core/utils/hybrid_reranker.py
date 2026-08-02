"""
Hybrid Reranker Module for JKAI Zenith.
Implements a hybrid scoring system:
hybrid_score = 0.6 * cosine_score + 0.3 * bm25_score + 0.1 * freshness_score
"""

import logging
import math
import re
from datetime import datetime, date
from typing import List, Dict, Any, Union, Optional

logger = logging.getLogger("hybrid_reranker")

class BM25Calculator:
    """
    Lightweight BM25 calculator implemented in pure Python.
    """
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lengths = []
        self.doc_term_frequencies = [] # List of term frequency dict per document
        self.idf = {}
        
        # Tokenize corpus
        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.avg_doc_length = sum(len(doc) for doc in tokenized_corpus) / max(self.corpus_size, 1)
        
        # Document frequencies for IDF calculation
        doc_frequencies = {}
        for doc in tokenized_corpus:
            self.doc_lengths.append(len(doc))
            tf = {}
            for term in doc:
                tf[term] = tf.get(term, 0) + 1
            self.doc_term_frequencies.append(tf)
            
            # Record unique terms in doc to calculate df
            for term in set(doc):
                doc_frequencies[term] = doc_frequencies.get(term, 0) + 1
                
        # Calculate IDF (Okapi BM25 formula)
        for term, df in doc_frequencies.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))
            
    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        text = text.lower()
        # Simple tokenization by splitting on alphanumeric characters
        words = re.findall(r'\w+', text)
        return words

    def get_score(self, doc_idx: int, query_terms: List[str]) -> float:
        """
        Calculate BM25 score for a document index given tokenized query terms.
        """
        score = 0.0
        tf_dict = self.doc_term_frequencies[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        
        for term in query_terms:
            if term not in tf_dict:
                continue
            tf = tf_dict[term]
            idf = self.idf.get(term, 0.0)
            
            # BM25 term score formula
            numerator = tf * (self.k1 + 1.0)
            denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(self.avg_doc_length, 1.0)))
            score += idf * (numerator / denominator)
            
        return score


class HybridReranker:
    """
    Reranks documents based on a hybrid scoring function:
    hybrid_score = 0.6 * cosine_score + 0.3 * bm25_score + 0.1 * freshness_score
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def _parse_date(self, date_val: Any) -> Optional[date]:
        """
        Attempts to parse date from various formats (string, datetime, date, timestamp).
        """
        if not date_val:
            return None
        if isinstance(date_val, date):
            if isinstance(date_val, datetime):
                return date_val.date()
            return date_val
        
        if isinstance(date_val, (int, float)):
            try:
                from datetime import timezone
                return datetime.fromtimestamp(date_val, timezone.utc).date()
            except Exception:
                return None
                
        if isinstance(date_val, str):
            # Clean and try to parse
            clean_val = date_val.split("+")[0].split("Z")[0].strip()
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(clean_val, fmt).date()
                except ValueError:
                    continue
        return None

    def _calculate_freshness_score(self, doc_date: Optional[date], current_date: date) -> float:
        """
        Calculates freshness score between 0.0 and 1.0.
        If the date is in the last 12 months, it gets high priority (0.5 to 1.0).
        Older documents decay towards 0.0.
        """
        if not doc_date:
            return 0.0
            
        delta = current_date - doc_date
        delta_days = delta.days
        
        if delta_days <= 0:
            return 1.0
            
        # 12 months = 365 days
        if delta_days <= 365:
            # Linear decay from 1.0 to 0.5 within the first year
            return 1.0 - 0.5 * (delta_days / 365.0)
        else:
            # Exponential decay after 1 year, starting from 0.5
            # decays by half every ~2 years (730 days)
            return 0.5 * math.exp(-(delta_days - 365.0) / 730.0)

    def rerank(
        self,
        documents: List[Dict[str, Any]],
        query: str,
        current_date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Reranks a list of documents.
        Each document dict should ideally contain:
        - 'text' (or 'content'): content of the document for BM25 calculation.
        - 'cosine_score' (or 'score'): the initial vector search score (defaults to 0.0 if missing).
        - 'metadata' (dict): containing date info under keys like 'date', 'created_at', 'timestamp'.
        
        Args:
            documents: List of document dicts.
            query: The search query.
            current_date_str: Optional ISO format current date (e.g. '2026-07-01').
                              If not provided, uses datetime.utcnow().date().
                              
        Returns:
            A new list of documents sorted in descending order of hybrid_score.
            Each document will have extra fields: 'cosine_score', 'bm25_score', 'freshness_score', 'hybrid_score'.
        """
        if not documents:
            return []

        # Parse current date
        if current_date_str:
            parsed_current = self._parse_date(current_date_str)
            current_dt = parsed_current if parsed_current else date(2026, 7, 1)
        else:
            current_dt = date(2026, 7, 1) # Fallback to context current time date

        # 1. Extract texts and initialize BM25
        corpus = []
        for doc in documents:
            text = doc.get("text") or doc.get("content") or ""
            corpus.append(text)
            
        bm25_calc = BM25Calculator(corpus, k1=self.k1, b=self.b)
        
        # Tokenize query for BM25
        query_terms = bm25_calc._tokenize(query)
        
        # Compute BM25 raw scores
        raw_bm25_scores = []
        for i in range(len(documents)):
            score = bm25_calc.get_score(i, query_terms)
            raw_bm25_scores.append(score)
            
        # Normalize BM25 scores to [0, 1] range
        min_bm25 = min(raw_bm25_scores) if raw_bm25_scores else 0.0
        max_bm25 = max(raw_bm25_scores) if raw_bm25_scores else 0.0
        bm25_range = max_bm25 - min_bm25
        
        normalized_bm25_scores = []
        for score in raw_bm25_scores:
            if bm25_range > 0:
                normalized_score = (score - min_bm25) / bm25_range
            else:
                # If all docs have the same BM25 score, set to 1.0 if score > 0 else 0.0
                normalized_score = 1.0 if score > 0 else 0.0
            normalized_bm25_scores.append(normalized_score)

        # 2. Process each document and calculate hybrid score
        reranked_docs = []
        for idx, doc in enumerate(documents):
            # Copy to avoid side-effects on original document list
            doc_copy = dict(doc)
            
            # Extract Cosine Score
            cosine_val = doc_copy.get("cosine_score")
            if cosine_val is None:
                cosine_val = doc_copy.get("score", 0.0)
            try:
                cosine_score = float(cosine_val)
            except (ValueError, TypeError):
                cosine_score = 0.0
                
            # Extract Date for Freshness
            metadata = doc_copy.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
                
            # Find date field
            doc_date_val = None
            for key in ["date", "created_at", "timestamp", "publish_date"]:
                if key in metadata:
                    doc_date_val = metadata[key]
                    break
            if not doc_date_val:
                # Fallback to check root keys of doc
                for key in ["date", "created_at", "timestamp", "publish_date"]:
                    if key in doc_copy:
                        doc_date_val = doc_copy[key]
                        break
                        
            parsed_doc_date = self._parse_date(doc_date_val)
            freshness_score = self._calculate_freshness_score(parsed_doc_date, current_dt)
            bm25_score = normalized_bm25_scores[idx]
            
            # Hybrid scoring formula
            hybrid_score = 0.6 * cosine_score + 0.3 * bm25_score + 0.1 * freshness_score
            
            # Update fields in the copied document
            doc_copy["cosine_score"] = cosine_score
            doc_copy["bm25_score"] = bm25_score
            doc_copy["raw_bm25_score"] = raw_bm25_scores[idx]
            doc_copy["freshness_score"] = freshness_score
            doc_copy["hybrid_score"] = hybrid_score
            
            reranked_docs.append(doc_copy)
            
        # Sort documents by hybrid score in descending order
        reranked_docs.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return reranked_docs

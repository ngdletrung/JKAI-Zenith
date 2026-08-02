from __future__ import annotations

import os
import sys
import re
import json
import asyncio
import time
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List, Dict
import concurrent.futures
import httpx

# Đảm bảo nạp được các module từ core (Đi lên 5 cấp từ intelligence/skills/RESEARCH/SEARCH_WEB_GLOBAL/logic.py)
SYS_PATH_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if SYS_PATH_DIR not in sys.path:
    sys.path.append(SYS_PATH_DIR)

from core.utils.embed import embed
from core.qdrant_client import qdrant_client
from core.utils.engine import engine
from core.utils import report_formatter as rf

# ──────────────────────────────────────────────────────────────────
# 📋  STRUCTURED LOGGER
# ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("JKAI.Search")

# ──────────────────────────────────────────────────────────────────
# ⚡  IN-MEMORY SMART CACHE  (TTL + LRU-eviction)
# ──────────────────────────────────────────────────────────────────
@dataclass
class _CacheEntry:
    value: Any
    expires_at: float
    last_accessed: float = field(default_factory=time.time)

class SmartCache:
    """Thread-safe TTL cache ket hop LRU de giu cac entries duoc truy cap gan nhat."""
    def __init__(self, max_size: int = 512, default_ttl: int = 300):
        self._store: dict[str, _CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl

    @staticmethod
    def _key(raw: str) -> str:
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, raw_key: str) -> Optional[Any]:
        key = self._key(raw_key)
        entry = self._store.get(key)
        if entry:
            if time.time() < entry.expires_at:
                entry.last_accessed = time.time()
                return entry.value
            else:
                try:
                    del self._store[key]
                except KeyError:
                    pass
        return None

    def set(self, raw_key: str, value: Any, ttl: int | None = None) -> None:
        key = self._key(raw_key)
        now = time.time()
        
        expired_keys = [k for k, v in self._store.items() if now >= v.expires_at]
        for k in expired_keys:
            try:
                del self._store[k]
            except KeyError:
                pass
            
        if len(self._store) >= self.max_size:
            sorted_entries = sorted(self._store.items(), key=lambda x: (x[1].last_accessed, x[1].expires_at))
            for k, _ in sorted_entries[: max(1, self.max_size // 10)]:
                try:
                    del self._store[k]
                except KeyError:
                    pass
                
        self._store[key] = _CacheEntry(
            value=value, 
            expires_at=now + (ttl or self.default_ttl),
            last_accessed=now
        )

_cache = SmartCache(max_size=512, default_ttl=300)

# ──────────────────────────────────────────────────────────────────
# 🔌  CIRCUIT BREAKER
# ──────────────────────────────────────────────────────────────────
class CircuitState(Enum):
    CLOSED = "CLOSED"       # hoạt động bình thường
    OPEN = "OPEN"           # đang chặn request
    HALF_OPEN = "HALF_OPEN" # thử phục hồi

@dataclass
class CircuitBreaker:
    """Tự động ngắt khi API liên tục thất bại."""
    name: str
    fail_threshold: int = 5
    recovery_timeout: int = 60  # giây

    _failures: int = field(default=0, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _opened_at: float = field(default=0.0, init=False)

    @property
    def is_open(self) -> bool:
        if self._state == CircuitState.OPEN:
            if time.time() - self._opened_at > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                log.warning(f"[{self.name}] Circuit HALF-OPEN — đang thử phục hồi...")
                # [PROBE-ASSIST]: Khi HALF_OPEN, trigger probe async để cập nhật sức khỏe backend
                # Không await — chạy ngầm, không block request hiện tại
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_search_probe._probe_one(self.name.lower()))
                except RuntimeError:
                    pass  # Không có event loop đang chạy — bỏ qua
                return False
            return True
        return False

    def record_success(self):
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.fail_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            log.error(
                f"[{self.name}] Circuit OPEN sau {self._failures} lỗi liên tiếp. "
                f"Tạm ngưng {self.recovery_timeout}s."
            )

_cb_tavily = CircuitBreaker("Tavily", fail_threshold=4, recovery_timeout=60)
_cb_jina   = CircuitBreaker("Jina",   fail_threshold=3, recovery_timeout=45)

# ──────────────────────────────────────────────────────────────────
# 🩺  PROACTIVE BACKEND PROBE  (Agent-Reach pattern)
#     Chủ động kiểm tra sức khỏe backend TRƯỚC khi gọi.
#     CB = reactive (học từ lỗi runtime)
#     Probe = proactive (kiểm tra trước → skip ngay nếu DEAD)
# ──────────────────────────────────────────────────────────────────
class BackendStatus(Enum):
    UNKNOWN  = "unknown"   # Chưa probe lần nào
    OK       = "ok"        # Hoạt động tốt
    DEGRADED = "degraded"  # Có thể dùng nhưng chậm / rate-limited
    DEAD     = "dead"      # Không dùng được

@dataclass
class BackendHealth:
    name: str
    status: BackendStatus = BackendStatus.UNKNOWN
    latency_ms: float = 0.0
    last_probe: float = 0.0
    note: str = ""

class SearchBackendProbe:
    """
    Proactive health-check cho toàn bộ search backends.
    - probe_if_stale(name): Lazy probe — chỉ re-probe sau PROBE_INTERVAL giây.
    - probe_all(): Force probe tất cả song song.
    - doctor_report(): Báo cáo sức khỏe dạng text đẹp.
    """
    PROBE_INTERVAL = 300  # Re-probe mỗi 5 phút

    def __init__(self):
        self._health: dict[str, BackendHealth] = {
            "tavily":   BackendHealth("tavily"),
            "ddg":      BackendHealth("ddg"),
            "jina":     BackendHealth("jina"),
            "crawl4ai": BackendHealth("crawl4ai"),
        }
        self._probe_lock: asyncio.Lock | None = None  # Lazy-init trong async context
        self._probing = False

    def _get_lock(self) -> asyncio.Lock:
        """Khởi tạo Lock trong đúng event loop (tránh lỗi cross-loop)."""
        if self._probe_lock is None:
            self._probe_lock = asyncio.Lock()
        return self._probe_lock

    def is_stale(self, name: str) -> bool:
        """True nếu chưa probe hoặc đã quá PROBE_INTERVAL."""
        h = self._health.get(name)
        if not h:
            return False
        return (h.status == BackendStatus.UNKNOWN or
                time.time() - h.last_probe > self.PROBE_INTERVAL)

    def get_status(self, name: str) -> BackendStatus:
        return self._health.get(name, BackendHealth(name)).status

    async def probe_if_stale(self, name: str) -> BackendHealth:
        """Probe backend nếu stale. Không block nếu không cần."""
        if self.is_stale(name):
            await self._probe_one(name)
        return self._health.get(name, BackendHealth(name))

    async def probe_all(self) -> dict[str, BackendHealth]:
        """Probe toàn bộ backends đồng thời. Dùng cho doctor report."""
        probe_tasks = [
            self._probe_one("tavily"),
            self._probe_one("ddg"),
            self._probe_one("jina"),
            self._probe_one("crawl4ai"),
        ]
        await asyncio.gather(*probe_tasks, return_exceptions=True)
        return self._health

    async def _probe_one(self, name: str):
        """Probe một backend cụ thể và cập nhật _health."""
        probe_fn = {
            "tavily":   self._probe_tavily,
            "ddg":      self._probe_ddg,
            "jina":     self._probe_jina,
            "crawl4ai": self._probe_crawl4ai,
        }.get(name)
        if not probe_fn:
            return
        try:
            result = await probe_fn()
            self._health[name] = result
        except Exception as e:
            self._health[name] = BackendHealth(name, BackendStatus.DEAD, 0, time.time(), f"Probe exception: {e}")

    async def _probe_tavily(self) -> BackendHealth:
        """Kiểm tra Tavily API: validate key + thử request nhẹ."""
        t0 = time.time()
        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            return BackendHealth("tavily", BackendStatus.DEAD, 0, time.time(),
                                 "TAVILY_API_KEY chưa được cấu hình")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": api_key, "query": "health check", "max_results": 1}
                )
            ms = (time.time() - t0) * 1000
            if resp.status_code == 200:
                return BackendHealth("tavily", BackendStatus.OK, ms, time.time(), f"API online ({ms:.0f}ms)")
            elif resp.status_code == 429:
                return BackendHealth("tavily", BackendStatus.DEGRADED, ms, time.time(), "Rate limit (429) — dùng được nhưng chậm")
            elif resp.status_code == 401:
                return BackendHealth("tavily", BackendStatus.DEAD, ms, time.time(), "API key không hợp lệ (401)")
            else:
                return BackendHealth("tavily", BackendStatus.DEGRADED, ms, time.time(), f"HTTP {resp.status_code}")
        except Exception as e:
            ms = (time.time() - t0) * 1000
            return BackendHealth("tavily", BackendStatus.DEAD, ms, time.time(), f"Không kết nối được: {e}")

    async def _probe_ddg(self) -> BackendHealth:
        """Kiểm tra DuckDuckGo library sẵn sàng và có thể tìm kiếm."""
        t0 = time.time()
        try:
            from duckduckgo_search import DDGS
            with DDGS(timeout=5) as ddgs:
                r = list(ddgs.text("python", max_results=1))
            ms = (time.time() - t0) * 1000
            if r:
                return BackendHealth("ddg", BackendStatus.OK, ms, time.time(), f"Phản hồi bình thường ({ms:.0f}ms)")
            return BackendHealth("ddg", BackendStatus.DEGRADED, ms, time.time(), "Không có kết quả probe")
        except ImportError:
            return BackendHealth("ddg", BackendStatus.DEAD, 0, time.time(), "duckduckgo_search chưa được cài")
        except Exception as e:
            ms = (time.time() - t0) * 1000
            return BackendHealth("ddg", BackendStatus.DEAD, ms, time.time(), str(e))

    async def _probe_jina(self) -> BackendHealth:
        """Kiểm tra Jina Reader (r.jina.ai) bằng cách đọc example.com."""
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    "https://r.jina.ai/https://example.com",
                    headers={"Accept": "text/plain"},
                )
            ms = (time.time() - t0) * 1000
            if resp.status_code == 200 and len(resp.text) > 30:
                return BackendHealth("jina", BackendStatus.OK, ms, time.time(), f"Phản hồi bình thường ({ms:.0f}ms)")
            return BackendHealth("jina", BackendStatus.DEGRADED, ms, time.time(), f"HTTP {resp.status_code}")
        except Exception as e:
            ms = (time.time() - t0) * 1000
            return BackendHealth("jina", BackendStatus.DEAD, ms, time.time(), str(e))

    async def _probe_crawl4ai(self) -> BackendHealth:
        """Kiểm tra Crawl4AI local service qua /health endpoint."""
        t0 = time.time()
        try:
            crawl4ai_url = os.getenv("CRAWL4AI_URL", "http://localhost:11235")
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{crawl4ai_url}/health")
            ms = (time.time() - t0) * 1000
            if resp.status_code == 200:
                return BackendHealth("crawl4ai", BackendStatus.OK, ms, time.time(), f"Service online ({ms:.0f}ms)")
            return BackendHealth("crawl4ai", BackendStatus.DEAD, ms, time.time(), f"HTTP {resp.status_code}")
        except Exception as e:
            ms = (time.time() - t0) * 1000
            return BackendHealth("crawl4ai", BackendStatus.DEAD, ms, time.time(), f"Service offline")

    def doctor_report(self) -> str:
        """Báo cáo sức khỏe toàn bộ backends — format đẹp cho Mission Log."""
        ICONS = {
            BackendStatus.OK:       "✅",
            BackendStatus.DEGRADED: "⚠️",
            BackendStatus.DEAD:     "🔴",
            BackendStatus.UNKNOWN:  "❓",
        }
        rows = []
        for name, h in self._health.items():
            icon = ICONS[h.status]
            latency = f"{h.latency_ms:.0f}ms" if h.latency_ms > 0 else "N/A"
            rows.append([name.upper(), f"{icon} {h.status.value}", latency])
        return rf.build([
            rf.header("SEARCH-DOCTOR", "Trang thai cac Backend Tim kiem"),
            rf.table(["Backend", "Status", "Latency"], rows),
        ])

# [SINGLETON]: Dùng chung toàn bộ process — probe state được giữ giữa các request
_search_probe = SearchBackendProbe()


# ──────────────────────────────────────────────────────────────────
# 🔄  RETRY  với Exponential Backoff
# ──────────────────────────────────────────────────────────────────
async def _retry_async(coro_fn, retries: int = 3, base_delay: float = 1.0):
    """Chạy lại coro với backoff mũ. Ném lỗi cuối nếu vẫn thất bại."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return await coro_fn()
        except Exception as exc:
            last_exc = exc
            wait = base_delay * (2 ** attempt)
            log.warning(f"Lần {attempt+1}/{retries} thất bại ({exc}). Thử lại sau {wait:.1f}s...")
            await asyncio.sleep(wait)
    raise last_exc  # type: ignore

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".obsidian", 
    "archive", "00_Import", "quarantine", "temp", ".venv", "env"
}

# ──────────────────────────────────────────────────────────────────
# 🧮  BM25 ADVANCED PHRASE-AWARE SCORING (Vietnamese & Slang Native)
# ──────────────────────────────────────────────────────────────────
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

def _bm25_score(query: str, text: str, k1: float = 1.5, b: float = 0.75) -> float:
    """
    Advanced Phrase-Aware BM25 for a single document score against query.
    Extracts contiguous n-grams (up to length 3) to preserve Vietnamese phrases and slang.
    """
    if not text or not query:
        return 0.0
        
    clean_text = _normalize_text(text)
    clean_query = _normalize_text(query)
    
    words_d = clean_text.split()
    doc_len = len(words_d)
    if doc_len == 0:
        return 0.0
        
    avg_len = 300.0  # Estimated average length
    
    query_terms = list(set(_extract_ngrams(clean_query, max_n=3)))
    padded_chunk = f" {clean_text} "
    score = 0.0
    
    for term in query_terms:
        padded_term = f" {term} "
        tf = padded_chunk.count(padded_term)
        if tf == 0:
            continue
            
        term_word_count = len(term.split())
        phrase_boost = 1.0
        if term_word_count == 2:
            phrase_boost = 1.5
        elif term_word_count >= 3:
            phrase_boost = 2.0
            
        # Simplified IDF for single document: longer queries with rare phrases get ranked beautifully
        idf_val = 1.0
        denominator = tf + k1 * (1.0 - b + b * (doc_len / avg_len))
        score += phrase_boost * idf_val * (tf * (k1 + 1.0)) / denominator
        
    return score


# =================================================================
# 🔍 JKAI ZENITH: LOGIC SIÊU TÌM KIẾM (SUPER SEARCH) v2.0
# =================================================================

def kham_pha_du_an(start_path: str = ".") -> dict:
    """Tự thám hiểm cấu trúc thư mục của dự án (Tối ưu hóa bộ nhớ với Generator)."""
    log.info(f"🗺️ [JKAI-EXPLORE] Scouting project structure from: {start_path}")
    structure = []
    start_p = Path(start_path)
    
    # Giới hạn quét tối đa để tránh tràn bộ nhớ
    max_lines = 200
    
    for root, dirs, files in os.walk(start_p):
        # Loại bỏ các thư mục rác ngay tại chỗ để os.walk không tốn công duyệt sâu
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        level = Path(root).relative_to(start_p).parts
        indent = ' ' * 4 * len(level)
        structure.append(f"{indent}{os.path.basename(root)}/")
        
        if len(structure) >= max_lines: 
            break
        
        sub_indent = ' ' * 4 * (len(level) + 1)
        for f in files:
            structure.append(f"{sub_indent}{f}")
            if len(structure) >= max_lines: 
                break

    return {"status": "success", "structure": "\n".join(structure[:max_lines])}

async def truy_luc_tri_thuc(query: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    """
    Truy xuất RAG từ Qdrant, sau đó rerank bằng BM25-lite.
    Kết quả được cache để tránh gọi lại embedding trùng lặp.
    """
    cache_key = f"rag:{query}"
    if cached := _cache.get(cache_key):
        log.info(f"[RAG-CACHE HIT] query='{query}'")
        return cached

    engine.publish_mission_log(
        "BRAIN_QUERY",
        f"🧠 [NEURAL-SEARCH]: Truy xuất tri thức cho: `{query}`",
        task_id, trace_id,
    )

    try:
        query_vector = await embed.get_embedding_async(query)
        if not query_vector:
            return {"status": "error", "msg": "Không tạo được embedding cho truy vấn."}

        # Tìm kiếm trong Qdrant
        results = await qdrant_client.search_similar(query_vector, limit=6)
        if not results:
            return {"status": "success", "results": "Không tìm thấy tri thức tương ứng trong bộ nhớ dài hạn."}

        # ── Reranking bằng BM25-lite ─────────────────────────────
        results = sorted(
            results,
            key=lambda r: _bm25_score(query, r.get("text", "")),
            reverse=True,
        )[:3]

        formatted_results = "\n\n".join([
            f"📄 [Nguồn: {r.get('metadata', {}).get('source', 'Unknown')}]:\n{r.get('text')}" 
            for r in results
        ])
        
        out = {"status": "success", "results": formatted_results}
        _cache.set(cache_key, out, ttl=300)
        return out

    except Exception as e:
        log.exception("[RAG] Lỗi truy lục")
        return {"status": "error", "msg": str(e)}

def split_long_text(text: str, max_len: int = 1500, overlap: int = 150) -> List[str]:
    """
    Phan ra cac khoi van ban cuc ky dai de dam bao moi khoi con luon nho hon hoac bang max_len.
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


class FactVerifier:
    """
    Bo kiem chung su that (Consensus-based Technical Fact Verifier) de phat hien xung dot ve phien ban, port, cau hinh.
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


def _append_citations_footer(text: str, sources: List[Dict]) -> str:
    """
    Trinh bay cac nguon tin theo phong cach Perplexity thieu Master.
    """
    if not sources:
        return text
        
    footer = "\n\n---\n### 📄 Nguồn trích dẫn thông tin:\n"
    seen_urls = set()
    idx = 1
    for s in sources:
        url = s.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = s.get("title") or "Nguồn tin"
        if len(title) > 60:
            title = title[:57] + "..."
        date_str = f" *({s.get('date')})*" if s.get('date') else ""
        footer += f"- **[{idx}]** [{title}]({url}){date_str}\n"
        idx += 1
        
    return text.strip() + footer


def _append_verification_footer(ranked_content: str, verification_data: dict) -> str:
    """
    Trinh bay cac canh bao mau thuan ky thuat neu co thieu Master.
    """
    warnings = verification_data.get("contradiction_warnings", [])
    if not warnings:
        return ranked_content
        
    footer = "\n\n---\n⚠️ **CẢNH BÁO MÂU THUẪN KỸ THUẬT PHÁT HIỆN TỪ CÁC NGUỒN TIN (FactVerifier)**:\n"
    for w in warnings[:5]:
        footer += f"- {w}\n"
    return ranked_content + footer


def chunk_and_rank_segments(query: str, raw_text: str, chunk_size: int = 800, max_segments: int = 5) -> str:
    """
    Slices raw search result text into 500-1000 character chunks,
    ranks them by advanced Phrase-Aware Local-Corpus BM25 (BM25-CP) against the query,
    and returns only the top 3-5 clean segments (max 2k tokens/approx 8k chars).
    """
    if not raw_text:
        return ""
    
    # 1. Slice raw_text into chunks (between 500 and 1000 chars)
    paragraphs = re.split(r'\n+', raw_text)
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) > chunk_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            # Dung split_long_text de phan cap thong minh ho, tranh chia doi tu vung
            sub_p_list = split_long_text(para, chunk_size, 100)
            chunks.extend(sub_p_list)
        elif current_len + len(para) > chunk_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [para]
            current_len = len(para)
        else:
            current_chunk.append(para)
            current_len += len(para) + 1
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    chunks = [c for c in chunks if c.strip()]
    if not chunks:
        return ""
        
    N = len(chunks)
    k1, b = 1.5, 0.75
    
    # Pre-normalize all chunks
    clean_chunks = [_normalize_text(c) for c in chunks]
    chunk_lens = [len(c.split()) for c in clean_chunks]
    avgdl = sum(chunk_lens) / N if N > 0 else 1.0
    if avgdl == 0:
        avgdl = 1.0
        
    clean_query = _normalize_text(query)
    query_terms = list(set(_extract_ngrams(clean_query, max_n=3)))
    
    # Calculate n(t) - number of chunks containing each query term
    n_t = {}
    for term in query_terms:
        count = 0
        padded_term = f" {term} "
        for clean_chunk in clean_chunks:
            padded_chunk = f" {clean_chunk} "
            if padded_term in padded_chunk:
                count += 1
        n_t[term] = count
        
    # Calculate IDF for each query term with smoothing
    import math
    idf = {}
    for term in query_terms:
        count = n_t[term]
        val = (N - count + 0.5) / (count + 0.5)
        idf[term] = math.log(max(val, 0.0001) + 1.0)
        
    # 2. Rank chunks using advanced BM25-CP thưa Master
    chunk_scores = []
    for idx, clean_chunk in enumerate(clean_chunks):
        doc_len = chunk_lens[idx]
        padded_chunk = f" {clean_chunk} "
        score = 0.0
        for term in query_terms:
            padded_term = f" {term} "
            tf = padded_chunk.count(padded_term)
            if tf == 0:
                continue
                
            term_word_count = len(term.split())
            phrase_boost = 1.0
            if term_word_count == 2:
                phrase_boost = 1.5
            elif term_word_count >= 3:
                phrase_boost = 2.0
                
            term_idf = idf[term]
            denominator = tf + k1 * (1.0 - b + b * (doc_len / avgdl))
            score += phrase_boost * term_idf * (tf * (k1 + 1.0)) / denominator
            
        chunk_scores.append((score, idx))
        
    # Sort chunks by BM25 score
    chunk_scores.sort(key=lambda x: x[0], reverse=True)
    
    # Pick top 3-5 clean segments (max_segments)
    top_indices = [idx for _, idx in chunk_scores[:max_segments]]
    top_indices.sort() # Keep sequential reading order
    
    selected_chunks = [chunks[idx] for idx in top_indices]
    return "\n\n---\n\n".join(selected_chunks)
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
                import ast
                parsed = ast.literal_eval(query_str)
                return _clean_query(parsed)
            except Exception:
                try:
                    parsed = json.loads(query_str)
                    return _clean_query(parsed)
                except Exception:
                    pass
        return query_str
    return str(query)

async def SEARCH_WEB_GLOBAL(
    query: str,
    task_id: str = "sys",
    trace_id: str = "system",
    search_depth: str = "advanced",
    **kwargs,
) -> dict:
    """
    Sequential Cascading Search (Tavily -> DuckDuckGo -> Browser -> Cloud LLM)
    Returns data from the first successful source and stops further search.
    """
    query = _clean_query(query)
    
    # 🕒 [SEARCH-FRESHNESS]: Advanced dynamic temporal enhancement thưa Master
    import datetime
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    current_day = now.day
    
    query_lower = query.lower()
    time_appended = False
    
    # 1. "hôm nay" / "today" -> append exact date DD/MM/YYYY
    if "hôm nay" in query_lower or "today" in query_lower:
        exact_date = f"{current_day:02d}/{current_month:02d}/{current_year}"
        if exact_date not in query:
            query = f"{query} {exact_date}"
            time_appended = True
            log.info(f"🕒 [FRESHNESS-BOOST]: Appended today's exact date. New query: '{query}'")
            
    # 2. "tháng trước" / "last month" -> append previous month "tháng MM/YYYY"
    elif "tháng trước" in query_lower or "last month" in query_lower:
        prev_month = current_month - 1
        prev_year = current_year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1
        prev_month_str = f"tháng {prev_month:02d}/{prev_year}"
        if prev_month_str not in query_lower:
            query = f"{query} {prev_month_str}"
            time_appended = True
            log.info(f"🕒 [FRESHNESS-BOOST]: Appended previous month. New query: '{query}'")
            
    # 3. "tháng này" / "this month" / "tuần này" / "this week" -> append current month "tháng MM/YYYY"
    elif any(kw in query_lower for kw in ["tháng này", "this month", "tuần này", "this week"]):
        month_str = f"tháng {current_month:02d}/{current_year}"
        if month_str not in query_lower:
            query = f"{query} {month_str}"
            time_appended = True
            log.info(f"🕒 [FRESHNESS-BOOST]: Appended current month. New query: '{query}'")

    # 4. Fallback: general news/latest queries -> append current year if no 4-digit year exists
    if not time_appended:
        temporal_patterns = r"(?<!\w)(tin tức|thời sự|diễn biến|mới nhất|tình hình|news|latest|breaking)(?!\w)"
        if re.search(temporal_patterns, query_lower):
            if not re.search(r"\b\d{4}\b", query):
                query = f"{query} {current_year}"
                log.info(f"🕒 [FRESHNESS-BOOST]: Fallback appended current year. New query: '{query}'")
    cache_key = f"web:{query}:{search_depth}"
    if cached := _cache.get(cache_key):
        engine.publish_mission_log("WEB_CACHE", f"WEB-CACHE: Using cached results for {query}", task_id, trace_id)
        return cached

    # [PROBE-GATE]: Lazy probe — kiểm tra sức khỏe backend trước khi gọi.
    # Nếu backend đã được probe gần đây (< 5 phút), dùng kết quả cũ ngay — không có delay.
    tavily_health, ddg_health = await asyncio.gather(
        _search_probe.probe_if_stale("tavily"),
        _search_probe.probe_if_stale("ddg"),
        return_exceptions=True
    )
    # Fallback an toàn nếu probe bị lỗi
    if not isinstance(tavily_health, BackendHealth):
        tavily_health = BackendHealth("tavily", BackendStatus.UNKNOWN)
    if not isinstance(ddg_health, BackendHealth):
        ddg_health = BackendHealth("ddg", BackendStatus.UNKNOWN)

    # Phase 1: Tavily API
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    # [PROBE-GATE]: Skip ngay nếu probe xác nhận DEAD — không cần chờ timeout
    tavily_probe_ok = tavily_health.status != BackendStatus.DEAD
    if tavily_api_key and tavily_probe_ok and not _cb_tavily.is_open:
        engine.publish_mission_log(
            "WEB_SEARCH", f"TAVILY: Initiating global web search for {query}", task_id, trace_id
        )
        try:
            async def _do_search():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={"api_key": tavily_api_key, "query": query, "search_depth": search_depth},
                    )
                    try:
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as e:
                        log.error(f"Tavily API failed with status {resp.status_code}: {resp.text}")
                        engine.publish_mission_log("WEB_ERR", f"TAVILY-HTTP-ERR: {resp.status_code} - {resp.text}", task_id, trace_id)
                        raise e
                    return resp.json()

            data = await _retry_async(_do_search, retries=2, base_delay=1.0)
            _cb_tavily.record_success()

            results = data.get("results", [])
            if results:
                log_msg = f"TAVILY-FOUND: Discovered {len(results)} results.\n"
                for i, r in enumerate(results[:3], 1):
                    log_msg += f"{i}. {r.get('title', '')[:60]} ({r.get('url', '')})\n"
                engine.publish_mission_log("WEB_DATA", log_msg, task_id, trace_id)

                # Chay FactVerifier de kiem tra thong tin ky thuat
                candidates = []
                sources = []
                combined_raw_parts = []
                for r in results:
                    url = r.get("url", "https://tavily.com")
                    content = r.get("content", "")
                    api_date = r.get("published_date") or r.get("date")
                    
                    extracted_date = extract_date_info(content, url, api_date)
                    date_prefix = f"[Ngày {extracted_date}] " if extracted_date else ""
                    
                    paragraphs = content.split("\n")
                    paragraphs_with_date = []
                    for p in paragraphs:
                        if p.strip():
                            p_strip = p.strip()
                            if date_prefix and not p_strip.startswith("[Ngày"):
                                paragraphs_with_date.append(f"{date_prefix}{p_strip}")
                            else:
                                paragraphs_with_date.append(p_strip)
                    
                    processed_content = "\n".join(paragraphs_with_date)
                    candidates.append({"url": url, "content": processed_content})
                    sources.append({"title": r.get("title"), "url": url, "date": extracted_date})
                    combined_raw_parts.append(f"Source: {r.get('title')}\nURL: {url}\nContent: {processed_content}")
                
                verifier = FactVerifier()
                v_data = verifier.verify_and_detect_contradictions(candidates)
                if v_data["contradiction_warnings"]:
                    warn_msg = "⚠️ [FACT-CONFLICTS] Phat hien mau thuan ky thuat:\n" + "\n".join(v_data["contradiction_warnings"][:3])
                    engine.publish_mission_log("WEB_WARN", warn_msg, task_id, trace_id)

                combined_raw = "\n\n".join(combined_raw_parts)
                ranked_content = chunk_and_rank_segments(query, combined_raw)
                
                # Append citations va verification warnings
                ranked_content = _append_citations_footer(ranked_content, sources)
                ranked_content = _append_verification_footer(ranked_content, v_data)
                
                data["results"] = [{
                    "title": "Zenith Ranked Segments",
                    "url": "https://tavily-ranked.internal",
                    "content": ranked_content
                }]
                data["answer"] = ranked_content
                _cache.set(cache_key, data, ttl=600)
                return data
            else:
                engine.publish_mission_log("WEB_WARN", f"TAVILY-EMPTY: No results for {query}", task_id, trace_id)
                _cb_tavily.record_failure()
        except Exception as e:
            _cb_tavily.record_failure()
            engine.publish_mission_log("WEB_ERR", f"TAVILY-FAIL: {e} - cascading to DuckDuckGo...", task_id, trace_id)
            log.error(f"Tavily search failed: {e}")
    else:
        reason_parts = []
        if not tavily_api_key:
            reason_parts.append("TAVILY_API_KEY missing")
        elif not tavily_probe_ok:
            reason_parts.append(f"Probe={tavily_health.status.value} ({tavily_health.note})")
        elif _cb_tavily.is_open:
            reason_parts.append("Circuit Open")
        reason = " | ".join(reason_parts) or "Unknown"
        engine.publish_mission_log("WEB_WARN", f"TAVILY-SKIP: {reason} - cascading to DuckDuckGo...", task_id, trace_id)

    # Phase 2: DuckDuckGo Native (via DDGS library)
    # [PROBE-GATE]: Skip DDG nếu probe xác nhận không dùng được (package không cài / bị chặn)
    if ddg_health.status == BackendStatus.DEAD:
        engine.publish_mission_log("WEB_WARN", f"DDG-SKIP: Probe báo DEAD ({ddg_health.note}) - cascading to Browser...", task_id, trace_id)
    else:
        engine.publish_mission_log("WEB_SEARCH", f"DUCKDUCKGO: Cascading to DDG search for {query}", task_id, trace_id)
    if ddg_health.status != BackendStatus.DEAD:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_results = [r for r in ddgs.text(query, max_results=5)]

            if ddg_results:
                log_msg = f"DUCKDUCKGO-FOUND: Discovered {len(ddg_results)} results.\n"
                for i, r in enumerate(ddg_results[:3], 1):
                    log_msg += f"{i}. {r.get('title', '')[:60]} ({r.get('href', '')})\n"
                engine.publish_mission_log("WEB_DATA", log_msg, task_id, trace_id)

                # Chay FactVerifier de kiem tra thong tin ky thuat
                candidates = []
                sources = []
                combined_raw_parts = []
                for r in ddg_results:
                    if not r.get('href'):
                        continue
                    url = r.get("href")
                    content = r.get("body", "")
                    api_date = r.get("published_date") or r.get("date")

                    extracted_date = extract_date_info(content, url, api_date)
                    date_prefix = f"[Ngày {extracted_date}] " if extracted_date else ""

                    # Prepend date to paragraphs
                    paragraphs = content.split("\n")
                    paragraphs_with_date = []
                    for p in paragraphs:
                        if p.strip():
                            p_strip = p.strip()
                            if date_prefix and not p_strip.startswith("[Ngày"):
                                paragraphs_with_date.append(f"{date_prefix}{p_strip}")
                            else:
                                paragraphs_with_date.append(p_strip)

                    processed_content = "\n".join(paragraphs_with_date)
                    candidates.append({"url": url, "content": processed_content})
                    sources.append({"title": r.get("title"), "url": url, "date": extracted_date})
                    combined_raw_parts.append(f"Source: {r.get('title')}\nURL: {url}\nContent: {processed_content}")

                verifier = FactVerifier()
                v_data = verifier.verify_and_detect_contradictions(candidates)
                if v_data["contradiction_warnings"]:
                    warn_msg = "⚠️ [FACT-CONFLICTS] Phat hien mau thuan ky thuat:\n" + "\n".join(v_data["contradiction_warnings"][:3])
                    engine.publish_mission_log("WEB_WARN", warn_msg, task_id, trace_id)

                combined_raw = "\n\n".join(combined_raw_parts)
                ranked_content = chunk_and_rank_segments(query, combined_raw)

                # Append citations va verification warnings
                ranked_content = _append_citations_footer(ranked_content, sources)
                ranked_content = _append_verification_footer(ranked_content, v_data)

                data = {
                    "status": "success",
                    "results": [{
                        "title": "Zenith Ranked Segments (DuckDuckGo)",
                        "url": "https://ddg-ranked.internal",
                        "content": ranked_content
                    }],
                    "answer": ranked_content
                }
                _cache.set(cache_key, data, ttl=600)
                return data
            else:
                engine.publish_mission_log("WEB_WARN", f"DUCKDUCKGO-EMPTY: No results for {query}", task_id, trace_id)
        except Exception as e:
            engine.publish_mission_log("WEB_ERR", f"DUCKDUCKGO-FAIL: {e} - cascading to Browser...", task_id, trace_id)
            log.error(f"DuckDuckGo search failed: {e}")

    # Phase 3: Browser Search (DuckDuckGo HTML Scraping)
    engine.publish_mission_log("WEB_SEARCH", f"BROWSER-SEARCH: Cascading to Browser Search for {query}", task_id, trace_id)
    try:
        browser_data = await _run_browser_search(query, task_id, trace_id)
        if browser_data.get("status") == "success" and browser_data.get("results"):
            _cache.set(cache_key, browser_data, ttl=600)
            return browser_data
        else:
            engine.publish_mission_log("WEB_WARN", f"BROWSER-EMPTY: Browser search returned empty results", task_id, trace_id)
    except Exception as e:
        engine.publish_mission_log("WEB_ERR", f"BROWSER-FAIL: {e} - cascading to Cloud LLM...", task_id, trace_id)
        log.error(f"Browser fallback failed: {e}")

    # Phase 4: Cloud LLM Search
    engine.publish_mission_log("WEB_SEARCH", f"CLOUD-LLM: Cascading to Cloud LLM search for {query}", task_id, trace_id)
    try:
        prompt = (
            f"Vui lòng tìm kiếm trên Internet thông tin mới nhất về: '{query}'. "
            "Trả lời ngắn gọn, chi tiết và chứa các thông tin thời sự/thực tế."
        )
        answer = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="PLANNER",
            task_id=f"cloud_search_{task_id}",
            trace_id=trace_id
        )
        if isinstance(answer, dict) and "answer" in answer:
            ans_text = answer["answer"]
        else:
            ans_text = str(answer)

        if ans_text and ans_text.strip():
            engine.publish_mission_log("WEB_DATA", f"CLOUD-LLM-FOUND: Successfully synthesized search content.", task_id, trace_id)
            data = {
                "status": "success",
                "results": [{
                    "title": "Cloud LLM Search Results",
                    "url": "https://cloud-llm.internal",
                    "content": ans_text
                }],
                "answer": ans_text
            }
            _cache.set(cache_key, data, ttl=600)
            return data
        else:
            engine.publish_mission_log("WEB_WARN", f"CLOUD-LLM-EMPTY: Cloud LLM returned empty response", task_id, trace_id)
    except Exception as e:
        engine.publish_mission_log("WEB_ERR", f"CLOUD-LLM-FAIL: {e}", task_id, trace_id)
        log.error(f"Cloud LLM fallback failed: {e}")

    # Fallback absolute: All sources failed
    return {
        "status": "error",
        "msg": "All search sources (Tavily, DuckDuckGo, Browser, Cloud LLM) have failed or returned empty results."
    }

async def _run_browser_search(query: str, task_id: str, trace_id: str, cache_key: str = None) -> dict:
    """[BROWSER-SATELLITE]: Backup search via DuckDuckGo."""
    reason = "TAVILY_API_KEY missing" if not os.getenv("TAVILY_API_KEY") else "Circuit Open or Empty Result"
    engine.publish_mission_log("WEB_FALLBACK", f"BROWSER-SEARCH: Using DuckDuckGo via ai_browse (Reason: {reason})", task_id, trace_id)
    try:
        search_url = f"https://duckduckgo.com/html/?q={query}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{engine.executor_url}/call_tool",
                json={
                    "name": "ai_browse",
                    "args": {"url": search_url, "action": "extract_links"},
                    "task_id": task_id,
                    "trace_id": trace_id
                }
            )
            if resp.status_code == 200:
                search_res = resp.json()
                if search_res.get("status") == "success":
                    links = search_res.get("output", [])[:5]
                    results = []
                    sources = []
                    for l in links:
                        if not l.get("href"):
                            continue
                        url = l.get("href")
                        extracted_date = extract_date_info("", url)
                        date_prefix = f" [Ngày {extracted_date}]" if extracted_date else ""
                        title = l.get("text", "Nguồn tin")
                        results.append({
                            "title": title + date_prefix,
                            "url": url,
                            "content": f"Vui lòng dùng ai_browse để đọc chi tiết.{date_prefix}"
                        })
                        sources.append({
                            "title": title,
                            "url": url,
                            "date": extracted_date
                        })
                    engine.publish_mission_log("WEB_DATA", f"BROWSER-FOUND: Discovered {len(results)} links from DuckDuckGo.", task_id, trace_id)
                    
                    # Chay FactVerifier va append citations
                    verifier = FactVerifier()
                    v_data = verifier.verify_and_detect_contradictions(results)
                    
                    ranked_content = "Danh sach cac lien ket tim thay tu trinh duyet:\n\n" + "\n".join([f"- [{r.get('title')}]({r.get('url')})" for r in results])
                    ranked_content = _append_citations_footer(ranked_content, sources)
                    ranked_content = _append_verification_footer(ranked_content, v_data)
                    
                    data = {
                        "status": "success", 
                        "results": results,
                        "answer": ranked_content
                    }
                    if cache_key: _cache.set(cache_key, data, ttl=600)
                    return data
        return {"status": "error", "msg": "Browser search failed or returned no results."}
    except Exception as e:
        engine.publish_mission_log("WEB_ERR", f"BROWSER-FAIL: {e}", task_id, trace_id)
        return {"status": "error", "msg": f"Browser fallback failed: {e}"}

async def search_web(query: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    """💎 [ALIAS]: Giao thức tìm kiếm web thấu thị."""
    return await SEARCH_WEB_GLOBAL(query, task_id, trace_id)

async def tim_kiem_web(query: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    """💎 [BACKWARD-COMPATIBILITY]: Tương thích ngược."""
    return await SEARCH_WEB_GLOBAL(query, task_id, trace_id)

def clear_navigation_noise(text: str) -> str:
    """
    🧹 [NEURAL-PURIFIER]: Loại bỏ toàn bộ nhiễu navigation bar, footer, link menu
    để giữ lại văn bản bài viết cốt lõi nhất.
    """
    if not text:
        return ""
    
    lines = text.splitlines()
    title = ""
    for line in lines[:5]:
        if line.lower().startswith("title:"):
            title = line[6:].strip()
            break
            
    if title:
        # Tìm các dòng H1 khớp với tiêu đề
        h1_indices = []
        clean_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
        for idx, line in enumerate(lines):
            line_strip = line.strip()
            if line_strip.startswith("# "):
                clean_line = re.sub(r'[^\w\s]', '', line_strip[2:].lower()).strip()
                # Kiểm tra khớp chính xác hoặc chứa nhau
                if clean_line == clean_title or clean_title in clean_line or clean_line in clean_title:
                    h1_indices.append(idx)
                    
        # Nếu xuất hiện H1 tiêu đề từ 2 lần trở lên, cắt bỏ phần menu điều hướng rác ở giữa
        if len(h1_indices) >= 2:
            lines = lines[h1_indices[-1]:]

    # Các cụm từ đặc trưng của navigation, menu, tags và footer
    skip_patterns = [
        r'vnn_source=',
        r'tag\d+\.html',
        r'#vnn_source',
        r'\/tag\w+',
        r'Luyện thi lớp 10',
        r'Tuyển sinh',
        r'Du học',
        r'Dân sinh',
        r'Giao thông',
        r'Tin nóng',
        r'Đô thị',
        r'Tài chính',
        r'Đầu tư',
        r'Thị trường',
        r'Doanh nhân',
        r'Tư vấn tài chính',
        r'Sắc màu Việt Nam',
        r'Chính sách phát triển',
        r'Đời sống tôn giáo',
        r'Điểm thi THPT',
        r'Điểm chuẩn CĐ-ĐH',
        r'Bình luận quốc tế',
        r'Thế giới đó đây',
        r'Việt Nam và thế giới',
        r'Bóng đá Việt Nam',
        r'Bóng đá quốc tế',
        r'Tin chuyển nhượng',
        r'Tường thuật trực tiếp',
        r'Video thể thao',
        r'Dữ liệu bóng đá',
        r'Các môn khác',
        r'Thế giới sao',
        r'Phim - Truyền hình',
        r'Mỹ thuật - Sân khấu',
        r'LHP châu Á Đà Nẵng',
        r'Chuyện của những dòng sông',
        r'Đi đâu chơi đi',
        r'Ăn Ăn Uống Uống',
        r'Ngủ Ngủ Nghỉ Nghỉ',
        r'Ngày mai tươi sáng',
        r'Liên hệ tòa soạn',
        r'Liên hệ quảng cáo',
        r'Tải ứng dụng',
        r'Độc giả gửi bài',
        r'Tuyển dụng',
        r'Lịch vạn niên',
        r'Chân dung',
        r'Hồ sơ vụ án',
        r'Tư vấn pháp luật',
        r'Ký sự pháp đình',
        r'Sau tay lái',
        r'Diễn đàn',
        r'Đánh giá xe',
        r'Giá xe',
        r'Dữ liệu xe',
        r'Cơ hội an cư',
        r'Đính chính',
        r'Multimedia',
        r'Bảo vệ người tiêu dùng',
        r'Thị trường tiêu dùng',
        r'Giảm nghèo bền vững',
        r'Nông thôn mới',
        r'Dân tộc thiểu số',
        r'Nội dung chuyên đề',
        # Thêm các patterns rác của VietnamNet
        r'vietnamnet\.vn/(chinh-tri|thoi-su|kinh-doanh|dan-toc-ton-giao|giao-duc|the-gioi|the-thao|van-hoa-giai-tri|doi-song|suc-khoe|cong-nghe|phap-luat|oto-xe-may|bat-dong-san|du-lich|ban-doc|podcast|premium|en)(/[^.\s]*)?(\?|\"|\'|\s|\)|$)',
        r'vnncdn\.net',
        r'vgcloud\.vn',
        r'Cơ quan chủ quản:',
        r'Số giấy phép:',
        r'Tổng biên tập:',
        r'Toà nhà Cục Viễn thông',
        r'Hotline:',
        r'support@tech\.vietnamnet\.vn',
        r'contact@vietnamnet\.vn',
        r'vietnamnet@vietnamnet\.vn',
        r'All rights reserved',
        r'Chỉ được phát hành lại thông tin',
        r'Theo dõi VietNamNet trên',
        r'Tải ứng dụng',
        r'Độc giả gửi bài',
        r'Lịch vạn niên',
        r'Xem các bài viết của tác giả',
        r'Chia sẻ bài viết lên',
        r'Sao chép liên kết',
        r'Lưu bài viết',
        r'Bình luận \!\[Image'
    ]
    
    skip_regex = re.compile('|'.join(skip_patterns), re.IGNORECASE)
    
    clean_lines = []
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            clean_lines.append("")
            continue
            
        # Bỏ các dòng link điều hướng dằng dặc của VietnamNet hoặc báo khác
        if skip_regex.search(line_strip):
            continue
            
        # Bỏ các dòng chỉ chứa markdown link dạng điều hướng của báo
        if (line_strip.startswith('*') or line_strip.startswith('-') or line_strip.startswith('[')) and ('vietnamnet.vn' in line_strip or 'vnn_source' in line_strip or 'vnncdn.net' in line_strip or 'vgcloud.vn' in line_strip):
            continue
            
        if 'javascript:;' in line_strip or 'javascript:void(0)' in line_strip or 'javasctip:void(0)' in line_strip:
            continue
            
        clean_lines.append(line)
        
    result = "\n".join(clean_lines)
    result = re.compile(r'\n{3,}').sub('\n\n', result)
    return result.strip()

async def cao_du_lieu_web(
    url: str,
    task_id: str = "sys",
    trace_id: str = "system",
    max_chars: int = 15000,
) -> dict:
    """Trich xuat van ban tu URL qua Crawl4AI (uu tien) hoac Jina (du phong) voi cache."""
    cache_key = f"scrape:{url}"
    if cached := _cache.get(cache_key):
        log.info(f"[SCRAPE-CACHE HIT] url='{url}'")
        return cached

    # 1. Thu cao du lieu sieu toc bang Crawl4AI thuan tuyet
    try:
        engine.publish_mission_log(
            "SCRAPER", f"🕷️ [CRAWL4AI]: Boc tach du lieu tu URL: `{url}`...", task_id, trace_id
        )
        from intelligence.skills.CORE.duyet_browse_zenith.logic import ai_browse
        browse_res = await ai_browse(url=url, action="extract_text", task_id=task_id, trace_id=trace_id)
        if browse_res.get("status") == "success" and browse_res.get("output"):
            raw_content = browse_res["output"]
            clean_content = clear_navigation_noise(raw_content)
            out = {"status": "success", "content": clean_content[:max_chars], "engine": browse_res.get("engine", "Crawl4AI")}
            _cache.set(cache_key, out, ttl=1800)
            return out
    except Exception as crawl_err:
        log.warning(f"[CRAWL4AI-SCRAPE-WARN] Crawl4AI that bai: {crawl_err}. Chuyener sang Jina.ai...")

    # 2. Du phong: Trich xuat qua Jina.ai
    if _cb_jina.is_open:
        return {"status": "error", "msg": "Ca Crawl4AI va Jina deu khong the trich xuat du lieu."}

    engine.publish_mission_log(
        "SCRAPER", f"📄 [JINA-FALLBACK]: Boc tach du lieu tu URL: `{url}`...", task_id, trace_id
    )

    async def _do_scrape():
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"https://r.jina.ai/{url}")
            resp.raise_for_status()
            return resp.text

    try:
        raw_content = await _retry_async(_do_scrape, retries=2, base_delay=1.5)
        _cb_jina.record_success()
        
        # Thanh loc cac link rac/thanh dieu huong de giu lai noi dung chinh xac nhat
        clean_content = clear_navigation_noise(raw_content)
        
        out = {"status": "success", "content": clean_content[:max_chars], "engine": "Jina"}
        _cache.set(cache_key, out, ttl=1800)
        return out
    except Exception as e:
        _cb_jina.record_failure()
        log.error(f"[SCRAPE] Jina that bai: {e}")
        return {"status": "error", "msg": str(e)}

async def read_url_content(url: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    """💎 [ALIAS]: Giao thức đọc nội dung URL thấu thị."""
    return await cao_du_lieu_web(url, task_id, trace_id)

# ──────────────────────────────────────────────────────────────────
# ✂️  ADAPTIVE SEMANTIC CHUNKING
# ──────────────────────────────────────────────────────────────────
_CODE_EXTS   = {".py", ".js", ".ts", ".jsx", ".tsx"}
_PROSE_EXTS  = {".md", ".txt", ".rst"}
_MAX_CHUNK   = 1500
_OVERLAP     = 200  # chữ trùng lặp để giữ ngữ cảnh giữa các chunk

def semantic_chunking(text: str, file_ext: str) -> list[str]:
    """
    Phân mảnh thông minh:
    - Prose: tách theo header Markdown
    - Code: tách theo def/class/async def
    - Fallback: sliding-window với overlap để không mất ngữ cảnh
    """
    chunks: list[str] = []

    if file_ext in _PROSE_EXTS:
        parts = re.split(r"(?=\n#{1,4} )", text)
        for part in parts:
            part_clean = part.strip()
            if not part_clean:
                continue
            if len(part_clean) <= _MAX_CHUNK:
                chunks.append(part_clean)
            else:
                # Sliding-window với overlap
                for start in range(0, len(part_clean), _MAX_CHUNK - _OVERLAP):
                    chunk = part_clean[start : start + _MAX_CHUNK].strip()
                    if chunk:
                        chunks.append(chunk)
    elif file_ext in _CODE_EXTS:
        parts = re.split(r"(?=\n(?:async def|def|class) )", text)
        # Lớp mã nguồn: Giữ overlap vài dòng để bảo tồn ngữ cảnh
        prev_tail = ""
        for i, part in enumerate(parts):
            part_clean = part.strip()
            if not part_clean:
                continue
            if prev_tail and i > 0:
                part_clean = prev_tail + "\n" + part_clean
            
            lines_part = part_clean.splitlines()
            prev_tail = "\n".join(lines_part[-3:]) if len(lines_part) >= 3 else ""
            
            chunks.append(part_clean)
    else:
        # sliding-window fallback
        for start in range(0, len(text), _MAX_CHUNK - _OVERLAP):
            chunk = text[start : start + _MAX_CHUNK].strip()
            if chunk:
                chunks.append(chunk)

    return [c for c in chunks if c]

# ──────────────────────────────────────────────────────────────────
# 🌀  TOTAL INDEX  (xử lý song song + tóm tắt ngữ cảnh)
# ──────────────────────────────────────────────────────────────────
async def _index_single_file(
    full_path: Path,
    profile: str,
    semaphore: asyncio.Semaphore,
    count_dict: dict,
) -> tuple[int, int]:
    """Index một file đơn lẻ. Trả về (success_count, error_count)."""
    count, errors = 0, 0
    async with semaphore:
        try:
            # Non-blocking file read using to_thread
            def read_file():
                return full_path.read_text(encoding="utf-8", errors="ignore").strip()
            text = await asyncio.to_thread(read_file)
            if not text:
                return 0, 0

            ext = full_path.suffix
            chunks = semantic_chunking(text, ext)

            # Tạo embedding song song cho tất cả chunks của file này
            async def _embed_chunk(i: int, chunk: str):
                nonlocal count, errors
                try:
                    # Tóm tắt ngữ cảnh
                    summary = "Knowledge chunk"
                    if len(chunk) > 300:
                        try:
                            summary_resp = await engine.call_chat(
                                messages=[
                                    {
                                        "role": "system",
                                        "content": (
                                            "Viết 1 câu ngắn (dưới 15 từ) mô tả nội dung sau nói về gì. "
                                            "Chỉ trả lời câu đó, không thêm gì khác."
                                        ),
                                    },
                                    {"role": "user", "content": chunk[:800]},
                                ],
                                role="SUMMARIZER",
                                profile=profile,
                            )
                            if summary_resp:
                                summary = summary_resp.strip()
                        except Exception:
                            pass  # dùng fallback "Knowledge chunk"

                    enriched = f"CONTEXT: {summary}\n\nCONTENT:\n{chunk}"
                    vector = await embed.get_embedding_async(enriched)
                    if vector:
                        await qdrant_client.upsert_intel(
                            text=enriched,
                            embedding=vector,
                            metadata={
                                "source": str(full_path),
                                "summary": summary,
                                "chunk_id": i,
                                "type": "elite_smart_vault",
                            },
                        )
                        count += 1
                        count_dict["count"] += 1
                        if count_dict["count"] % 20 == 0 and count_dict["count"]:
                            engine.publish_progress(
                                0, f"🧬 Đã vector hoá {count_dict['count']} phân đoạn...", "smart_index"
                            )
                except Exception as exc:
                    log.warning(f"[INDEX-CHUNK] {full_path.name}[{i}]: {exc}")
                    errors += 1

            # Execute all chunks in parallel using asyncio.gather
            await asyncio.gather(*[_embed_chunk(i, c) for i, c in enumerate(chunks)])

        except Exception as exc:
            log.error(f"[INDEX-FILE] {full_path}: {exc}")
            errors += 1

    return count, errors

async def dong_bo_toan_dien_qdrant(
    folder_path: str = "/intelligence",
    profile: str = "FAST_RESPONSE",
    max_concurrency: int = 8,
) -> dict:
    """
    🌀 [ELITE SMART INDEXING v2.0]:
    Vector hóa toàn diện, song song hóa Non-blocking I/O siêu tốc.
    """
    engine.publish_mission_log(
        "SMART_INDEX",
        f"🌀 [ELITE-INDEX]: Khởi động Quy trình Tổng chỉ mục Thông minh tại: `{folder_path}`"
    )

    base = Path(folder_path)
    
    # 1. Chuyển đổi đọc file đồng bộ sang Non-blocking I/O bằng ThreadPool ngầm qua asyncio
    def get_all_files():
        valid_files = []
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in [".md", ".txt", ".py", ".js"]:
                    valid_files.append(Path(root) / file)
        return valid_files

    target_files = await asyncio.to_thread(get_all_files)
    log.info(f"[INDEX] Tìm thấy {len(target_files)} file để index.")

    semaphore = asyncio.Semaphore(max_concurrency)
    count_dict = {"count": 0}
    total_count, total_errors = 0, 0

    # Chạy song song tất cả các files
    tasks = [_index_single_file(f, profile, semaphore, count_dict) for f in target_files]
    
    # Dùng asyncio.gather để gom tất cả lại
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for res in results:
        if isinstance(res, tuple):
            c, e = res
            total_count += c
            total_errors += e

    msg = f"Đã hoàn tất Tổng chỉ mục Thông minh. Đã nạp thành công {total_count} phân đoạn tri thức có ngữ cảnh vào Qdrant Vault, {total_errors} lỗi."
    engine.publish_mission_log("SMART_INDEX", f"✅ [INDEX-COMPLETE]: {msg}")
    return {
        "status": "success",
        "msg": msg,
        "errors": total_errors,
        "count": total_count
    }

# ──────────────────────────────────────────────────────────────────
# 🔎  FUZZY GREP  (regex + Levenshtein gần đúng)
# ──────────────────────────────────────────────────────────────────
def _levenshtein(a: str, b: str) -> int:
    """Khoảng cách chỉnh sửa giữa hai chuỗi ngắn (O(mn))."""
    if len(a) > len(b):
        a, b = b, a
    row = list(range(len(a) + 1))
    for c2 in b:
        new_row = [row[0] + 1]
        for j, c1 in enumerate(a):
            new_row.append(min(new_row[-1] + 1, row[j + 1] + 1, row[j] + (c1 != c2)))
        row = new_row
    return row[-1]


def _fuzzy_match(query: str, line: str, threshold: int = 2) -> bool:
    """Kiểm tra xem query có xuất hiện gần đúng trong line không."""
    words = line.lower().split()
    q = query.lower()
    return any(_levenshtein(q, w) <= threshold for w in words)


async def truy_luc_thuc_dia(
    query: str,
    path: str | None = None,
    extension: str = ".py",
    task_id: str = "sys",
    fuzzy: bool = False,
    fuzzy_threshold: int = 2,
    max_results: int = 50,
) -> dict:
    """
    🔍 [PHYSICAL-GREP v32.0]: 
    Quét mã nguồn thực địa bằng xử lý đa luồng non-blocking kết hợp Asyncio chuẩn chỉ.
    Hỗ trợ Regex chính xác (mặc định) và Fuzzy matching Levenshtein tuỳ chọn.
    """
    from core.config import settings
    search_path = Path(path or settings.WORKSPACE_ROOT)

    engine.publish_mission_log(
        "GREP",
        f"🔎 [GREP-v2] query=`{query}` ext=`{extension}` fuzzy={fuzzy} path=`{search_path}`",
        task_id,
    )

    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error as e:
        return {"status": "error", "msg": f"Regex không hợp lệ: {e}"}

    # Hàm quét file đồng bộ chạy an toàn trên Worker Thread
    def _sync_grep():
        local_results = []
        
        # Generator quét tệp tối ưu bộ nhớ
        file_generator = (
            p for p in search_path.rglob(f"*{extension}")
            if not any(part in p.parts for part in IGNORE_DIRS)
        )
        
        for file_path in file_generator:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        matched = bool(pattern.search(line))
                        if not matched and fuzzy:
                            matched = _fuzzy_match(query, line, fuzzy_threshold)
                        if matched:
                            local_results.append({
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.strip(),
                                "match_type": "exact" if pattern.search(line) else "fuzzy",
                            })
            except Exception:
                pass
        return local_results

    try:
        # Đẩy toàn bộ quá trình Grep nặng nề sang Thread Pool, giải phóng hoàn toàn Async Loop
        results = await asyncio.to_thread(_sync_grep)

        if not results:
            return {"status": "success", "msg": "Không tìm thấy kết quả nào trên thực địa."}

        # Sắp xếp: exact trước, fuzzy sau
        results.sort(key=lambda r: (r["match_type"] != "exact", r["file"], r["line"]))
        top = results[:max_results]

        report = f"✅ Đã định vị {len(results)} điểm trùng khớp. Dưới đây là các vị trí trọng tâm:\n"
        for r in top[:20]:
            tag = "🎯" if r["match_type"] == "exact" else "〰️"
            report += f"- {tag} `{r['file']}:{r['line']}` -> {r['content'][:90]}\n"
        
        engine.publish_mission_log(
            "GREP", f"✅ [GREP-SUCCESS]: Hoàn tất trích xuất {len(results)} điểm tương quan.", task_id
        )
        return {
            "status": "success", 
            "count": len(results), 
            "data": top, 
            "report": report
        }

    except Exception as e:
        return {"status": "error", "msg": f"Lỗi quét thực địa: {str(e)}"}


# ──────────────────────────────────────────────────────────────────
# 🩺  SEARCH DOCTOR  — Chẩn đoán sức khỏe toàn bộ Search Backends
#     Kích hoạt bằng: "kiểm tra sức khỏe tìm kiếm" / "search health"
# ──────────────────────────────────────────────────────────────────
async def run_search_doctor(engine_instance=None, task_id: str = "doctor") -> dict:
    """
    Force probe toàn bộ backends và trả về báo cáo sức khỏe chi tiết.
    Dùng cho diagnostic khi Master muốn kiểm tra trạng thái hệ thống.

    Trả về dict với keys:
      - report (str): Báo cáo dạng text đẹp
      - health (dict): Trạng thái từng backend dưới dạng dict
      - overall (str): "ok" | "degraded" | "critical"
    """
    _eng = engine_instance or engine
    _eng.publish_mission_log("SYSTEM_HEALTH", "🩺 [SEARCH-DOCTOR]: Bắt đầu chẩn đoán toàn bộ Search Backends...", task_id)

    # Probe song song tất cả backends
    await _search_probe.probe_all()

    report = _search_probe.doctor_report()
    _eng.publish_mission_log("SYSTEM_HEALTH", report, task_id)

    # Tính trạng thái tổng thể
    statuses = [h.status for h in _search_probe._health.values()]
    if all(s == BackendStatus.DEAD for s in statuses):
        overall = "critical"
        _eng.publish_mission_log("SYSTEM_HEALTH",
            "🚨 [SEARCH-CRITICAL]: TẤT CẢ backends đang DEAD. Hệ thống tìm kiếm không thể hoạt động!", task_id)
    elif any(s in (BackendStatus.OK, BackendStatus.DEGRADED) for s in statuses):
        dead_count = sum(1 for s in statuses if s == BackendStatus.DEAD)
        if dead_count > 0:
            overall = "degraded"
            _eng.publish_mission_log("SYSTEM_HEALTH",
                f"⚠️ [SEARCH-DEGRADED]: {dead_count} backend(s) DEAD, nhưng vẫn còn backup hoạt động.", task_id)
        else:
            overall = "ok"
            _eng.publish_mission_log("SYSTEM_HEALTH",
                "✅ [SEARCH-HEALTHY]: Tất cả backends đang hoạt động tốt.", task_id)
    else:
        overall = "unknown"

    return {
        "status": "success",
        "report": report,
        "health": {name: {"status": h.status.value, "latency_ms": h.latency_ms, "note": h.note}
                   for name, h in _search_probe._health.items()},
        "overall": overall,
    }

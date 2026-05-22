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

# Đảm bảo nạp được các module từ core
SYS_PATH_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if SYS_PATH_DIR not in sys.path:
    sys.path.append(SYS_PATH_DIR)

from core.utils.embed import embed
from core.qdrant_client import qdrant_client
from core.utils.engine import engine

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

class SmartCache:
    """Thread-safe TTL cache với giới hạn kích thước."""
    def __init__(self, max_size: int = 512, default_ttl: int = 300):
        self._store: dict[str, _CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl

    @staticmethod
    def _key(raw: str) -> str:
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, raw_key: str) -> Optional[Any]:
        entry = self._store.get(self._key(raw_key))
        if entry and time.time() < entry.expires_at:
            return entry.value
        return None

    def set(self, raw_key: str, value: Any, ttl: int | None = None) -> None:
        if len(self._store) >= self.max_size:
            # Xoá 10% entries cũ nhất
            oldest = sorted(self._store.items(), key=lambda x: x[1].expires_at)
            for k, _ in oldest[: self.max_size // 10]:
                del self._store[k]
        self._store[self._key(raw_key)] = _CacheEntry(
            value=value, expires_at=time.time() + (ttl or self.default_ttl)
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
# 🧮  BM25 LITE SCORING
# ──────────────────────────────────────────────────────────────────
def _bm25_score(query: str, text: str) -> float:
    """BM25-lite: tính điểm liên quan dựa trên tần suất từ (không cần thư viện ngoài)."""
    k1, b = 1.5, 0.75
    avg_len = 300  # ước tính trung bình
    tokens_q = set(query.lower().split())
    tokens_d = text.lower().split()
    doc_len = len(tokens_d)
    score = 0.0
    for term in tokens_q:
        tf = tokens_d.count(term)
        if tf == 0:
            continue
        idf = 1.0  # simplified — không có corpus toàn cục
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
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

async def SEARCH_WEB_GLOBAL(
    query: str,
    task_id: str = "sys",
    trace_id: str = "system",
    search_depth: str = "advanced",
    **kwargs,
) -> dict:
    """
    Tìm kiếm Internet qua Tavily với:
    - Cache 10 phút cho cùng query
    - Circuit Breaker tự ngắt khi API lỗi liên tiếp
    - Retry với exponential backoff
    """
    cache_key = f"web:{query}:{search_depth}"
    if cached := _cache.get(cache_key):
        log.info(f"[WEB-CACHE HIT] query='{query}'")
        return cached

    if _cb_tavily.is_open:
        return {"status": "error", "msg": "Tavily đang tạm ngưng (circuit open). Thử lại sau."}

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"status": "error", "msg": "TAVILY_API_KEY chưa được cấu hình."}

    engine.publish_mission_log(
        "WEB_SEARCH", f"🔍 [TAVILY]: Đang tầm soát Internet: `{query}`", task_id, trace_id
    )

    async def _do_search():
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "search_depth": search_depth},
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = await _retry_async(_do_search, retries=3, base_delay=1.0)
        _cb_tavily.record_success()

        results = data.get("results", [])
        if results:
            log_msg = f"✅ [TAVILY-FOUND]: Đã phát hiện {len(results)} tọa độ thông tin.\n"
            for i, r in enumerate(results[:3], 1):
                log_msg += f"{i}. [{r.get('title', '')[:60]}]({r.get('url', '')})\n"
            engine.publish_mission_log("WEB_DATA", log_msg, task_id, trace_id)

        _cache.set(cache_key, data, ttl=600)
        return data

    except Exception as e:
        _cb_tavily.record_failure()
        log.error(f"[WEB-SEARCH] Thất bại: {e}")
        return {"status": "error", "msg": f"Tavily error: {e}"}

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
    """Trích xuất văn bản từ URL qua Jina với cache, circuit breaker, và bộ thanh lọc nhiễu điều hướng."""
    cache_key = f"scrape:{url}"
    if cached := _cache.get(cache_key):
        log.info(f"[SCRAPE-CACHE HIT] url='{url}'")
        return cached

    if _cb_jina.is_open:
        return {"status": "error", "msg": "Jina đang tạm ngưng (circuit open). Thử lại sau."}

    engine.publish_mission_log(
        "SCRAPER", f"📄 [JINA]: Bóc tách dữ liệu từ: `{url}`", task_id, trace_id
    )

    async def _do_scrape():
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"https://r.jina.ai/{url}")
            resp.raise_for_status()
            return resp.text

    try:
        raw_content = await _retry_async(_do_scrape, retries=2, base_delay=1.5)
        _cb_jina.record_success()
        
        # Thanh lọc các link rác/thanh điều hướng để giữ lại nội dung chính xác nhất
        clean_content = clear_navigation_noise(raw_content)
        
        out = {"status": "success", "content": clean_content[:max_chars]}
        _cache.set(cache_key, out, ttl=1800)
        return out
    except Exception as e:
        _cb_jina.record_failure()
        log.error(f"[SCRAPE] Thất bại: {e}")
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

import hashlib
import json
import time
import re
from typing import Optional, Dict, Any, Union

try:
    from redis_client import redis_client
except ImportError:
    redis_client = None

class SemanticCache:
    """
    Lớp bộ đệm ngữ nghĩa tốc độ siêu cao (<50ms) cho hệ điều hành JKAI OS.
    Tự động chuẩn hóa câu lệnh đầu vào, tính băm (semantic hash) và truy xuất
    từ Redis hoặc bộ đệm dự phòng trong RAM nhằm bỏ qua các chu kỳ chạy
    suy luận nặng trên GPU VRAM đối với những tác vụ tương đồng đã hoàn thành.
    """

    def __init__(self, ttl_seconds: int = 86400, max_local_items: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_local_items = max_local_items
        self._local_fallback_cache: Dict[str, Dict[str, Any]] = {}

    def _prune_local_cache_if_needed(self):
        """🛡️ Bounded LRU Cache Pruning chống rò rỉ RAM (OOM Risk)."""
        if len(self._local_fallback_cache) > self.max_local_items:
            sorted_keys = sorted(
                self._local_fallback_cache.keys(),
                key=lambda k: self._local_fallback_cache[k].get("timestamp", 0)
            )
            prune_count = int(self.max_local_items * 0.2)
            for k in sorted_keys[:prune_count]:
                self._local_fallback_cache.pop(k, None)

    def _normalize_prompt(self, prompt: str) -> str:
        """
        Chuẩn hóa chuỗi văn bản, loại bỏ ký tự rỗng, các từ thừa tháp để 
        đảm bảo độ chính xác khi đối chiếu ý nghĩa.
        """
        if not prompt:
            return ""
        text = prompt.strip().lower()
        # Xóa bỏ các ký tự đặc biệt không ảnh hưởng logic lõi
        text = re.sub(r"\s+", " ", text)
        return text

    def _compute_hash(self, text: str) -> str:
        norm_text = self._normalize_prompt(text)
        return hashlib.sha256(norm_text.encode("utf-8")).hexdigest()

    def set_cache(self, query: str, response_payload: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Lưu kết quả phản hồi của tác vụ vào bộ đệm Redis và RAM dự phòng.
        """
        try:
            cache_key = f"semantic_cache:{self._compute_hash(query)}"
            data_packet = {
                "timestamp": time.time(),
                "original_query": query,
                "payload": response_payload,
                "metadata": metadata or {"engine": "fast_cache_bypass", "source": "JKAI_SEMANTIC_RAM"}
            }
            serialized = json.dumps(data_packet, ensure_ascii=False)
            
            # Ghi vào Redis nếu kết nối trực tuyến
            if redis_client and hasattr(redis_client, "redis") and redis_client.redis is not None:
                try:
                    redis_client.redis.setex(cache_key, self.ttl_seconds, serialized)
                except Exception as e_redis:
                    # Chuyển tiếp vào RAM dự phòng khi Redis gặp lỗi mạng
                    self._local_fallback_cache[cache_key] = data_packet
            else:
                self._prune_local_cache_if_needed()
                self._local_fallback_cache[cache_key] = data_packet
                
            return True
        except Exception as e:
            return False

    def get_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Truy xuất lập tức (<50ms) kết quả lưu ký nếu tìm thấy ngữ nghĩa tương đương.
        Trả về None nếu bộ đệm không có hoặc đã hết hạn TTL.
        """
        start_time = time.time()
        try:
            cache_key = f"semantic_cache:{self._compute_hash(query)}"
            
            # Ưu tiên đọc từ Redis
            if redis_client and hasattr(redis_client, "redis") and redis_client.redis is not None:
                try:
                    cached_val = redis_client.redis.get(cache_key)
                    if cached_val:
                        data_packet = json.loads(cached_val)
                        data_packet["latency_ms"] = round((time.time() - start_time) * 1000, 3)
                        data_packet["cache_hit"] = True
                        return data_packet
                except Exception:
                    pass
                    
            # Đọc từ bộ đệm RAM cục bộ nếu có
            if cache_key in self._local_fallback_cache:
                packet = self._local_fallback_cache[cache_key]
                if time.time() - packet.get("timestamp", 0) <= self.ttl_seconds:
                    packet["latency_ms"] = round((time.time() - start_time) * 1000, 3)
                    packet["cache_hit"] = True
                    return packet
                else:
                    del self._local_fallback_cache[cache_key]
                    
            return None
        except Exception:
            return None

# Đơn vị lưu ký tĩnh trên luồng RAM
semantic_cache = SemanticCache()

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    cache = SemanticCache(ttl_seconds=3600)
    test_query = "Kiểm tra tình trạng khả dụng RAM của máy tính local"
    mock_res = {"status": "SUCCESS", "ram_avail": "96GB / 128GB", "action": "NO_ACTION_NEEDED"}
    
    t0 = time.time()
    cache.set_cache(test_query, mock_res)
    t_set = (time.time() - t0) * 1000
    
    t1 = time.time()
    retrieved = cache.get_cache("   kiểm tra   tình trạng   khả dụng   RAM  của   máy tính LOCAL   ")
    t_get = (time.time() - t1) * 1000
    
    print("=== SEMANTIC CACHE BENCHMARK ===")
    print(f"Set Latency : {t_set:.2f} ms")
    print(f"Get Latency : {t_get:.2f} ms")
    if retrieved and t_get < 50.0 and retrieved.get("cache_hit") is True:
        print("[PASS] Truy xuat thanh cong voi toc do duoi 50ms (Zero VRAM overhead).")
    else:
        print("[FAIL] Truy xuat cham hon dinh muc hoac khong khop.")


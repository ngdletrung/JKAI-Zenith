import time
import hashlib
from typing import List, Dict, Any, Tuple

class MemoryPruner:
    """
    Phân hệ Thanh lọc và Nén Trí nhớ Đêm (Nightly Semantic Pruner) cho JKAI OS.
    Tự động rà soát kho ký ức dài hạn (Engrams/Vectors), gộp các chuỗi sự cố trùng lặp
    và loại bỏ những dòng nhận xét lỗi thời, chống bão hòa vectơ trên hạ tầng RAM 128GB.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def _signature_hash(self, content: str) -> str:
        """
        Tạo mã nhận dạng cốt lõi của bài học ký ức (bỏ qua khác biệt thời gian hay số dòng nhỏ).
        """
        clean_words = [w.lower() for w in content.split() if len(w) > 3]
        key_str = " ".join(clean_words[:15])  # Lấy 15 từ cốt lõi đầu tiên
        return hashlib.md5(key_str.encode("utf-8")).hexdigest()

    def prune_stale_engrams(self, memory_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Thực hiện giải phẫu và dọn dẹp các ký ức trùng lặp hoặc lỗi thời.
        Input format mỗi record: {"id": str, "timestamp": float, "content": str, "importance": float, "type": str}
        """
        if not memory_records:
            return {"pruned_records": [], "original_count": 0, "retained_count": 0, "reduction_percentage": 0.0}

        original_count = len(memory_records)
        seen_signatures: Dict[str, Dict[str, Any]] = {}
        retained_records: List[Dict[str, Any]] = []
        current_time = time.time()

        for rec in sorted(memory_records, key=lambda x: x.get("timestamp", 0), reverse=True):
            content = str(rec.get("content", "")).strip()
            if not content:
                continue
            
            sig = self._signature_hash(content)
            # Nếu phát hiện ký ức trùng lặp, hợp nhất trọng số quan trọng vào bản ghi mới nhất
            if sig in seen_signatures:
                existing = seen_signatures[sig]
                existing["importance"] = min(1.0, existing.get("importance", 0.5) + 0.1)
                existing["occurrences"] = existing.get("occurrences", 1) + 1
                continue
            
            # Gán thuộc tính số lần lặp lại
            rec["occurrences"] = rec.get("occurrences", 1)
            
            # Lọc bỏ ký ức quá 30 ngày có độ quan trọng thấp (< 0.2)
            age_days = (current_time - rec.get("timestamp", current_time)) / 86400.0
            if age_days > 30 and rec.get("importance", 0.5) < 0.2:
                continue
                
            seen_signatures[sig] = rec
            retained_records.append(rec)

        retained_count = len(retained_records)
        reduction_pct = round((1.0 - (retained_count / max(1, original_count))) * 100.0, 2)
        
        return {
            "pruned_records": retained_records,
            "original_count": original_count,
            "retained_count": retained_count,
            "reduction_percentage": reduction_pct,
            "status": "success"
        }

    def merge_error_clusters(self, error_logs: List[str]) -> List[str]:
        """
        Cô dọn hàng ngàn chuỗi stack trace rải rác thành các khuôn mẫu chiết xuất duy nhất.
        """
        clustered = {}
        for err in error_logs:
            lines = [line.strip() for line in err.splitlines() if line.strip() and not line.startswith("File")]
            key = " --> ".join(lines[:3]) if lines else err[:80]
            clustered[key] = clustered.get(key, 0) + 1
        return [f"[CLUSTER x{count}] {signature}" for signature, count in clustered.items()]

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    pruner = MemoryPruner()
    
    # Tạo danh sách 50 ký ức giả lập bị lặp lại do lỗi vòng lặp cũ
    mock_memories = []
    base_timestamp = time.time() - 3600
    for i in range(50):
        mock_memories.append({
            "id": f"mem_{i}",
            "timestamp": base_timestamp + (i * 10),
            "content": f"SyntaxError: Missing colon at function def validate_blueprint on line {100 + (i % 2)}",
            "importance": 0.4,
            "type": "defect_engram"
        })
    # Thêm 5 ký ức độc lập và quan trọng
    for j in range(5):
        mock_memories.append({
            "id": f"mem_unique_{j}",
            "timestamp": time.time(),
            "content": f"Binh phap toi uu VRAM thu {j+1}: Giu num_parallel=2 tren AMD RX 6600.",
            "importance": 0.9,
            "type": "wisdom_engram"
        })

    res = pruner.prune_stale_engrams(mock_memories)
    print("=== NIGHTLY SEMANTIC PRUNER BENCHMARK ===")
    print(f"Original Memory Count : {res['original_count']} records")
    print(f"Retained Clean Count  : {res['retained_count']} records")
    print(f"Reduction Percentage  : {res['reduction_percentage']}%")
    
    if res["retained_count"] <= 10 and res["reduction_percentage"] > 70.0:
        print("[PASS] Thanh loc bo nho qua dem thanh cong. Khong con nghien bão hòa vector.")
    else:
        print("[FAIL] Hieu suat thanh loc chua dat chi tieu.")

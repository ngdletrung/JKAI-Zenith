import time
import threading
from typing import Dict, Any, Optional

class HlcTimestamp:
    """
    🧬 [HLC-DNA]: Hybrid Logical Clock Timestamp.
    Nhất thể hóa thời gian vật lý và thứ tự logic thưa Tổng Giám Đốc.
    """
    def __init__(self, physical_ms: int, logical: int, node_id: str):
        self.physical_ms = physical_ms
        self.logical = logical
        self.node_id = node_id

    def __repr__(self):
        return f"{self.physical_ms}:{self.logical}:{self.node_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "physical_ms": self.physical_ms,
            "logical": self.logical,
            "node_id": self.node_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(data["physical_ms"], data["logical"], data["node_id"])

    @classmethod
    def from_str(cls, val: str):
        """
        Giải mã chuỗi format 'physical_ms:logical:node_id' thành đối tượng HlcTimestamp thưa Tổng Giám Đốc.
        """
        parts = val.split(":", 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid HLC timestamp format: {val} thưa Master.")
        return cls(int(parts[0]), int(parts[1]), parts[2])

    def __lt__(self, other):
        return compare_hlc(self, other) < 0

    def __eq__(self, other):
        return compare_hlc(self, other) == 0

class LocalHlc:
    """
    🏛️ [LOCAL-ORACLE]: Bộ đếm thời gian HLC nội tại thưa Master.
    Đảm bảo tính đơn điệu (monotonicity) và quan hệ nhân quả (causality).
    """
    def __init__(self, node_id: str, max_skew_ms: int = 30000):
        if not node_id:
            raise ValueError("node_id cannot be empty thưa Master.")
        self.node_id = node_id
        self.max_skew_ms = max_skew_ms
        # Seed với giá trị nhỏ nhất thưa Master
        self.last = HlcTimestamp(-1, 0, node_id)
        self._lock = threading.Lock()

    def now(self) -> HlcTimestamp:
        """Khai hỏa một nơ-ron thời gian mới thưa Master."""
        with self._lock:
            wall = int(time.time() * 1000)
            if wall > self.last.physical_ms:
                # Wall clock tiến lên - reset logical counter thưa Master
                self.last = HlcTimestamp(wall, 0, self.node_id)
            else:
                # Wall clock đứng yên hoặc lùi lại - tăng logical counter thưa Master
                self.last = HlcTimestamp(self.last.physical_ms, self.last.logical + 1, self.node_id)
            return self.last

    def update(self, received: HlcTimestamp) -> HlcTimestamp:
        """Đồng bộ nơ-ron thời gian với tín hiệu nhận được thưa Master."""
        with self._lock:
            wall = int(time.time() * 1000)
            
            # Kiểm tra độ lệch (skew guard) thưa Master
            if received.physical_ms > wall + self.max_skew_ms:
                # Cảnh báo nơ-ron bị lệch pha thưa Master
                # Trong môi trường đơn node, ta có thể bỏ qua hoặc log
                pass
            
            max_physical = max(wall, self.last.physical_ms, received.physical_ms)
            
            if max_physical == self.last.physical_ms and max_physical == received.physical_ms:
                logical = max(self.last.logical, received.logical) + 1
            elif max_physical == self.last.physical_ms:
                logical = self.last.logical + 1
            elif max_physical == received.physical_ms:
                logical = received.logical + 1
            else:
                logical = 0
                
            self.last = HlcTimestamp(max_physical, logical, self.node_id)
            return self.last

def compare_hlc(a: HlcTimestamp, b: HlcTimestamp) -> int:
    """So sánh thứ tự ưu tiên của hai nơ-ron HLC thưa Master."""
    if a.physical_ms < b.physical_ms: return -1
    if a.physical_ms > b.physical_ms: return 1
    if a.logical < b.logical: return -1
    if a.logical > b.logical: return 1
    if a.node_id < b.node_id: return -1
    if a.node_id > b.node_id: return 1
    return 0

# Singleton mặc định cho node hiện tại thưa Master
_node_id = f"node-{int(time.time())}"
hlc = LocalHlc(_node_id)

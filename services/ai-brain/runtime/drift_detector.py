class DriftDetector:
    """
    🧭 Cảnh Sát Sai Lệch (Intent Drift Prevention)
    Ngăn chặn Planner/Executor tự ý biến tấu yêu cầu ban đầu.
    """
    def __init__(self):
        pass

    def validate_proposal(self, parent_manifest_hash: str, current_manifest_hash: str):
        """Khóa Intent. Đề xuất của Planner phải dựa trên Manifest do Dispatcher gốc sinh ra."""
        if parent_manifest_hash != current_manifest_hash:
            raise ValueError("[DRIFT-DETECTED]: Planner đã cố gắng thay đổi Intent hoặc Risk của Dispatcher!")

    def detect_semantic_drift(self, original_intent: str, proposed_tool: str) -> float:
        """
        Đo độ lệch chuẩn Semantic giữa Intent gốc và Tool được chọn.
        Ví dụ: Intent="Tóm tắt tài liệu", Tool="format_disk" -> Drift Score = 1.0 (Nguy hiểm)
        """
        # TODO: Cắm mô hình Embedding Similarity
        return 0.0

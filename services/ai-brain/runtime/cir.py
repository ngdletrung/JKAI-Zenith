import json
import hashlib
from typing import Dict, Any

class CanonicalIntentRepresentation:
    """
    🔤 Canonical Intent Representation (CIR)
    Duy trì tính ổn định của ngữ nghĩa và loại bỏ sai lệch do LLM sinh chuỗi ngẫu nhiên.
    """
    def __init__(self, intent: str, target: str, scope: str, metadata: Dict[str, Any] = None):
        self.cir_version = "1.0"
        self.intent = intent.upper()
        self.target = target
        self.scope = scope.upper()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cir_version": self.cir_version,
            "intent": self.intent,
            "target": self.target,
            "scope": self.scope,
            "metadata": self.metadata
        }

    def canonicalize(self) -> str:
        """
        Ổn định hóa JSON. 
        Đảm bảo {"a": 1, "b": 2} và {"b": 2, "a": 1} cho ra cùng một Hash.
        """
        payload = self.to_dict()
        return json.dumps(payload, sort_keys=True, separators=(',', ':'))

    def hash(self) -> str:
        """Định danh nguyên tử của Intent này."""
        return hashlib.sha256(self.canonicalize().encode()).hexdigest()

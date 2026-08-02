import logging
import os
from typing import Optional

logger = logging.getLogger("JKAI.Context.Reference")

_MAX_SLICE_BYTES = 2000
_CONTEXT_BEFORE = 1000
_CONTEXT_AFTER = 1000


class DocumentSlice:
    def __init__(self, source_file: str, offset: int, content: str, length: int):
        self.source_file = source_file
        self.offset = offset
        self.content = content
        self.length = length

    def to_dict(self) -> dict:
        return {"source_file": self.source_file, "offset": self.offset, "content": self.content, "length": self.length}


class Reference:
    def __init__(self, doc_id: str, source_file: str, offset: int = 0, length: int = 0, score: float = 0.0, end_char_idx: int = 0):
        self.doc_id = doc_id
        self.source_file = source_file
        self.offset = offset
        self.length = length
        self.score = score
        self.end_char_idx = end_char_idx

    @staticmethod
    def from_qdrant_hit(hit: dict) -> Optional["Reference"]:
        payload = hit.get("payload", {}) or {}
        source_file = payload.get("source_file", payload.get("source", ""))
        if not source_file:
            return None
        offset = payload.get("start_char_idx", payload.get("offset", 0))
        if isinstance(offset, str):
            try:
                offset = int(offset)
            except ValueError:
                offset = 0
        end_char_idx = payload.get("end_char_idx", 0)
        if isinstance(end_char_idx, str):
            try:
                end_char_idx = int(end_char_idx)
            except ValueError:
                end_char_idx = 0
        doc_id = payload.get("doc_id", payload.get("id", hit.get("id", "")))
        score = hit.get("score", 0.0)
        return Reference(doc_id=doc_id, source_file=source_file, offset=offset, score=score, end_char_idx=end_char_idx)

    def __repr__(self):
        return f"Reference(doc_id={self.doc_id}, file={self.source_file}, offset={self.offset}, score={self.score:.2f})"


class ReferenceResolver:
    _FILE_CACHE: dict = {}

    def resolve(self, ref: Reference, max_bytes: int = _MAX_SLICE_BYTES) -> Optional[DocumentSlice]:
        filepath = self._find_file(ref.source_file)
        if not filepath or not os.path.isfile(filepath):
            logger.warning(f"[REF-RESOLVE] File not found: {ref.source_file}")
            return None
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            file_len = len(content)
            chunk_end = ref.end_char_idx if ref.end_char_idx > ref.offset else ref.offset
            start = max(0, ref.offset - _CONTEXT_BEFORE)
            end = min(file_len, chunk_end + _CONTEXT_AFTER)
            slice_content = content[start:end]
            return DocumentSlice(source_file=ref.source_file, offset=start, content=slice_content, length=len(slice_content))
        except Exception as e:
            logger.warning(f"[REF-RESOLVE] read error {ref.source_file}: {e}")
            return None

    def resolve_from_qdrant(self, hits: list) -> list[DocumentSlice]:
        slices = []
        seen = set()
        for hit in hits:
            ref = Reference.from_qdrant_hit(hit)
            if ref and ref.source_file not in seen:
                seen.add(ref.source_file)
                if len(slices) >= 3:
                    break
                ds = self.resolve(ref)
                if ds:
                    slices.append(ds)
        return slices

    def _find_file(self, source_file: str) -> Optional[str]:
        if os.path.isfile(source_file):
            return source_file
        base = os.path.join(os.getcwd(), "intelligence")
        candidate = os.path.join(base, source_file)
        if os.path.isfile(candidate):
            return candidate
        for root, dirs, files in os.walk(base):
            for f in files:
                if f == os.path.basename(source_file) or f == source_file:
                    return os.path.join(root, f)
        return None

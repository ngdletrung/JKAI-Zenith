import hashlib

_ID_SPACE = 2 ** 63


def deterministic_point_id(text: str, chunk_index: int = 0) -> int:
    """Stable Qdrant id: same content and chunk index map to the same id across processes."""
    digest = hashlib.sha256(f"{chunk_index}\x00{text}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % _ID_SPACE or 1

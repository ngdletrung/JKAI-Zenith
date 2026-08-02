import logging
from typing import Optional

from .claw_compactor.fusion.engine import FusionEngine

logger = logging.getLogger("JKAI.PromptEngine.Context")


class ContextCompressor:
    """
    Wraps Claw Compactor FusionPipeline for JKAI's prompt_engine.
    Zero external dependencies, fully local, <50ms typical latency.

    Used to compress KB chunks, memory, and tools output before
    injecting into the prompt — stretching 8192 context window further.
    """

    def __init__(self):
        self._engine = FusionEngine()

    def compress_kb_chunks(self, chunks: list[str], max_chars: int = 3500) -> str:
        """
        Compress knowledge base chunks before sending to model.
        Deduplicates semantically similar chunks, compresses prose.

        Returns a single compressed string ready for <knowledge_context>.
        """
        if not chunks:
            return ""

        raw = "\n---\n".join(chunks)

        if len(raw) <= max_chars * 0.7:
            return raw[:max_chars]

        result = self._engine.compress(raw, content_type="text")
        compressed = result["compressed"]

        if len(compressed) > max_chars:
            compressed = compressed[:max_chars]

        saved = result["stats"].get("reduction_pct", 0)
        logger.debug("[CTX-COMPRESS] KB: %d chars -> %d chars (%d%% saved)",
                     len(raw), len(compressed), saved)
        return compressed

    def compress_memory(self, memory_text: str) -> str:
        if not memory_text:
            return ""
        result = self._engine.compress(memory_text, content_type="text")
        return result["compressed"]

    def deduplicate(self, texts: list[str]) -> list[str]:
        if len(texts) <= 1:
            return texts
        combined = "\n---CHUNK---\n".join(texts)
        result = self._engine.compress(combined, content_type="text")
        compressed = result["compressed"]
        return [compressed] if compressed else texts

    def stats(self) -> dict:
        return {"engine": "ClawCompactor v7.1.0", "stages": 14}


context_compressor = ContextCompressor()

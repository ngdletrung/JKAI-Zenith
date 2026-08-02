"""
Constraint Engine — abstract structured generation layer.
Hiện tại dùng Ollama format=schema, sau này có thể mở rộng sang Outlines/vLLM.
"""

from core.constraint.base import ConstraintEngine, ConstraintResult
from core.constraint.engines.ollama import OllamaEngine
from core.constraint import schemas

ENGINES = {"ollama": OllamaEngine}


def get_engine(name: str | None = None) -> ConstraintEngine:
    import os

    engine_name = name or os.getenv("JKAI_CONSTRAINT_ENGINE", "ollama")
    cls = ENGINES.get(engine_name)
    if cls is None:
        raise ValueError(f"Unknown constraint engine: {engine_name}. Available: {list(ENGINES)}")
    return cls()


__all__ = [
    "ConstraintEngine", "ConstraintResult",
    "OllamaEngine",
    "get_engine",
    "schemas",
]

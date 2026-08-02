import json
import os
import threading
from typing import Optional

from core.knowledge_sources.sources.source import Source, SourceType

CONNECTIONS_PATH = os.getenv(
    "KS_CONNECTIONS_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "intelligence",
        "Knowledge_Manager",
        "connections.json",
    ),
)


class SourceRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._sources: dict[str, Source] = {}
        return cls._instance

    def register(self, source: Source) -> bool:
        self._sources[source.id] = source
        self._persist()
        return True

    def remove(self, source_id: str) -> Optional[Source]:
        source = self._sources.pop(source_id, None)
        if source:
            self._persist()
        return source

    def get(self, source_id: str) -> Optional[Source]:
        return self._sources.get(source_id)

    def list_all(self) -> list[Source]:
        return list(self._sources.values())

    def set_enabled(self, source_id: str, enabled: bool) -> bool:
        if source_id in self._sources:
            self._sources[source_id].enabled = enabled
            self._persist()
            return True
        return False

    def _persist(self):
        try:
            db_dir = os.path.dirname(CONNECTIONS_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            data = [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.type.value,
                    "config": s.config,
                    "enabled": s.enabled,
                    "target_collection": s.target_collection,
                }
                for s in self._sources.values()
            ]
            with open(CONNECTIONS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load(self):
        try:
            if not os.path.exists(CONNECTIONS_PATH):
                return
            with open(CONNECTIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                src = Source(
                    id=item["id"],
                    name=item["name"],
                    type=SourceType(item["type"]),
                    config=item.get("config", {}),
                    enabled=item.get("enabled", True),
                    target_collection=item.get("target_collection", "jkai_external"),
                )
                self._sources[src.id] = src
        except Exception:
            pass


source_registry = SourceRegistry()
source_registry._load()

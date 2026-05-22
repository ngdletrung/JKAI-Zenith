import asyncio
import json
import os
from pathlib import Path
from core.utils.engine import engine
from core.qdrant_client import qdrant_client

class DossierInvestigator:
    """
    🕵️ JKAI ZENITH: DOSSIER INVESTIGATOR (v3.6 Elite)
    Trinh sát đa chiều, đệ quy và song song.
    """
    def __init__(self):
        from core.config import settings
        self.dossier_dir = Path(settings.INTELLIGENCE_DIR) / "dossiers"
        self.dossier_dir.mkdir(parents=True, exist_ok=True)

    async def investigate(self, seed: str, max_depth: int = 2, **kwargs):
        """
        🚀 Giao thức Trinh sát Fan-out: Quét song song đa nguồn.
        """
        engine.publish_mission_log("DOSSIER", f"🔍 [START]: Bắt đầu trinh sát hạt giống: {seed}")
        
        dossier = {
            "seed": seed,
            "entities": [],
            "edges": [],
            "metadata": {"depth": max_depth, "sources": []}
        }

        # Round 0: Parallel Fan-out
        sources = [
            self._search_memory(seed),
            self._search_web(seed),
            self._search_code(seed)
        ]
        
        results = await asyncio.gather(*sources)
        
        # Aggregate results
        for idx, res in enumerate(results):
            if res:
                dossier["entities"].extend(res.get("entities", []))
                dossier["edges"].extend(res.get("edges", []))
        
        # Save Dossier
        slug = seed.replace(" ", "_").lower()
        file_path = self.dossier_dir / f"{slug}.json"
        await engine.concurrent_atomic_write(str(file_path), json.dumps(dossier, indent=2, ensure_ascii=False))
        
        return {
            "status": "success",
            "msg": f"✅ [DOSSIER]: Đã hoàn tất trinh sát hạt giống `{seed}`. Hồ sơ đã được lưu trữ.",
            "path": str(file_path)
        }

    async def _search_memory(self, query):
        # Truy vấn Qdrant
        from core.utils.embed import embed
        vector = embed(query)
        hits = await qdrant_client.search_similar(vector, limit=5)
        return {
            "entities": [{"id": h['id'], "text": h['payload']['text']} for h in hits],
            "edges": [{"from": query, "to": h['id'], "source": "Qdrant"}]
        }

    async def _search_web(self, query):
        # Trình duyệt (Mockup for now)
        return {"entities": [], "edges": []}

    async def _search_code(self, query):
        # Rà soát mã nguồn
        return {"entities": [], "edges": []}

# singleton
_instance = DossierInvestigator()
investigate = _instance.investigate

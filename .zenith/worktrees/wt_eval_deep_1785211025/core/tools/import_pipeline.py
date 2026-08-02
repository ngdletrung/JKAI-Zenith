import os
import time
import asyncio
import shutil
import logging
from pathlib import Path

from core.utils import path_manager

logger = logging.getLogger("IMPORT_PIPELINE")

SUPPORTED_EXTS = {".md", ".txt", ".pdf", ".docx", ".csv", ".json", ".yaml", ".toml", ".py", ".js", ".ts", ".html", ".css", ".sh"}
MIN_CONTENT_LEN = 100
CHUNK_SIZE = 2000

WIKI_CATEGORIES = {
    "system": ["kien truc", "architecture", "design pattern", "flow", "component", "module", "he thong"],
    "decisions": ["decision", "quyet dinh", "tai sao", "reason", "adr"],
    "bugs": ["bug", "loi", "error", "fix", "hotfix", "issue", "crash", "stack trace"],
    "roadmap": ["roadmap", "ke hoach", "plan", "improvement", "cai tien", "todo", "backlog"],
    "devops": ["devops", "docker", "ci/cd", "deploy", "kubernetes", "container", "pipeline", "jenkins", "github action"],
    "coding": ["coding", "code", "programming", "python", "javascript", "typescript", "api", "standard", "pattern", "refactor"],
    "ai": ["ai", "llm", "model", "prompt", "openai", "gpt", "embedding", "rag", "vector db", "machine learning", "neural"],
    "business": ["business", "domain", "nghiep vu", "process", "workflow", "n8n", "automation"],
    "security": ["security", "bao mat", "encrypt", "auth", "permission", "firewall", "vulnerability"],
    "data_science": ["data", "ml", "machine learning", "quantum", "statistic", "analytics", "visualization"],
    "research": ["research", "nghien cuu", "exploration", "paper", "survey", "benchmark"],
    "finance": ["finance", "tai chinh", "payment", "invoice", "accounting", "budget"],
    "references": ["reference", "tham khao", "guide", "tutorial", "manual", "documentation", "wiki"],
}

CATEGORY_ORDER = list(WIKI_CATEGORIES.keys())


async def run_import_pipeline(task_id: str = "import_pipeline") -> dict:
    from core.utils.converter import converter
    from core.utils.engine import engine
    from core.qdrant_client import qdrant_client

    import_dir = _get_path("FILES_INPUT")
    delete_dir = _get_path("FILES_DELETE")
    wiki_dir = _get_path("WIKI_DIR")

    os.makedirs(import_dir, exist_ok=True)
    os.makedirs(delete_dir, exist_ok=True)
    os.makedirs(wiki_dir, exist_ok=True)

    files = [f for f in Path(import_dir).iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]
    if not files:
        return {"status": "ok", "imported": 0, "deleted": 0, "msg": "Khong co file nao trong Import."}

    imported = 0
    deleted = 0
    errors = []

    for file_path in files:
        try:
            content = await converter.to_markdown(str(file_path), task_id=task_id)
            if not content or len(content.strip()) < MIN_CONTENT_LEN:
                dest = Path(delete_dir) / file_path.name
                shutil.move(str(file_path), str(dest))
                deleted += 1
                logger.info(f"[DELETE] {file_path.name} (noi dung qua ngan hoac rong)")
                continue

            chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
            embeddings = await asyncio.gather(
                *[engine.get_embeddings(chunk) for chunk in chunks],
                return_exceptions=True
            )

            collection = "jkai_wiki"
            try:
                await qdrant_client.ensure_collection(collection)
            except Exception:
                pass

            success = 0
            for chunk, emb in zip(chunks, embeddings):
                if isinstance(emb, Exception) or not emb:
                    continue
                metadata = {
                    "filename": file_path.name,
                    "source": str(file_path),
                    "imported_at": time.time(),
                    "task_id": task_id,
                }
                await qdrant_client.upsert_intel(
                    text=chunk,
                    embedding=emb,
                    collection=collection,
                    metadata=metadata,
                )
                success += 1

            if success > 0:
                wiki_subdir = _detect_category(file_path.name, content)
                dest_dir = Path(wiki_dir) / wiki_subdir
                os.makedirs(str(dest_dir), exist_ok=True)
                dest = dest_dir / file_path.name
                shutil.move(str(file_path), str(dest))
                imported += 1
                logger.info(f"[IMPORT] {file_path.name} -> {wiki_subdir}/ ({success} chunks)")
            else:
                dest = Path(delete_dir) / file_path.name
                shutil.move(str(file_path), str(dest))
                deleted += 1
                logger.warning(f"[DELETE] {file_path.name} (embed that bai)")
        except Exception as e:
            errors.append(f"{file_path.name}: {e}")
            try:
                dest = Path(delete_dir) / file_path.name
                shutil.move(str(file_path), str(dest))
                deleted += 1
            except Exception:
                pass

    msg = f"Nhap {imported} file, xoa {deleted} file."
    if errors:
        msg += f" Loi: {'; '.join(errors[:5])}"
    return {"status": "ok", "imported": imported, "deleted": deleted, "errors": errors, "msg": msg}


def _detect_category(filename: str, content: str) -> str:
    text = f"{filename.lower()} {content.lower()}"

    scores = {}
    for cat, keywords in WIKI_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score

    if not scores:
        return "references"

    best = max(scores, key=scores.get)
    return best


def _get_path(var: str) -> str:
    val = path_manager.get(var)
    if val:
        return val
    fallbacks = {
        "FILES_INPUT": "files/Import",
        "FILES_DELETE": "files/Delete",
        "WIKI_DIR": "intelligence/wiki",
    }
    return os.path.join(path_manager.get_root(), fallbacks.get(var, "intelligence/wiki"))

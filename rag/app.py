import os
import httpx
import asyncio
import logging
import subprocess
import hashlib
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http.models import VectorParams, Distance

# [ANTI-HALLUCINATION]: Epistemic Discipline Engine
try:
    from core.utils.hallucination_guard import (
        query_classifier,
        epistemic_shield,
        PromptLock,
        QueryType,
        fallback_decider,
        NoRagFallbackLevel,
    )
    _GUARD_AVAILABLE = True
except ImportError as _guard_err:
    logging.warning("[RAG] hallucination_guard not available: %s", _guard_err)
    _GUARD_AVAILABLE = False

# [CRITIC-VERIFIER]: RAG fact-checking engine
try:
    from core.utils.critic_rag_verifier import critic_rag_verifier
    _VERIFIER_AVAILABLE = True
except ImportError as _verifier_err:
    logging.warning("[RAG] critic_rag_verifier not available: %s", _verifier_err)
    _VERIFIER_AVAILABLE = False

# LlamaIndex core & Qdrant integration
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document, StorageContext, VectorStoreIndex, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JKAI Zenith RAG Engine - Core Knowledge Matrix")

# ====================== ELITE CONFIG (UNIFIED ENGINE) ======================
from core.utils.engine import engine

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "n8n_knowledge")
# [FALLBACK-L1]: URL endpoint web search (optional — neu khong set, skip Level 1)
RAG_WEB_SEARCH_URL = os.getenv("RAG_WEB_SEARCH_URL", "")

qdrant = AsyncQdrantClient(
    host=QDRANT_HOST,
    port=int(os.getenv("QDRANT_PORT", 6333)),
    prefer_grpc=False,
    https=False,
)

# 💎 Persistent Client for Elite Neural Communication
client = httpx.AsyncClient(
    timeout=httpx.Timeout(600.0, connect=10.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
)

# ====================== HELPER (ASYNC NEURAL) ======================
async def get_embedding(text: str):
    try:
        return await engine.get_embeddings(text)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise

async def generate_response(prompt: str, temperature: float):
    try:
        answer = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="RECEPTIONIST",
            options={"temperature": temperature} if temperature > 0 else None
        )
        return answer
    except Exception as e:
        logger.error(f"Generate error: {e}")
        raise

# ====================== LLAMAINDEX CONFIG ======================
def run_sync(coro):
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()

class JKAIEmbedding(BaseEmbedding):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def class_name(cls) -> str:
        return "JKAIEmbedding"

    def _get_query_embedding(self, query: str):
        return run_sync(get_embedding(query))

    def _get_text_embedding(self, text: str):
        return run_sync(get_embedding(text))

    async def _aget_query_embedding(self, query: str):
        return await get_embedding(query)

    async def _aget_text_embedding(self, text: str):
        return await get_embedding(text)

Settings.embed_model = JKAIEmbedding()
Settings.llm = None

# ====================== INIT COLLECTION ======================
async def init_collection():
    """Khởi tạo collection trong Qdrant nếu chưa tồn tại thưa Master"""
    try:
        collections = await qdrant.get_collections()
        existing = [c.name for c in collections.collections]
        
        if COLLECTION_NAME not in existing:
            logger.info(f"Creating collection: {COLLECTION_NAME}")
            await qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )
            logger.info("Collection created successfully")
        else:
            logger.info(f"Collection {COLLECTION_NAME} already exists")
    except Exception as e:
        logger.error(f"Failed to init collection: {e}")

@app.on_event("startup")
async def startup_event():
    await init_collection()

# ====================== MODELS ======================
class AskRequest(BaseModel):
    query: str
    collection: str = COLLECTION_NAME
    top_k: int = 5
    temperature: float = -1.0   # -1.0 = auto (HallucinationGuard sets per QueryType)

class IngestTextRequest(BaseModel):
    text: str
    metadata: dict = {}
    collection: str = COLLECTION_NAME

# ====================== ENDPOINTS ======================
@app.get("/")
@app.get("/health")
@app.get("/healthz")
def health():
    cfg = engine.get_role_config("RECEPTIONIST")
    return {"status": "RAG Service is ready ✅", "model": cfg["model"]}

def expand_node_context(node) -> str:
    original_text = node.node.get_content(metadata_mode="none")
    metadata = node.node.metadata or {}
    source_path = metadata.get("source_path") or metadata.get("file_path")
    
    if not source_path:
        return original_text
        
    if not os.path.exists(source_path):
        # Fallback to absolute project path or common workspace path
        possible_paths = [
            source_path,
            os.path.join(os.getcwd(), source_path),
            os.path.join(os.getcwd(), "workspace", os.path.basename(source_path)),
            os.path.join("d:\\Docker\\JKAI", source_path)
        ]
        found = False
        for p in possible_paths:
            if os.path.exists(p):
                source_path = p
                found = True
                break
        if not found:
            return original_text

    try:
        start_idx = getattr(node.node, "start_char_idx", None)
        end_idx = getattr(node.node, "end_char_idx", None)
        
        with open(source_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        file_len = len(content)
        if start_idx is not None and end_idx is not None:
            # Expand context window 1000 characters before & after
            start = max(0, start_idx - 1000)
            end = min(file_len, end_idx + 1000)
            expanded_text = content[start:end]
            return f"--- FILE SLICE: {os.path.basename(source_path)} (Chars: {start}-{end}) ---\n... {expanded_text.strip()} ..."
        else:
            idx = content.find(original_text[:100])
            if idx != -1:
                start = max(0, idx - 1000)
                end = min(file_len, idx + len(original_text) + 1000)
                expanded_text = content[start:end]
                return f"--- FILE SLICE: {os.path.basename(source_path)} (Chars: {start}-{end}) ---\n... {expanded_text.strip()} ..."
            else:
                return original_text
    except Exception as e:
        logger.warning(f"[RAG-EXPAND-WARN] Failed to read original file {source_path}: {e}")
        return original_text

def expand_context_from_hit(hit) -> str:
    payload = hit.payload or {}
    chunk_text = getattr(payload, "text", "") if hasattr(payload, "text") else (payload.get("text", "") if isinstance(payload, dict) else "")
    source_path = getattr(payload, "source_path", "") or getattr(payload, "source", "") if hasattr(payload, "source_path") else (payload.get("source_path") or payload.get("source", "") if isinstance(payload, dict) else "")
    if isinstance(payload, dict):
        start_idx = payload.get("start_char_idx")
        end_idx = payload.get("end_char_idx")
    else:
        start_idx = getattr(payload, "start_char_idx", None)
        end_idx = getattr(payload, "end_char_idx", None)

    if not source_path or start_idx is None or end_idx is None:
        return chunk_text

    possible_paths = [
        source_path,
        os.path.join(os.getcwd(), source_path),
        os.path.join("d:\\Docker\\JKAI", source_path),
        os.path.join("d:\\Docker\\JKAI", os.path.basename(source_path)),
    ]
    found_path = None
    for p in possible_paths:
        if os.path.exists(p):
            found_path = p
            break
    if not found_path:
        return chunk_text

    try:
        with open(found_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        file_len = len(content)
        start = max(0, start_idx - 1000)
        end = min(file_len, end_idx + 1000)
        expanded = content[start:end]
        return f"--- FILE SLICE: {os.path.basename(source_path)} (Chars: {start}-{end}) ---\n... {expanded.strip()} ..."
    except Exception as e:
        logger.warning(f"[RAG-EXPAND-WARN] Failed to read {found_path}: {e}")
        return chunk_text

@app.post("/ask")
async def ask(req: AskRequest):
    try:
        t_start = time.monotonic()
        query_vector = await get_embedding(req.query)
        search_result = (await qdrant.query_points(
            collection_name=req.collection,
            query=query_vector,
            limit=req.top_k,
            with_payload=True,
        )).points

        # Expand context from source files
        documents = []
        for hit in search_result:
            expanded = expand_context_from_hit(hit)
            documents.append({
                "text": expanded,
                "cosine_score": float(hit.score) if hit.score else 0.0,
                "metadata": hit.payload or {},
            })

        # Apply HybridReranker
        from core.utils.hybrid_reranker import HybridReranker
        reranker = HybridReranker()
        reranked_docs = reranker.rerank(documents, req.query)

        context = "\n\n".join([doc["text"] for doc in reranked_docs])
        rag_scores = [doc["hybrid_score"] for doc in reranked_docs]
        retrieved_hits = search_result

        # ── [ANTI-HALLUCINATION] Step 1: Classify query ──────────────────────
        if _GUARD_AVAILABLE:
            query_type = query_classifier.classify(req.query)
            prompt_lock = PromptLock.get_system_lock(query_type)
            # Use auto temperature from PromptLock unless caller explicitly set one
            effective_temp = (
                PromptLock.get_temperature(query_type)
                if req.temperature < 0
                else req.temperature
            )
        else:
            query_type = None
            prompt_lock = (
                "Ban la JKAI Zenith. Khi khong co du lieu trong tai lieu, "
                "phai noi ro: '[JKAI-UNVERIFIED]: Khong co du lieu xac thuc.'"
            )
            effective_temp = 0.3 if req.temperature < 0 else req.temperature

        logger.info(
            "[RAG-GUARD] query_type=%s temp=%.1f sources=%d query=%s",
            getattr(query_type, 'value', 'N/A'), effective_temp,
            len(retrieved_hits), req.query[:60],
        )

        # ── [ANTI-HALLUCINATION] Step 2: Build prompt theo 3-level fallback ──────
        has_rag_context = bool(context.strip())
        fallback_level = None
        used_web_search = False
        web_search_context = ""

        if _GUARD_AVAILABLE and query_type == QueryType.FACT_CRITICAL and not has_rag_context:
            # Xac dinh fallback level khi khong co RAG
            web_search_available = bool(RAG_WEB_SEARCH_URL)
            fallback_level = fallback_decider.decide(req.query, web_search_available)
            logger.info("[RAG-FALLBACK] No RAG context. Level=%s query=%s", fallback_level.value, req.query[:60])

            # ---- LEVEL 1: Web Search ------------------------------------------
            if fallback_level == NoRagFallbackLevel.WEB_SEARCH:
                try:
                    async with httpx.AsyncClient(timeout=15.0) as search_client:
                        search_resp = await search_client.post(
                            RAG_WEB_SEARCH_URL,
                            json={"query": req.query, "limit": 3},
                        )
                    if search_resp.status_code == 200:
                        search_data = search_resp.json()
                        snippets = search_data.get("results") or search_data.get("snippets") or []
                        if snippets:
                            web_search_context = "\n".join(
                                f"[WEB] {s.get('title','')}: {s.get('snippet') or s.get('text','')[:300]}"
                                for s in snippets[:3]
                            )
                            context = web_search_context
                            used_web_search = True
                            logger.info("[RAG-FALLBACK-L1] Web search returned %d results", len(snippets))
                        else:
                            # Web search tra ve rong → giam xuong Level 2
                            fallback_level = fallback_decider.decide(req.query, web_search_available=False)
                            logger.warning("[RAG-FALLBACK-L1] Web search empty, demoting to %s", fallback_level.value)
                except Exception as ws_err:
                    logger.warning("[RAG-FALLBACK-L1] Web search failed (%s), demoting", ws_err)
                    fallback_level = fallback_decider.decide(req.query, web_search_available=False)

            # ---- LEVEL 2: Model + Disclaimer ----------------------------------
            if fallback_level == NoRagFallbackLevel.MODEL_DISCLAIMER and not used_web_search:
                prompt_lock = PromptLock.MODEL_DISCLAIMER_LOCK  # type: ignore[attr-defined]
                effective_temp = 0.1  # Rat thap — gioi han sang tao khi khong co RAG
                context = "[KHONG CO TAI LIEU NOI BO — Dang dung kien thuc model voi disclaimer]"

            # ---- LEVEL 3: Tu choi hoan toan -----------------------------------
            elif fallback_level == NoRagFallbackLevel.UNVERIFIED and not used_web_search:
                unverified_answer = PromptLock.UNVERIFIED_RESPONSE  # type: ignore[attr-defined]
                cfg_early = engine.get_role_config("RECEPTIONIST")
                elapsed_ms_early = (time.monotonic() - t_start) * 1000
                if _GUARD_AVAILABLE:
                    guarded_early = epistemic_shield.wrap(
                        answer=unverified_answer,
                        query_type=query_type,
                        rag_evidence_count=0,
                        rag_scores=[],
                        verifier_verdict="UNVERIFIED",
                        elapsed_ms=elapsed_ms_early,
                    )
                    return {
                        "answer": guarded_early.answer,
                        "uncertainty_warning": guarded_early.uncertainty_warning,
                        "sources": 0,
                        "query_type": guarded_early.query_type.value,
                        "data_source": "UNVERIFIED",
                        "confidence": 0.0,
                        "should_verify": True,
                        "verifier_verdict": "UNVERIFIED",
                        "fallback_level": "UNVERIFIED",
                        "elapsed_ms": round(elapsed_ms_early, 1),
                        "model_used": cfg_early["model"],
                    }
                return {"answer": unverified_answer, "sources": 0, "model_used": cfg_early["model"]}

        # Build RAG prompt (dung cho ca 4 luong: RAG co san, Web Search, Model Disclaimer, va PARAMETRIC_SAFE)
        display_context = context if context.strip() else "[KHONG CO TAI LIEU LIEN QUAN TRONG KHO TRI THUC]"
        context_label = "NGUON WEB" if used_web_search else "TAI LIEU NOI BO"

        rag_prompt = f"""Ban la JKAI Zenith - He thong Tri tue Nhan tao cao cap cua Master.

{prompt_lock}

=== {context_label} ===
{display_context}

=== CAU HOI CUA NGUOI DUNG ===
{req.query}

Tra loi:"""

        answer = await generate_response(rag_prompt, effective_temp)
        cfg = engine.get_role_config("RECEPTIONIST")

        # ── [ANTI-HALLUCINATION] Step 3: Hook CriticRagVerifier for FACT_CRITICAL ──
        verifier_verdict = ""
        verifier_reasoning = ""
        if (
            _VERIFIER_AVAILABLE
            and _GUARD_AVAILABLE
            and query_type == QueryType.FACT_CRITICAL
            and answer
            and len(retrieved_hits) > 0
        ):
            try:
                verify_result = await critic_rag_verifier.verify_claim(
                    answer[:500], context_hint=req.query[:100]
                )
                verifier_verdict = verify_result.verdict
                verifier_reasoning = verify_result.reasoning
                logger.info(
                    "[RAG-CRITIC] verdict=%s confidence=%.2f query=%s",
                    verifier_verdict, verify_result.confidence, req.query[:60],
                )
                # Append contradiction warning to answer
                if verifier_verdict == "CONTRADICTION":
                    answer = (
                        f"{answer}\n\n"
                        f"[JKAI-CANH-BAO-MAU-THUAN]: Kiet qua kiem chung phat hien mau thuan "
                        f"trong tai lieu. {verifier_reasoning}"
                    )
            except Exception as verify_err:
                logger.warning("[RAG-CRITIC] Verifier error (non-fatal): %s", verify_err)

        # ── [ANTI-HALLUCINATION] Step 4: Wrap with EpistemicShield ───────────
        elapsed_ms = (time.monotonic() - t_start) * 1000
        # Ghi nhan nguon thuc su (RAG / Web / Model)
        effective_source_count = len(retrieved_hits) + (3 if used_web_search else 0)
        effective_scores = rag_scores if rag_scores else ([0.75] * 3 if used_web_search else [])

        if _GUARD_AVAILABLE:
            guarded = epistemic_shield.wrap(
                answer=answer,
                query_type=query_type,
                rag_evidence_count=effective_source_count,
                rag_scores=effective_scores,
                verifier_verdict=verifier_verdict,
                elapsed_ms=elapsed_ms,
            )
            return {
                "answer": guarded.answer,
                "uncertainty_warning": guarded.uncertainty_warning,
                "sources": guarded.rag_evidence_count,
                "query_type": guarded.query_type.value,
                "data_source": "WEB_SEARCH" if used_web_search else guarded.data_source,
                "confidence": round(guarded.confidence, 3),
                "should_verify": guarded.should_verify,
                "verifier_verdict": guarded.verifier_verdict,
                "fallback_level": fallback_level.value if fallback_level else "RAG",
                "elapsed_ms": round(guarded.elapsed_ms, 1),
                "model_used": cfg["model"],
            }

        # Fallback khi guard khong available
        return {
            "answer": answer,
            "sources": len(retrieved_hits),
            "model_used": cfg["model"],
        }

    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search(req: AskRequest):
    try:
        query_vector = await get_embedding(req.query)
        search_result = (await qdrant.query_points(
            collection_name=req.collection,
            query=query_vector,
            limit=req.top_k,
            with_payload=True,
        )).points

        documents = [
            {
                "text": expand_context_from_hit(hit),
                "cosine_score": float(hit.score) if hit.score else 0.0,
                "metadata": hit.payload or {},
            }
            for hit in search_result
        ]

        from core.utils.hybrid_reranker import HybridReranker
        reranker = HybridReranker()
        reranked_docs = reranker.rerank(documents, req.query)
        
        results = [
            {
                "text": doc["text"],
                "score": doc["hybrid_score"],
                "metadata": doc["metadata"]
            }
            for doc in reranked_docs
        ]
        return {"results": results}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/text")
async def ingest_text(req: IngestTextRequest):
    try:
        parser = SentenceSplitter(chunk_size=375, chunk_overlap=37)
        doc = Document(text=req.text, metadata=req.metadata)
        nodes = parser.get_nodes_from_documents([doc])

        vectors = await asyncio.gather(*[get_embedding(n.get_content()[:4000]) for n in nodes])
        points = []
        for i, (node, vector) in enumerate(zip(nodes, vectors)):
            if vector:
                points.append({
                    "id": abs(hash(node.get_content())) % 10**12,
                    "vector": vector,
                    "payload": {
                        "text": node.get_content(),
                        "source_path": req.metadata.get("source_path", ""),
                        "start_char_idx": node.start_char_idx,
                        "end_char_idx": node.end_char_idx,
                        "chunk_index": i,
                        **req.metadata,
                    },
                })

        if points:
            await qdrant.upsert(collection_name=req.collection, points=points)

        return {"status": "success", "message": f"Đã nạp văn bản và phân mảnh thành {len(nodes)} chunks thành công."}
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/scan")
async def trigger_scan():
    try:
        result = subprocess.run(
            ["python", "-m", "ingest.ingest_cron"],
            capture_output=True,
            text=True,
            cwd="/app",
            timeout=300
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "AI đã học xong các file mới từ Obsidian",
                "details": result.stdout
            }
        else:
            return {
                "status": "error",
                "message": "Lỗi khi quét thư mục",
                "error": result.stderr
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Scan timeout after 300 seconds"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
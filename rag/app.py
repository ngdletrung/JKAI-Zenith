import os
import httpx
import asyncio
import logging
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http.models import VectorParams, Distance
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JKAI Zenith RAG Engine - Core Knowledge Matrix")

# ====================== ELITE CONFIG (UNIFIED ENGINE) ======================
from core.utils.engine import engine

# 🎯 TUÂN THỦ CHỈ THỊ MASTER: Chuyển sang Giao thức Nhất thể hóa
# Lưu ý: Các model sẽ được lấy động trong mỗi request để đảm bảo Sync tuyệt đối.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "n8n_knowledge")

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

# Gọi khởi tạo bất đồng bộ thưa Master
@app.on_event("startup")
async def startup_event():
    await init_collection()

# ====================== MODELS ======================
class AskRequest(BaseModel):
    query: str
    collection: str = COLLECTION_NAME
    top_k: int = 5
    temperature: float = 0.3

class IngestTextRequest(BaseModel):
    text: str
    metadata: dict = {}
    collection: str = COLLECTION_NAME

# ====================== HELPER (ASYNC NEURAL) ======================
async def get_embedding(text: str):
    try:
        # 🎯 SỬ DỤNG ENGINE TRUNG ƯƠNG ĐỂ MÃ HÓA THỨA MASTER
        # Điều này đảm bảo RAG luôn dùng đúng Model đã cấu hình trong rule_hardware.md
        return await engine.get_embeddings(text)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise

async def generate_response(prompt: str, temperature: float):
    try:
        # 🧪 SỬ DỤNG UNIFIED ENGINE ĐỂ TẬP TRUNG QUYỀN LỰC THƯA MASTER
        answer = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="DATA_SCOUT",
            options={"temperature": temperature} if temperature > 0 else None
        )
        return answer
    except Exception as e:
        logger.error(f"Generate error: {e}")
        raise

# ====================== ENDPOINTS ======================
@app.get("/")
@app.get("/health")
def health():
    cfg = engine.get_role_config("DATA_SCOUT")
    return {"status": "RAG Service is ready ✅", "model": cfg["model"]}

@app.post("/ask")
async def ask(req: AskRequest):
    try:
        query_vector = await get_embedding(req.query)
        
        search_result = (await qdrant.query_points(
            collection_name=req.collection,
            query=query_vector,
            limit=req.top_k
        )).points
        
        context = "\n\n".join([hit.payload.get("text", "") for hit in search_result])
        
        rag_prompt = f"""Bạn là JKAI Zenith - Hệ thống Trí tuệ Nhân tạo cao cấp của Master.
Sử dụng kiến thức từ Kho Tri thức (Obsidian) dưới đây để trả lời.
Nếu thông tin không có trong tài liệu, hãy dựa vào kiến thức chuyên môn của bạn nhưng phải nêu rõ.

=== TÀI LIỆU NỘI BỘ ===
{context}

=== CÂU HỎI CỦA NGƯỜI DÙNG ===
{req.query}

Trả lời:"""
        
        answer = await generate_response(rag_prompt, req.temperature)
        cfg = engine.get_role_config("DATA_SCOUT")
        
        return {
            "answer": answer,
            "sources": len(search_result),
            "model_used": cfg["model"]
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
            limit=req.top_k
        )).points
        # Chỉ trả về văn bản thô và metadata
        results = [
            {"text": hit.payload.get("text", ""), "score": hit.score, "metadata": hit.payload}
            for hit in search_result
        ]
        return {"results": results}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/text")
async def ingest_text(req: IngestTextRequest):
    try:
        vector = await get_embedding(req.text)
        
        # Tạo ID từ hash
        point_id = abs(hash(req.text)) % 1000000000
        
        await qdrant.upsert(
            collection_name=req.collection,
            points=[{
                "id": point_id,
                "vector": vector,
                "payload": {"text": req.text, **req.metadata}
            }]
        )
        return {"status": "success", "message": "Đã nạp văn bản vào bộ nhớ AI"}
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
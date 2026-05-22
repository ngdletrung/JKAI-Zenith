import os
import httpx
import sys
import re
import json
import asyncio

# Đảm bảo nạp được các module từ core
try:
    from core.utils.engine import engine
except ImportError:
    pass)))))
from core.utils.embed import embed
from core.qdrant_client import qdrant_client
from core.utils.engine import engine

# =================================================================
# 🔍 JKAI ZENITH: LOGIC SIÊU TÌM KIẾM (SUPER SEARCH)
# =================================================================

def kham_pha_du_an(start_path: str = "."):
    """Tự thám hiểm cấu trúc thư mục của dự án."""
    print(f"🗺️ [JKAI-EXPLORE] Scouting project structure from: {start_path}")
    structure = []
    for root, dirs, files in os.walk(start_path):
        if any(x in root for x in ["node_modules", ".git", "__pycache__"]):
            continue
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * level
        structure.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            structure.append(f"{sub_indent}{f}")
    return {"status": "success", "structure": "\n".join(structure[:200])}

async def truy_luc_tri_thuc(query: str, task_id: str = "sys"):
    """Truy xuất tri thức từ Kho lưu trữ Qdrant (RAG)."""
    engine.publish_mission_log("BRAIN_QUERY", f"🧠 [NEURAL-SEARCH]: Đang truy xuất tri thức từ Vector Vault cho: `{query}`", task_id)
    
    try:
        # 1. Tạo embedding cho câu truy vấn (Async)
        query_vector = await embed.get_embedding_async(query)
        if not query_vector:
            return {"status": "error", "msg": "Không thể tạo embedding cho truy vấn."}
            
        # 2. Tìm kiếm trong Qdrant
        results = await qdrant_client.search_similar(query_vector, limit=3)
        
        if not results:
            return {"status": "success", "results": "Không tìm thấy tri thức tương ứng trong bộ nhớ dài hạn."}
            
        formatted_results = "\n\n".join([f"📄 [Nguồn: {r.get('metadata', {}).get('source', 'Unknown')}]:\n{r.get('text')}" for r in results])
        return {"status": "success", "results": formatted_results}
        
    except Exception as e:
        return {"status": "error", "msg": f"Lỗi truy lục RAG: {str(e)}"}

async def tim_kiem_web(query: str, task_id: str = "sys"):
    """Tìm kiếm thông tin mới nhất trên Internet."""
    api_key = os.getenv("TAVILY_API_KEY")
    engine.publish_mission_log("WEB_SEARCH", f"🔍 [TAVILY]: Đang tầm soát Internet: `{query}`", task_id)
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post("https://api.tavily.com/search", json={
                    "api_key": api_key, "query": query, "search_depth": "advanced"
                })
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {"status": "error", "msg": f"Tavily API Error: {resp.status_code} - {resp.text}"}
        except Exception as e:
            return {"status": "error", "msg": f"Search Connection Fault: {str(e)}"}
    return {"status": "error", "msg": "API Key missing."}

async def search_web(query: str, task_id: str = "sys"):
    """💎 [ALIAS]: Giao thức tìm kiếm web thấu thị."""
    return await tim_kiem_web(query, task_id)

async def cao_du_lieu_web(url: str):
    """Trích xuất nội dung văn bản từ một trang web."""
    print(f"📄 [JKAI-SCRAPE] Scraping content from: {url}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"https://r.jina.ai/{url}")
        if resp.status_code == 200:
            return {"status": "success", "content": resp.text[:5000]}
    return {"status": "error", "msg": "Scrape failed."}

async def read_url_content(url: str):
    """💎 [ALIAS]: Giao thức đọc nội dung URL thấu thị."""
    return await cao_du_lieu_web(url)

def semantic_chunking(text: str, file_ext: str):
    """Phân mảnh thông minh dựa trên cấu trúc (Markdown/Code)."""
    chunks = []
    if file_ext in [".md", ".txt"]:
        # Tách theo các Header (#, ##, ###)
        parts = re.split(r'(?=\n#{1,3} )', text)
        for p in parts:
            if len(p) > 2000: # Nếu quá dài thì cắt nhỏ tiếp
                chunks.extend([p[i:i+1500] for i in range(0, len(p), 1200)])
            else:
                chunks.append(p)
    elif file_ext in [".py", ".js"]:
        # Tách theo Class hoặc Function
        parts = re.split(r'(?=\n(?:def|class|async def) )', text)
        for p in parts:
            chunks.append(p)
    else:
        chunks = [text[i:i+1200] for i in range(0, len(text), 1000)]
    return [c.strip() for c in chunks if c.strip()]

async def dong_bo_toan_dien_qdrant(folder_path: str = "/intelligence", profile: str = "FAST_RESPONSE"):
    """
    🌀 [QUY TRÌNH TỔNG CHỈ MỤC THÔNG MINH - ELITE SMART INDEXING]:
    Vector hóa toàn bộ kho lưu trữ với khả năng Tóm tắt Ngữ cảnh.
    """
    engine.publish_mission_log("SMART_INDEX", f"🌀 [ELITE-INDEX]: Khởi động Quy trình Tổng chỉ mục Thông minh tại: `{folder_path}`")
    count = 0
    errors = 0
    
    # 1. Duyệt toàn bộ tệp tin
    for root, dirs, files in os.walk(folder_path):
        if any(x in root for x in [".obsidian", ".git", "node_modules", "archive", "00_Import", "quarantine", "temp"]): continue
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in [".md", ".txt", ".py", ".js"]: continue
            
            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if not content.strip(): continue
                
                # 2. Phân mảnh Ngữ nghĩa (Semantic Chunking)
                chunks = semantic_chunking(content, ext)
                
                for i, chunk in enumerate(chunks):
                    # 3. TẠO TÓM TẮT NGỮ CẢNH (Contextual Summary)
                    # Sử dụng model nhẹ để hiểu nhanh mảnh này nói về cái gì
                    summary = "Knowledge chunk"
                    try:
                        summary_resp = await engine.call_chat(
                            messages=[
                                {"role": "system", "content": "Bạn là chuyên gia tóm lược. Hãy viết 1 câu cực ngắn (dưới 15 từ) mô tả nội dung này nói về cái gì."},
                                {"role": "user", "content": chunk[:1000]}
                            ],
                            role="SUMMARIZER",
                            profile="FAST_RESPONSE"
                        )
                        summary = summary_resp.strip()
                    except: pass

                    # 4. Tạo Embedding & Upsert (Nội dung = Tóm tắt + Nội dung gốc)
                    enriched_text = f"CONTEXT: {summary}\n\nCONTENT:\n{chunk}"
                    vector = await embed.get_embedding_async(enriched_text)
                    
                    if vector:
                        await qdrant_client.upsert_intel(
                            text=enriched_text,
                            embedding=vector,
                            metadata={
                                "source": full_path,
                                "summary": summary,
                                "chunk_id": i,
                                "type": "elite_smart_vault"
                            }
                        )
                        count += 1
                        if count % 10 == 0:
                            engine.publish_progress(0, f"Đã vector hóa {count} phân đoạn tri thức...", "smart_index")
                        await asyncio.sleep(0.05)
            except Exception as e:
                print(f"⚠️ [SMART-SYNC-ERR] Skip {file}: {e}")
                errors += 1
                
    msg = f"Đã hoàn tất Tổng chỉ mục Thông minh. Đã nạp {count} phân đoạn tri thức có ngữ cảnh vào Qdrant."
    engine.publish_mission_log("SMART_INDEX", f"✅ [INDEX-COMPLETE]: {msg}")
    return {
        "status": "success", 
        "msg": msg,
        "errors": errors
    }

async def truy_luc_thuc_dia(query: str, path: str = None, extension: str = ".py", task_id: str = "sys"):
    """
    🔍 [PHYSICAL-GREP v31.0]: Truy lục chính xác từng dòng mã trên thực địa.
    """
    from core.config import settings
    path = path or settings.WORKSPACE_ROOT
    engine.publish_mission_log("GREP", f"🔎 [GREP-START]: Đang quét thực địa tìm `{query}` trong các tệp `{extension}`...", task_id)
    
    results = []
    try:
        import concurrent.futures
        from pathlib import Path

        base_path = Path(path)
        pattern = re.compile(query, re.IGNORECASE)
        
        def scan_file(file_path):
            file_results = []
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            file_results.append({
                                "file": str(file_path),
                                "line": i,
                                "content": line.strip()
                            })
            except: pass
            return file_results

        # Quét đệ quy
        target_files = [f for f in base_path.rglob(f"*{extension}") if not any(x in str(f) for x in [".git", "node_modules", "__pycache__"])]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(scan_file, f): f for f in target_files}
            for future in concurrent.futures.as_completed(future_to_file):
                results.extend(future.result())

        if not results:
            return {"status": "success", "msg": "Không tìm thấy kết quả nào trên thực địa."}

        # 🧠 [NEURAL-RANKING]: Nếu quá nhiều, chỉ lấy 20 kết quả đầu tiên và báo cáo
        report = f"✅ Đã tìm thấy {len(results)} kết quả. Dưới đây là các vị trí trọng tâm:\n"
        for r in results[:20]:
            report += f"- `{r['file']}:{r['line']}`: {r['content'][:100]}\n"
        
        engine.publish_mission_log("GREP", f"✅ [GREP-SUCCESS]: Đã tìm thấy {len(results)} điểm tương quan.", task_id)
        return {"status": "success", "count": len(results), "data": results[:50], "report": report}

    except Exception as e:
        logger.error(f"❌ [GREP-ERR] {e}")
        return {"status": "error", "msg": str(e)}

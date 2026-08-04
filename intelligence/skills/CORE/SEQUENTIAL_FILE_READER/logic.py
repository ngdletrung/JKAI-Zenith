import os
import json
import asyncio
import logging
from typing import Dict, Any, List
from core.utils.engine import engine

logger = logging.getLogger("JKAI.SequentialReader")

class SequentialReader:
    def __init__(self):
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "d:\\Docker\\JKAI")

    async def execute(self, file_path: str, query: str, task_id: str = "sys", **kwargs) -> Dict[str, Any]:
        target_path = file_path
        if not os.path.isabs(target_path):
            target_path = os.path.join(self.workspace_root, target_path)

        if not os.path.exists(target_path) or not os.path.isfile(target_path):
            return {"status": "error", "msg": f"File không tồn tại: {target_path}"}

        try:
            # Đọc toàn bộ nội dung file vào RAM
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            file_len = len(content)
            if file_len == 0:
                return {"status": "error", "msg": "Tệp tin rỗng."}

            # Lấy cấu hình num_ctx động từ mô hình đang chạy
            num_ctx = 4096
            try:
                role_cfg = engine.get_role_config("RECEPTIONIST")
                num_ctx = int(role_cfg.get("options", {}).get("num_ctx", 4096))
            except Exception:
                pass

            # Mỗi chunk an toàn chiếm tối đa 40% num_ctx (ví dụ: 1600 tokens ~ 6400 ký tự)
            # để đảm bảo mô hình có đủ không gian xử lý hướng dẫn và sinh từ
            chunk_size = int(num_ctx * 0.4 * 4)
            if chunk_size < 2000:
                chunk_size = 2000
            chunk_overlap = int(chunk_size * 0.1)

            # Phân đoạn tệp tin thành các chunks gối đầu nhau một cách thông minh (giữ dòng nguyên vẹn)
            paragraphs = [p for p in content.split("\n")]
            chunks = []
            current_chunk_lines = []
            current_len = 0
            
            for line in paragraphs:
                line_len = len(line) + 1 # +1 cho ký tự xuống dòng
                if current_len + line_len > chunk_size and current_chunk_lines:
                    chunks.append("\n".join(current_chunk_lines))
                    
                    # Giữ overlap thông minh bằng cách lấy ngược các dòng cuối cùng đạt chunk_overlap
                    overlap_lines = []
                    overlap_len = 0
                    for op in reversed(current_chunk_lines):
                        if overlap_len + len(op) + 1 < chunk_overlap:
                            overlap_lines.insert(0, op)
                            overlap_len += len(op) + 1
                        else:
                            break
                    current_chunk_lines = overlap_lines
                    current_len = overlap_len
                
                current_chunk_lines.append(line)
                current_len += line_len
            
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))

            num_chunks = len(chunks)
            logger.info("[SEQUENTIAL-READER] File size=%s chars. Chunking into %s chunks (size=%s).", file_len, num_chunks, chunk_size)
            engine.publish_mission_log(
                "SYSTEM",
                f"[SEQUENTIAL-READER] Đang nạp tệp ({file_len} ký tự). Phân rã thành {num_chunks} mảnh thông minh...",
                task_id
            )

            # Lấy cấu hình model và hardware động để tính toán concurrency
            model_name = "qwen3.5:4b"
            hardware_type = "GPU"
            try:
                role_cfg = engine.get_role_config("RECEPTIONIST")
                model_name = role_cfg.get("model", "qwen3.5:4b")
                hardware_type = role_cfg.get("hardware", "GPU")
            except Exception:
                pass

            from core.utils.hardware_scheduler import hardware_scheduler
            # Lấy số luồng song song tối ưu thời gian thực
            concurrency = await hardware_scheduler.calculate_optimal_concurrency(
                model_name=model_name,
                hardware_type=hardware_type,
                chunk_ctx=int(chunk_size / 4)
            )
            
            engine.publish_mission_log(
                "SYSTEM",
                f"⚙️ [SEQUENTIAL-READER]: Kích hoạt quét song song tối ưu phần cứng (Concurrency={concurrency})",
                task_id
            )

            # ── [LỌC NGỮ NGHĨA VECTOR - SEMANTIC PRE-FILTERING] ────────────
            # Chỉ áp dụng lọc vector nếu số lượng mảnh lớn (> 5) để tránh lãng phí thời gian
            final_chunks_to_scan = []
            if num_chunks > 5:
                engine.publish_mission_log(
                    "SYSTEM",
                    f"🔍 [SEQUENTIAL-READER]: Đang tính độ tương đồng vector cho {num_chunks} mảnh...",
                    task_id
                )
                try:
                    from core.utils.embed import embed
                    query_vector = await embed.get_embedding_async(query[:1000])
                    
                    if query_vector:
                        async def _embed_chunk(idx, text):
                            # Trích 2000 ký tự đầu của chunk để tăng tốc độ tính embedding
                            v = await embed.get_embedding_async(text[:2000])
                            return idx, v
                        
                        # Tính embedding song song cho toàn bộ chunks
                        emb_results = await asyncio.gather(*[_embed_chunk(i, c) for i, c in enumerate(chunks)])
                        
                        def cosine_similarity(v1, v2):
                            if not v1 or not v2: return 0.0
                            dot = sum(a*b for a, b in zip(v1, v2))
                            norm_a = sum(a*a for a in v1) ** 0.5
                            norm_b = sum(b*b for b in v2) ** 0.5
                            if norm_a == 0 or norm_b == 0: return 0.0
                            return dot / (norm_a * norm_b)
                        
                        ranked_chunks = []
                        for idx, v in emb_results:
                            score = cosine_similarity(query_vector, v)
                            ranked_chunks.append((score, idx, chunks[idx]))
                        
                        # Sắp xếp theo độ tương đồng giảm dần
                        ranked_chunks.sort(key=lambda x: x[0], reverse=True)
                        
                        # Lấy Top K mảnh liên quan nhất (Tối đa 30 mảnh có score >= 0.25)
                        top_k = min(30, num_chunks)
                        filtered = [item for item in ranked_chunks[:top_k] if item[0] >= 0.25]
                        
                        # Khởi phòng hờ: Giữ lại ít nhất 3 mảnh điểm cao nhất nếu bộ lọc quá gắt
                        if not filtered:
                            filtered = ranked_chunks[:min(3, num_chunks)]
                        
                        # Sắp xếp ngược lại theo index ban đầu để giữ tính tuần tự mạch lạc
                        filtered.sort(key=lambda x: x[1])
                        final_chunks_to_scan = [(item[1], item[2]) for item in filtered]
                        
                        engine.publish_mission_log(
                            "SYSTEM",
                            f"🔍 [SEQUENTIAL-READER]: Đã lọc lấy {len(final_chunks_to_scan)}/{num_chunks} mảnh liên quan nhất.",
                            task_id
                        )
                    else:
                        final_chunks_to_scan = list(enumerate(chunks))
                except Exception as embed_err:
                    logger.warning(f"Lỗi khi tính toán embeddings: {embed_err}")
                    final_chunks_to_scan = list(enumerate(chunks))
            else:
                final_chunks_to_scan = list(enumerate(chunks))

            # Thực thi song song có kiểm soát (Map Phase) cho các mảnh đã lọc
            extracted_facts = []
            sem = asyncio.Semaphore(concurrency)

            async def process_chunk(idx, chunk):
                async with sem:
                    # Tính % tiến trình dựa trên số mảnh thực tế sẽ quét
                    percent = int((idx / num_chunks) * 100)
                    engine.publish_mission_log(
                        "EXECUTOR",
                        f"⚙️ [SEQUENTIAL-READER]: Đang quét mảnh {idx + 1}/{num_chunks} ({percent}%) song song...",
                        task_id
                    )
                    prompt = (
                        "You are a precise data extractor. Analyze the following document chunk and extract "
                        "any information, facts, or data points that are relevant to this user query.\n"
                        "If the chunk does not contain relevant information, reply with 'NO_RELEVANT_DATA'.\n"
                        "Do not extrapolate or assume.\n\n"
                        f"User query: {query}\n\n"
                        f"--- DOCUMENT CHUNK {idx + 1}/{num_chunks} ---\n"
                        f"{chunk}\n\n"
                        "Extracted findings:"
                    )
                    try:
                        res = await engine.call_chat(
                            messages=[{"role": "user", "content": prompt}],
                            role="RECEPTIONIST",
                            options={"temperature": 0.2},
                            task_id=task_id
                        )
                        res_text = str(res).strip()
                        if "NO_RELEVANT_DATA" not in res_text and len(res_text) > 10:
                            extracted_facts.append((idx, f"[Mảnh {idx + 1}/{num_chunks}]: {res_text}"))
                    except Exception as chunk_err:
                        logger.warning(f"Failed to process chunk {idx+1}: {chunk_err}")

            await asyncio.gather(*(process_chunk(i, c) for i, c in final_chunks_to_scan))
            
            # Sắp xếp lại facts theo đúng thứ tự mảnh ban đầu
            extracted_facts.sort(key=lambda x: x[0])
            sorted_facts = [f[1] for f in extracted_facts]

            if not sorted_facts:
                return {
                    "status": "success",
                    "output": "Không tìm thấy thông tin nào liên quan đến yêu cầu của bạn trong tệp tin.",
                    "metadata": {"file": file_path, "total_chunks": num_chunks}
                }

            # Gom và nén đệ quy kết quả (Reduce Phase)
            engine.publish_mission_log(
                "SYSTEM",
                f"📝 [SEQUENTIAL-READER]: Thu thập thành công {len(sorted_facts)} nhóm sự thật. Đang tổng hợp kết quả...",
                task_id
            )

            combined_extracted = "\n\n".join(sorted_facts)
            reduce_prompt = (
                "You are the supreme report synthesizer. Synthesize the following extracted findings from "
                "different parts of a large document into a structured, comprehensive, and professional report "
                "in Vietnamese that perfectly answers the user query.\n\n"
                f"User query: {query}\n\n"
                f"Extracted findings:\n{combined_extracted}\n\n"
                "Final synthesis report (Vietnamese):"
            )

            final_report = await engine.call_chat(
                messages=[{"role": "user", "content": reduce_prompt}],
                role="RECEPTIONIST",
                options={"temperature": 0.3},
                task_id=task_id
            )

            return {
                "status": "success",
                "output": str(final_report).strip(),
                "metadata": {
                    "file_path": file_path,
                    "file_size_chars": file_len,
                    "total_chunks": num_chunks,
                    "extracted_count": len(extracted_facts)
                }
            }

        except Exception as e:
            logger.error(f"Error in sequential_read: {e}")
            return {"status": "error", "msg": f"Lỗi xử lý file: {str(e)}"}

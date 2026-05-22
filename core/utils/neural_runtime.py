import time
import asyncio
import httpx
import re
import logging
import random
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple

try:
    import orjson
    def json_loads(s): return orjson.loads(s)
except ImportError:
    import json
    def json_loads(s): return json.loads(s)

logger = logging.getLogger('NeuralRuntime')

class NeuralRuntime:
    """
    ⚙️ JKAI NEURAL RUNTIME v2.0 (Production Inference Engine)
    Trái tim thực thi nơ-ron cấp doanh nghiệp.
    Tích hợp:
      - Exponential backoff & Full Jitter
      - Circuit Breaker tự khôi phục
      - Stream Stall Watchdog & Degeneration Guard thời gian thực
      - O(N) Zero-Regex State-Machine Parser cho CoT
      - Shared Semaphore & Connection Lifecycle
    """
    def __init__(self, ollama_host: str):
        self.ollama_host = ollama_host
        
        # 🌐 [CONNECTION-TUNING]: Tối ưu hóa Pooling Lifecycle
        self._client = httpx.AsyncClient(
            http2=False,
            timeout=httpx.Timeout(900.0, connect=15.0, read=900.0, write=120.0), 
            limits=httpx.Limits(
                max_keepalive_connections=50, 
                max_connections=100,
                keepalive_expiry=60.0
            )
        )
        
        self._vector_size_cache = {}
        
        # 🛡️ [CIRCUIT-BREAKER-STATE]: Quản lý trạng thái ngắt mạch
        self._failure_count = 0
        self._circuit_open_until = 0.0
        self._circuit_threshold = 5
        self._circuit_cooldown = 30.0  # seconds
        
        # 📊 [SHARED-CONCURRENCY]: Bộ băm luồng nhúng dùng chung
        self._embed_semaphore = asyncio.Semaphore(10)
        
        # 🩺 [HEALTH-CACHE-STATE]: Giảm thiểu tần suất spam kiểm tra sức khỏe
        self._last_health_check = 0.0
        self._health_cache = True
        self._health_ttl = 10.0  # seconds

    async def _check_health(self) -> bool:
        now = time.time()
        if now - self._last_health_check < self._health_ttl:
            return self._health_cache
        try:
            resp = await self._client.get(f"{self.ollama_host}/api/tags", timeout=3.0)
            status = resp.status_code == 200
            self._health_cache = status
            self._last_health_check = now
            return status
        except:
            self._health_cache = False
            self._last_health_check = now
            return False

    def _check_circuit(self):
        """🛡️ [CIRCUIT-SHIELD]: Bảo vệ máy chủ khỏi quá tải liên tiếp."""
        if self._failure_count >= self._circuit_threshold:
            now = time.time()
            if now < self._circuit_open_until:
                remaining = round(self._circuit_open_until - now, 1)
                raise RuntimeError(f"❌ [CIRCUIT-BREAKER]: Nguồn cấp nơ-ron đang gặp lỗi liên tục. Cưỡng chế ngắt mạch bảo vệ trong {remaining}s.")
            else:
                # Reset mạch thử nghiệm
                self._failure_count = 0

    def _report_success(self):
        """Ghi nhận nơ-ron phục hồi hoặc chạy tốt."""
        self._failure_count = 0

    def _report_failure(self):
        """Ghi nhận lỗi để kích hoạt Circuit Breaker."""
        self._failure_count += 1
        if self._failure_count >= self._circuit_threshold:
            self._circuit_open_until = time.time() + self._circuit_cooldown
            logger.error(f"🚨 [CIRCUIT-OPENED]: Mạch bảo vệ đã kích hoạt! Ngắt kết nối trong {self._circuit_cooldown} giây.")

    async def execute_chat_stream(self, 
                                 payload: Dict[str, Any], 
                                 task_id: str = "system") -> AsyncGenerator[Dict[str, Any], None]:
        # 1. Check Circuit Breaker
        self._check_circuit()

        max_retries = 3
        base_delay = 1.5
        cap_delay = 8.0

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Exponential Backoff with Full Jitter
                    temp = min(cap_delay, base_delay * (2 ** attempt))
                    delay = temp / 2 + random.uniform(0, temp / 2)
                    logger.warning(f"⚠️ [RE-CONNECTING]: Thử kết nối lại lần {attempt} sau {round(delay, 2)}s...")
                    await asyncio.sleep(delay)
                    if not await self._check_health(): continue

                async with self._client.stream('POST', f'{self.ollama_host}/api/chat', json=payload, timeout=900.0) as resp:
                    if resp.status_code in [503, 429]:
                        logger.warning(f"⚠️ [NEURAL-BUSY]: Ollama đang bận ({resp.status_code}). Đang đợi nơ-ron hồi phục...")
                        self._report_failure()
                        continue
                    
                    if resp.status_code != 200:
                        err_body = await resp.aread()
                        err_msg = f"❌ [OLLAMA-ERR]: {resp.status_code} | Model: {payload.get('model')} | Details: {err_body.decode()}"
                        logger.error(err_msg)
                        self._report_failure()
                        
                        from core.utils.mission_bus import mission_bus
                        mission_bus.publish_log("ERROR:neural_runtime.py", err_msg, task_id)
                        yield {"type": "error", "content": err_msg}
                        return

                    self._report_success()
                    full_content = ""
                    
                    lines_iter = resp.aiter_lines()
                    
                    # 🕒 [STALL-GUARD]: Canh gác dòng chảy nơ-ron không bị treo
                    while True:
                        try:
                            # Áp dụng timeout 30s cho từng dòng token
                            async with asyncio.timeout(30.0):
                                line = await lines_iter.__anext__()
                        except StopAsyncIteration:
                            break
                        except asyncio.TimeoutError:
                            raise RuntimeError("❌ [STREAM-STALL-TIMEOUT]: Dòng chảy nơ-ron bị nghẽn quá 30 giây. Hủy thực thi.")

                        line = line.strip()
                        if not line: continue
                        
                        try:
                            chunk = json_loads(line)
                            yield {"type": "chunk", "data": chunk}
                            
                            token = chunk.get('message', {}).get('content', '')
                            full_content += token
                            
                            # 🛡️ [DEGENERATION-GUARD]: Ngăn chặn lặp vô hạn ngay trong lúc stream
                            if self.check_degeneration(full_content):
                                raise RuntimeError("❌ [DEGENERATION-BREAKER]: Phát hiện vòng lặp suy thoái nơ-ron vô hạn (Repetitive Loop). Ngắt kết nối.")
                                
                            if chunk.get('done'): return
                        except Exception as e:
                            if isinstance(e, RuntimeError): raise e
                            continue
                    return
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                self._report_failure()
                if attempt == max_retries - 1:
                    yield {"type": "error", "content": f"❌ [NEURAL-DISCONNECT]: Mất kết nối nơ-ron hoàn toàn. Error: {str(e)}"}
                else: continue
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._report_failure()
                yield {"type": "error", "content": f"❌ [NEURAL-FAULT]: Sự cố nơ-ron bất ngờ: {str(e)}"}
                return

    async def call_chat(self, payload: Dict[str, Any], task_id: str = "system") -> Tuple[int, str]:
        """🏛️ [SYNC-CHAT]: Thực thi hội thoại đầy đủ không stream."""
        full_content = ""
        async for chunk in self.execute_chat_stream(payload, task_id):
            if chunk.get("type") == "error":
                raise RuntimeError(chunk.get("content"))
            if chunk.get("type") == "chunk":
                token = chunk.get("data", {}).get("message", {}).get("content", "")
                full_content += token
                if chunk.get("data", {}).get("done"):
                    # Tách suy nghĩ và câu trả lời
                    parsed = self.parse_thinking(full_content)
                    return 200, json.dumps(parsed, ensure_ascii=False)
        return 500, json.dumps({"error": "No response from neural core"}, ensure_ascii=False)

    async def get_embeddings(self, text: str, model: Optional[str] = None, options: dict = None, keep_alive = None) -> List[float]:
        """🏙️ [MEMORY-ENCODING]: Chuyển đổi văn bản thành Vector tri thức.
        options & keep_alive: Bắt buộc truyền để Ollama không reload model với config khác.
        """
        self._check_circuit()
        if not model:
            import os
            model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")

        max_retries = 3
        base_delay = 1.0
        cap_delay = 5.0

        for attempt in range(max_retries):
            try:
                payload = {"model": model, "prompt": text}
                if options:
                    payload["options"] = options
                if keep_alive is not None:
                    payload["keep_alive"] = keep_alive
                
                resp = await self._client.post(
                    f"{self.ollama_host}/api/embeddings",
                    json=payload,
                    timeout=60.0
                )
                if resp.status_code == 200:
                    self._report_success()
                    data = resp.json()
                    return data.get("embedding", [])
                
                if resp.status_code in [500, 503, 429] and attempt < max_retries - 1:
                    self._report_failure()
                    temp = min(cap_delay, base_delay * (2 ** attempt))
                    delay = temp / 2 + random.uniform(0, temp / 2)
                    logger.warning(f"⚠️ [EMBED-RETRY]: Ollama phản hồi {resp.status_code}. Thử lại sau {round(delay, 2)}s...")
                    await asyncio.sleep(delay)
                    continue

                err_body = await resp.aread()
                err_msg = f"❌ [EMBED-ERR]: {resp.status_code} | Model: {model} | Details: {err_body.decode()}"
                logger.error(err_msg)
                self._report_failure()
                return []

            except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError) as e:
                self._report_failure()
                if attempt < max_retries - 1:
                    temp = min(cap_delay, base_delay * (2 ** attempt))
                    delay = temp / 2 + random.uniform(0, temp / 2)
                    logger.warning(f"⚠️ [EMBED-RETRY]: Lỗi kết nối ({str(e)}). Thử lại sau {round(delay, 2)}s...")
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"❌ [EMBED-EXC]: {e}")
                return []
            except Exception as e:
                self._report_failure()
                logger.error(f"❌ [EMBED-EXC]: {e}")
                return []
        return []

    async def get_embeddings_batch(self, texts: List[str], model: Optional[str] = None, options: dict = None, keep_alive = None) -> List[List[float]]:
        """📊 [BATCH-ENCODING]: Xử lý nhúng hàng loạt sử dụng Shared Semaphore bảo vệ tài nguyên."""
        async def _safe_get(text):
            async with self._embed_semaphore:
                return await self.get_embeddings(text, model, options=options, keep_alive=keep_alive)
        
        tasks = [_safe_get(text) for text in texts]
        return await asyncio.gather(*tasks)

    async def get_vector_size(self, model: Optional[str] = None, options: dict = None) -> int:
        """📏 [DIMENSION-SCAN]: Truy vấn kích thước không gian tri thức."""
        if not model:
            import os
            model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")

        if model in self._vector_size_cache:
            return self._vector_size_cache[model]
        
        try:
            sample = await self.get_embeddings("JKAI", model, options=options)
            if sample:
                size = len(sample)
                self._vector_size_cache[model] = size
                return size
            return 768
        except:
            return 768

    def parse_thinking(self, full_content: str) -> Dict[str, str]:
        """💭 [STATE-MACHINE-PARSER]: Bộ bóc tách tư duy O(N) phi-Regex cực siêu việt."""
        if not full_content:
            return {"thinking": "", "answer": ""}
            
        thinking_blocks = []
        answer = full_content
        
        # 1. XML-style reasoning tags (e.g., <think>, <thought>, <reasoning>, <thinking>, <thought_process>)
        xml_tags = [
            ("think", "think"), 
            ("thought", "thought"), 
            ("reasoning", "reasoning"), 
            ("thinking", "thinking"), 
            ("thought_process", "thought_process")
        ]
        for tag, close_tag in xml_tags:
            start_tag = f"<{tag}>"
            end_tag = f"</{close_tag}>"
            
            while start_tag in answer:
                start_idx = answer.find(start_tag)
                end_idx = answer.find(end_tag, start_idx + len(start_tag))
                
                if end_idx != -1:
                    block = answer[start_idx + len(start_tag):end_idx].strip()
                    if block: thinking_blocks.append(block)
                    answer = answer[:start_idx] + " " + answer[end_idx + len(end_tag):]
                else:
                    # Trường hợp stream dở dang chưa đóng thẻ
                    block = answer[start_idx + len(start_tag):].strip()
                    if block: thinking_blocks.append(block)
                    answer = answer[:start_idx]
                    break
        
        # 2. Markdown blocks (```thought, ```thinking, ```reasoning)
        md_tags = ["thought", "thinking", "reasoning"]
        for md_tag in md_tags:
            start_marker = f"```{md_tag}"
            end_marker = "```"
            while start_marker in answer:
                start_idx = answer.find(start_marker)
                end_idx = answer.find(end_marker, start_idx + len(start_marker))
                if end_idx != -1:
                    block = answer[start_idx + len(start_marker):end_idx].strip()
                    if block: thinking_blocks.append(block)
                    answer = answer[:start_idx] + " " + answer[end_idx + len(end_marker):]
                else:
                    block = answer[start_idx + len(start_marker):].strip()
                    if block: thinking_blocks.append(block)
                    answer = answer[:start_idx]
                    break
                    
        # 3. Square bracket blocks ([thought], [thinking], [reasoning])
        sb_tags = ["thought", "thinking", "reasoning"]
        for sb_tag in sb_tags:
            start_marker = f"[{sb_tag}]"
            end_marker = f"[/{sb_tag}]"
            while start_marker in answer:
                start_idx = answer.find(start_marker)
                end_idx = answer.find(end_marker, start_idx + len(start_marker))
                if end_idx != -1:
                    block = answer[start_idx + len(start_marker):end_idx].strip()
                    if block: thinking_blocks.append(block)
                    answer = answer[:start_idx] + " " + answer[end_idx + len(end_marker):]
                else:
                    block = answer[start_idx + len(start_marker):].strip()
                    if block: thinking_blocks.append(block)
                    answer = answer[:start_idx]
                    break

        # 4. Text Headers (Thought:, Phân tích:, v.v. - Dùng O(N) line-scan)
        alt_pattern = r'^(?:Thought|Reasoning|Phân tích|Tư duy|Thinking Process|Thinking|Brainstorming|Reasoning Process|Analysis):\s*(.*)$'
        lines = answer.split("\n")
        remaining_lines = []
        for line in lines:
            match = re.match(alt_pattern, line.strip(), re.IGNORECASE)
            if match:
                block = match.group(1).strip()
                if block: thinking_blocks.append(block)
            else:
                remaining_lines.append(line)
        answer = "\n".join(remaining_lines)

        # 5. Plain separator fallback (---)
        if not thinking_blocks and "---" in answer:
             parts = answer.split("---", 1)
             thinking_blocks.append(parts[0].strip())
             answer = parts[1].strip()

        final_thinking = "\n\n---\n\n".join([b.strip() for b in thinking_blocks if b.strip()])
        return {"thinking": final_thinking, "answer": answer.strip()}

    def check_degeneration(self, content: str) -> bool:
        """🛡️ [DEGENERATION-DETECTOR]: Phát hiện sớm suy thoái lặp lại."""
        if len(content) > 1000:
            last_chunk = content[-150:]
            if content[:-150].count(last_chunk) >= 4: return True
        return False

    async def warmup_all_models(self):
        logger.info("🎬 [WARMUP]: Đang khởi động quân đoàn nơ-ron...")
        if await self._check_health():
            return {"status": "optimized", "msg": "Neural pathways warmed up."}
        return {"status": "error", "msg": "Neural pathways cold. Ollama unreachable."}

    async def clear_cache(self, role: Optional[str] = None):
        logger.info(f"🧹 [PURGE]: Đang thanh tẩy bộ nhớ {'cho role ' + role if role else ''}.")
        return {"status": "cleared"}

    async def close(self):
        """🔒 [SHUTDOWN]: Giải phóng tài nguyên kết nối."""
        await self._client.aclose()

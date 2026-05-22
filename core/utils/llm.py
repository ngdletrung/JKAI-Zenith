"""
🧠 LLM Utils V4 — Unified Ollama Caller (Optimized)
- Hỗ trợ nhiều mode: fast, reason, code
- Retry logic + timeout
- Structured output support (JSON)
- Logging chi tiết
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger("llm_utils_v4")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

def call_llm(
    prompt: str,
    model: Optional[str] = None,
    mode: str = "reason",          # fast / reason / code
    temperature: float = 0.3,
    max_tokens: int = 2048,
    json_mode: bool = False,
    retries: int = 2,
) -> str:
    """
    Gọi Ollama một cách an toàn và tối ưu
    """
    # Chọn model theo mode
    if not model:
        if mode == "fast":
            model = os.getenv("MODEL_FAST")
        elif mode == "code":
            model = os.getenv("MODEL_CODE")
        else:
            model = os.getenv("MODEL_REASON")

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }

    if json_mode:
        payload["format"] = "json"

    for attempt in range(retries + 1):
        try:
            start_time = time.time()
            resp = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            response_text = data.get("response", "").strip()
            latency = time.time() - start_time

            logger.debug(f"LLM call [{mode}] {model} | Latency: {latency:.2f}s | Tokens: ~{len(response_text)//4}")

            return response_text

        except requests.exceptions.Timeout:
            logger.warning(f"LLM timeout (attempt {attempt+1}/{retries+1})")
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Is Ollama running?")
            if attempt == retries:
                return "Error: Cannot connect to Ollama service."
        except Exception as e:
            logger.error(f"LLM call failed (attempt {attempt+1}): {e}")
            if attempt == retries:
                return f"LLM Error: {str(e)}"

        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))  # backoff

    return "Error: Failed to get response from LLM after retries."


# Convenience functions
def call_fast(prompt: str, **kwargs) -> str:
    return call_llm(prompt, mode="fast", temperature=0.7, **kwargs)

def call_reason(prompt: str, **kwargs) -> str:
    return call_llm(prompt, mode="reason", temperature=0.3, **kwargs)

def call_code(prompt: str, **kwargs) -> str:
    return call_llm(prompt, mode="code", temperature=0.2, **kwargs)

def call_json(prompt: str, **kwargs) -> Dict:
    """Gọi và parse JSON"""
    text = call_llm(prompt, json_mode=True, **kwargs)
    try:
        return json.loads(text)
    except Exception:
        logger.warning("Failed to parse JSON from LLM response")
        return {"error": "JSON parse failed", "raw": text}
"""
🏛️ JKAI ZENITH — OLLAMA RUNTIME ADAPTER
File: core/runtime/ollama_adapter.py

Purpose:
    Concrete RuntimeAdapter implementation for Ollama backend.
    All Ollama-specific HTTP calls are isolated here.
    The rest of JKAI only sees RuntimeAdapter / ExecutionProfile.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Dict, List, Optional, Any, TYPE_CHECKING
import httpx
import requests

from core.runtime.base_adapter import RuntimeAdapter, RuntimeModelInfo, RuntimeHealth

if TYPE_CHECKING:
    from core.governor.model_capabilities import ExecutionProfile

logger = logging.getLogger("OllamaAdapter")


class OllamaRuntimeAdapter(RuntimeAdapter):
    """
    Ollama HTTP API runtime adapter.

    Implements RuntimeAdapter so that all Ollama-specific logic
    (endpoint paths, request shapes, response parsing) is contained
    in this single class.
    """

    def __init__(self, host: str, gpu_access: bool = True, timeout: float = 600.0):
        self._host = host.rstrip("/")
        if not self._host.startswith("http://") and not self._host.startswith("https://"):
            self._host = f"http://{self._host}"
        self._gpu_access = gpu_access
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    # ------------------------------------------------------------------
    # RuntimeAdapter interface
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Dict[str, str]],
        profile: ExecutionProfile,
        task_id: str = "system",
    ) -> str:
        client = self._get_client()
        payload = {
            "model": profile.model_name,
            "messages": messages,
            "stream": False,
            "options": profile.to_ollama_options(),
        }

        try:
            resp = await client.post(f"{self._host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPStatusError as e:
            logger.error(f"[OllamaAdapter] HTTP error during generate ({profile.model_name}): {e}")
            raise
        except Exception as e:
            logger.error(f"[OllamaAdapter] Generate failed for {profile.model_name}: {e}")
            raise

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        profile: ExecutionProfile,
        task_id: str = "system",
    ) -> AsyncIterator[str]:
        client = self._get_client()
        payload = {
            "model": profile.model_name,
            "messages": messages,
            "stream": True,
            "options": profile.to_ollama_options(),
        }

        async with client.stream("POST", f"{self._host}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    import json
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass

    async def list_models(self) -> List[str]:
        try:
            client = self._get_client()
            resp = await client.get(f"{self._host}/api/tags", timeout=10.0)
            if resp.status_code == 200:
                return [m["name"].lower() for m in resp.json().get("models", [])]
        except Exception as e:
            logger.warning(f"[OllamaAdapter] list_models failed: {e}")
        return []

    async def list_models_with_digest(self) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            resp = await client.get(f"{self._host}/api/tags", timeout=10.0)
            if resp.status_code == 200:
                return [
                    {
                        "name":   m["name"].lower(),
                        "digest": m.get("digest", ""),
                        "size_gb": round(m.get("size", 0) / (1024 ** 3), 2),
                    }
                    for m in resp.json().get("models", [])
                ]
        except Exception as e:
            logger.warning(f"[OllamaAdapter] list_models_with_digest failed: {e}")
        return []

    async def inspect_model(self, model_name: str) -> Optional[RuntimeModelInfo]:
        """Async inspect via /api/show."""
        try:
            client = self._get_client()
            resp = await client.post(
                f"{self._host}/api/show",
                json={"name": model_name, "verbose": True},
                timeout=30.0,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()

            size_bytes = 0
            for blob in data.get("details", {}).get("manifest", {}).get("layers", []):
                size_bytes += blob.get("size", 0)
            if size_bytes == 0:
                size_bytes = data.get("model_info", {}).get("general.file_size", 0)

            return RuntimeModelInfo(
                model_name=model_name,
                model_info=data.get("model_info", {}),
                details=data.get("details", {}),
                capabilities=data.get("capabilities", []),
                template=data.get("template", ""),
                digest=data.get("digest", ""),
                size_gb=round(size_bytes / (1024 ** 3), 2) if size_bytes else 0.0,
            )
        except Exception as e:
            logger.warning(f"[OllamaAdapter] inspect_model({model_name}) failed: {e}")
            return None

    def inspect_model_sync(self, model_name: str) -> Optional[RuntimeModelInfo]:
        """Synchronous inspect via /api/show for boot orchestrator use."""
        try:
            resp = requests.post(
                f"{self._host}/api/show",
                json={"name": model_name, "verbose": True},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()

            size_bytes = 0
            for blob in data.get("details", {}).get("manifest", {}).get("layers", []):
                size_bytes += blob.get("size", 0)
            if size_bytes == 0:
                size_bytes = data.get("model_info", {}).get("general.file_size", 0)

            return RuntimeModelInfo(
                model_name=model_name,
                model_info=data.get("model_info", {}),
                details=data.get("details", {}),
                capabilities=data.get("capabilities", []),
                template=data.get("template", ""),
                digest=data.get("digest", ""),
                size_gb=round(size_bytes / (1024 ** 3), 2) if size_bytes else 0.0,
            )
        except Exception as e:
            logger.warning(f"[OllamaAdapter] inspect_model_sync({model_name}) failed: {e}")
            return None

    async def health_check(self) -> RuntimeHealth:
        try:
            import time
            client = self._get_client()
            t0 = time.monotonic()
            resp = await client.get(f"{self._host}/api/version", timeout=5.0)
            latency = (time.monotonic() - t0) * 1000
            if resp.status_code == 200:
                return RuntimeHealth(
                    is_alive=True,
                    host=self._host,
                    version=resp.json().get("version", ""),
                    latency_ms=latency,
                )
        except Exception as e:
            return RuntimeHealth(is_alive=False, host=self._host, error=str(e))
        return RuntimeHealth(is_alive=False, host=self._host)

    @property
    def runtime_id(self) -> str:
        return f"ollama:{self._host}"

    @property
    def supports_gpu(self) -> bool:
        return self._gpu_access

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Alias for backward compatibility
OllamaAdapter = OllamaRuntimeAdapter

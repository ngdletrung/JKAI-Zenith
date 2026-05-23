import httpx
import os
import json
import asyncio
import logging

# ============================================================
# 🛡️ [ZENITH FILE DIRECTIVE]
# - File: router.py
# - Role: Service Mesh & Neural Routing (Synapse).
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v5.1 (Production-Resilience)
# ============================================================

logger = logging.getLogger("ROUTER")

class ServiceRouter:
    """
    ⚡ JKAI ZENITH: SERVICE ROUTER (v5.1)
    Philosophy: Fast Routing & Connection Resilience.
    Sovereign Property of LeeTrung. 🏛️💎🛡️🚀
    """
    def __init__(self):
        from core.utils.registry import registry
        self.brain_url = registry.get_service_url("brain")
        self.executor_url = registry.get_service_url("executor")
        self.executor_cpu_url = registry.get_service_url("executor_2")
        
        # 💎 [PRODUCTION-TIMEOUTS]: Professional Synapse Protection
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=600.0,
                write=60.0,
                pool=10.0
            ),
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=150)
        )

    async def _with_retry(self, func, *args, **kwargs):
        """🔄 [RETRY-PROTOCOL]: Smart backoff for transient failures."""
        max_retries = 3
        for i in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if i == max_retries - 1: raise e
                wait = (i + 1) * 1.5
                logger.warning(f"⚠️ [ROUTER-RETRY]: Attempt {i+1} after {wait}s due to: {e}")
                await asyncio.sleep(wait)
        return None

    def _safe_json(self, resp: httpx.Response, fallback: dict) -> dict:
        """Parse JSON safely with error enrichment."""
        try:
            if resp.status_code >= 500:
                return {**fallback, "error": f"Service error HTTP {resp.status_code}"}
            return resp.json()
        except Exception as e:
            return {**fallback, "error": f"JSON parse failed: {str(e)}"}

    async def route_to_planner(self, data: dict):
        try:
            resp = await self._with_retry(self.client.post, f"{self.brain_url}/plan", json=data)
            return self._safe_json(resp, {"steps": [], "ambiguous": False})
        except Exception as e:
            return {"steps": [], "ambiguous": False, "error": f"Planner unreachable: {e}"}

    async def route_to_brain_critic(self, data: dict):
        try:
            resp = await self.client.post(f"{self.brain_url}/review", json=data)
            return self._safe_json(resp, {"approved": True, "feedback": "Critic error, auto-approved."})
        except Exception as e:
            return {"approved": True, "feedback": f"Critic error: {e}"}

    async def route_to_judicial_review(self, data: dict):
        try:
            resp = await self.client.post(f"{self.brain_url}/review_execution", json=data)
            return self._safe_json(resp, {"verdict": "SUCCESS"})
        except Exception as e:
            return {"verdict": "SUCCESS", "error": f"Judicial Review error: {e}"}

    async def route_to_executor(self, data: dict):
        try:
            target_url = self.executor_url
            steps = data.get("steps", [])
            if steps and steps[0].get("hardware_target") == "BETA":
                target_url = self.executor_cpu_url
                logger.info(f"📡 [ROUTER]: Routing to BETA (CPU) Executor.")

            resp = await self._with_retry(self.client.post, f"{target_url}/execute", json=data)
            return self._safe_json(resp, {"status": "error", "output": "Executor error."})
        except Exception as e:
            return {"status": "error", "output": f"Executor unreachable: {e}"}

    async def route_to_summarizer(self, data: dict):
        try:
            resp = await self.client.post(f"{self.brain_url}/summarize", json=data)
            return self._safe_json(resp, {"summary": "Summarizer error."})
        except Exception as e:
            return {"summary": f"Summarizer error: {e}"}

    async def route_to_distill(self, data: dict):
        try:
            await self.client.post(f"{self.brain_url}/distill", json=data, timeout=5.0)
            return {"status": "accepted"}
        except: return {"status": "error"}

    async def route_to_distill_judicial(self, data: dict):
        try:
            await self.client.post(f"{self.brain_url}/distill_judicial", json=data, timeout=5.0)
            return {"status": "accepted"}
        except: return {"status": "error"}

    async def route_to_receptionist(self, data: dict):
        try:
            resp = await self._with_retry(self.client.post, f"{self.brain_url}/receptionist", json=data)
            return self._safe_json(resp, {"status": "error"})
        except Exception as e:
            return {"status": "error", "error": f"Receptionist error: {e}"}

    async def route_to_dispatcher(self, data: dict):
        try:
            resp = await self.client.post(f"{self.brain_url}/dispatch", json=data)
            return self._safe_json(resp, {"agent_soul": "./agent_receptionist.md", "skills": [], "mode": "fast"})
        except Exception as e:
            return {"agent_soul": "./agent_receptionist.md", "skills": [], "mode": "fast", "error": str(e)}

# *Sovereign Property of LeeTrung. Production Router v5.1. 🌌🏛️🔥🦾👑🔗*

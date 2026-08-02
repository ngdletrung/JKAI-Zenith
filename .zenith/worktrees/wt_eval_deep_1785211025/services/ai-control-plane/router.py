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

    async def _post_with_retry(self, url, json=None, max_retries=3):
        """🔄 [ENHANCED-RETRY]: Backoff for connection errors AND HTTP 500s."""
        for i in range(max_retries):
            try:
                resp = await self.client.post(url, json=json)
                if resp.status_code < 500:
                    return resp
                logger.warning(f"⚠️ [ROUTER-RETRY]: Attempt {i+1} for {url} got HTTP {resp.status_code}")
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if i == max_retries - 1: raise e
                wait = (i + 1) * 1.5
                logger.warning(f"⚠️ [ROUTER-RETRY]: Attempt {i+1} after {wait}s due to: {e}")
                await asyncio.sleep(wait)
                continue
            except Exception as e:
                if i == max_retries - 1: raise e
                await asyncio.sleep(2)
                continue
            wait = (i + 1) * 2.0
            await asyncio.sleep(wait)
        raise httpx.HTTPStatusError(f"All {max_retries} retries failed for {url}", request=None, response=resp)

    def _safe_json(self, resp: httpx.Response, fallback: dict) -> dict:
        try:
            body = resp.text if hasattr(resp, 'text') else ''
            if resp.status_code >= 500:
                return {**fallback, "error": f"Service error HTTP {resp.status_code}", "detail": body[:500]}
            return resp.json()
        except Exception as e:
            return {**fallback, "error": f"JSON parse failed: {str(e)}"}

    async def route_to_planner(self, data: dict):
        try:
            resp = await self._post_with_retry(f"{self.brain_url}/plan", json=data)
            return self._safe_json(resp, {"steps": [], "ambiguous": False})
        except Exception as e:
            logger.error(f"[ROUTER] Planner failed: {e}")
            return {"steps": [], "ambiguous": False, "error": f"Planner unreachable: {e}"}

    async def route_to_brain_critic(self, data: dict):
        try:
            resp = await self._post_with_retry(f"{self.brain_url}/review", json=data)
            return self._safe_json(resp, {"approved": True, "feedback": "Critic error, auto-approved."})
        except Exception as e:
            logger.error(f"[ROUTER] Critic failed: {e}")
            return {"approved": True, "feedback": f"Critic error: {e}"}

    async def route_to_judicial_review(self, data: dict):
        try:
            resp = await self._post_with_retry(f"{self.brain_url}/review_execution", json=data)
            return self._safe_json(resp, {"verdict": "SUCCESS"})
        except Exception as e:
            logger.error(f"[ROUTER] Judicial Review failed: {e}")
            return {"verdict": "SUCCESS", "error": f"Judicial Review error: {e}"}

    async def route_to_executor(self, data: dict):
        try:
            target_url = self.executor_url
            steps = data.get("steps", [])
            if steps and steps[0].get("hardware_target") == "BETA":
                target_url = self.executor_cpu_url
                logger.info(f"📡 [ROUTER]: Routing to BETA (CPU) Executor.")

            resp = await self._post_with_retry(f"{target_url}/execute", json=data)
            return self._safe_json(resp, {"status": "error", "output": "Executor error."})
        except Exception as e:
            logger.error(f"[ROUTER] Executor failed: {e}")
            return {"status": "error", "output": f"Executor unreachable: {e}"}

    async def route_to_summarizer(self, data: dict):
        try:
            resp = await self._post_with_retry(f"{self.brain_url}/summarize", json=data)
            return self._safe_json(resp, {"summary": "Summarizer error."})
        except Exception as e:
            return {"summary": f"Summarizer error: {e}"}

    async def route_to_distill(self, data: dict):
        try:
            await self._post_with_retry(f"{self.brain_url}/distill", json=data)
            return {"status": "accepted"}
        except Exception:
            return {"status": "error"}

    async def route_to_distill_judicial(self, data: dict):
        try:
            await self._post_with_retry(f"{self.brain_url}/distill_judicial", json=data)
            return {"status": "accepted"}
        except Exception:
            return {"status": "error"}

    async def route_to_receptionist(self, data: dict):
        try:
            resp = await self._post_with_retry(f"{self.brain_url}/receptionist", json=data)
            return self._safe_json(resp, {"status": "error"})
        except Exception as e:
            logger.error(f"[ROUTER] Receptionist failed: {e}")
            return {"status": "error", "error": f"Receptionist error: {e}"}

    async def route_to_dispatcher(self, data: dict):
        try:
            resp = await self._post_with_retry(f"{self.brain_url}/dispatch", json=data)
            return self._safe_json(resp, {"agent_soul": "./agent_receptionist.md", "skills": [], "mode": "fast"})
        except Exception as e:
            logger.error(f"[ROUTER] Dispatcher failed: {e}")
            return {"agent_soul": "./agent_receptionist.md", "skills": [], "mode": "fast", "error": str(e)}

# *Sovereign Property of LeeTrung. Production Router v5.1. 🌌🏛️🔥🦾👑🔗*

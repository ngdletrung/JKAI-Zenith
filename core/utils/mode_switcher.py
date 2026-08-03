# -----------------------------------------------------------------------------
# [ZENITH SOVEREIGN DIRECTIVE]
# - File: core/utils/mode_switcher.py
# - Role: Mode-Aware Dynamic Engine Switcher (Resident Check & Lazy Warmup)
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v21.0 (AMD RX 6600 & Qwen3-30B Resident Optimized)
# [WORKING PRINCIPLES]:
# 1. Inspects active VRAM/RAM residency via Ollama /api/ps before any memory transitions.
# 2. If model is already loaded (e.g. Qwen3-30B booted via Start_JKAI_Zenith), runs instantly with zero delay.
# 3. Maintains exclusive memory state between FAST (Qwen3-30B MoE) and DEEP (Multi-agent Swarm).
# 4. Purges opposing mode models only upon explicit mode transitions to protect 8GB VRAM / 128GB RAM limits.
# 5. No emojis are used in system tracking logs outside standard corporate telemetry.
# -----------------------------------------------------------------------------

import os
import asyncio
import logging
from typing import Optional, Set

logger = logging.getLogger("JKAI_ModeSwitcher")

class ModeSwitcher:
    _instance = None
    _current_mode: str = "NONE"  # Initial state after system boot

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._lock = asyncio.Lock()

    @classmethod
    def get_active_mode(cls) -> str:
        return cls._current_mode

    @classmethod
    def reset_mode(cls):
        cls._current_mode = "NONE"

    async def _get_loaded_models_from_hosts(self, client, hosts: list) -> Set[str]:
        """Inspects real-time loaded models in Ollama across GPU and CPU hosts.
        Uses increased timeout and retry to avoid false empty result when Ollama is busy.
        """
        loaded = set()
        for host in hosts:
            for attempt in range(2):  # retry once if first attempt times out
                try:
                    resp = await client.get(f"{host}/api/ps", timeout=8.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        for m in data.get("models", []):
                            m_name = m.get("name", "").strip().lower()
                            if m_name:
                                loaded.add(m_name)
                                loaded.add(m_name.replace(":latest", ""))
                                loaded.add(m_name.split(":")[0])
                                if "/" in m_name:
                                    base = m_name.split("/")[-1]
                                    loaded.add(base)
                                    loaded.add(base.replace(":latest", ""))
                                    loaded.add(base.split(":")[0])
                        break  # success — no retry needed
                except Exception as e:
                    if attempt == 0:
                        logger.debug(f"[MODE-SWITCHER] /api/ps on {host} attempt {attempt+1} failed: {e}. Retrying...")
                        await asyncio.sleep(1.0)
                    else:
                        logger.debug(f"[MODE-SWITCHER] Could not check /api/ps on {host}: {e}")
        return loaded

    def _is_model_loaded(self, target_model: str, loaded_set: Set[str]) -> bool:
        if not target_model:
            return True
        target_clean = target_model.strip().lower()
        if target_clean in loaded_set:
            return True
        if target_clean.replace(":latest", "") in loaded_set:
            return True
        if target_clean.split(":")[0] in loaded_set:
            return True
        if "/" in target_clean:
            base = target_clean.split("/")[-1]
            if base in loaded_set or base.replace(":latest", "") in loaded_set or base.split(":")[0] in loaded_set:
                return True
        return False

    async def switch_to(self, target_mode: str, engine_instance=None, task_id: str = "system") -> bool:
        """
        Safely transitions Neural Engine memory residency to target_mode ('FAST' or 'DEEP').
        Inspects live resident models to skip redundant loads and ensure instant execution.
        """
        target_mode = target_mode.upper().strip()
        if target_mode not in ("FAST", "DEEP"):
            logger.warning(f"[MODE-SWITCHER] Unknown mode '{target_mode}'. Defaulting without eviction.")
            return False

        if engine_instance is None:
            from core.utils.engine import engine
            engine_instance = engine

        client = engine_instance._get_client()
        hosts = [engine_instance.ollama_host_gpu, engine_instance.ollama_host_cpu]

        # 1. Real-time Residency Inspection via /api/ps
        loaded_models = await self._get_loaded_models_from_hosts(client, hosts)

        async with self._lock:
            if target_mode == "FAST":
                cfg = engine_instance.get_role_config("RECEPTIONIST")
                fast_model = cfg.get("model", "") if isinstance(cfg, dict) else getattr(cfg, "model", "")

                # Check if Qwen3-30B MoE (or mapped fast model) is already residing in RAM/VRAM
                if self._is_model_loaded(fast_model, loaded_models):
                    if self._current_mode != "FAST":
                        engine_instance.publish_mission_log(
                            "SYSTEM",
                            f"[ENGINE-READY]: FAST mode — {fast_model} already resident in RAM/VRAM. Zero-latency start.",
                            task_id
                        )
                        ModeSwitcher._current_mode = "FAST"
                    else:
                        logger.debug("[MODE-SWITCHER] Active mode remains FAST with resident model. Zero latency continuation.")
                    return True

                # /api/ps returned empty but model may still be loading — do a short wait and recheck once
                if loaded_models == set():
                    logger.debug("[MODE-SWITCHER] /api/ps returned empty set — Ollama may be busy. Waiting 3s before recheck...")
                    await asyncio.sleep(3.0)
                    loaded_models = await self._get_loaded_models_from_hosts(client, hosts)
                    if self._is_model_loaded(fast_model, loaded_models):
                        engine_instance.publish_mission_log(
                            "SYSTEM",
                            f"[ENGINE-READY]: FAST mode — {fast_model} confirmed resident after recheck. Zero-latency start.",
                            task_id
                        )
                        ModeSwitcher._current_mode = "FAST"
                        return True

                # Not loaded -> Evict opposing mode models if needed and load FAST model
                if self._current_mode != "FAST":
                    engine_instance.publish_mission_log(
                        "SYSTEM",
                        f"🔄 [ENGINE-SWITCH]: Chuyển sang quy trình FAST — Giải phóng cụm mô hình DEEP và nạp `{fast_model}` vào VRAM/RAM...",
                        task_id
                    )
                    await self._evict_roles(["PLANNER", "CRITIC", "EXECUTOR", "EXECUTOR_ALPHA", "EXECUTOR_BETA", "SUMMARIZER"], engine_instance, client, hosts)
                else:
                    engine_instance.publish_mission_log(
                        "SYSTEM",
                        f"⏳ [ENGINE-INIT]: Mô hình `{fast_model}` chưa nạp. Đang nạp vào VRAM/RAM (keep_alive=-1) cho chế độ FAST...",
                        task_id
                    )

                # Warmup and lock in memory
                await self._warmup_roles(["RECEPTIONIST"], engine_instance, client, keep_alive=-1)
                ModeSwitcher._current_mode = "FAST"
                logger.info("[MODE-SWITCHER] Transitioned to FAST mode successfully.")
                return True

            elif target_mode == "DEEP":
                deep_roles = ["PLANNER", "EXECUTOR", "CRITIC", "SUMMARIZER"]
                deep_models = set()
                for r in deep_roles:
                    cfg = engine_instance.get_role_config(r)
                    m = cfg.get("model", "") if isinstance(cfg, dict) else getattr(cfg, "model", "")
                    if m:
                        deep_models.add(m)

                # Check if essential DEEP models are already residing in RAM/VRAM
                all_loaded = all(self._is_model_loaded(m, loaded_models) for m in deep_models)
                if all_loaded and deep_models:
                    if self._current_mode != "DEEP":
                        engine_instance.publish_mission_log(
                            "SYSTEM",
                            "⚡ [ENGINE-READY]: Chế độ DEEP — Cụm mô hình tư duy sâu đã có sẵn trên RAM/VRAM. Khởi chạy lập trình ngay!",
                            task_id
                        )
                        ModeSwitcher._current_mode = "DEEP"
                    else:
                        logger.debug("[MODE-SWITCHER] Active mode remains DEEP with resident models. Zero latency continuation.")
                    return True

                # Not fully loaded -> Evict FAST model if needed and load DEEP cluster
                if self._current_mode != "DEEP":
                    rec_cfg = engine_instance.get_role_config("RECEPTIONIST")
                    rec_model = rec_cfg.get("model", "RECEPTIONIST") if isinstance(rec_cfg, dict) else getattr(rec_cfg, "model", "RECEPTIONIST")
                    engine_instance.publish_mission_log(
                        "SYSTEM",
                        f"🔄 [ENGINE-SWITCH]: Chuyển sang quy trình DEEP — Đồng bộ chuyển đổi mô hình Lễ Tân (`{rec_model}`) sang cụm mô hình DEEP...",
                        task_id
                    )
                    await self._evict_roles(["RECEPTIONIST"], engine_instance, client, hosts)
                else:
                    engine_instance.publish_mission_log(
                        "SYSTEM",
                        "⏳ [ENGINE-INIT]: Đang nạp cụm mô hình quy trình DEEP vào RAM/VRAM...",
                        task_id
                    )

                # Warmup DEEP cluster and retain in memory (-1) until explicit switch to FAST
                await self._warmup_roles(deep_roles, engine_instance, client, keep_alive=-1)
                ModeSwitcher._current_mode = "DEEP"
                logger.info("[MODE-SWITCHER] Transitioned to DEEP mode successfully with keep_alive=-1.")
                return True

        return False

    async def _evict_roles(self, roles: list, engine_inst, client, hosts: list):
        """Sends keep_alive=0 to Ollama hosts for all models mapped to specified roles (disabled by default for 128GB resident RAM)."""
        if os.getenv("ENABLE_MODEL_EVICTION", "false").lower() != "true":
            logger.info("[MODE-SWITCHER] Skipping model eviction — Keeping models resident in 128GB System RAM for 0s cold-start latency.")
            return

        unloaded_models = set()
        for r in roles:
            cfg = engine_inst.get_role_config(r)
            m_name = cfg.get("model", "") if isinstance(cfg, dict) else getattr(cfg, "model", "")
            if m_name and m_name not in unloaded_models:
                unloaded_models.add(m_name)

        for m in unloaded_models:
            for host in hosts:
                try:
                    await client.post(
                        f"{host}/api/generate",
                        json={"model": m, "prompt": "", "keep_alive": 0},
                        timeout=5.0
                    )
                    logger.debug(f"[MODE-SWITCHER] Evicted '{m}' from {host}.")
                except Exception as e:
                    logger.debug(f"[MODE-SWITCHER] Silent error evicting '{m}' on {host}: {e}")

    async def _warmup_roles(self, roles: list, engine_inst, client, keep_alive):
        """Sends lightweight warmup prompt to Ollama to preload models into VRAM/RAM with specified keep_alive."""
        warmed_models = set()
        for r in roles:
            cfg = engine_inst.get_role_config(r)
            m_name = cfg.get("model", "") if isinstance(cfg, dict) else getattr(cfg, "model", "")
            if not m_name or m_name in warmed_models:
                continue
            warmed_models.add(m_name)

            hw_col = cfg.get("hardware", "").upper() if isinstance(cfg, dict) else getattr(cfg, "hardware", "").upper()
            target_host = engine_inst.ollama_host_gpu if ("GPU" in hw_col or cfg.get("num_gpu", -1) > 0) else engine_inst.ollama_host_cpu
            
            # 🧮 [SMART-ADAPTIVE-TIMEOUT]: Tính toán timeout thông minh dựa trên dung lượng mô hình thực tế
            size_gb = 4.0
            m_lower = m_name.lower()
            if any(k in m_lower for k in ['30b', '32b', '35b', 'moe', '70b']):
                size_gb = 17.0
            elif any(k in m_lower for k in ['12b', '14b']):
                size_gb = 9.0
            elif any(k in m_lower for k in ['7b', '8b']):
                size_gb = 5.0
            
            w_timeout = max(45.0, min(300.0, 30.0 + size_gb * 10.0))
            
            logger.info(f"⏳ [ADAPTIVE-WARMUP]: Đang nạp mô hình `{m_name}` trên `{target_host}` (Timeout tối đa: {w_timeout:.0f}s, keep_alive={keep_alive})...")
            try:
                await client.post(
                    f"{target_host}/api/generate",
                    json={"model": m_name, "prompt": ".", "keep_alive": keep_alive},
                    timeout=w_timeout
                )
                logger.info(f"✅ [ADAPTIVE-WARMUP]: Nạp thành công mô hình `{m_name}` trên `{target_host}`!")
            except Exception as e:
                # 🛡️ [RESIDENT-RECHECK]: Kiểm tra lại /api/ps xem mô hình đã kịp nạp thành công chưa trước khi báo lỗi
                try:
                    await asyncio.sleep(2.0)
                    resp = await client.get(f"{target_host}/api/ps", timeout=5.0)
                    if resp.status_code == 200:
                        loaded = [m.get("name", "") for m in resp.json().get("models", [])]
                        if any(m_name.split(":")[0].lower() in m.lower() for m in loaded):
                            logger.info(f"✅ [ADAPTIVE-WARMUP-RECHECK]: Mô hình `{m_name}` đã nạp thành công trong VRAM/RAM!")
                            continue
                except Exception:
                    pass
                logger.warning(f"⚠️ [ADAPTIVE-WARMUP]: Lỗi hoặc timeout nạp mô hình '{m_name}' trên {target_host}: {e}")

# Global singleton instance
mode_switcher = ModeSwitcher.get_instance()

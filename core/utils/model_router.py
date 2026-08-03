import os
import re
import logging
from typing import Dict, Any, Optional, List
from core.utils.models import RoleConfig, NeuralProfile, ModelOptions

logger = logging.getLogger('ModelRouter')

class ModelRouter:
    """
    📡 JKAI MODEL ROUTER v2.0
    Central parser for rule_hardware.md — single source of truth.
    Provides both dict-based (legacy) and dataclass-based interfaces.
    """
    def __init__(self, rules_path: str):
        self.rules_path = rules_path
        self._rules_last_mtime = 0
        self._role_mapping_cache: Dict[str, dict] = {}
        self._role_config_cache: Dict[str, RoleConfig] = {}
        self._profiles_cache: Dict[str, dict] = {}
        self._model_sizes: Dict[str, float] = {}
        self.global_params: Dict[str, str] = {}

    def get_role_config(self, role: str) -> Dict[str, Any]:
        self._refresh_rules_if_needed()
        role_upper = role.upper()
        return self._role_mapping_cache.get(role_upper, self._role_mapping_cache.get("CHAT", {}))

    def get_role_config_dataclass(self, role: str) -> Optional[RoleConfig]:
        self._refresh_rules_if_needed()
        role_upper = role.upper()
        # Return from dataclass cache, or build it on demand for roles not pre-built
        cached = self._role_config_cache.get(role_upper)
        if cached:
            return cached
        # Fallback to dict cache
        fallback = self._role_mapping_cache.get(role_upper, self._role_mapping_cache.get("CHAT"))
        if fallback:
            return self._dict_to_role_config(fallback)
        return None

    def get_global_params(self) -> Dict[str, str]:
        self._refresh_rules_if_needed()
        return dict(self.global_params)

    def _dict_to_role_config(self, d: dict) -> RoleConfig:
        opts = d.get('options', {})
        return RoleConfig(
            model=d.get('model', ''),
            options=ModelOptions(**{k: v for k, v in opts.items() if k in ModelOptions.model_fields}),
            keep_alive=str(d.get('keep_alive', '5m')),
            hardware=d.get('hardware', '').upper(),
        )

    def _refresh_rules_if_needed(self):
        try:
            mtime = os.path.getmtime(self.rules_path)
            if mtime > self._rules_last_mtime:
                self._parse_rules()
                self._rules_last_mtime = mtime
        except Exception as e:
            logger.error(f"❌ [ROUTER-REFRESH-ERR]: {e}")

    def _parse_rules(self):
        try:
            if not os.path.exists(self.rules_path): return
            
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_r_cache = {}
            new_role_config_cache = {}
            self.global_params = {}
            self._profiles_cache = {}
            self._model_sizes = {}
            
            lines = content.split('\n')
            in_section_2 = False
            in_section_25 = False 
            in_section_3 = False  
            headers = []

            # Parse global params from top of file: "- **KEY**: VALUE"
            for line in lines[:60]:
                stripped = line.strip()
                if stripped.startswith('- **') and ':' in stripped:
                    clean_line = stripped[4:].replace('**:', ':').replace('**', '')
                    if ':' in clean_line:
                        p_key, p_val = clean_line.split(':', 1)
                        self.global_params[p_key.strip().upper()] = p_val.split('(')[0].strip()

            for line in lines:
                line = line.strip()
                if not line or not line.startswith('|') or ':---' in line:
                    if 'II. MO HINH THUC TE' in line or '2. Model Tier Registry' in line:
                        in_section_2, in_section_25, in_section_3 = True, False, False
                        headers = []
                    elif '2.5. Neural Hardware Profiles' in line:
                        in_section_2, in_section_25, in_section_3 = False, True, False
                        headers = []
                    elif '3. Active Role Mapping' in line:
                        in_section_2, in_section_25, in_section_3 = False, False, True
                        headers = []
                    elif line.startswith('#'):
                        # Reset section flags when encountering other headings to avoid parsing subsequent tables incorrectly
                        in_section_2, in_section_25, in_section_3 = False, False, False
                        headers = []
                    continue

                parts = [p.strip() for p in line.split('|')]
                if 'MODEL' in line.upper() or 'ROLE' in line.upper() or 'PROFILE NAME' in line.upper():
                    headers = [p.upper() for p in parts]
                    continue

                if len(parts) >= 3 and headers:
                    # 🚀 [SECTION-II-PARSING]: Trích xuất kích thước model
                    if in_section_2:
                        m_name = parts[1].replace('`', '').replace('**', '').strip().lower()
                        size_raw = parts[2].replace('**', '').strip().upper()
                        size_val = 0.0
                        nums = re.findall(r'(\d+\.?\d*)', size_raw)
                        if nums:
                            val = float(nums[0])
                            if "MB" in size_raw: val = val / 1024.0
                            size_val = val
                        self._model_sizes[m_name] = size_val
                        continue

                    key = re.sub(r'[^a-zA-Z0-9_-]', '', parts[1].replace('**', '')).strip().upper()
                    target = re.sub(r'[^a-zA-Z0-9:._/-]', '', parts[2].replace('**', '')).strip().lower()
                    if not key or not target: continue

                    def get_val(h_name, is_float=False):
                        idx = next((i for i, h in enumerate(headers) if h_name in h), -1)
                        if idx != -1 and idx < len(parts):
                            val = parts[idx].replace('**', '').strip().lower()
                            if not val or val == 'n/a': return None
                            nums = re.findall(r'^-?\d+\.?\d*', val)
                            if nums: return float(nums[0]) if is_float else int(float(nums[0]))
                        return None

                    opts_block = {
                        "num_ctx": get_val('NUM_CTX'),
                        "num_predict": get_val('NUM_PREDICT'),
                        "num_thread": get_val('NUM_THREAD'),
                        "num_gpu": get_val('NUM_GPU'),
                        "temperature": get_val('TEMP', True),
                        "top_p": get_val('TOP_P', True),
                        "repeat_penalty": get_val('REPEAT_P', True) or get_val('REPEAT_PENALTY', True)
                    }
                    opts_block = {k: v for k, v in opts_block.items() if v is not None}

                    if in_section_25:
                        self._profiles_cache[key] = opts_block
                    elif in_section_3:
                        final_opts = {}
                        idx_profile = next((i for i, h in enumerate(headers) if 'PROFILE' in h), -1)
                        p_name = ""
                        if idx_profile != -1:
                            p_name = parts[idx_profile].replace('**', '').strip().upper()
                            if p_name in self._profiles_cache:
                                final_opts.update(self._profiles_cache[p_name])
                        
                        # ⚠️ [NOTE]: Không truyền 'profile' vào Ollama options — đây là meta-data nội bộ
                        final_opts.update(opts_block)
                        
                        idx_hw = next((i for i, h in enumerate(headers) if 'HW' in h or 'HARDWARE' in h), -1)
                        hardware = parts[idx_hw].replace('**', '').strip().upper() if idx_hw != -1 else "GPU"

                        # [HYBRID MOE & CPU TURBO]: Inject mmap zero-copy cho cả CPU và mô hình chia RAM/VRAM MoE
                        if final_opts.get('num_gpu', 100) == 0 or "MOE" in p_name or "RAM" in hardware:
                            final_opts['use_mmap'] = True
                            final_opts['num_batch'] = 512
                        
                        idx_ka = next((i for i, h in enumerate(headers) if 'KEEP' in h), -1)
                        keep_alive_raw = parts[idx_ka].replace('**', '').strip() if idx_ka != -1 else "5m"
                        
                        try:
                            if keep_alive_raw == "-1" or keep_alive_raw.isdigit():
                                keep_alive = int(keep_alive_raw)
                            else:
                                keep_alive = keep_alive_raw
                        except Exception:
                            keep_alive = "5m"

                        idx_cap = next((i for i, h in enumerate(headers) if 'CAPABILITY' in h or 'CAPABILITIES' in h), -1)
                        cap_val = parts[idx_cap].replace('**', '').strip() if idx_cap != -1 else ""

                        idx_qual = next((i for i, h in enumerate(headers) if 'QUALITY' in h), -1)
                        qual_val = parts[idx_qual].replace('**', '').strip() if idx_qual != -1 else "medium"

                        new_r_cache[key] = {
                            'role': key,
                            'model': target,
                            'capability': cap_val,
                            'quality': qual_val,
                            'options': final_opts,
                            'keep_alive': keep_alive,
                            'hardware': hardware,
                            'size_gb': self._model_sizes.get(target, 0.0) # 💎 Gắn kích thước
                        }
            
            self._role_mapping_cache = new_r_cache
            # Build dataclass cache from dict cache
            for rk, rv in new_r_cache.items():
                new_role_config_cache[rk] = self._dict_to_role_config(rv)
            self._role_config_cache = new_role_config_cache
            logger.info(f"✅ [ROUTER]: Đã nạp {len(new_r_cache)} quy tắc nơ-ron (VRAM-Aware & AMG v2).")
        except Exception as e:
            logger.error(f"❌ [ROUTER-PARSE-ERR]: {e}")

    def resolve_execution_profile(self, role: str, hw_state=None, task_id: str = ""):
        """
        AMG v2 primary entry point.
        Converts role config → ExecutionProfile using AMG pipeline.

        Routing logic:
            model == "auto"     → PortfolioGovernor (capability/quality scoring)
            model is explicit   → build_legacy_profile (direct mapping, no scoring)

        Args:
            role     : Role name (e.g. "PLANNER", "RECEPTIONIST")
            hw_state : HardwareState (optional — fetched from HardwareMonitor if None)
            task_id  : Optional task ID for DecisionTrace linkage

        Returns:
            ExecutionProfile — consumed by engine.call_chat() / NeuralRuntime.execute()

        Backward compatibility:
            Callers can still use get_role_config() — it is NOT affected.
            This method is additive (new code path only).
        """
        import time
        t0 = time.time()

        config = self.get_role_config(role)
        if not config:
            logger.warning(f"[ROUTER-AMG]: No config for role={role!r}, using CHAT fallback")
            config = self._role_mapping_cache.get("CHAT", {})

        model = config.get("model", "").strip()

        from core.governor.execution_policy import ExecutionPolicy
        policy = ExecutionPolicy()

        # Inject live HardwareState if caller didn't supply one
        if hw_state is None:
            try:
                from core.governor.hardware_monitor import HardwareMonitor
                hw_state = HardwareMonitor.get_state()
                policy._get_governor()._hw = hw_state
            except Exception as e:
                logger.debug(f"[ROUTER-AMG]: HardwareMonitor unavailable: {e}")

        profile = policy.derive_profile(config)

        # Record decision trace (non-blocking, best-effort)
        try:
            from core.governor.decision_trace import get_tracer, DecisionTrace
            latency_ms = (time.time() - t0) * 1000
            resolved_via = getattr(profile, "resolved_via", "explicit" if model.lower() not in ("auto", "") else "auto")
            trace = DecisionTrace(
                trace_id=__import__("uuid").uuid4().hex,
                role_name=role.upper(),
                task_id=task_id,
                selected_model=profile.model_name,
                resolved_via=resolved_via,
                backend=profile.backend,
                num_ctx=profile.num_ctx,
                temperature=profile.temperature,
                capability_requirements=[c.strip() for c in config.get("capability", "").split(",") if c.strip()],
                quality_target=config.get("quality", "medium"),
                hardware_state_vram_free_mb=getattr(hw_state, "vram_free_mb", 0.0) if hw_state else 0.0,
                hardware_state_ram_free_gb=getattr(hw_state, "ram_free_gb", 0.0) if hw_state else 0.0,
                decision_latency_ms=latency_ms,
                decision_summary=(
                    f"role={role!r} resolved to {profile.model_name!r} "
                    f"via {resolved_via} in {latency_ms:.1f}ms"
                    + (f" [config_model={model!r}]" if model and model != profile.model_name else "")
                ),
            )
            get_tracer().record(trace)
        except Exception as te:
            logger.debug(f"[ROUTER-TRACE]: Could not record trace: {te}")

        return profile


mission_router = None

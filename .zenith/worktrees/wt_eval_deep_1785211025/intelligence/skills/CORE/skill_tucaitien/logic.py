# [ZENITH FILE DIRECTIVE]
# - File: logic.py
# - Role: Core Cognitive Logic for skill_tucaitien
# - Status: Optimized | Version: Zenith v7.0

import os
import sys
import json
import ast
import asyncio
import logging
import difflib
import traceback
import time
from pathlib import Path
from typing import Dict, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from core.utils.engine import engine
from core.kernel.capability_broker import capability_broker, CapabilityType, sandbox_executor
from core.kernel.cognitive_scheduler import cognitive_transaction_manager

logger = logging.getLogger("ZenithEvolutionEngine")


class ZenithEvolutionEngine:
    def __init__(self):
        from core.config import settings
        intelligence_dir = getattr(settings, "INTELLIGENCE_DIR", None)
        if intelligence_dir and Path(intelligence_dir).exists():
            self.base_dir = Path(intelligence_dir)
        else:
            env_dir = os.getenv("INTELLIGENCE_DIR")
            if env_dir and Path(env_dir).exists():
                self.base_dir = Path(env_dir)
            else:
                self.base_dir = Path(__file__).resolve().parents[3]

        workspace_root = getattr(settings, "WORKSPACE_ROOT", None)
        if workspace_root and Path(workspace_root).exists():
            self.root_dir = Path(workspace_root)
        else:
            from core.utils import path_manager
            pm_root = path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
            if pm_root and Path(pm_root).exists():
                self.root_dir = Path(pm_root)
            else:
                self.root_dir = self.base_dir.parent

    def _find_logic_path(self, skill_id: str) -> Optional[Path]:
        skills_dir = self.base_dir / "skills"
        if not skills_dir.exists():
            return None
        for root, dirs, files in os.walk(str(skills_dir)):
            if skill_id in dirs:
                candidate = Path(root) / skill_id / "logic.py"
                if candidate.exists():
                    return candidate

        known_modules = {
            "planner": self.root_dir / "services" / "ai-brain" / "planner.py",
            "receptionist_core": self.root_dir / "services" / "ai-brain" / "receptionist" / "receptionist_core.py",
            "task_manager": self.root_dir / "services" / "ai-control-plane" / "task_manager.py",
            "router": self.root_dir / "services" / "ai-control-plane" / "router.py",
            "skill_deck": self.root_dir / "core" / "utils" / "skill_deck_index.py",
            "engine": self.root_dir / "core" / "utils" / "engine.py",
            "repo_surgeon": self.root_dir / "core" / "utils" / "repo_surgeon.py",
            "session_context": self.root_dir / "core" / "utils" / "session_context.py",
            "security": self.root_dir / "core" / "utils" / "security.py",
            "model_router": self.root_dir / "core" / "utils" / "model_router.py",
        }
        mapped = known_modules.get(skill_id)
        if mapped and mapped.exists():
            return mapped
        return None

    async def _regenerate_map_graph(self):
        temp_root_script = self.root_dir / "JKAI_MAP_graph.py"
        try:
            skill_map_script = self.base_dir / "skills" / "CORE" / "skill_tucaitien" / "JKAI_MAP_graph.py"
            if not skill_map_script.exists():
                logic_path = self._find_logic_path("skill_tucaitien")
                if logic_path:
                    skill_map_script = logic_path.parent / "JKAI_MAP_graph.py"

            if skill_map_script.exists():
                script_code = skill_map_script.read_text(encoding="utf-8")
                temp_root_script.write_text(script_code, encoding="utf-8")
                
                process = await asyncio.create_subprocess_exec(
                    sys.executable, str(temp_root_script),
                    cwd=str(self.root_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.warning(f"Map graph script failed with code {process.returncode}: {stderr.decode('utf-8', errors='replace')}")
            else:
                logger.warning(f"Source map graph script not found at {skill_map_script}")
        except Exception as e:
            logger.warning(f"Failed to copy or execute map graph script at project root: {e}")
        finally:
            if temp_root_script.exists():
                try:
                    os.remove(str(temp_root_script))
                except Exception as ce:
                    logger.warning(f"Failed to delete temporary map graph script from root: {ce}")

    def _load_map_context(self, skill_id: str) -> str:
        map_path = self.root_dir / "JKAI_MAP_GRAPH.md"
        if not map_path.exists():
            return ""
        try:
            lines = map_path.read_text(encoding="utf-8", errors="replace").splitlines()
            relevant = []
            for line in lines:
                if skill_id in line or (f"skills/" in line and skill_id.lower() in line.lower()):
                    relevant.append(line)
            if relevant:
                return "\n".join(relevant[:15])
        except Exception as e:
            logger.warning(f"Failed to load map context: {e}")
        return ""

    async def _call_llm_safe(self, prompt: str, role: str = "EXECUTOR", timeout: int = 120) -> str:
        from core.utils.engine import engine
        llm_engine = engine

        fallback_roles = [role, "EXECUTOR", "RESERVE_AGENT", "CHAT"]
        last_error = None

        for current_role in fallback_roles:
            try:
                result = await llm_engine.call_chat(
                    messages=[{"role": "user", "content": prompt}],
                    role=current_role,
                    lock_timeout=timeout,
                    timeout=timeout
                )
                if result and isinstance(result, str) and not result.startswith("Error:"):
                    return result
                last_error = result
                logger.warning(f"[FALLBACK] Role '{current_role}' that bai: {result}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"[FALLBACK-ERR] Role '{current_role}': {e}")
                await asyncio.sleep(1)

        raise RuntimeError(f"LLM call failed after fallback roles. Last error: {last_error}")

    async def _tim_kiem_tri_thuc_cai_tien(self, skill_id: str) -> Dict[str, Any]:
        """Sử dụng OmniSearchEngine tìm kiếm tri thức và DNA xác minh kỹ thuật."""
        try:
            import importlib.util
            omni_path = self._find_logic_path("OMNI_SEARCH_ENGINE")
            if not omni_path:
                logger.debug(f"[TRI-THUC] OMNI_SEARCH_ENGINE not found for {skill_id}")
                return {"content": "", "metadata": {}}
            spec = importlib.util.spec_from_file_location("omni_search_engine", str(omni_path))
            if spec is None or spec.loader is None:
                logger.warning(f"[TRI-THUC] Cannot load OMNI_SEARCH_ENGINE from {omni_path}")
                return {"content": "", "metadata": {}}
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            searcher = module.OmniSearchEngine()
            query = f"latest improvements best practices coding patterns for {skill_id} Python optimization 2025 2026"
            result = await searcher.omni_search(query, mode="fast")
            if result.get("status") == "success":
                output = result.get("output", {})
                if isinstance(output, dict):
                    content = output.get("content", "")
                    metadata = output.get("metadata", {})
                else:
                    content = str(output)
                    metadata = {}
                return {
                    "content": content[:2500],
                    "metadata": metadata
                }
        except ImportError as e:
            logger.warning(f"[TRI-THUC] OMNI_SEARCH_ENGINE import failed for {skill_id}: {e}")
        except Exception as e:
            logger.warning(f"[TRI-THUC] Search that bai cho {skill_id}: {e}")
        return {"content": "", "metadata": {}}

    def _clean_llm_code(self, raw_code: str) -> str:
        import re
        code = raw_code.strip()
        
        # 1. Match standard markdown python blocks (including py, python, python3, or multiple backticks)
        pattern_py = re.compile(r"```+(?:python|py|python3)?\s*(.*?)\s*```+", re.DOTALL | re.IGNORECASE)
        match_py = pattern_py.search(code)
        if match_py:
            code = match_py.group(1).strip()
        else:
            # 2. Match any generic code block
            pattern_generic = re.compile(r"```\s*(.*?)\s*```", re.DOTALL)
            match_generic = pattern_generic.search(code)
            if match_generic:
                code = match_generic.group(1).strip()
            else:
                # 3. If no backticks, search for common Python start anchors in the lines to strip conversational preamble
                lines = code.splitlines()
                start_idx = 0
                for idx, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith("# [ZENITH") or stripped.startswith("# - File:") or stripped.startswith("import ") or stripped.startswith("from ") or stripped.startswith("class ") or stripped.startswith("def "):
                        start_idx = idx
                        break
                if start_idx > 0:
                    code = "\n".join(lines[start_idx:])
        
        # Strip simple fallbacks
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()

        # 4. Self-Healing: If there is syntax error, try to heal by stripping trailing conversational lines
        try:
            compile(code, "<string>", "exec")
        except SyntaxError:
            lines = code.splitlines()
            for _ in range(20):
                if not lines:
                    break
                candidate = "\n".join(lines).strip()
                try:
                    compile(candidate, "<string>", "exec")
                    code = candidate
                    break
                except SyntaxError:
                    lines.pop()
                    
        return code.strip()

    def _generate_diff(self, old_code: str, new_code: str, filename: str) -> str:
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}"
        )
        return "".join(diff)

    async def promote_from_test_file(self, skill_id: str, **kwargs) -> Dict[str, Any]:
        """
        Chỉ dùng file thử đã có: test sandbox → copy sang production (không gọi LLM lại).
        """
        from core.utils import path_manager
        from core.utils.sandbox_deploy_gate import (
            get_evolution_candidate_path,
            test_candidate_file,
            promote_candidate_to_production,
            format_gate_footer,
        )

        logic_path = self._find_logic_path(skill_id)
        if not logic_path:
            return {"output": f"[ERROR]: Khong tim thay `{skill_id}`.", "status": "error"}

        workspace_root = path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
        candidate_path = get_evolution_candidate_path(skill_id, workspace_root)
        if not candidate_path.is_file():
            return {
                "output": (
                    f"[ERROR]: Chua co file thu. Chay truoc: `/tucaitien {skill_id}` "
                    "(dry-run) de tao `logic_candidate.py`."
                ),
                "status": "error",
            }

        sandbox_scope = os.path.normpath(os.path.join(workspace_root, "scratch/sandbox"))
        skills_root = os.path.dirname(os.path.dirname(os.path.dirname(str(logic_path))))
        gate = await test_candidate_file(
            candidate_path=candidate_path,
            filesystem_scope=sandbox_scope,
            skills_root=skills_root,
            task_id=kwargs.get("task_id", "sys"),
        )
        if not gate["passed"]:
            return {
                "output": (
                    f"{gate['summary']}\nFile thu: `{candidate_path}`\n"
                    "Production **khong doi**."
                ),
                "status": "error",
                "sandbox_gate": gate,
            }

        tx_id = f"tx-promote-{skill_id}-{int(time.time())}"
        await cognitive_transaction_manager.begin_transaction(tx_id, "sys")
        try:
            await cognitive_transaction_manager.register_backup(tx_id, str(logic_path))
            old_code = logic_path.read_text(encoding="utf-8", errors="replace")
            cand_code = candidate_path.read_text(encoding="utf-8", errors="replace")
            ok, promote_msg = promote_candidate_to_production(candidate_path, logic_path)
            if not ok:
                raise RuntimeError(promote_msg)
            await cognitive_transaction_manager.commit_transaction(tx_id)
            diff_str = self._generate_diff(old_code, cand_code, f"{skill_id}/logic.py")
            return {
                "output": (
                    f"[TRIEN-KHAI-TU-FILE-THU] {promote_msg}\n{gate['summary']}\n\n"
                    f"Diff:\n{diff_str}{format_gate_footer(True)}"
                ),
                "status": "success",
                "sandbox_gate": gate,
            }
        except Exception as e:
            await cognitive_transaction_manager.rollback_transaction(tx_id)
            return {"output": f"[HUY-BO] {e}", "status": "error"}

    async def phau_thuat_logic(self, skill_id: str = None, optimization_goal: str = None, dry_run: bool = False, **kwargs) -> Dict[str, Any]:
        """Tiến hành tự động cải tiến mã nguồn tích hợp bản đồ liên kết vĩ mô, ACID transaction và kiểm nghiệm Sandbox."""
        skill_id = skill_id or kwargs.get("skill_id")
        optimization_goal = optimization_goal or kwargs.get("optimization_goal")
        dry_run = kwargs.get("dry_run", dry_run)

        if not skill_id or not optimization_goal:
            return {"output": "[ERROR]: Thieu tham so dau vao skill_id hoac optimization_goal.", "status": "error"}

        logic_path = self._find_logic_path(skill_id)
        if not logic_path:
            return {"output": f"[ERROR]: Khong tim thay ma nguon cua {skill_id}.", "status": "error"}

        # 1. Đồng bộ hóa bản đồ đồ thị
        engine.publish_mission_log(
            "EVOLUTION",
            f"[DO-THI] Dang dong bo hoa ban do thuc dia thoi gian thuc cho `{skill_id}`...",
            "sys", "sys"
        )
        await self._regenerate_map_graph()
        map_context = self._load_map_context(skill_id)

        # 2. Cấp phát thẻ năng quyền
        fs_token = capability_broker.issue_token(
            task_id="sys",
            cap_type=CapabilityType.FILESYSTEM,
            scope=os.path.dirname(str(logic_path))
        )
        from core.utils import path_manager
        workspace_root = path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
        sandbox_scope = os.path.normpath(os.path.join(workspace_root, "scratch/sandbox"))
        exec_token = capability_broker.issue_token(
            task_id="sys",
            cap_type=CapabilityType.EXECUTION,
            scope=sandbox_scope
        )

        if not capability_broker.verify_privilege(fs_token.token_id, CapabilityType.FILESYSTEM, str(logic_path)):
            return {"output": "[PRIVILEGE-ERROR]: The FILESYSTEM khong du tham quyen truy cap.", "status": "error"}

        # 3. Khởi tạo Giao dịch ACID nhận thức
        tx_id = f"tx-evolution-{skill_id}-{int(time.time())}"
        await cognitive_transaction_manager.begin_transaction(tx_id, "sys")

        try:
            await cognitive_transaction_manager.register_backup(tx_id, str(logic_path))
            current_code = logic_path.read_text(encoding="utf-8", errors="replace")

            # 4. Tìm kiếm tri thức thế giới & Triết lý kiến thức chéo
            engine.publish_mission_log(
                "EVOLUTION",
                "[KET-NOI] Dang ra soat va thu thap tri thuc lap trinh tu mang toan cau...",
                "sys", "sys"
            )
            search_res = await self._tim_kiem_tri_thuc_cai_tien(skill_id)
            search_context = search_res.get("content", "")
            search_metadata = search_res.get("metadata", {})
            
            # Trích xuất DNA Tri thức
            verification_data = search_metadata.get("verification_data", {})
            verified_facts = verification_data.get("verified_facts", {})
            contradiction_warnings = verification_data.get("contradiction_warnings", [])
            
            dna_context_lines = []
            if verified_facts:
                dna_context_lines.append("XAC MINH THONG SO KY THUAT (VERIFIED FACTS):")
                for k, v in verified_facts.items():
                    if v:
                        dna_context_lines.append(f"- {k.upper()}: {v}")
            if contradiction_warnings:
                dna_context_lines.append("CANH BAO MAU THUAN CHEO (CONTRADICTION WARNINGS):")
                for w in contradiction_warnings:
                    dna_context_lines.append(f"- [!] {w}")
            
            dna_context = "\n".join(dna_context_lines)

            # 5. Khởi tạo Prompt tiến hóa toàn diện v7.0
            prompt = f"""[ZENITH EVOLUTION DIRECTIVE v7.0]
- Target Skill: {skill_id}
- Goal: {optimization_goal}
- Status: Analytical Evolution Phase

GLOBAL ARCHITECTURAL DEPENDENCIES (from JKAI_MAP_GRAPH.md):
{map_context if map_context else "(No direct dependencies found)"}

LATEST GLOBAL BEST PRACTICES (from OmniSearch):
{search_context if search_context else "(No online references found)"}

VERIFIED KNOWLEDGE DNA (Cross-source parameters & conflicts):
{dna_context if dna_context else "(No verified conflicts or warnings detected)"}

CURRENT IMPLEMENTATION:
```python
{current_code}
```

REQUIRED INSTRUCTIONS:
1. Rewrite the ENTIRE logic.py file. Do NOT omit any existing helper functions or vital logic unless explicitly requested.
2. If contradiction warnings are listed above, you MUST write code defensive against those contradictions (e.g. support both configurations or provide clear error reporting/fallback).
3. Maintain strict clinical and technical discipline. Do NOT use emojis in code logic or comments (strict violation of Rule 10).
4. Prefix the file with a compliant SDS directive header block:
# [ZENITH FILE DIRECTIVE]
# - File: logic.py
# - Role: Core Cognitive Logic for {skill_id}
# - Status: Optimized | Version: Zenith v7.0

5. You must define a modular Singleton contract:
   At the very end of the file, instantiate a lazy singleton:
   _instance = YourClassName()
   And define module-level asynchronous wrappers (matching the existing wrappers in logic.py) that unpack **kwargs and invoke methods on _instance.
6. Return ONLY executable Python code block. No explanations, no markdown styling around the code block other than triple backticks."""

            engine.publish_mission_log(
                "EVOLUTION",
                f"[HOI-CHAN] Tien hanh thiet ke mo hinh nhan thuc nang cap cho `{skill_id}`...",
                "sys", "sys"
            )
            
            new_code_raw = await self._call_llm_safe(prompt, role="EXECUTOR", timeout=120)
            new_code = self._clean_llm_code(new_code_raw)

            # 6. Ghi file THỬ (candidate) — production logic.py chưa đổi
            from core.utils.sandbox_deploy_gate import (
                write_evolution_candidate,
                test_candidate_file,
                promote_candidate_to_production,
                format_gate_footer,
                get_evolution_candidate_path,
            )

            skills_root = os.path.dirname(os.path.dirname(os.path.dirname(str(logic_path))))
            candidate_path = write_evolution_candidate(
                skill_id=skill_id,
                workspace_root=workspace_root,
                new_code=new_code,
                production_path=logic_path,
            )

            # 7. Test file thử trong hộp sandbox
            gate = await test_candidate_file(
                candidate_path=candidate_path,
                filesystem_scope=sandbox_scope,
                skills_root=skills_root,
                task_id=kwargs.get("task_id", "sys"),
                timeout_sec=10.0,
            )
            if not gate["passed"]:
                raise RuntimeError(
                    f"{gate['summary']}\n"
                    f"File thử giữ tại: `{candidate_path}` — `logic.py` production **không bị sửa**."
                )

            diff_str = self._generate_diff(current_code, new_code, f"{skill_id}/logic.py")
            gate_block = f"{gate['summary']}\n"
            file_block = (
                f"📄 **File thử:** `{candidate_path}`\n"
                f"📄 **Production (gốc):** `{logic_path}`\n\n"
            )

            if dry_run:
                await cognitive_transaction_manager.rollback_transaction(tx_id)
                msg = (
                    f"[THU-NGHIEM] `{skill_id}` — đã ghi file thử + sandbox PASS.\n"
                    f"**`logic.py` production chưa thay đổi.**\n\n"
                    f"{file_block}{gate_block}Diff (production vs candidate):\n\n{diff_str}"
                    f"{format_gate_footer(True)}\n"
                    f"Phê duyệt qua tab Kế Hoạch để triển khai."
                )
                return {
                    "output": msg,
                    "status": "success",
                    "diff": diff_str,
                    "sandbox_gate": gate,
                    "candidate_path": str(candidate_path),
                }

            # APPLY: copy file thử → production (không ghi trực tiếp từ LLM)
            ok, promote_msg = promote_candidate_to_production(candidate_path, logic_path)
            if not ok:
                raise RuntimeError(promote_msg)
            await cognitive_transaction_manager.commit_transaction(tx_id)
            msg = (
                f"[TRIEN-KHAI-THAT] Đã test file thử OK → copy sang production.\n"
                f"{promote_msg}\n\n{file_block}{gate_block}Diff:\n\n{diff_str}"
                f"{format_gate_footer(True)}"
            )
            return {
                "output": msg,
                "status": "success",
                "diff": diff_str,
                "sandbox_gate": gate,
                "candidate_path": str(candidate_path),
            }

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[EVOLUTION-CRASH] {e}\n{tb}")
            await cognitive_transaction_manager.rollback_transaction(tx_id)
            return {
                "output": f"[HUY-BO-GIAO-DICH] Cai tien that bai, khoi phuc nguyen trang tep tin. Chi tiet loi: {str(e)}",
                "status": "error"
            }

    async def system_improvement_plan(
        self,
        optimization_goal: str,
        dry_run: bool = True,
        target_skill: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        _tid = kwargs.get("task_id", "sys")
        sections = []
        sep = "\n\n---\n\n"

        # ── SECTION 1: HEADER ──
        sections.append(
            f"🏛️ KẾ HOẠCH CẢI TIẾN HỆ THỐNG (ZENITH)\n"
            f"📋 Mục tiêu: {optimization_goal}\n"
            f"🔒 Chế độ: {'DRY-RUN (khong ghi file)' if dry_run else 'APPLY (ghi file that)'}"
        )

        # ── SECTION 2: MAP/DECK ──
        engine.publish_mission_log("TUCAITIEN", "📦 Dang tai SkillDeckIndex...", _tid)
        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            deck = SkillDeckIndex.get()
            deck.ensure_loaded(force=True)
            deck_total = len(deck._by_deck)
            unmapped = [e.deck_id for e in deck._by_deck.values() if not e.registry_id]
            map_lines = ["| Key | Value |", "| --- | --- |"]
            map_lines.append(f"| MAP/Deck | {deck_total} muc, {len(unmapped)} chua map registry |")
            if unmapped:
                map_lines.append(f"| Uu tien sua | #{', #'.join(unmapped[:8])}{' ...' if len(unmapped) > 8 else ''} |")
            sections.append("## 1. MAP/DECK REGISTRY\n" + "\n".join(map_lines))
        except Exception as e:
            sections.append(f"## 1. MAP/DECK REGISTRY\n| Trang thai | Loi: {e} |")

        # ── SECTION 3: MODULES ──
        engine.publish_mission_log("TUCAITIEN", "📂 Dang kiem tra module...", _tid)
        core_targets = [
            ("services/ai-brain/planner.py", "Agent registry, plan validation"),
            ("services/ai-brain/receptionist/receptionist_core.py", "Ingress / DEEP routing"),
            ("core/utils/skill_deck_index.py", "Command Deck bridge"),
            ("services/ai-control-plane/task_manager.py", "Mission routing"),
            ("intelligence/skills/CORE/SELF_HEALING_SENTINEL/logic.py", "Warrior audit"),
        ]
        mod_rows = []
        for path, note in core_targets:
            full = self.root_dir / path.replace("/", os.sep)
            flag = "CO" if full.exists() else "THIEU"
            mod_rows.append(f"| {flag} | `{path}` | {note} |")
        sections.append("## 2. MODULES\n| Trang thai | Module | Ghi chu |\n| --- | --- | --- |\n" + "\n".join(mod_rows))

        # ── SECTION 4: REPO AUDIT ──
        engine.publish_mission_log("TUCAITIEN", "🔍 Dang ra soat ma nguon...", _tid)
        try:
            from core.utils.repo_surgeon import audit_repo
            repo_data = audit_repo(optimization_goal)
            syn_n = len(repo_data.get("syntax_errors") or [])
            bug_n = len(repo_data.get("common_bugs") or [])
            engine.publish_mission_log("TUCAITIEN", f"✅ Ra soat xong: {syn_n} loi cu phap, {bug_n} loi tiem an.", _tid)

            audit_lines = []

            # 4a. Syntax errors
            errs = repo_data.get("syntax_errors") or []
            if errs:
                audit_lines.append("### Syntax Errors\n| File | Dong | Loi |\n| --- | --- | --- |")
                for e in errs[:10]:
                    audit_lines.append(f"| `{e['path']}` | {e['line']} | {e['msg']} |")
                if len(errs) > 10:
                    audit_lines.append(f"| ... | ... | va {len(errs) - 10} file khac |")
            else:
                audit_lines.append("### Syntax Errors\n- Khong co loi cu phap.")

            # 4b. Bug patterns
            bugs = repo_data.get("common_bugs") or []
            if bugs:
                bug_counts = {}
                for b in bugs:
                    bug_counts[b["bug"]] = bug_counts.get(b["bug"], 0) + 1
                summary = ", ".join(f"{k}: {v}" for k, v in sorted(bug_counts.items()))
                audit_lines.append(f"\n### Bug Patterns ({summary})")
                _BUG_LABELS = {
                    "bare-except": "Bare except:", "mutable-default-list": "Mutable list default",
                    "mutable-default-dict": "Mutable dict default", "sync-sleep-in-async": "time.sleep() trong async",
                    "print-in-prod": "print() trong production",
                }
                audit_lines.append("| File | Dong | Loai |\n| --- | --- | --- |")
                for b in bugs[:15]:
                    label = _BUG_LABELS.get(b["bug"], b["bug"])
                    audit_lines.append(f"| `{b['path']}` | {b['line']} | {label} |")
                if len(bugs) > 15:
                    audit_lines.append(f"| ... | ... | va {len(bugs) - 15} loi khac |")
            else:
                audit_lines.append("\n### Bug Patterns\n- Khong phat hien.")

            # 4c. Import scan
            imp = repo_data.get("import_issues") or []
            if imp:
                audit_lines.append(f"\n### Import Anomalies\n| File | Import | Ghi chu |\n| --- | --- | --- |")
                for ix in imp[:8]:
                    audit_lines.append(f"| `{ix['path']}` | `{ix['import']}` | {ix['note']} |")
                if len(imp) > 8:
                    audit_lines.append(f"| ... | ... | va {len(imp) - 8} van de khac |")
            else:
                audit_lines.append("\n### Import Scan\n- Khong phat hien.")

            # 4d. Grep hits
            gh = repo_data.get("grep_hits") or []
            if gh:
                audit_lines.append(f"\n### Grep ({len(gh)} diem cham)")
                audit_lines.append("| File | Dong | Tu khoa |\n| --- | --- | --- |")
                for h in gh[:8]:
                    audit_lines.append(f"| `{h['path']}` | {h['line']} | {h['keyword']} |")
                if len(gh) > 8:
                    audit_lines.append(f"| ... | ... | va {len(gh) - 8} diem cham khac |")

            sections.append("## 3. PHAT HIEN LOI\n" + "\n".join(audit_lines))

            if not dry_run and repo_data.get("syntax_errors"):
                from core.utils.repo_surgeon import propose_repo_patches, apply_repo_patches
                patches = await propose_repo_patches(optimization_goal, repo_data, task_id=_tid)
                fix_block, _promoted = await apply_repo_patches(patches, dry_run=False, task_id=_tid)
                sections.append(f"## 4. DA SUA\n{fix_block}")
        except Exception as e:
            sections.append(f"## 3. PHAT HIEN LOI\n| Loi | {e} |")

        # ── SECTION 5: SELF-DIAGNOSIS ──
        engine.publish_mission_log("TUCAITIEN", "🚑 Dang quet loi tu cac nhiem vu gan day...", _tid)
        diag_lines = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as hclient:
                res = await hclient.get("http://mission-control:9999/api/missions")
                if res.status_code == 200:
                    missions = res.json()
                    error_found = False
                    for m in missions[:10]:
                        mid = m.get("id")
                        try:
                            m_res = await hclient.get(f"http://mission-control:9999/api/mission/{mid}")
                            if m_res.status_code == 200:
                                m_data = m_res.json()
                                m_logs = m_data.get("logs", [])
                                err_logs = [l for l in m_logs if l.get("level", "").upper() == "ERROR" or "error" in l.get("msg", "").lower() or "timeout" in l.get("msg", "").lower()]
                                if err_logs:
                                    error_found = True
                                    title = (m.get('title') or '')[:40]
                                    diag_lines.append(f"| ⚠️ | `{mid}` | {title} | {len(err_logs)} loi |")
                        except Exception:
                            pass
                    if error_found:
                        diag_lines.insert(0, "| Muc | ID | Tieu de | So loi |\n| --- | --- | --- | --- |")
                    else:
                        diag_lines.append("- Khong phat hien loi trong 10 nhiem vu gan nhat.")
                else:
                    diag_lines.append(f"- API tra ve ma loi: {res.status_code}")
        except Exception as diag_err:
            diag_lines.append(f"- Khong the ket noi mission-control: {diag_err}")

        sections.append("## 5. TU CHAN DOAN (10 nhiem vu gan nhat)\n" + "\n".join(diag_lines))

        # ── SECTION 6: TARGET SKILL ──
        chosen = target_skill or kwargs.get("target_skill")
        if not chosen:
            gl = optimization_goal.lower()
            for cand in ("SELF_HEALING_SENTINEL", "skill_self_healing", "skill_tucaitien", "planner", "skill_deck"):
                if cand.lower() in gl:
                    chosen = cand
                    break

        if chosen and str(chosen).lower() not in ("system", "jkai", "all", "zenith"):
            logic_path = self._find_logic_path(chosen)
            if not logic_path:
                sections.append(f"## 6. MODULE `{chosen}`\n- Khong phai skill, phan tich rieng.")
            else:
                _sk2 = {k: v for k, v in kwargs.items() if k not in ("skill_id", "optimization_goal", "dry_run")}
                sub = await self.phau_thuat_logic(skill_id=chosen, optimization_goal=optimization_goal, dry_run=dry_run, **_sk2)
                sections.append(f"## 6. THU NGHIEM SKILL `{chosen}`\n" + str(sub.get("output", sub)))
                lines_out = sep.join(sections)
                engine.publish_mission_log("TUCAITIEN", "✅ Hoan tat.", _tid)
                return {"output": lines_out, "status": sub.get("status", "success"), "nested": sub}

        sections.append(
            "## 7. KET LUAN\n"
            "- Ke hoach da duoc luu vao tab Ke Hoach.\n"
            "- `/tucaitien`: ra soat toan dien he thong.\n"
            "- `/tucaitien_<skill_id>`: ra soat rieng mot ky nang."
        )

        lines_out = sep.join(sections)
        engine.publish_mission_log("TUCAITIEN", "✅ Hoan tat.", _tid)
        return {"output": lines_out, "status": "success"}

    async def tu_nang_cap_ban_than(self, **kwargs) -> Dict[str, Any]:
        """Tự cải tiến chính tệp logic.py này lên cấp độ tối ưu cao nhất."""
        _kw = dict(kwargs)
        _kw.pop("skill_id", None); _kw.pop("optimization_goal", None)
        return await self.phau_thuat_logic(
            skill_id="skill_tucaitien",
            optimization_goal="Nang cap nang luc nhan thuc tu toi uu hoa ma nguon, kien tao kien thuc cheo tu DNA va phat hien mau thuan.",
            **_kw
        )


try:
    _instance = ZenithEvolutionEngine()
except Exception as _e:
    logger.error(f"[SKILL-INIT-FAILED] Khong the khoi tao ZenithEvolutionEngine: {_e}")
    _instance = None


async def phau_thuat_logic(**kwargs):
    return await _instance.phau_thuat_logic(**kwargs)

async def tu_nang_cap_ban_than(**kwargs):
    return await _instance.tu_nang_cap_ban_than(**kwargs)

async def SKILL_TUCAITIEN(**kwargs):
    return await skill_tucaitien(**kwargs)


async def skill_tucaitien(**kwargs):
    if _instance is None:
        return {"output": "[ERROR]: ZenithEvolutionEngine chua khoi tao.", "status": "error"}

    skill_id = kwargs.get("skill_id", "System")
    optimization_goal = kwargs.get("optimization_goal") or (
        "Rà soát toàn diện hệ thống, đề xuất cải tiến tối ưu."
    )

    dry_run = True
    scope = str(skill_id).strip().lower()
    _sk = {k: v for k, v in kwargs.items() if k not in ("skill_id", "optimization_goal", "dry_run")}

    if scope in ("system", "jkai", "all", "zenith", ""):
        result = await _instance.system_improvement_plan(
            optimization_goal=optimization_goal,
            dry_run=True,
            **_sk,
        )
        title = "Kế hoạch Cải tiến Hệ thống ZENITH"
    else:
        result = await _instance.system_improvement_plan(
            optimization_goal=optimization_goal,
            dry_run=True,
            target_skill=skill_id,
            **_sk,
        )
        title = f"Kế hoạch Cải tiến Kỹ năng {skill_id}"

    if result and result.get("status") != "error":
        try:
            from core.redis_client import get_redis
            r = get_redis()
            if r:
                plan_text = result.get("output", "")
                task_id_val = kwargs.get("task_id", f"plan_{int(time.time())}")
                proposal = {
                    "id": f"plan_{int(time.time())}",
                    "task_id": task_id_val,
                    "title": title,
                    "description": plan_text,
                    "source_module": "TUCAITIEN",
                    "proposal_type": "SYSTEM_IMPROVEMENT",
                    "is_red_zone": False,
                    "execute_goal": optimization_goal,
                    "metadata": {"dry_run": True},
                    "status": "pending",
                    "created_at": time.time(),
                }
                r.lpush("zenith:proposals", json.dumps(proposal, ensure_ascii=False))
                r.publish("monitor:proposal_channel", json.dumps({"event": "proposal_created", "payload": proposal}, ensure_ascii=False))
        except ImportError:
            logger.warning("[REDIS] core.redis_client not available, skipping proposal save.")
        except Exception as e:
            logger.warning(f"[REDIS] Failed to save proposal: {e}")

    return result

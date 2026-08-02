# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/context/mission_context.py
# - Role: Mission Context Manager bridged to Mission State v2
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v2.0 (Integrated)

import json
import logging
from datetime import datetime, timezone
from typing import Optional

# Import Zenith OS v2 components
from mission_state import MissionRuntime, MissionState, MissionEvent

logger = logging.getLogger("JKAI.Context.Mission")

_MISSION_TTL = 86400
_CONVERSATION_LINK_KEY = "conversation:last_mission"
_ENGINE = None


def _get_engine_redis():
    global _ENGINE
    if _ENGINE is None:
        try:
            from core.utils.engine import engine as _e
            _ENGINE = _e
        except Exception:
            return None
    try:
        return _ENGINE._get_redis()
    except Exception:
        return None


_VN_DIA = str.maketrans({'à':'a','á':'a','ạ':'a','ả':'a','ã':'a','â':'a','ầ':'a','ấ':'a','ậ':'a','ẩ':'a','ẫ':'a','ă':'a','ằ':'a','ắ':'a','ặ':'a','ẳ':'a','ẵ':'a','è':'e','é':'e','ẹ':'e','ẻ':'e','ẽ':'e','ê':'e','ề':'e','ế':'e','ệ':'e','ể':'e','ễ':'e','ì':'i','í':'i','ị':'i','ỉ':'i','ĩ':'i','ò':'o','ó':'o','ọ':'o','ỏ':'o','õ':'o','ô':'o','ồ':'o','ố':'o','ộ':'o','ổ':'o','ỗ':'o','ơ':'o','ờ':'o','ớ':'o','ợ':'o','ở':'o','ỡ':'o','ù':'u','ú':'u','ụ':'u','ủ':'u','ũ':'u','ư':'u','ừ':'u','ứ':'u','ự':'u','ử':'u','ữ':'u','ỳ':'y','ý':'y','ỵ':'y','ỷ':'y','ỹ':'y','đ':'d'})

_SUBJECT_KEYWORDS = ["vàng", "bạc", "dầu", "xăng", "usd", "eur", "bitcoin", "eth",
                     "chứng khoán", "tỷ giá", "lãi suất", "cổ phiếu", "python",
                     "docker", "kubernetes", "nginx", "linux", "windows", "macos"]

_SUBJECT_KEYWORDS_NODIA = [kw.translate(_VN_DIA) for kw in _SUBJECT_KEYWORDS]


class MissionContext:
    def __init__(self, mission_id: str, goal: str = ""):
        now = _iso_now()
        self.meta = {"version": 1, "goal": goal, "created_at": now, "updated_at": now}
        self.conversation = {"last_subject": "", "last_query": "", "last_answer": "", "facts": [], "entities": []}
        self.working_memory = {"tool_results": {}, "active_files": [], "records": []}
        self.runtime = {"status": "running", "task_id": mission_id, "trace_id": ""}
        self.derived = {"current_topic": "", "confidence": 0.0, "requires_refresh": False, "pending_question": None}
        self.data_pool = []
        
        # 🧬 Zenith OS v2 Mission State binding
        self.mission_state_v2 = MissionRuntime(user_goal=goal)

    def to_dict(self) -> dict:
        d = {
            "meta": self.meta,
            "conversation": self.conversation,
            "working_memory": self.working_memory,
            "runtime": self.runtime,
            "derived": self.derived,
            "data_pool": self.data_pool
        }
        # Dump mission state v2
        d["mission_state_v2_data"] = self.mission_state_v2.state.model_dump(mode="json")
        return d

    @staticmethod
    def from_dict(d: dict) -> "MissionContext":
        mc = MissionContext(d.get("runtime", {}).get("task_id", "unknown"), d.get("meta", {}).get("goal", ""))
        mc.meta = d.get("meta", mc.meta)
        mc.conversation = d.get("conversation", mc.conversation)
        mc.working_memory = d.get("working_memory", mc.working_memory)
        mc.runtime = d.get("runtime", mc.runtime)
        mc.derived = d.get("derived", mc.derived)
        mc.data_pool = d.get("data_pool", [])
        
        # Load mission state v2 back
        if "mission_state_v2_data" in d:
            try:
                mc.mission_state_v2.state = MissionState.model_validate(d["mission_state_v2_data"])
            except Exception as e:
                logger.warning(f"[MISSION-CONTEXT] validate v2 state error: {e}")
        return mc

    def add_fact(self, fact_type: str, value: str, field: str = "", source: str = ""):
        self.conversation.setdefault("facts", []).append({"type": fact_type, "value": value, "field": field, "source": source, "ts": _iso_now()})
        self.meta["updated_at"] = _iso_now()
        
        # Sync Fact with TMS of mission_state v2 (Synchronous reducer application)
        try:
            event = MissionEvent(
                mission_id=self.mission_state_v2.state.metadata.mission_id,
                event_type="FactAdded",
                payload={
                    "fact_id": f"F{len(self.mission_state_v2.state.facts.facts_db) + 1}",
                    "data": f"{fact_type}: {value}",
                    "dependencies": []
                }
            )
            self.mission_state_v2.state = self.mission_state_v2.reducer.apply(self.mission_state_v2.state, event)
            self.mission_state_v2.event_log.append(event)
        except Exception as e:
            logger.warning(f"[MISSION-CONTEXT] Sync FactAdded v2 failed: {e}")

    def set_derived(self, topic: str, confidence: float):
        self.derived["current_topic"] = topic
        self.derived["confidence"] = confidence
        self.meta["updated_at"] = _iso_now()

    def pool_push(self, source: str, query: str, content: str, subject: str = ""):
        if not content or len(content) < 20:
            return
        if not subject:
            subject = self._extract_subject(query)
        entry = {"source": source, "query": query, "subject": subject, "content": content, "ts": _iso_now()}
        self.data_pool.append(entry)
        if len(self.data_pool) > 20:
            self.data_pool = self.data_pool[-20:]
        self.meta["updated_at"] = _iso_now()

    def pool_find(self, query: str, min_score: int = 1) -> list:
        query_subjects = set(self._extract_keywords(query))
        if not query_subjects:
            return []
        matches = []
        for entry in self.data_pool:
            entry_keys = set(self._extract_keywords(entry.get("subject", "")))
            overlap = query_subjects & entry_keys
            if len(overlap) >= min_score:
                matches.append((len(overlap), entry))
        matches.sort(key=lambda x: -x[0])
        return [e for _, e in matches]

    def pool_best_content(self, query: str) -> str:
        matches = self.pool_find(query, min_score=1)
        if not matches:
            return ""
        best = matches[0]
        content = best.get("content", "")
        if len(content) < 50:
            return ""
        if len(content) > 3000:
            content = content[:3000] + "..."
        return content

    @staticmethod
    def _extract_keywords(text: str) -> list:
        if not text:
            return []
        text_lower = text.lower()
        found = []
        for kw in _SUBJECT_KEYWORDS:
            if kw in text_lower:
                found.append(kw)
        if not found:
            text_nodia = text_lower.translate(_VN_DIA)
            for i, kw_nodia in enumerate(_SUBJECT_KEYWORDS_NODIA):
                if kw_nodia in text_nodia:
                    found.append(_SUBJECT_KEYWORDS[i])
        return found

    @staticmethod
    def _extract_subject(text: str) -> str:
        text_lower = text.lower()
        for kw in _SUBJECT_KEYWORDS:
            if kw in text_lower:
                idx = text_lower.index(kw)
                start = max(0, idx - 8)
                end = min(len(text), idx + len(kw) + 20)
                return text[start:end].strip()
        return text[:60]


class MissionContextManager:
    def _key(self, mission_id: str) -> str:
        return f"mission:{mission_id}"

    def get_or_create(self, mission_id: str, goal: str = "") -> MissionContext:
        r = _get_engine_redis()
        if r:
            try:
                raw = r.get(self._key(mission_id))
                if raw:
                    return MissionContext.from_dict(json.loads(raw))
            except Exception as e:
                logger.warning(f"[MISSION-CONTEXT] get error: {e}")
        return MissionContext(mission_id, goal)

    def save(self, mc: MissionContext):
        r = _get_engine_redis()
        if r:
            try:
                r.setex(self._key(mc.runtime["task_id"]), _MISSION_TTL, json.dumps(mc.to_dict(), ensure_ascii=False))
            except Exception as e:
                logger.warning(f"[MISSION-CONTEXT] save error: {e}")

    def link_conversation(self, user_key: str, mission_id: str):
        r = _get_engine_redis()
        if r:
            try:
                r.setex(_CONVERSATION_LINK_KEY + ":" + user_key, _MISSION_TTL, mission_id)
            except Exception as e:
                logger.warning(f"[MISSION-CONTEXT] link error: {e}")

    def get_linked_mission(self, user_key: str) -> Optional[str]:
        r = _get_engine_redis()
        if r:
            try:
                return r.get(_CONVERSATION_LINK_KEY + ":" + user_key)
            except Exception:
                return None
        return None

    def update_from_answer(self, mc: MissionContext, query: str, answer: str, resolved_query: str = ""):
        mc.conversation["last_query"] = query
        mc.conversation["last_answer"] = answer
        if resolved_query and resolved_query != query:
            mc.conversation["last_resolved_query"] = resolved_query
        mc.meta["updated_at"] = _iso_now()
        
        # Sync step completion with mission_state v2
        try:
            event = MissionEvent(
                mission_id=mc.mission_state_v2.state.metadata.mission_id,
                event_type="StepCompleted",
                payload={"step": query}
            )
            mc.mission_state_v2.state = mc.mission_state_v2.reducer.apply(mc.mission_state_v2.state, event)
            mc.mission_state_v2.event_log.append(event)
        except Exception as e:
            logger.warning(f"[MISSION-CONTEXT] Sync StepCompleted v2 failed: {e}")

        self.save(mc)

    def clear(self, mission_id: str):
        r = _get_engine_redis()
        if r:
            try:
                r.delete(self._key(mission_id))
            except Exception:
                pass


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

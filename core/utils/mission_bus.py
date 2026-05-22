import time
import json
import os
import re
import hashlib
from typing import Any, Dict, List, Optional
from core.utils.redis_client import redis_safe

# 🛡️ [ENVIRONMENT-ADAPTER]: Operating environment detection
try:
    import gevent
    HAS_GEVENT = True
except ImportError:
    HAS_GEVENT = False

try:
    import asyncio
    HAS_ASYNCIO = True
except ImportError:
    HAS_ASYNCIO = False

import threading

# ═══════════════════════════════════════════════════════════════════
# 🎯 [3-CHANNEL ROUTING CONSTANTS] — Gán kênh tường minh, không xung đột
# ═══════════════════════════════════════════════════════════════════
# Kênh 1: Nhật ký Điều hành — câu hỏi/trả lời cuối cùng, lỗi nghiêm trọng
CH_EXECUTIVE = "executive"
# Kênh 2: Tab Tiến Trình — toàn bộ kỹ thuật, suy nghĩ, pipeline
CH_PROGRESS  = "progress"
# Kênh 3: Telegram — thông báo quan trọng tới Master
CH_TELEGRAM  = "telegram"

# 💎 [CHANNEL PRESETS] — Các bộ kênh tiền định nghĩa sẵn dùng
# Dùng trong publish_log(..., channels=CH_FULL) thay vì liệt kê từng kênh
CH_FULL      = [CH_EXECUTIVE, CH_PROGRESS, CH_TELEGRAM]   # Hiển thị khắp nơi
CH_EXEC_TELE = [CH_EXECUTIVE, CH_TELEGRAM]                 # Executive + Telegram (no progress spam)
CH_PROG_ONLY = [CH_PROGRESS]                               # Chỉ Tab Tiến Trình
CH_EXEC_PROG = [CH_EXECUTIVE, CH_PROGRESS]                 # Executive + Progress (no Telegram)
CH_TELE_ONLY = [CH_TELEGRAM]                               # Chỉ Telegram
CH_SILENT    = []                                          # Im lặng hoàn toàn (stealth)


class MissionEvent:
    TASK_STARTED   = "EVENT_TASK_STARTED"
    TASK_COMPLETED = "EVENT_TASK_COMPLETED"
    TASK_FAILED    = "EVENT_TASK_FAILED"
    TASK_ABORTED   = "EVENT_TASK_ABORTED"
    GPU_LOCKED     = "EVENT_GPU_LOCKED"
    GPU_RELEASED   = "EVENT_GPU_RELEASED"
    THINKING_STARTED  = "EVENT_THINKING_STARTED"
    THINKING_FINISHED = "EVENT_THINKING_FINISHED"
    STREAM_STARTED    = "EVENT_STREAM_STARTED"
    STREAM_FINISHED   = "EVENT_STREAM_FINISHED"
    MEMORY_INJECTED   = "EVENT_MEMORY_INJECTED"


class MissionBus:
    """
    🛰️ JKAI ZENITH AI OPERATING SYSTEM BUS v2.0 — 3-CHANNEL ARCHITECTURE
    ═══════════════════════════════════════════════════════════════════════
    3 kênh độc lập hoàn toàn, không xung đột nhau:

      KÊNH 1 [executive]: Nhật ký Điều hành
        → Chỉ Master, JKAI, ERROR, MISSION_RESULT
        → Redis: monitor:log_channel → socket: agent_log

      KÊNH 2 [progress]: Tab Tiến Trình  
        → Toàn bộ log kỹ thuật: THOUGHT, PLANNER, SYSTEM, PROGRESS...
        → Redis: monitor:progress_channel → socket: progress_log

      KÊNH 3 [telegram]: Telegram Mobile
        → Thông báo quan trọng, không spam
        → Gọi tg_callback trực tiếp

    CÁCH DÙNG:
      # Gán tường minh (recommended):
      bus.publish_log("JKAI", answer, channels=CH_FULL)          # Hiện khắp nơi
      bus.publish_log("THOUGHT:Planner", thought, channels=CH_PROG_ONLY)  # Chỉ progress
      bus.publish_log("SYSTEM", "debug info", channels=CH_SILENT) # Ẩn hoàn toàn

      # Legacy (backward-compatible): không truyền channels → tự suy luận từ tag
      bus.publish_log("JKAI", answer)  # → tự routing như cũ
    """

    def __init__(self):
        self.channel              = "monitor:log_channel"
        self.history_key          = "monitor:log_history"
        self.progress_history_key = "monitor:progress_history"
        self.tg_callback          = None
        # 🕒 [NANO-ORDERING]: Counter for absolute ordering within same ms
        self._log_counter = 0
        self._last_ts = 0

    def publish_event(self, event_type: str, data: Dict[str, Any], task_id: str = "system"):
        payload = {
            "type": event_type, "data": data,
            "task_id": task_id, "ts": int(time.time() * 1000), "source": "mission_bus"
        }
        redis_safe(lambda r: r.publish("mission:events", json.dumps(payload, ensure_ascii=False)))

    def publish_log(
        self,
        tag: str,
        msg: str,
        task_id: str = "system",
        trace_id: str = "system",
        channels: Optional[List[str]] = None,   # 🎯 NEW: tường minh kênh đích
        **kwargs
    ):
        """
        Phát tín hiệu nơ-ron tới các kênh đích.

        Args:
            tag:      Nhãn nguồn phát (vd: "JKAI", "THOUGHT:Planner", "SYSTEM")
            msg:      Nội dung tín hiệu
            task_id:  ID nhiệm vụ
            trace_id: ID vết theo dõi
            channels: Danh sách kênh đích tường minh [CH_EXECUTIVE, CH_PROGRESS, CH_TELEGRAM]
                      Nếu None → tự suy luận từ tag (backward-compatible)
            **kwargs: stealth, pin_id, action, summary, pct, ...
        """
        if not msg or not str(msg).strip():
            return

        clean_msg = msg.strip()

        # ── Duration tracking ────────────────────────────────────────
        duration = 0
        if task_id and task_id not in ["system", "manual"]:
            start_ts = redis_safe(lambda r: r.get(f"zenith:task_timer:{task_id}"))
            if start_ts:
                try: duration = time.time() - float(start_ts)
                except: pass

        # ── Tag parsing ──────────────────────────────────────────────
        tag_upper    = tag.upper()
        primary_tag  = tag_upper.split(':')[0] if ':' in tag_upper else tag_upper
        source_name  = tag_upper.split(':')[1] if ':' in tag_upper else ""

        # ── Action label with emoji ──────────────────────────────────
        action_emojis = {
            "Thinking":          "📝 Strategic Planning...",
            "Analyzing file":    "🔍 Reviewing Data...",
            "Viewing file":      "📂 Reading Document...",
            "Exploring directory":"📁 Indexing Directory...",
            "Searching the web": "🌐 Web Research...",
            "Executing command": "⚡ System Operation...",
            "Editing file":      "✍️ Updating File...",
            "Generating image":  "🎨 Generating Asset...",
            "Healing system":    "🛠️ System Maintenance...",
            "Planning":          "📋 Task Formulation...",
            "Reviewing":         "🧐 Quality Audit...",
            "System":            "⚙️ System Management",
            "Error":             "❌ System Exception",
        }
        raw_action       = kwargs.get("action", tag.replace('_', ' ').title())
        action_with_emoji = raw_action
        for key, val in action_emojis.items():
            if key in raw_action:
                action_with_emoji = val if key == raw_action else f"{val.split(' ')[0]} {raw_action}"
                break

        # ── Nano-precision timestamp ─────────────────────────────────
        current_ts = int(time.time() * 1000)
        if current_ts <= self._last_ts:
            self._log_counter += 1
        else:
            self._log_counter = 0
            self._last_ts = current_ts
        precise_ts = current_ts + (self._log_counter / 1000.0)

        # ── Stable ID protocol ───────────────────────────────────────
        content_hash = hashlib.md5(f"{trace_id}:{primary_tag}:{clean_msg}".encode()).hexdigest()[:12]
        is_stable_log = primary_tag in ["PROGRESS", "HEARTBEAT", "THOUGHT", "RECEPTIONIST", "PLANNER", "GATEWAY", "MASTER"]

        if kwargs.get("pin_id"):
            log_id = kwargs.get("pin_id")
        elif "HEARTBEAT" in clean_msg.upper() or primary_tag == "HEARTBEAT":
            log_id = f"pulse_{task_id}_{primary_tag.lower()}"
        elif is_stable_log:
            log_id = f"stable_{trace_id}_{content_hash}"
        else:
            log_id = f"log_{current_ts}_{self._log_counter}_{content_hash[:4]}"

        # ── Build payload ────────────────────────────────────────────
        is_heartbeat = (
            "HEARTBEAT" in clean_msg.upper() or
            primary_tag == "HEARTBEAT" or
            "PULSE" in clean_msg.upper()
        )

        payload = {
            "id":          log_id,
            "pin_id":      kwargs.get("pin_id"),
            "stealth":     kwargs.get("stealth", False),
            "tag":         primary_tag,
            "source":      source_name,
            "full_tag":    tag_upper,
            "msg":         clean_msg,
            "action":      action_with_emoji,
            "summary":     kwargs.get("summary", "Neural Operation"),
            "ts":          precise_ts,
            "duration":    round(duration, 3),
            "task_id":     task_id,
            "trace_id":    trace_id,
            "is_result":   primary_tag in ["MISSION_RESULT", "JKAI", "DONE", "RESULT"],
            "collapsible": len(clean_msg) > 150 or primary_tag in ["THOUGHT", "MISSION_RESULT"],
            "is_internal": primary_tag in ["SYSTEM", "DEBUG", "LATENCY", "GATEWAY", "VRAM_FLUSH"],
            # 🎯 [CHANNEL-DECLARATION]: Gửi thông tin kênh tới frontend
            "channels":    channels,
        }

        json_payload = json.dumps(payload, ensure_ascii=False)
        stealth      = kwargs.get("stealth", False)

        # ══════════════════════════════════════════════════════════════
        # 🎯 [3-CHANNEL ROUTING ENGINE]
        # Nếu channels được khai báo tường minh → dùng ngay, bỏ qua heuristics.
        # Nếu channels=None → legacy tag-based routing (backward-compatible).
        # ══════════════════════════════════════════════════════════════

        if channels is not None:
            # ── EXPLICIT ROUTING (recommended) ───────────────────────
            go_executive = CH_EXECUTIVE in channels
            go_progress  = CH_PROGRESS  in channels
            go_telegram  = CH_TELEGRAM  in channels and self.tg_callback and not stealth and not is_heartbeat

        else:
            # ── LEGACY ROUTING: suy luận từ tag (backward-compatible) ─
            # Kênh Executive (Nhật ký điều hành): Nhận toàn bộ log ngoại trừ Progress/Thought
            go_executive = (
                primary_tag not in ["PROGRESS", "THOUGHT", "HEARTBEAT"]
                and not payload.get("is_internal")
            )

            # Kênh Progress (Tiến trình): Chỉ nhận Progress, Thought và Heartbeat
            go_progress = primary_tag in ["PROGRESS", "THOUGHT", "HEARTBEAT"]

            # Kênh Telegram: Mirror những sự kiện quan trọng (Executive + Progress)
            go_telegram = (
                self.tg_callback and
                not stealth and
                not is_heartbeat
            )

        # ── KÊNH 1: EXECUTIVE (Nhật ký Điều hành) ───────────────────
        if go_executive and not stealth:
            redis_safe(lambda r: r.publish(self.channel, json_payload))
            redis_safe(lambda r: r.lpush(self.history_key, json_payload))
            redis_safe(lambda r: r.ltrim(self.history_key, 0, 499))

        # ── KÊNH 2: PROGRESS (Tab Tiến Trình) ───────────────────────
        if go_progress and not stealth:
            redis_safe(lambda r: r.publish("monitor:progress_channel", json_payload))
            redis_safe(lambda r: r.lpush(self.progress_history_key, json_payload))
            redis_safe(lambda r: r.ltrim(self.progress_history_key, 0, 1999))

        # ── KÊNH 3: TELEGRAM (Mobile Alert) ─────────────────────────
        if go_telegram:
            try:
                prefix = (
                    "👑" if primary_tag in {"MASTER", "MASTER_WEB", "MASTER_TELE"} else
                    "🧠" if primary_tag in {"JKAI", "MISSION_RESULT", "DONE", "RESULT"} else
                    "🚨" if primary_tag == "ERROR" else
                    "⚙️" if primary_tag == "SYSTEM" else
                    "💭" if "THOUGHT" in primary_tag else
                    "⚡"
                )
                top_tags = {"MASTER", "JKAI", "MISSION_RESULT", "ERROR", "DONE",
                            "RESULT", "MASTER_WEB", "MASTER_TELE"}
                if primary_tag in top_tags:
                    msg_to_send = f"{prefix} [{primary_tag}]\n{clean_msg}"
                else:
                    action_label = payload.get('action') or primary_tag.replace('_', ' ').title()
                    short_msg    = clean_msg[:300] + "..." if len(clean_msg) > 300 else clean_msg
                    msg_to_send  = f"{prefix} [{action_label}]\n{short_msg}"

                def _send():
                    try:
                        if HAS_ASYNCIO and asyncio.iscoroutinefunction(self.tg_callback):
                            asyncio.run(self.tg_callback(msg_to_send))
                        else:
                            self.tg_callback(msg_to_send)
                    except: pass

                if HAS_GEVENT:
                    gevent.spawn(_send)
                elif HAS_ASYNCIO:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(self.tg_callback(msg_to_send))
                        else:
                            threading.Thread(target=_send).start()
                    except:
                        threading.Thread(target=_send).start()
                else:
                    threading.Thread(target=_send).start()
            except: pass

        return clean_msg


mission_bus = MissionBus()

# -*- coding: utf-8 -*-
"""
Patch script for Continuation Memory Handler and WebGUI / Visual Actuation.
"""
import sys

def patch_intent_router():
    path = "core/os/routing/intent_router.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    target = """        tags: List[str] = list(tags_set)

        # ── PRIORITY 1: MATH (<1ms) ──"""

    replacement = """        tags: List[str] = list(tags_set)

        # ── PRIORITY 0.5: CONTINUATION / NỐI TIẾP NHIỆM VỤ (<0.1ms) ──
        _CONTINUATION_CUES = {
            "tiếp tục", "tiếp", "tiep tuc", "tiep", "continue", "tiếp đi", "tiep di",
            "viết tiếp", "viet tiep", "nói tiếp", "noi tiep", "làm tiếp", "lam tiep",
            "chạy tiếp", "chay tiep", "trình bày tiếp", "trinh bay tiep", "tiếp tục nào",
            "tiếp tục đi", "nói tiếp đi", "làm tiếp đi", "go on", "proceed"
        }
        g_clean = g_low.strip(" .!?:;\\n\\t\\\"'")
        is_cont = g_clean in _CONTINUATION_CUES or any(
            g_clean.startswith(c) for c in ["tiếp tục", "tiếp đi", "nói tiếp", "viết tiếp", "làm tiếp", "chạy tiếp"]
        )
        if is_cont:
            decision = RouteDecision(
                mode=IntentMode.REASONING,
                role="PLANNER",
                action_type=ActionType.EXECUTE,
                need_kb=True,
                need_web=False,
                need_tools=True,
                confidence=0.99,
                reason=f"Phát hiện khẩu lệnh tiếp nối nhiệm vụ ('{g_strip}'). Kế thừa ngữ cảnh, cấm reset về hội thoại xã giao.",
                tags=["CONTINUATION", "ANALYSIS"],
                max_turns=5,
                kb_top_k=5,
                is_compound=False,
                route_path="RULE"
            )
            active_learning_engine.record_query(g_strip, "REASONING", 0.99, ["CONTINUATION", "ANALYSIS"])
            return decision

        # ── PRIORITY 1: MATH (<1ms) ──"""

    if target not in text:
        print("[INTENT_ROUTER] Target not found or already patched.")
        return False

    new_text = text.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(new_text)
    print("[INTENT_ROUTER] Successfully patched CONTINUATION logic into intent_router.py")
    return True


def patch_receptionist_context():
    path = "services/ai-brain/receptionist/receptionist_core.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    target = """                prev_mission_id = ctx_mgr.get_linked_mission("default")
                if prev_mission_id and prev_mission_id != task_id:
                    # Nếu mission mới (không có last_subject), clear context cũ
                    if not mc.conversation.get("last_subject"):
                        ctx_mgr.clear(prev_mission_id)
                        prev_mission_id = None
                    else:
                        prev_mc = ctx_mgr.get_or_create(prev_mission_id)
                        resolved_goal = ent_resolver.resolve(goal, last_subject=prev_mc.conversation.get("last_subject", ""), last_query=prev_mc.conversation.get("last_query", ""))
                        if resolved_goal != goal:
                            self._log("BRAIN", f"[CONTEXT] Anaphora resolved: '{goal}' -> '{resolved_goal}'", task_id)
                            goal = resolved_goal"""

    replacement = """                prev_mission_id = ctx_mgr.get_linked_mission("default")
                if prev_mission_id and prev_mission_id != task_id:
                    prev_mc = ctx_mgr.get_or_create(prev_mission_id)
                    prev_last_answer = prev_mc.conversation.get("last_answer", "")
                    prev_last_query = prev_mc.conversation.get("last_query", "")
                    prev_last_subject = prev_mc.conversation.get("last_subject", "")
                    
                    is_cont_cue = any(
                        goal.strip().lower().startswith(c)
                        for c in ["tiếp tục", "tiếp", "tiep tuc", "tiep", "continue", "nói tiếp", "viết tiếp", "làm tiếp", "chạy tiếp"]
                    )
                    
                    if is_cont_cue and (prev_last_query or prev_last_answer):
                        # Giữ vững liên kết ngữ cảnh tiếp nối
                        mc.conversation["last_query"] = prev_last_query
                        mc.conversation["last_answer"] = prev_last_answer
                        mc.conversation["last_subject"] = prev_last_subject
                        mc.conversation["is_continuation"] = True
                        self._log("BRAIN", f"[CONTEXT] Continuation linked to prev mission '{prev_mission_id}'", task_id)
                    elif prev_last_subject:
                        resolved_goal = ent_resolver.resolve(goal, last_subject=prev_last_subject, last_query=prev_last_query)
                        if resolved_goal != goal:
                            self._log("BRAIN", f"[CONTEXT] Anaphora resolved: '{goal}' -> '{resolved_goal}'", task_id)
                            goal = resolved_goal"""

    if target not in text:
        print("[RECEPTIONIST] Target not found or already patched.")
        return False

    new_text = text.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(new_text)
    print("[RECEPTIONIST] Successfully patched context continuity into receptionist_core.py")
    return True


def patch_tool_arbiter_webgui():
    path = "core/kernel/tool_arbiter.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    target = """        # --- C. MIỀN HYBRID (FILE + TERMINAL: Phẫu thuật code & Chạy kiểm thử) ---"""

    replacement = """        # --- B2. MIỀN WEB-GUI / COMPUTER-USE (M2: Không cần URL đích danh nếu chỉ định rõ giao diện web / WebFig / click) ---
        WEB_GUI_KEYWORDS = {
            "webfig", "routeros", "mikrotik", "giao diện web", "trên giao diện",
            "click trực quan", "bước click", "thao tác giao diện", "điều khiển giao diện",
            "thao tác trên web", "điều khiển máy tính", "computer use", "webgui", "web gui"
        }
        has_web_gui = any(kw in g_low for kw in WEB_GUI_KEYWORDS)
        is_visual_action = any(kw in g_low for kw in cls.VISUAL_KEYWORDS) or any(
            kw in g_low for kw in ["click", "bấm", "chụp ảnh", "chụp màn hình", "nhấn"]
        )
        if (has_web_gui and is_visual_action) or ("webfig" in g_low):
            default_target = "http://127.0.0.1:8765" if "webfig" in g_low else "http://localhost:8000"
            return ArbiterVerdict(
                primary_domain=ToolDomain.BROWSER,
                secondary_domains=[],
                confidence=0.97,
                extracted_urls=[default_target],
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                is_visual_required=True,
                primary_target=default_target,
                mandatory_tools=["BROWSER_CONTROL", "browser_act", "visual_aci_gateway"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web"],
                reason=f"{hypo_prefix_note}Tác vụ điều khiển giao diện trực quan / WebFig ({default_target}). BẮT BUỘC dùng Visual Browser M2 & Visual ACI Gateway.",
            )

        # --- C. MIỀN HYBRID (FILE + TERMINAL: Phẫu thuật code & Chạy kiểm thử) ---"""

    if target not in text:
        print("[TOOL_ARBITER] Target not found or already patched.")
        return False

    new_text = text.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(new_text)
    print("[TOOL_ARBITER] Successfully patched WebGUI/Computer-Use into tool_arbiter.py")
    return True


def patch_tool_router_aliases():
    path = "services/ai-executor/tool_router.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    target = """                if t_upper in ("BROWSER_CONTROL", "AUTO_BROWSER", "AUTO_BROWSER_01", "BROWSER_ACTION", "BROWSER_INTERACT", "WEB_BROWSER"):"""
    replacement = """                if t_upper in ("BROWSER_CONTROL", "AUTO_BROWSER", "AUTO_BROWSER_01", "BROWSER_ACTION", "BROWSER_INTERACT", "WEB_BROWSER", "VISUAL_ACI_GATEWAY", "VISUAL_COMPUTER_USE", "SOM_BROWSER_CLICK", "BROWSER_ACT"):"""

    if target not in text:
        print("[TOOL_ROUTER] Target not found or already patched.")
        return False

    new_text = text.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(new_text)
    print("[TOOL_ROUTER] Successfully patched Visual ACI aliases into tool_router.py")
    return True


if __name__ == "__main__":
    patch_intent_router()
    patch_receptionist_context()
    patch_tool_arbiter_webgui()
    patch_tool_router_aliases()

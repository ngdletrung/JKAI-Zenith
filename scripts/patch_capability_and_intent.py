# -*- coding: utf-8 -*-
"""
scripts/patch_capability_and_intent.py
Cải tiến toàn diện nhận thức tự thân và phân tuyến câu hỏi năng lực của JKAI:
1. Khắc phục lỗi chính tả: "điều khỉ" -> "điều khiển", "ai-browse" -> "ai-browser".
2. Bổ sung Priority 1.2 (Capability Question Gate) trong CentralIntentRouter:
   Chuyển các câu hỏi về năng lực ("bạn có tính năng...", "bạn có điều khiển...") về META_INTROSPECTION / FAST.
   Tuyệt đối không để rơi vào DEEP_PIPELINE / CODING gây lập kế hoạch ảo.
3. Cập nhật Section 8 Sovereign Capability Catalog vào agent_receptionist.md.
"""
from pathlib import Path
import re

def update_agent_receptionist():
    targets = [
        Path("intelligence/agents/agent_receptionist.md"),
        Path("AI_TEAM/tasks/TASK-REFLEX-V2-001/workspaces/build_worktree/intelligence/agents/agent_receptionist.md")
    ]
    catalog_text = """

---

## 8. SOVEREIGN CAPABILITY CATALOG (HỒ SƠ TÍNH NĂNG THỰC TẾ CỦA HỆ THỐNG)
Khi Master hỏi về năng lực hoặc tính năng của JKAI (ví dụ: "bạn có tính năng gì", "bạn có tính năng ai-browse không", "bạn có điều khiển được trang web không"), bạn phải tự tin xác nhận chính xác các năng lực thực tế sau:
1. **Trình duyệt Thị giác & Điều khiển Máy tính (ai-browser / Computer-Use)**:
   - Dịch vụ vệ tinh `ai-browser` (port 8003) tích hợp Playwright Chromium thật.
   - Năng lực: Mở trang web thật, chụp ảnh màn hình, quét cấu trúc Set-of-Marks (`@e1`..`@eN`), tự động di chuột, click nút bấm, nhập liệu form và đo lường biến thiên thị giác (Visual Diff).
   - Khả năng: Điều khiển trực tiếp mọi trang web công cộng, hệ thống nội bộ hoặc giao diện mạng như MikroTik WebFig.
2. **Tìm kiếm Tri thức Internet Toàn cầu (Global Search)**:
   - Công cụ `SEARCH_WEB_GLOBAL` / `web_search` tra cứu dữ liệu thời gian thực.
3. **Phẫu thuật Mã nguồn & Tệp Workspace (Code Actuator)**:
   - Công cụ `VIEW_FILE`, `WRITE_TO_FILE`, `replace_file_content`, `smart_patch`.
4. **Thực thi Dòng lệnh An toàn (Terminal Executor)**:
   - Công cụ `EXECUTE_COMMAND`, `SYSTEM_CMD` có thang phê duyệt an ninh 4 nấc.
5. **Bộ nhớ & Tri thức Dài hạn (Memory & RAG)**:
   - Cơ sở dữ liệu vector Qdrant và bộ nhớ ngữ cảnh hội thoại.
"""
    for p in targets:
        if p.exists():
            text = p.read_text(encoding="utf-8")
            if "SOVEREIGN CAPABILITY CATALOG" not in text:
                text += catalog_text
                p.write_text(text, encoding="utf-8", newline="\r\n")
                print(f"[RECEPTIONIST] Updated capability catalog into {p}")


def update_intent_router():
    path = Path("core/os/routing/intent_router.py")
    text = path.read_text(encoding="utf-8")

    # 1. Thêm Typo Normalization ở đầu _route_inner
    typo_target = """        g_strip = goal.strip()
        g_low = g_strip.lower()"""

    typo_replacement = """        g_strip = goal.strip()
        g_low = g_strip.lower()

        # ── 0. TYPO & ACCENT NORMALIZATION (Chuẩn hóa lỗi gõ nhanh tiếng Việt) ──
        _TYPO_MAP = {
            "điều khỉ": "điều khiển",
            "dieu khi": "điều khiển",
            "ai-browse": "ai-browser",
            "ai browse": "ai-browser",
            "aibrowse": "ai-browser",
            "clik": "click",
            "clcik": "click",
        }
        for wrong, right in _TYPO_MAP.items():
            if wrong in g_low:
                g_low = g_low.replace(wrong, right)
                g_strip = re.sub(re.escape(wrong), right, g_strip, flags=re.IGNORECASE)"""

    # 2. Thêm PRIORITY 1.2 Capability Question Gate
    cap_target = """        # ── PRIORITY 1.5: META INTROSPECTION (Self-Knowledge & System Status) ──"""

    cap_replacement = """        # ── PRIORITY 1.2: CÂU HỎI TRA CỨU TÍNH NĂNG & NĂNG LỰC HỆ THỐNG (<0.2ms) ──
        # Nhận diện: "bạn có tính năng...", "bạn có điều khiển được...", "hệ thống có thể..."
        # Cưỡng chế định tuyến FAST Receptionist, cấm kích hoạt DEEP / CODING pipeline gây ảo giác!
        _CAP_QUESTION_LEADS = [
            "bạn có tính năng", "ban co tinh nang", "có tính năng", "co tinh nang",
            "bạn có chức năng", "ban co chuc nang", "có chức năng", "co chuc nang",
            "bạn có điều khiển", "ban co dieu khien", "có điều khiển được", "co dieu khien duoc",
            "bạn có thể điều khiển", "ban co the dieu khien", "có thể điều khiển",
            "bạn có làm được", "ban co lam duoc", "có làm được không", "co lam duoc khong",
            "ai-browser", "browser_control"
        ]
        is_cap_query = any(cq in g_low for cq in _CAP_QUESTION_LEADS)
        is_interrogative = any(q in g_low for q in ["không", "khong", "được", "duoc", "ah", "ạ", "hả", "ha", "chăng", "?"]) or any(
            g_low.startswith(p) for p in ["bạn có ", "ban co ", "hệ thống có ", "he thong co "]
        )
        is_explicit_cmd = any(cmd in g_low for cmd in ["hãy mở", "hãy click", "hãy làm", "hãy chạy", "hãy tạo", "hãy sửa"])

        if is_cap_query and is_interrogative and not is_explicit_cmd:
            decision = RouteDecision(
                mode=IntentMode.META_INTROSPECTION,
                role="RECEPTIONIST",
                action_type=ActionType.READ,
                need_kb=True,
                need_web=False,
                need_tools=False,
                confidence=0.99,
                reason=f"Câu hỏi tra cứu năng lực/tính năng hệ thống ('{g_strip}'). Định tuyến FAST Receptionist, cấm DEEP pipeline.",
                tags=["INTERNAL", "META", "CAPABILITY"],
                max_turns=1,
                kb_top_k=5,
                is_compound=is_compound,
                route_path="RULE"
            )
            active_learning_engine.record_query(g_strip, "META_INTROSPECTION", 0.99, ["CAPABILITY"])
            return decision

        # ── PRIORITY 1.5: META INTROSPECTION (Self-Knowledge & System Status) ──"""

    assert typo_target in text, "Typo target not found in intent_router.py!"
    assert cap_target in text, "Cap target not found in intent_router.py!"

    text = text.replace(typo_target, typo_replacement, 1)
    text = text.replace(cap_target, cap_replacement, 1)

    path.write_text(text, encoding="utf-8", newline="\r\n")
    print("[INTENT_ROUTER] Successfully patched Typo Normalizer & Capability Question Gate into intent_router.py")


if __name__ == "__main__":
    update_agent_receptionist()
    update_intent_router()

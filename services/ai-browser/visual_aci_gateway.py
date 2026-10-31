# -*- coding: utf-8 -*-
"""
visual_aci_gateway.py
Module Cổng Giao tiếp Tác tử - Máy tính Trực quan (Visual ACI Gateway) & Cổng Phê duyệt An toàn (Action Confirmation Gate).
Thuộc kiến trúc JKAI Zenith SDS v28.27.0.

Năng lực cốt lõi:
1. Đánh giá mức độ rủi ro thao tác (Mutation Risk Classifier): Phân loại READ_ONLY vs LOW vs MEDIUM vs HIGH risk.
2. Cổng phê duyệt an toàn Human-in-the-Loop (Action Confirmation Card): Khóa chữ ký số, chống TOCTOU drift, One-Time Token chống Replay.
3. Bộ phủ nhãn trực quan Set-of-Marks (SoM Engine): Đánh số [1], [2], [3] lên ảnh chụp màn hình tương ứng @e1..@eN.
4. Phản tư bằng mắt (Visual Diff Verifier): So sánh thay đổi pixel trước/sau hành động theo pixel RGB chuẩn xác.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import io
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("visual-aci-gateway")


def get_aci_secret_key() -> bytes:
    """
    Lấy secret HMAC từ biến môi trường JKAI_ACI_SECRET_KEY.
    Fail-closed tuyệt đối trong production nếu thiếu secret key; chỉ cho phép test key khi ở test mode.
    """
    key_str = os.getenv("JKAI_ACI_SECRET_KEY", "").strip()
    if key_str:
        return key_str.encode("utf-8")

    is_test_env = (
        os.getenv("JKAI_TEST_MODE", "0").lower() in ("1", "true")
        or "pytest" in sys.modules
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if is_test_env:
        return b"jkai_sovereign_secret_approval_gate_2026"

    raise RuntimeError("SECURITY_CRITICAL: JKAI_ACI_SECRET_KEY environment variable is missing. Production execution aborted.")


class ActionRiskLevel:
    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


MUTATION_KEYWORDS = {
    "apply", "save", "submit", "reboot", "restart", "delete", "remove",
    "drop", "format", "reset", "execute", "update", "overwrite", "cập nhật",
    "lưu", "áp dụng", "khởi động lại", "xóa", "thay đổi", "gửi"
}


class VisualACIGateway:
    """Cổng điều phối Visual ACI và Action Confirmation Gate."""

    # In-memory store chống replay attack cho one-time approval token
    _consumed_tokens: Set[str] = set()
    _registered_cards: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def evaluate_mutation_risk(
        cls,
        action: str,
        element_name: str = "",
        element_tag: str = "",
        element_role: str = "",
        value: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """
        Phân loại mức độ rủi ro của hành động GUI.
        Chuẩn hóa triệt để chữ thường (.lower()) cho tag, role, action và name.
        Trả về (risk_level, reasons).
        """
        reasons = []
        action = (action or "").lower().strip()
        tag_lower = (element_tag or "").lower().strip()
        role_lower = (element_role or "").lower().strip()
        name_lower = (element_name or "").lower().strip()
        combined_text = f"{name_lower} {tag_lower} {role_lower}".strip()

        # 1. Các hành động read-only
        if action in ("observe", "screenshot", "read", "extract", "hover", "scroll"):
            return ActionRiskLevel.READ_ONLY, ["Hành động quan sát không thay đổi trạng thái."]

        # 2. Kiểm tra từ khóa mutation nguy hiểm
        detected_keywords = [kw for kw in MUTATION_KEYWORDS if kw in combined_text]
        if detected_keywords:
            reasons.append(f"Phát hiện từ khóa thay đổi cấu hình/hệ thống: {', '.join(detected_keywords)}")
            return ActionRiskLevel.HIGH, reasons

        # 3. Thao tác click trên nút bấm hoặc liên kết
        if action == "click":
            if tag_lower in ("button", "a") or role_lower in ("button", "link"):
                reasons.append("Thao tác click vào thành phần tương tác.")
                return ActionRiskLevel.MEDIUM, reasons

        # 4. Thao tác nhập liệu
        if action in ("fill", "type"):
            reasons.append("Thao tác điền dữ liệu vào form.")
            return ActionRiskLevel.LOW, reasons

        return ActionRiskLevel.LOW, ["Thao tác thông thường."]

    @classmethod
    def generate_approval_token(
        cls,
        action_id: str,
        expiry_timestamp: int,
        state_before_hash: str = "",
    ) -> str:
        """Tạo mã xác thực HMAC ký duyệt hành động gắn với state_before_hash."""
        msg = f"{action_id}:{expiry_timestamp}:{state_before_hash}".encode("utf-8")
        return hmac.new(get_aci_secret_key(), msg, hashlib.sha256).hexdigest()

    @classmethod
    def create_confirmation_card(
        cls,
        task_id: str,
        trace_id: str,
        action: str,
        target_ref: str,
        element_name: str,
        element_rect: Optional[Dict[str, float]],
        state_before_hash: str,
        url: str = "",
        rollback_command: Optional[str] = None,
        timeout_seconds: int = 300,
        nonce: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tạo thẻ xác nhận hành động (Action Confirmation Card) gửi tới UI Master với Nonce chống va chạm."""
        now_ts = int(time.time())
        expiry_ts = now_ts + timeout_seconds
        active_nonce = nonce or os.urandom(8).hex()
        action_payload_raw = f"{task_id}:{trace_id}:{action}:{target_ref}:{state_before_hash}:{url}:{active_nonce}"
        action_id = f"act_{hashlib.sha256(action_payload_raw.encode('utf-8')).hexdigest()[:16]}"
        approval_token = cls.generate_approval_token(action_id, expiry_ts, state_before_hash)

        card = {
            "schema_version": "2.1.0",
            "action_id": action_id,
            "nonce": active_nonce,
            "task_id": task_id,
            "trace_id": trace_id,
            "action": action,
            "target_ref": target_ref,
            "element_name": element_name,
            "element_rect": element_rect,
            "url": url,
            "mutation_risk": ActionRiskLevel.HIGH,
            "state_before_hash": state_before_hash,
            "rollback_command": rollback_command or "MANUAL_REVERT_REQUIRED",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "expires_at_timestamp": expiry_ts,
            "approval_token": approval_token,
            "approval_status": "PENDING_USER_APPROVAL",
        }
        cls._registered_cards[action_id] = card
        return card

    @classmethod
    def verify_action_execution(
        cls,
        card: Dict[str, Any],
        provided_token: str,
        current_state_hash: str,
        current_action: Optional[str] = None,
        current_target_ref: Optional[str] = None,
        current_task_id: Optional[str] = None,
        current_trace_id: Optional[str] = None,
        current_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Kiểm tra tính hợp lệ của phê duyệt, TOCTOU Guard, chống Replay, và REQUEST-CARD BINDING:
        1. Kiểm tra One-Time Token đã bị consume chưa.
        2. Đối chiếu toàn vẹn Request Context với Card (Action, Target, Task, Trace, URL) chống Confused Deputy.
        3. Kiểm tra chữ ký HMAC và thời gian hết hạn.
        4. So khớp current_state_hash với state_before_hash để chống trôi màn hình.
        5. Tiêu hủy (consume) token ngay sau khi kiểm tra thành công.
        """
        action_id = card.get("action_id", "")
        if not action_id:
            return False, "INVALID_CARD_NO_ACTION_ID"

        # 1. Chống Replay Attack: Một token chỉ được dùng đúng 1 lần!
        if action_id in cls._consumed_tokens or card.get("approval_status") == "CONSUMED":
            logger.warning(f"❌ [GATE-REPLAY-BLOCKED] Replay attack detected for action_id: {action_id}")
            return False, "APPROVAL_TOKEN_ALREADY_CONSUMED"

        # 2. [FAIL-CLOSED CONTEXT BINDING P0]: Ngăn chặn cross-action và direct-call bỏ qua context
        required_contexts = {
            "action": current_action,
            "target_ref": current_target_ref,
            "task_id": current_task_id,
            "trace_id": current_trace_id,
            "url": current_url,
        }
        for field_name, field_val in required_contexts.items():
            card_val = card.get(field_name)
            # Nếu card có trường này thì request bắt buộc phải cung cấp và khớp hoàn toàn!
            if card_val:
                if not field_val or str(field_val).strip() == "":
                    logger.error(f"❌ [GATE-BINDING-MISSING] Missing required context field: '{field_name}'")
                    return False, f"CONTEXT_BINDING_REQUIRED_MISSING_FIELD({field_name})"
                if str(card_val).strip().lower() != str(field_val).strip().lower():
                    logger.error(f"❌ [GATE-BINDING-MISMATCH] {field_name} mismatch: card={card_val}, req={field_val}")
                    return False, f"CARD_{field_name.upper()}_MISMATCH(card={card_val}, req={field_val})"

        # 3. Kiểm tra Expiry
        now_ts = int(time.time())
        if now_ts > card.get("expires_at_timestamp", 0):
            return False, "APPROVAL_TOKEN_EXPIRED"

        # 4. Kiểm tra chữ ký số HMAC
        expected_token = cls.generate_approval_token(
            action_id, card["expires_at_timestamp"], card.get("state_before_hash", "")
        )
        if not hmac.compare_digest(expected_token, provided_token):
            return False, "INVALID_APPROVAL_SIGNATURE"

        # 5. TOCTOU Guard: Màn hình hoặc DOM bị thay đổi sau khi tạo thẻ xác nhận
        if current_state_hash != card.get("state_before_hash"):
            return False, f"TOCTOU_STATE_DRIFT(expected={card.get('state_before_hash')[:12]}, current={current_state_hash[:12]})"

        # 6. Consume Token thành công -> Đánh dấu đã sử dụng
        cls._consumed_tokens.add(action_id)
        card["approval_status"] = "CONSUMED"
        if action_id in cls._registered_cards:
            cls._registered_cards[action_id]["approval_status"] = "CONSUMED"

        return True, "APPROVAL_VERIFIED"

    @classmethod
    def reset_consumed_tokens(cls):
        """Dành riêng cho test fixtures làm sạch bộ nhớ replay."""
        cls._consumed_tokens.clear()
        cls._registered_cards.clear()

    @classmethod
    def render_set_of_marks(
        cls,
        image_bytes: bytes,
        elements: List[Dict[str, Any]],
    ) -> bytes:
        """
        Phủ lớp nhãn số Set-of-Marks (SoM) [1], [2], [3] lên ảnh chụp màn hình
        dựa trên bounding boxes của các phần tử @e1..@eN.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        except Exception as e:
            logger.error(f"Failed to open image bytes: {e}")
            return image_bytes

        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Bảng màu sắc tương phản cho các nhãn
        badge_bg = (235, 30, 30, 220)  # Đỏ cam nổi bật
        badge_border = (255, 255, 255, 255)
        text_color = (255, 255, 255, 255)
        box_outline = (255, 60, 60, 180)

        for idx, elem in enumerate(elements, start=1):
            rect = elem.get("rect")
            if not rect:
                continue

            x = rect.get("x", 0)
            y = rect.get("y", 0)
            w = rect.get("width", 0)
            h = rect.get("height", 0)

            if w <= 0 or h <= 0:
                continue

            # Vẽ khung viền bao quanh phần tử
            draw.rectangle([x, y, x + w, y + h], outline=box_outline, width=2)

            # Vẽ nhãn số [idx] nhỏ gọn góc trên trái
            label_text = f"[{idx}]"
            badge_w, badge_h = 24, 18
            bx1, by1 = x, max(0, y - badge_h)
            bx2, by2 = x + badge_w, by1 + badge_h

            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=3, fill=badge_bg, outline=badge_border, width=1)
            draw.text((bx1 + 3, by1 + 1), label_text, fill=text_color)

        combined = Image.alpha_composite(image, overlay).convert("RGB")
        out_buf = io.BytesIO()
        combined.save(out_buf, format="PNG")
        return out_buf.getvalue()

    @classmethod
    def compute_visual_diff(
        cls,
        image_before_bytes: bytes,
        image_after_bytes: bytes,
    ) -> Dict[str, Any]:
        """
        So sánh sai khác thị giác giữa ảnh trước và ảnh sau thao tác (Visual Diff).
        So sánh chuẩn xác theo từng pixel RGB (3 channels), không chia 3 thô sơ.
        """
        try:
            img1 = Image.open(io.BytesIO(image_before_bytes)).convert("RGB")
            img2 = Image.open(io.BytesIO(image_after_bytes)).convert("RGB")
        except Exception as e:
            return {"error": f"DIFF_IMAGE_OPEN_FAILED: {e}", "diff_percentage": 0.0, "state_changed": False}

        if img1.size != img2.size:
            return {"diff_percentage": 100.0, "state_changed": True, "note": "Kích thước màn hình thay đổi"}

        raw1 = img1.tobytes()
        raw2 = img2.tobytes()
        total_pixels = img1.width * img1.height
        threshold = 20

        # Duyệt từng pixel (3 byte: R, G, B)
        diff_pixels = 0
        limit = len(raw1) - 2
        for i in range(0, limit, 3):
            r1, g1, b1 = raw1[i], raw1[i + 1], raw1[i + 2]
            r2, g2, b2 = raw2[i], raw2[i + 1], raw2[i + 2]
            if abs(r1 - r2) > threshold or abs(g1 - g2) > threshold or abs(b1 - b2) > threshold:
                diff_pixels += 1

        diff_percent = round((diff_pixels / total_pixels) * 100, 2)
        state_changed = diff_percent > 0.05

        return {
            "diff_percentage": diff_percent,
            "state_changed": state_changed,
            "different_pixels": diff_pixels,
            "total_pixels": total_pixels,
        }

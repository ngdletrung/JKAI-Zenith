# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: intelligence/skills/CORE/ZENITH_AEGIS_GUARD/logic.py
# - Role: Hybrid Security Guard - Intent-Based Permission & Auth Key Sync
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.1 (Hybrid Elite)
# [WORKING PRINCIPLES]:
# 1. Combines Cognitive Rationale (Essence of Claude Code) with 
#    Hard Authentication (Operator Approval Key).
# 2. Performs tiered risk assessment: LOW (Log) -> MEDIUM (Ask) -> HIGH (Auth Key).
# 3. Ensures every sensitive action has a "Sovereign Justification".
# -----------------------------------------------------------------------------
import os
import json
import hashlib
from typing import Dict, Any, List

# Vùng Đỏ: Tuyệt đối cần Mật mã phê duyệt
RED_ZONES = [".env", "config/", "node_modules/", "core/auth/", "intelligence/protocols/"]
# Lệnh Rủi ro: Cần Giải trình + Phê duyệt nhanh
RISKY_COMMANDS = ["rm", "curl", "wget", "chmod", "chown", "mv", "cp -rf"]

async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    action = params.get("action", "verify_intent")
    target = params.get("target", "")
    proposed_change = params.get("change_summary", "")
    
    # Giao thức Hợp nhất Tinh hoa
    return await hybrid_handshake(target, proposed_change)

async def hybrid_handshake(target: str, change: str) -> Dict[str, Any]:
    risk_score = 0
    requirements = []
    
    # 1. Kiểm tra Vùng Đỏ (Trọng số 100)
    in_red_zone = any(zone in target for zone in RED_ZONES)
    if in_red_zone:
        risk_score += 100
        requirements.append("OPERATOR_APPROVAL_KEY")
    
    # 2. Kiểm tra Lệnh/Hành động (Trọng số 50)
    is_risky_op = any(target.startswith(cmd) for cmd in RISKY_COMMANDS)
    if is_risky_op:
        risk_score += 50
        requirements.append("COGNITIVE_RATIONALE")

    # 3. Phân tầng Phản xạ
    if risk_score >= 100:
        return {
            "status": "STOP_NEURAL_HANDSHAKE_REQUIRED",
            "risk_level": "CRITICAL",
            "rationale": f"Hành động tác động vào Vùng Đỏ: {target}. Cần đảm bảo tính toàn vẹn hệ thống.",
            "impact_analysis": f"Thay đổi này có thể ảnh hưởng đến cơ chế bảo mật hoặc cấu hình nòng cốt.",
            "verification_method": "HYBRID (Rationale + Password Key)",
            "action_required": "Master vui lòng cung cấp [OPERATOR_APPROVAL_KEY] để tiếp tục."
        }
    elif risk_score >= 50:
        return {
            "status": "PAUSE_CONFIRMATION_REQUIRED",
            "risk_level": "MEDIUM",
            "rationale": f"Lệnh '{target}' có tính phá hủy hoặc rủi ro cao.",
            "impact_analysis": "Có thể làm mất dữ liệu nếu không kiểm soát kỹ.",
            "verification_method": "COGNITIVE (Rationale Only)",
            "action_required": "Master xác nhận có muốn thực thi hành động này không?"
        }
    
    return {
        "status": "CLEAR",
        "risk_level": "LOW",
        "message": "Aegis Guard xác nhận an toàn. Thực thi ngay lập tức."
    }

async def verify_key(provided_key: str, stored_hash: str) -> bool:
    """Xác thực mật mã qua SHA-256 theo SOP #8"""
    input_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return input_hash == stored_hash

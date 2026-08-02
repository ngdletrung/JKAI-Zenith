# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: intelligence/skills/CORE/ZENITH_STRATEGIC_PLANNER/logic.py
# - Role: Strategic Reasoning Engine - Intent Decoder
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
# [WORKING PRINCIPLES]:
# 1. Decodes raw user input into structured technical goals.
# 2. Analyzes project state to provide architectural context.
# 3. Generates high-level implementation blueprints.
# -----------------------------------------------------------------------------
import os
import json
from typing import Dict, Any, List
from core.utils import report_formatter as rf

async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    user_intent = params.get("user_intent", "")
    depth = params.get("context_depth", "deep")
    force_swarm = params.get("force_swarm", False)

    if not user_intent:
        return {"status": "error", "message": "No intent provided for reasoning."}

    # 🧠 BƯỚC 1: GIẢI MÃ Ý ĐỊNH
    decoded_intent = await decode_intent(user_intent)
    
    # 🔍 BƯỚC 2: PHÂN TÍCH TẦM ẢNH HƯỞNG
    impact = await analyze_impact(decoded_intent)
    
    # ⚖️ BƯỚC 3: KIỂM TRA TRIGGER JUDICIAL (SWARM PHẢN BIỆN)
    # Tự động triệu tập Hội đồng nếu chạm vào lõi hoặc Master yêu cầu khắt khe
    is_high_impact = any("CORE" in p or "Intelligence" in p for p in impact)
    
    if is_high_impact or force_swarm:
        from core.utils.engine import engine
        print(f"🏛️ [JUDICIAL TRIGGER]: Nhiệm vụ tầm cao. Triệu tập Hội đồng Phán quyết...")
        council_res = await engine.call_skill("COUNCIL_OF_MINDS_DEBATE", {"topic": user_intent})
        return {
            "status": "success",
            "mode": "JUDICIAL_SWARM",
            "blueprint": council_res.get("answer"),
            "council_details": council_res.get("judicial_report")
        }

    # Generate Standard Blueprint for low-impact tasks
    blueprint = await generate_blueprint(decoded_intent, impact)
    
    return {
        "status": "success",
        "mode": "STANDARD",
        "decoded_intent": decoded_intent,
        "architectural_impact": impact,
        "blueprint": blueprint
    }

async def decode_intent(intent: str) -> Dict[str, Any]:
    # Mock-up logic for intent decoding
    # In a real scenario, this would use semantic mapping against the skill registry
    return {
        "raw": intent,
        "mapped_goal": "Optimize core system components",
        "inferred_skills": ["#106 (Compactor)", "#107 (Ultra-Vision)"]
    }

async def analyze_impact(decoded: Dict[str, Any]) -> List[str]:
    # Analyzes what parts of the system will be touched
    return [
        "Intelligence Layer (skills/CORE)",
        "Master Index (MAP_SKILLS.md)",
        "Registry (registry_Map_skills.json)"
    ]

async def generate_blueprint(decoded: Dict[str, Any], impact: List[str]) -> str:
    return rf.build([
        rf.section("ZENITH STRATEGIC BLUEPRINT"),
        rf.kvdict({
            "Mục tiêu giải mã": decoded['mapped_goal'],
            "Kỹ năng huy động": ', '.join(decoded['inferred_skills']),
            "Vùng ảnh hưởng": ', '.join(impact),
            "Tiến trình": "1. Nén ngữ cảnh -> 2. Kiểm định đa chiều -> 3. Cập nhật nhật ký."
        })
    ])

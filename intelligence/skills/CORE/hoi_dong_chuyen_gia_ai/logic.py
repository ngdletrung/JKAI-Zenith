# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: logic.py
- Role: Elite Skill execution - Cognitive Council (Hội Đồng Chuyên Gia AI) v4.0.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v4.0
"""
import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
from core.utils.engine import engine

logger = logging.getLogger("HoiDongChuyenGia")

_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SKILL_DIR, "..", "..", "..", ".."))
RULES_SOFTWARE_PATH = os.path.join(_PROJECT_ROOT, "intelligence", "rules_software.md")

# ─────────────────────────────────────────────
# CONFIG LOADERS
# ─────────────────────────────────────────────

def load_api_keys_from_markdown(file_path: str = RULES_SOFTWARE_PATH) -> Dict[str, Dict[str, str]]:
    config = {}
    if not os.path.exists(file_path):
        logger.error("Không tìm thấy file cấu hình API: %s", file_path)
        return config
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            if "|" in line and "`" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 5:
                    provider_raw = parts[1].replace("**", "").strip()
                    var_name_raw = parts[2].replace("`", "").strip()
                    url_raw      = parts[3].replace("`", "").strip()
                    key_raw      = parts[4].strip()
                    if var_name_raw in ["GEMINI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GROK_API_KEY"]:
                        config[var_name_raw] = {
                            "base_url": url_raw,
                            "api_key":  key_raw,
                            "provider": provider_raw
                        }
    except Exception as e:
        logger.error("Lỗi khi đọc rules_software.md: %s", e)
    return config


def load_manifest_config() -> Dict[str, Any]:
    manifest_path = os.path.join(_SKILL_DIR, "manifest.json")
    max_rounds = 2
    conflict_threshold = 0.5
    nodes = []
    try:
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            cfg = manifest_data.get("config", {})
            max_rounds = int(cfg.get("max_rounds", 2))
            conflict_threshold = float(cfg.get("conflict_threshold", 0.5))
            nodes = cfg.get("nodes", [])
    except Exception as e:
        logger.warning("Không thể đọc manifest.json: %s", e)
    return {"max_rounds": max_rounds, "conflict_threshold": conflict_threshold, "nodes": nodes}


# ─────────────────────────────────────────────
# CLOUD EXPERT CALLER
# ─────────────────────────────────────────────

def _build_payload(model_name: str, base_url: str, system_prompt: str, user_content: str) -> Dict:
    is_json_format_supported = not any(x in base_url for x in ["generativelanguage.googleapis.com", "api.x.ai"])
    json_suffix = ""
    if not is_json_format_supported:
        json_suffix = "\n\nCHÚ Ý: Bắt buộc chỉ trả về JSON thuần túy, không có markdown, không có ```json."

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt + json_suffix},
            {"role": "user",   "content": user_content}
        ],
        "temperature": 0.3
    }
    if is_json_format_supported:
        payload["response_format"] = {"type": "json_object"}
    return payload


async def _post_and_parse(client: httpx.AsyncClient, base_url: str, api_key: str, payload: Dict, label: str) -> Optional[Dict]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = await client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers, timeout=35.0)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```[a-z]*\n?", "", content)
                content = re.sub(r"\n?```$", "", content.strip())
            return json.loads(content)
        else:
            logger.error("%s error HTTP %s", label, response.status_code)
    except Exception as e:
        logger.error("Lỗi parse/gọi %s: %s", label, e)
    return None


async def call_cloud_node(client: httpx.AsyncClient, name: str, model: str, base_url: str, api_key: str, question: str, prior_opinions: Optional[Dict] = None, focus_area: Optional[str] = None) -> Dict[str, Any]:
    system_prompt = f"Bạn là [{name}], thực thể trí tuệ cao cấp trong Hội Đồng Chuyên Gia. "
    if focus_area:
        system_prompt += f"Lĩnh vực chuyên sâu cần tập trung phân tích: {focus_area}. "
    system_prompt += (
        "Hãy đưa ra phân tích sắc bén nhất cho bài toán của Master. "
        "Bắt buộc trả về định dạng JSON theo schema:\n"
        '{"claims": ["luận điểm"], "evidence": ["bằng chứng"], "confidence": 0.90, "risks": ["rủi ro"], "alternatives": []}'
    )
    if prior_opinions:
        user_content = (
            f"Vấn đề: '{question}'\n\n"
            f"Ý kiến của các thực thể khác:\n{json.dumps(prior_opinions, ensure_ascii=False, indent=2)}\n\n"
            "Dựa trên các phân tích trên, hãy tranh luận phản biện, bổ sung hoặc phản bác để tối ưu giải pháp."
        )
    else:
        user_content = f"Vấn đề: '{question}'"

    payload = _build_payload(model, base_url, system_prompt, user_content)
    result = await _post_and_parse(client, base_url, api_key, payload, name)
    if result is None:
        return {"claims": [], "evidence": [], "confidence": 0.0, "skipped": True}
    return result


# ─────────────────────────────────────────────
# SIMILARITY & CONSENSUS
# ─────────────────────────────────────────────

def calculate_conflict_score(opinions: Dict[str, Dict[str, Any]]) -> float:
    valid = {k: op for k, op in opinions.items() if not op.get("skipped")}
    keys = list(valid.keys())
    if len(keys) < 2:
        return 0.0
    conflicts = 0
    total_pairs = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            op1, op2 = valid[keys[i]], valid[keys[j]]
            c1 = set(c.lower() for c in op1.get("claims", []))
            c2 = set(c.lower() for c in op2.get("claims", []))
            if c1 and c2:
                union = len(c1 | c2)
                sim = len(c1 & c2) / union if union > 0 else 0.0
                if sim < 0.25:
                    conflicts += 1
            total_pairs += 1
    return float(conflicts / total_pairs) if total_pairs > 0 else 0.0


async def build_consensus(client: httpx.AsyncClient, opinions: Dict[str, Dict[str, Any]], question: str, api_config: Dict[str, Any]) -> Dict[str, Any]:
    builder_key = api_config.get("GEMINI_API_KEY") or api_config.get("OPENAI_API_KEY")
    if not builder_key:
        return {"final_decision": "Không có Key để chạy Consensus Node."}
    
    role_prompt = (
        "Bạn là Consensus Builder của Hội Đồng JKAI-Zenith. "
        "Nhiệm vụ: Đọc toàn bộ biên bản thảo luận của các Node (bao gồm cả local và cloud). "
        "Đúc kết ra giải pháp chung tối ưu nhất, chỉ rõ các luận điểm đồng thuận và các mâu thuẫn lớn còn tồn tại."
        "Trả về định dạng JSON: {\"final_decision\": \"kết luận chi tiết\", \"consensus_reached\": true}"
    )
    user_content = f"Vấn đề: '{question}'\n\nÝ kiến thảo luận:\n{json.dumps(opinions, ensure_ascii=False, indent=2)}"
    payload = _build_payload("gemini-3.5-flash", builder_key["base_url"], role_prompt, user_content)
    res = await _post_and_parse(client, builder_key["base_url"], builder_key["api_key"], payload, "ConsensusBuilder")
    return res or {"final_decision": "Không thể hoàn thành dung hợp tự động.", "consensus_reached": False}


def _format_opinion_details(res: Dict[str, Any]) -> str:
    parts = []

    claims = res.get("claims", [])
    if claims:
        parts.append("  * **Luận điểm:**")
        for c in claims:
            parts.append(f"    * {c}")

    evidence = res.get("evidence", [])
    if evidence:
        parts.append("  * **Bằng chứng:**")
        for e in evidence:
            parts.append(f"    * {e}")

    risks = res.get("risks", [])
    if risks:
        parts.append("  * **Rủi ro:**")
        for r in risks:
            parts.append(f"    * {r}")

    alternatives = res.get("alternatives", [])
    if alternatives:
        parts.append("  * **Giải pháp thay thế:**")
        for a in alternatives:
            parts.append(f"    * {a}")

    return "\n".join(parts) if parts else "  * Không có dữ liệu chi tiết."


# ─────────────────────────────────────────────
# EXECUTE & BUILD TRANSCRIPT
# ─────────────────────────────────────────────

async def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    task_id  = input_data.get("task_id", "sys")
    question = input_data.get("question")
    rounds   = input_data.get("rounds")
    focus_area = input_data.get("focus_area")

    if not question:
        return {"error": "Thiếu tham số bắt buộc: `question`"}

    api_config = load_api_keys_from_markdown()
    manifest_cfg = load_manifest_config()
    max_rounds = manifest_cfg["max_rounds"]
    conflict_threshold = manifest_cfg["conflict_threshold"]
    nodes = manifest_cfg.get("nodes", [])

    # Cap rounds to a maximum of 5
    rounds_to_run = min(max(1, int(rounds if rounds is not None else max_rounds)), 5)

    transcript_lines = []
    transcript_lines.append(f"## 🏛️ KÝ SỰ TRANH LUẬN HỘI ĐỒNG CHUYÊN GIA AI")
    transcript_lines.append(f"**Vấn đề:** *\"{question}\"*")
    if focus_area:
        transcript_lines.append(f"**Lĩnh vực tập trung:** `{focus_area}`\n")
    else:
        transcript_lines.append("")

    opinions = {}
    conflict_score = 0.0

    async with httpx.AsyncClient() as client:
        for r in range(1, rounds_to_run + 1):
            if r == 1:
                # ── Round 1: Independent Analysis ──
                transcript_lines.append("### ⚡ VÒNG 1: PHÂN TÍCH ĐỘC LẬP")
                engine.publish_mission_log("ZENITH", "[HOI_DONG] Vòng 1: Phân tích độc lập...", task_id)
                node_tasks = []
                node_names = []

                for node in nodes:
                    name = node["name"]
                    model = node["model"]
                    key_var = node["provider"]
                    if key_var in api_config:
                        cfg = api_config[key_var]
                        node_tasks.append(call_cloud_node(client, name, model, cfg["base_url"], cfg["api_key"], question, focus_area=focus_area))
                        node_names.append(name)
                        engine.publish_mission_log("ZENITH", f"[HOI_DONG] Triệu hồi {name} ({model})...", task_id)
                    else:
                        engine.publish_mission_log("WARN", f"[HOI_DONG] {name}: không có API key ({key_var})", task_id)

                if not node_tasks:
                    break

                results = await asyncio.gather(*node_tasks)
                for name, res in zip(node_names, results):
                    opinions[name] = res
                    if res.get("skipped"):
                        msg = f"⚠️ {name}: Không thể kết nối hoặc lỗi phản hồi."
                        transcript_lines.append(f"* **{name}**: {msg}")
                        engine.publish_mission_log("WARN", f"[HOI_DONG] {msg}", task_id)
                    else:
                        engine.publish_mission_log("ZENITH", f"[HOI_DONG] Raw response from {name}:\n{json.dumps(res, ensure_ascii=False, indent=2)}", task_id)
                        confidence = res.get('confidence', 0.0)
                        details = _format_opinion_details(res)
                        transcript_lines.append(f"* **{name}** (Độ tự tin: {confidence}):\n{details}")
                        claims_str = ", ".join(res.get("claims", []))[:300]
                        engine.publish_mission_log("ZENITH", f"[HOI_DONG] {name} hoàn tất (conf={confidence}): {claims_str}", task_id)

            else:
                # ── Round r > 1: Debate / Cross-Debate ──
                conflict_score = calculate_conflict_score(opinions)
                if conflict_score < conflict_threshold:
                    engine.publish_mission_log("ZENITH", f"[HOI_DONG] Consensus reached early at Round {r-1} (Conflict Score: {conflict_score:.2f} < {conflict_threshold}). Stopping debate.", task_id)
                    transcript_lines.append(f"\n* **Đạt đồng thuận sớm:** Chỉ số xung đột {conflict_score:.2f} nằm dưới ngưỡng {conflict_threshold}.")
                    break

                transcript_lines.append(f"\n### 🔥 VÒNG {r}: TRANH LUẬN & PHẢN BIỆN CHÉO")
                engine.publish_mission_log("ZENITH", f"[HOI_DONG] Vòng {r}: Tranh luận & phản biện chéo...", task_id)
                debate_tasks = []
                debate_names = []

                for node in nodes:
                    name = node["name"]
                    model = node["model"]
                    key_var = node["provider"]
                    if name in opinions and not opinions[name].get("skipped") and key_var in api_config:
                        cfg = api_config[key_var]
                        prior = {k: v for k, v in opinions.items() if k != name}
                        debate_tasks.append(call_cloud_node(client, name, model, cfg["base_url"], cfg["api_key"], question, prior_opinions=prior, focus_area=focus_area))
                        debate_names.append(name)
                        engine.publish_mission_log("ZENITH", f"[HOI_DONG] {name} đang phản biện ở vòng {r}...", task_id)

                if debate_tasks:
                    debate_results = await asyncio.gather(*debate_tasks)
                    for name, res in zip(debate_names, debate_results):
                        if not res.get("skipped"):
                          opinions[name] = res
                          engine.publish_mission_log("ZENITH", f"[HOI_DONG] Raw response from {name} (Round {r}):\n{json.dumps(res, ensure_ascii=False, indent=2)}", task_id)
                          details = _format_opinion_details(res)
                          transcript_lines.append(f"* **{name} (Cập nhật quan điểm ở Vòng {r}):**\n{details}")
                          claims_str = ", ".join(res.get("claims", []))[:300]
                          engine.publish_mission_log("ZENITH", f"[HOI_DONG] {name} phản biện hoàn tất ở vòng {r}: {claims_str}", task_id)

            conflict_score = calculate_conflict_score(opinions)
            transcript_lines.append(f"\n* **Chỉ số xung đột (Conflict Score) sau Vòng {r}:** {conflict_score:.2f} (Ngưỡng: {conflict_threshold})")
            engine.publish_mission_log("ZENITH", f"[HOI_DONG] Conflict Score sau Vòng {r}: {conflict_score:.2f}", task_id)

        # ── Consensus Summary ──
        transcript_lines.append("\n### 🤝 KẾT LUẬN ĐỒNG THUẬN")
        engine.publish_mission_log("ZENITH", "[HOI_DONG] Consensus Builder đang tổng hợp...", task_id)
        consensus = await build_consensus(client, opinions, question, api_config)
        final_decision = consensus.get("final_decision", "Không thể hoàn thành dung hợp ý kiến.")
        transcript_lines.append(final_decision)
        engine.publish_mission_log("ZENITH", f"[HOI_DONG] Consensus hoàn tất:\n{final_decision[:500]}", task_id)

    full_transcript = "\n".join(transcript_lines)

    return {
        "consensus_reached": consensus.get("consensus_reached", False),
        "conflict_score": conflict_score,
        "final_decision": full_transcript,
        "answer": full_transcript,
        "expert_opinions": opinions
    }


import os
import sys
import json
import time
import asyncio
from core.utils.engine import engine

# =================================================================
# 🛡️ JKAI ZENITH: LOGIC THẨM ĐỊNH MÃ NGUỒN ELITE v31.0 (QUANTUM AUDIT)
# =================================================================

async def audit_code(file_path: str, task_id: str = "audit"):
    """
    🔬 [QUANTUM-AUDIT]: Thẩm định mã nguồn đa tầng và kiến tạo giải pháp.
    """
    engine.publish_mission_log("AUDIT", f"🔍 [AUDIT-START]: Đang thẩm định chuyên sâu: `{file_path}`", task_id)

    if not os.path.exists(file_path):
        return {"status": "error", "msg": f"Tệp tin không tồn tại: {file_path}"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        # 🧬 [ELITE-PROMPT v31.0]: Kỷ luật sắt và Tư duy vĩ mô
        audit_prompt = f"""
        [HỆ THỐNG THẨM ĐỊNH TỐI CAO v31.0 - JKAI ZENITH]
        Nhiệm vụ: Phẫu thuật bối cảnh và chất lượng mã nguồn của tệp: {file_path}

        TIÊU CHUẨN ELITE:
        1. BẢO MẬT (Critical): Truy tìm dấu vết API Keys, Secrets, và các lỗ hổng thực thi.
        2. HIỆU NĂNG (Optimization): Phát hiện nghẽn nơ-ron, lãng phí tài nguyên CPU/VRAM.
        3. BẢN SẮC (Persona): Code có tuân thủ phong cách Elite (Gọn, Sắc, Chuyên nghiệp) không?
        4. GIẢI PHÁP (Surgery): Tạo ra mã thay thế trực tiếp.

        MÃ NGUỒN THỰC ĐỊA:
        ```python
        {code[:10000]} 
        ```
        (Ghi chú: Đã trích xuất 10,000 ký tự trọng tâm)

        TRẢ VỀ JSON:
        {{
            "score": 1-100,
            "issues": [
                {{ "type": "Security/Performance/Style", "severity": "High/Medium/Low", "desc": "..." }}
            ],
            "surgery_suggestion": {{
                "target": "Đoạn code lỗi",
                "replacement": "Đoạn code đã được tối ưu"
            }},
            "executive_summary": "Tóm tắt ngắn gọn cho Master"
        }}
        """

        # Triệu hồi CRITIC và JUDGE để có cái nhìn khách quan nhất
        response = await engine.call_chat(
            messages=[{"role": "user", "content": audit_prompt}],
            role="CRITIC",
            json_mode=True,
            task_id=task_id
        )

        if not response or "score" not in response:
            return {"status": "error", "msg": "Không thể giải mã báo cáo thẩm định nơ-ron."}

        # Lưu báo cáo vào Vault chuẩn v31.0
        ws_root = os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N")
        report_file = os.path.join(ws_root, "intelligence", "vault", f"AUDIT_{os.path.basename(file_path)}_{int(time.time())}.md")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        report_md = f"# 🏛️ BÁO CÁO THẨM ĐỊNH QUANTUM: {os.path.basename(file_path)}\n\n"
        report_md += f"**ĐIỂM CHẤT LƯỢNG: {response['score']}/100**\n\n"
        report_md += f"## 📊 TỔNG KẾT CHIẾN LƯỢC\n{response['executive_summary']}\n\n"
        report_md += "## 🚨 CÁC VẤN ĐỀ PHÁT HIỆN\n"
        for issue in response.get('issues', []):
            report_md += f"- **[{issue.get('type', 'Unknown')}]** ({issue.get('severity', 'Low')}): {issue.get('desc', '')}\n"
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_md)

        engine.publish_mission_log("AUDIT", f"✅ [AUDIT-SUCCESS]: Đã niêm phong báo cáo tại Vault. Điểm: {response['score']}/100", task_id)
        
        return {
            "status": "success",
            "score": response["score"],
            "report_path": report_file,
            "surgery_suggestion": response.get("surgery_suggestion"),
            "msg": f"Thẩm định hoàn tất. Điểm: {response['score']}. Master có muốn thực hiện phẫu thuật ngay không?"
        }

    except Exception as e:
        return {"status": "error", "msg": f"Sự cố thẩm định Quantum: {str(e)}"}

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N"), "services/ai-control-plane/task_manager.py")
    try:
        res = asyncio.run(audit_code(path))
        print(json.dumps(res, indent=2, ensure_ascii=True))
    except Exception as e:
        print(json.dumps({"status": "error", "msg": str(e)}))

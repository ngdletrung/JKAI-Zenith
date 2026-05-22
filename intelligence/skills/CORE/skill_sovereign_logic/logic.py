import os
import sys
import json
import asyncio

# Ép mã hóa UTF-8 cho Console Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 💎 GIAO THỨC KẾT NỐI LINH HOẠT (CONTEXT-AWARE)
if os.path.exists("/.dockerenv"):
    os.environ["REDIS_HOST"] = "redis-ai"
    os.environ["OLLAMA_HOST"] = "http://host.docker.internal:11434"
else:
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["OLLAMA_HOST"] = "http://localhost:11434"

# Đảm bảo nạp được core engine
try:
    from core.utils.engine import engine
except ImportError:
    pass)))))
from core.utils.engine import engine

# =================================================================
# 🏛️ JKAI ZENITH: SOVEREIGN ADVISORY ENGINE (v1.0 Elite)
# =================================================================

async def run_sovereign_analysis(goal: str, task_id: str = "sovereign_task"):
    print(f"[ZENITH-SOVEREIGN]: Initiating deep analysis for: {goal}")
    
    # 1. Nạp bối cảnh thấu thị
    context_files = [
        "intelligence/rule_hardware.md",
        "intelligence/JKAI_ZENITH_CORP.md",
        "intelligence/proposals/ZENITH_ASCENSION_V30_BLUEPRINT.md"
    ]
    
    context_data = ""
    for f_path in context_files:
        full_path = os.path.join(os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N"), f_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                context_data += f"\n---\nFILE: {f_path}\n{f.read()[:2000]}"

    # 2. Xây dựng prompt Thăng hoa
    sovereign_prompt = f"""Bạn là JKAI ZENITH SINGULARITY (v1.0 Elite) (since 01/05/2026). Master LeeTrung yêu cầu phân tích: "{goal}".
Hãy sử dụng toàn bộ trí tuệ nơ-ron chiến lược để:
1. Phân tích chiều sâu kiến trúc và rủi ro.
2. Đề xuất phương án thực thi "Surgical" (chuẩn xác nhất).
3. Đề xuất bước tiến hóa tiếp theo cho hệ thống.

NGỮ CẢNH HỆ THỐNG:
{context_data}
"""

    # 3. Gọi PLANNER (Dựa trên Hiến pháp rule_hardware.md)
    try:
        analysis = await engine.call_chat(
            messages=[{"role": "user", "content": sovereign_prompt}],
            role="PLANNER",
            task_id=task_id
        )
        
        # 4. Lưu kết quả vào Vault Chiến lược
        if os.path.exists("/.dockerenv"):
            vault_path = f"/intelligence/reports/SOVEREIGN_STRATEGY_{task_id}.md"
        else:
            vault_path = fos.getenv("WORKSPACE_ROOT", "D:/Docker/N8N") + "/intelligence/reports/SOVEREIGN_STRATEGY_{task_id}.md"
        
        os.makedirs(os.path.dirname(vault_path), exist_ok=True)
        with open(vault_path, "w", encoding="utf-8") as f:
            f.write(f"# 💎 CHẾ ĐỘ QUÂN SƯ: PHÂN TÍCH CHIẾN LƯỢC\n\n## YÊU CẦU: {goal}\n\n{analysis}\n\n--- \n*💎🫡🦾🚀⚡🌌🏛️🦾*")

        return {
            "status": "success",
            "analysis": analysis,
            "report": vault_path,
            "msg": "Phân tích chiến lược Sovereign đã hoàn tất."
        }
    except Exception as e:
        return {"status": "error", "msg": f"Sự cố nơ-ron: {str(e)}"}

if __name__ == "__main__":
    import sys as _sys
    query = " ".join(_sys.argv[1:]) if len(_sys.argv) > 1 else "Tối ưu hóa toàn diện hệ thống"
    res = asyncio.run(run_sovereign_analysis(query))
    print(json.dumps(res, indent=2, ensure_ascii=False))

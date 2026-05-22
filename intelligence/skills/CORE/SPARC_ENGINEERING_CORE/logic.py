import asyncio
from core.utils.engine import engine

class SPARCWorkflow:
    """
    💻 JKAI ZENITH: SPARC PIPELINE (Elite Programming)
    Quy trình 5 bước phát triển phần mềm chuẩn Ruflo v3.6.
    """
    def __init__(self):
        self.phases = ["SPECIFICATION", "PSEUDOCODE", "ARCHITECTURE", "REFINEMENT", "COMPLETION"]

    async def execute_sparc(self, task: str, **kwargs):
        """
        🚀 Kích hoạt Giao thức SPARC: Từ ý tưởng đến mã nguồn hoàn thiện.
        """
        engine.publish_mission_log("SPARC", f"💻 [START]: Khởi động quy trình SPARC cho nhiệm vụ: {task}")
        
        results = {}
        for phase in self.phases:
            engine.publish_mission_log("SPARC", f"🧬 [PHASE]: Đang thực hiện {phase}...")
            
            # Thực thi logic cho từng Phase
            phase_result = await self._run_phase(phase, task, results)
            results[phase] = phase_result
            
            engine.publish_mission_log("SPARC", f"✅ [DONE]: {phase} hoàn tất.")
            await asyncio.sleep(1) # Phản xạ nơ-ron

        return {
            "status": "success",
            "msg": f"🎯 [SPARC]: Đã hoàn thiện mã nguồn theo tiêu chuẩn Elite.",
            "artifacts": results
        }

    async def _run_phase(self, phase, task, previous_results):
        """Hỏi nơ-ron để thực hiện từng giai đoạn."""
        prompt = f"""
        [GIAO THỨC SPARC v3.6]
        Phase hiện tại: {phase}
        Nhiệm vụ tổng thể: {task}
        Dữ liệu từ các phase trước: {previous_results}
        
        Hãy thực hiện yêu cầu của Phase này và trả về kết quả cấu trúc.
        """
        return await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role=f"SPARC-{phase}",
            model="claude-3-5-sonnet" # Ưu tiên Sonnet cho lập trình
        )

# Singleton
_instance = SPARCWorkflow()
execute_sparc = _instance.execute_sparc

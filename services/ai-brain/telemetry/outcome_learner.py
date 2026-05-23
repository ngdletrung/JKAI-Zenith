import asyncio
import os
import json

class OutcomeLearner:
    """
    🧠 Buồng Học Trực Chiến (Outcome Learning Engine)
    Quét Execution Journal để rút kinh nghiệm và cập nhật Calibration Weights.
    """
    def __init__(self, calibration_engine, journal_dir: str = "d:/Docker/N8N/services/ai-brain/memory/journals"):
        self.calibration_engine = calibration_engine
        self.journal_dir = journal_dir

    async def distill_knowledge_from_journal(self):
        """Chạy ngầm (cron job) để đọc lại các vết tích thực thi cũ."""
        print("🌀 [OUTCOME LEARNER]: Khởi động quét Execution Journal để rút kinh nghiệm...")
        
        if not os.path.exists(self.journal_dir):
            print("Chưa có Journal nào được sinh ra.")
            return

        total_scanned = 0
        patterns = {"success": {}, "failures": {}}

        for filename in os.listdir(self.journal_dir):
            if not filename.endswith(".json"): continue
            
            filepath = os.path.join(self.journal_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    trace = json.load(f)
                    
                intent = trace.get("cir", {}).get("intent", "UNKNOWN")
                state = trace.get("final_state", "FAILED")
                
                # Cập nhật điểm uy tín cho Calibration Engine
                is_success = (state == "COMPLETED")
                self.calibration_engine.update_reliability(intent, is_success)
                
                # Thống kê Pattern
                if is_success:
                    patterns["success"][intent] = patterns["success"].get(intent, 0) + 1
                else:
                    patterns["failures"][intent] = patterns["failures"].get(intent, 0) + 1
                    
                total_scanned += 1
            except Exception as e:
                print(f"Lỗi đọc journal {filename}: {e}")

        print(f"✅ [OUTCOME LEARNER]: Đã quét {total_scanned} traces.")
        print(f"📊 Failure Patterns: {patterns['failures']}")

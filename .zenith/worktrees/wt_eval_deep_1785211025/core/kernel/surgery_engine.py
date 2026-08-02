"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — AUTONOMIC SURGERY ENGINE                         ║
║   Phòng Phẫu Thuật Mã Nguồn & Tự Chữa Lành Hệ Thống               ║
╚══════════════════════════════════════════════════════════════════╝
*Ban Y tế Kỹ thuật & Tự chữa lành Mã nguồn Thân thể của JKAI. 🌌🔬🧬*
"""

import os
import ast
import json
import time
import logging
import traceback
from typing import Dict, Any, Optional, Tuple

from core.utils.engine import engine
from core.kernel.capability_broker import capability_broker, CapabilityType
from core.kernel.cognitive_scheduler import cognitive_transaction_manager
from core.kernel.cognitive_event_bus import cognitive_event_bus, CognitiveEvent

logger = logging.getLogger("SurgeryEngine")

class SurgeryEngine:
    """
    ⚙️ PHÒNG PHẪU THUẬT LÕI MÃ NGUỒN (Autonomic Self-Healing Code Surgery Engine)
    Tự động dò quét, lập bệnh án và tiến hành phẫu thuật khẩn cấp (hot-patch)
    mã nguồn khi phát hiện sự cố biên dịch, lỗi cú pháp hoặc ngoại lệ nghiêm trọng.
    """
    
    @staticmethod
    def verify_syntax(code_content: str, file_path: str) -> Tuple[bool, str]:
        """
        🧪 [KIỂM TRA LÂM SÀNG]: Độc lập biên dịch thử mã nguồn để kiểm tra lỗi cú pháp (SyntaxError).
        """
        try:
            compile(code_content, file_path, "exec")
            return True, "Hồ sơ sức khỏe tốt. Không phát hiện lỗi cú pháp biên dịch."
        except SyntaxError as se:
            err_detail = f"SyntaxError tại dòng {se.lineno}: {se.msg} -> Đoạn lỗi: {se.text}"
            return False, err_detail
        except Exception as e:
            return False, f"Lỗi kiểm toán không xác định: {str(e)}"

    async def attempt_surgery(self, 
                              file_path: str, 
                              error_message: str, 
                              task_id: str = "sys", 
                              trace_id: str = "sys") -> bool:
        """
        ⚡ [GIAO THỨC PHẪU THUẬT KHẨN CẤP COGNITIVE ACID THƯA TỔNG GIÁM ĐỐC]:
        1. Cấp phát Capability Token bảo mật từ CapabilityBroker (Microkernel).
        2. Khởi động Giao dịch Nhận thức và sao lưu vật lý dạng `{file_path}.bak` (Method A).
        3. Triệu tập Hội chẩn LLM (spawns an LLM consultation session) để đề xuất bản vá.
        4. Phẫu thuật thử nghiệm trên môi trường hộp cát Shadow Clone và AST verification.
        5. Ghi đè (hot-patch) tệp tin gốc nếu bản vá an toàn 100% và Commit giao dịch.
        6. Rollback hoàn toàn về nguyên trạng ban đầu nếu bất kỳ bước nào trong quy trình gặp sự cố.
        """
        # 🏢 LOG VĂN PHÒNG CHUẨN DOANH NGHIỆP
        engine.publish_mission_log(
            "SURGERY",
            f"🩺 [PHÒNG PHẪU THUẬT LÕI] Đã tiếp nhận ca cấp cứu mã nguồn khẩn cấp tại tệp: `{os.path.basename(file_path)}` thưa Tổng Giám Đốc.",
            task_id,
            trace_id
        )

        if not os.path.exists(file_path):
            engine.publish_mission_log(
                "ERROR",
                f"❌ [PHẪU THUẬT THẤT BẠI] Bệnh án không tồn tại tệp mục tiêu: `{file_path}`",
                task_id,
                trace_id
            )
            return False

        # -------------------------------------------------------------
        # 🔐 1. MICROKERNEL PRIVILEGE ACQUISITION
        # -------------------------------------------------------------
        fs_token = capability_broker.issue_token(
            task_id=task_id,
            cap_type=CapabilityType.FILESYSTEM,
            scope=os.path.dirname(file_path)
        )
        exec_token = capability_broker.issue_token(
            task_id=task_id,
            cap_type=CapabilityType.EXECUTION,
            scope="d:/Docker/JKAI/scratch/sandbox"
        )

        if not capability_broker.verify_privilege(fs_token.token_id, CapabilityType.FILESYSTEM, file_path):
            engine.publish_mission_log(
                "ERROR",
                "❌ [PHẪU THUẬT THẤT BẠI] Từ chối quyền phẫu thuật: Thẻ năng lực FILESYSTEM không đủ thẩm quyền thưa Master!",
                task_id,
                trace_id
            )
            return False

        # -------------------------------------------------------------
        # 🏛️ 2. COGNITIVE ACID TRANSACTION BEGIN & BACKUP
        # -------------------------------------------------------------
        tx_id = f"tx-surgery-{task_id}-{int(time.time())}"
        tx = await cognitive_transaction_manager.begin_transaction(tx_id, task_id)
        
        try:
            # Ghi nhận backup dạng .bak theo Phương án A đã chọn thưa Master
            await cognitive_transaction_manager.register_backup(tx_id, file_path)

            # Đọc nội dung file hiện tại
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            # -------------------------------------------------------------
            # 🔬 3. CHẨN ĐOÁN LÂM SÀNG & ĐỀ XUẤT BẢN VÁ LLM
            # -------------------------------------------------------------
            engine.publish_mission_log(
                "SURGERY",
                "🔬 [PHÒNG PHẪU THUẬT LÕI] Hội đồng Y khoa (LLM Consultation) đang hội chẩn lâm sàng...",
                task_id,
                trace_id
            )

            prompt = (
                f"Bạn là Giáo Sư Phẫu Thuật Lõi (Chief Surgery Officer) của Tập đoàn JKAI Zenith.\n"
                f"Một tệp mã nguồn trong hệ thống của chúng ta đang gặp sự cố nghiêm trọng sau đây:\n\n"
                f"📁 TỆP TIN: {file_path}\n"
                f"🚨 THÔNG BÁO LỖI HỆ THỐNG / TRACEBACK:\n{error_message}\n\n"
                f"NỘI DUNG MÃ NGUỒN HIỆN TẠI:\n"
                f"```python\n{original_content}\n```\n\n"
                f"NHIỆM VỤ CỦA GIÁO SƯ:\n"
                f"Hãy phân tích và viết một đoạn mã đã sửa lỗi hoàn toàn, đảm bảo khắc phục triệt để lỗi trên mà KHÔNG ảnh hưởng hay làm mất các logic khác của hệ thống.\n"
                f"Hãy xuất ra dưới cấu trúc JSON chuẩn mực như sau để Ban Thư ký thực thi:\n"
                f"{{\n"
                f"  \"target_content\": \"Đoạn mã bị lỗi chính xác cần tìm để thay thế (phải khớp từng ký tự bao gồm khoảng trắng)\",\n"
                f"  \"replacement_content\": \"Đoạn mã mới an toàn sẽ thay thế vào đó\"\n"
                f"}}\n\n"
                f"Chú ý: Trả về CHỈ duy nhất khối JSON đó, không giải thích gì thêm."
            )

            consult_res = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="SUMMARIZER",
                task_id=task_id
            )

            # Phân tích đề xuất từ JSON
            try:
                clean_res = consult_res.strip()
                if clean_res.startswith("```json"):
                    clean_res = clean_res[7:]
                if clean_res.endswith("```"):
                    clean_res = clean_res[:-3]
                clean_res = clean_res.strip()

                try:
                    proposal = json.loads(clean_res)
                except Exception:
                    proposal = ast.literal_eval(clean_res)
            except Exception as parse_err:
                engine.publish_mission_log(
                    "WARN",
                    f"⚠️ [PHẪU THUẬT CẢNH BÁO] Hội đồng đề xuất định dạng phức tạp ({str(parse_err)}). Đang chuyển sang chiến lược vá toàn văn...",
                    task_id,
                    trace_id
                )
                if "def" in consult_res or "import" in consult_res:
                    proposal = {"target_content": original_content, "replacement_content": consult_res}
                else:
                    await cognitive_transaction_manager.rollback_transaction(tx_id)
                    return False

            target = proposal.get("target_content", "")
            replacement = proposal.get("replacement_content", "")

            if not target or not replacement:
                engine.publish_mission_log(
                    "ERROR",
                    "❌ [PHẪU THUẬT THẤT BẠI] Bản vá đề xuất rỗng hoặc thiếu thông tin thay thế.",
                    task_id,
                    trace_id
                )
                await cognitive_transaction_manager.rollback_transaction(tx_id)
                return False

            # Gắn khớp bản vá
            if target not in original_content:
                engine.publish_mission_log(
                    "WARN",
                    "⚠️ [PHẪU THUẬT KHÔNG KHỚP] Đoạn mã mục tiêu tìm kiếm không khớp hoàn hảo với mã nguồn thực tế. Đang kích hoạt cứu hộ...",
                    task_id,
                    trace_id
                )
                await cognitive_transaction_manager.rollback_transaction(tx_id)
                return False

            patched_content = original_content.replace(target, replacement)

            # -------------------------------------------------------------
            # 🔬 4. KIỂM TRA LÂM SÀNG CÚ PHÁP & CHẠY THỬ TRONG HỘP CÁT SECURE
            # -------------------------------------------------------------
            # 4.1 AST Compile Check địa phương
            ok, diag_msg = self.verify_syntax(patched_content, file_path)
            if not ok:
                engine.publish_mission_log(
                    "ERROR",
                    f"🚨 [PHẪU THUẬT THẤT BẠI] Bản vá thử nghiệm không vượt qua vòng kiểm tra cú pháp biên dịch! Chi tiết: {diag_msg}",
                    task_id,
                    trace_id
                )
                await cognitive_transaction_manager.rollback_transaction(tx_id)
                return False

            # 4.2 Sandbox Subprocess Isolation Check
            # Prepend workspace paths so that imports work beautifully inside sandbox
            sandbox_code = (
                f"import sys\n"
                f"sys.path.insert(0, r'{os.path.dirname(os.path.dirname(os.path.dirname(file_path)))}')\n"
                f"{patched_content}\n"
            )
            
            sb_ok, exit_code, stdout, stderr = await sandbox_executor.execute_isolated_code(
                token_id=exec_token.token_id,
                code_content=sandbox_code,
                script_name=f"test_{os.path.basename(file_path)}",
                timeout_sec=5.0
            )

            if not sb_ok and exit_code != 0:
                engine.publish_mission_log(
                    "ERROR",
                    f"🚨 [PHẪU THUẬT THẤT BẠI] Bản vá thử nghiệm bị sập hoặc treo bên trong Hộp cát Shadow Clone! Exit Code: {exit_code}\nStderr: {stderr}",
                    task_id,
                    trace_id
                )
                await cognitive_transaction_manager.rollback_transaction(tx_id)
                return False

            # -------------------------------------------------------------
            # ✨ 5. CAM KẾT VÀ KHÂU VẾT MỔ (COMMIT & PROMOTE CANARY)
            # -------------------------------------------------------------
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(patched_content)

            # Commit giao dịch, dọn dẹp file .bak an toàn
            await cognitive_transaction_manager.commit_transaction(tx_id)

            engine.publish_mission_log(
                "SURGERY",
                f"⚙️ [PHÒNG PHẪU THUẬT LÕI] Ca phẫu thuật thành công mỹ mãn! Đã hot-patch thành công tệp `{os.path.basename(file_path)}`. Hệ thống tự động phục hồi hành pháp! ✨🫡💎",
                task_id,
                trace_id
            )

            # Phát sự kiện lên Bus hệ thần kinh
            await cognitive_event_bus.publish(CognitiveEvent(
                event_id=f"evt-srg-ok-{int(time.time())}",
                event_type="PATCH_APPROVED",
                task_id=task_id,
                agent_id="SurgeryEngine",
                payload={"file_path": file_path, "tx_id": tx_id}
            ))

            return True

        except Exception as e:
            tb = traceback.format_exc()
            engine.publish_mission_log(
                "ERROR",
                f"❌ [LỖI PHẪU THUẬT PHÁT SINH]: {str(e)} \nTraceback: {tb}",
                task_id,
                trace_id
            )
            # Hoàn tác cứu nguy khẩn cấp thưa Master
            await cognitive_transaction_manager.rollback_transaction(tx_id)
            return False

surgery_engine = SurgeryEngine()

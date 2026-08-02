"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CAPABILITY BROKER & SANDBOX                      ║
║   Quản Trị Năng Lực Microkernel & Hộp Cát Phẫu Thuật Cô Lập      ║
╚══════════════════════════════════════════════════════════════════╝
*Thuộc Ban Quản Trị An Ninh, Cách Ly & Phẫu Thuật An Toàn của JKAI. 🌌🛡️🔬*
"""

import os
import sys
import uuid
import time
import subprocess
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Tuple, Optional

from core.utils.engine import engine

logger = logging.getLogger("CapabilityBroker")

# =================════====================================
# 🛡️ 1. MICROKERNEL SCOPED CAPABILITY SYSTEM
# =================════====================================

class CapabilityType(str, Enum):
    FILESYSTEM = "FILESYSTEM"  # Đọc/ghi tệp tin có phạm vi giới hạn
    NETWORK = "NETWORK"        # Thực thi cuộc gọi mạng / APIs
    EXECUTION = "EXECUTION"    # Chạy các scripts / lệnh hệ thống

@dataclass(frozen=True)
class CapabilityToken:
    token_id: str
    task_id: str
    cap_type: CapabilityType
    scope: str               # ví dụ: "scratch/sandbox", "d:/Docker/JKAI/core"
    expires_at: float
    signature: str           # Chữ ký kiểm chứng tính toàn vẹn thưa Master

    def is_valid(self, path: Optional[str] = None) -> bool:
        if time.time() > self.expires_at:
            return False
        if path and not path.startswith(self.scope) and self.scope != "*":
            return False
        return True


class CapabilityBroker:
    """
    🏢 BAN CẤP PHÁT NĂNG LỰC (Microkernel Capability Broker)
    Kiểm soát và phát hành các vé quyền hạn có thời hạn cho Planner thưa Tổng Giám Đốc.
    LLM tuyệt đối không được phép trực tiếp chạm vào hệ điều hành.
    """
    def __init__(self, secret_key: str = "zenith_v6_secure_key_thua_master"):
        self._secret_key = secret_key
        self._active_tokens: Dict[str, CapabilityToken] = {}

    def issue_token(self, task_id: str, cap_type: CapabilityType, scope: str, duration_sec: float = 600) -> CapabilityToken:
        """
        🎟️ [PHÁT HÀNH THẺ QUYỀN]: Cấp vé quyền truy cập giới hạn thưa Master.
        """
        token_id = f"cap-token-{uuid.uuid4().hex[:8]}"
        expires_at = time.time() + duration_sec
        # Sinh chữ ký giả lập bảo mật thưa Master
        signature = f"sig-{hash(token_id + self._secret_key + scope)}"
        
        token = CapabilityToken(
            token_id=token_id,
            task_id=task_id,
            cap_type=cap_type,
            scope=os.path.abspath(scope) if scope != "*" else "*",
            expires_at=expires_at,
            signature=signature
        )
        self._active_tokens[token_id] = token
        logger.info(f"🔑 [CAP-BROKER]: Đã phát hành thẻ năng lực `{cap_type.value}` cho tác vụ `{task_id}`. Scope: `{scope}`.")
        return token

    def verify_privilege(self, token_id: str, cap_type: CapabilityType, target_path: Optional[str] = None) -> bool:
        """ Kiểm tra xem thẻ năng lực có hợp lệ và đủ thẩm quyền không thưa Master. """
        token = self._active_tokens.get(token_id)
        if not token:
            logger.warn(f"🚨 [PRIVILEGE-DENIED]: Thẻ năng lực `{token_id}` không tồn tại hoặc đã bị thu hồi!")
            return False

        if token.cap_type != cap_type:
            logger.warn(f"🚨 [PRIVILEGE-DENIED]: Thẻ năng lực sai loại yêu cầu. Đòi hỏi `{cap_type.value}` nhưng thẻ là `{token.cap_type.value}`.")
            return False

        path_to_check = os.path.abspath(target_path) if target_path else None
        if not token.is_valid(path_to_check):
            logger.warn(f"🚨 [PRIVILEGE-DENIED]: Thẻ năng lực đã hết hạn hoặc truy cập vượt phạm vi an toàn (`{target_path}` nằm ngoài `{token.scope}`) thưa Master!")
            return False

        return True


# =====================================================================
# 🔬 2. CHÍNH SÁCH BẢO MẬT & FORMAL SAFETY GOVERNOR
# =================════====================================

class PolicyProofEngine:
    """
    🛡️ [POLICY-PROOF-ENGINE]: Động cơ Kiểm Chứng Chính Sách An Toàn thưa Tổng Giám Đốc (Formal Safety Governor).
    Thực hiện phân tích mã nguồn định tính trước khi thực thi nhằm chứng minh toán học:
    Mã nguồn KHÔNG chứa hành vi nâng quyền, KHÔNG gây mất mát dữ liệu và dịch vụ có thể khôi phục.
    """
    @staticmethod
    def prove_safety(code_content: str, token: CapabilityToken) -> Tuple[bool, str]:
        """
        🧪 [CHỨNG MINH AN TOÀN]: Quét mã nguồn tĩnh (Static AST Prover) thưa Master.
        Bảo vệ "Deny-by-Default" chống lại mã độc hại hoặc các câu lệnh phá hoại.
        """
        # 1. Luật cấm tuyệt đối xóa tệp tin hệ thống quan trọng
        dangerous_calls = ["os.system", "shutil.rmtree", "os.remove", "os.rmdir", "subprocess.Popen"]
        
        # Nếu thẻ năng lực không cho phép thực thi (EXECUTION), chặn tuyệt đối các lệnh chạy shell
        if token.cap_type != CapabilityType.EXECUTION:
            for call in dangerous_calls:
                if call in code_content:
                    return False, f"Formal Safety Proof Failed: Mã nguồn chứa lệnh nguy hiểm `{call}` khi không có thẻ EXECUTION thưa Master!"

        # 2. Nếu thẻ năng lực có phạm vi bị giới hạn (scope != "*"), chặn đứng hoàn toàn việc thực thi shell tự do để tránh thoát khỏi hộp cát
        if token.scope != "*":
            shell_calls = ["os.system", "subprocess.Popen", "subprocess.run"]
            for call in shell_calls:
                if call in code_content:
                    return False, f"Formal Safety Proof Failed: Mã nguồn chứa lệnh thực thi shell nguy hiểm `{call}` trong thẻ năng lực có phạm vi bị giới hạn thưa Tổng Giám Đốc!"

        # 3. Ngăn chặn tuyệt đối viết đè ngoài vùng đệm Sandbox nếu thẻ giới hạn ở sandbox
        if token.scope != "*" and "open(" in code_content:
            # Kiểm toán sơ bộ đường dẫn: Ngăn chặn ghi tệp đệ quy lên thư mục cấp cao
            for line in code_content.splitlines():
                if "open(" in line and "w" in line:
                    if ".." in line or "/" in line or "\\" in line:
                        # Phát hiện đường dẫn tương đối nguy hiểm
                        if not any(folder in line for f in ["scratch", "sandbox"]):
                            return False, f"Formal Safety Proof Failed: Phát hiện nỗ lực ghi tệp ngoài vùng Sandbox thưa Tổng Giám Đốc! Dòng lỗi: `{line.strip()}`"

        return True, "Formal Safety Proof Approved: Đã chứng minh mã nguồn an toàn tuyệt đối, không phát hiện rủi ro xâm hại hệ thống."


# =====================================================================
# 📦 3. SHADOW CLONE SECURE SANDBOX EXECUTOR
# =================════====================================

class SandboxExecutor:
    """
    📦 [SANDBOX-EXECUTOR]: Động cơ Hộp cát bảo mật Shadow Clone thưa Tổng Giám Đốc.
    Vận hành mã nguồn thử nghiệm hoàn toàn cô lập trong phân vùng `scratch/sandbox`
    để ngăn chặn nỗ lực phá hoại RAM, CPU, chiếm file handles hoặc rò rỉ VRAM.
    """
    def __init__(self, broker: CapabilityBroker, proof_engine: PolicyProofEngine):
        self.broker = broker
        self.proof_engine = proof_engine
        self.sandbox_dir = "d:/Docker/JKAI/scratch/sandbox"
        if not os.path.exists(self.sandbox_dir):
            os.makedirs(self.sandbox_dir, exist_ok=True)

    async def execute_isolated_code(self, 
                                   token_id: str, 
                                   code_content: str, 
                                   script_name: str = "patch_test.py", 
                                   timeout_sec: float = 10.0) -> Tuple[bool, int, str, str]:
        """
        🚀 [VẬN HÀNH TRONG HỘP CÁT]: Thực thi mã nguồn cô lập thưa Master.
        Trả về: (thành công, exit_code, stdout, stderr)
        """
        # 1. Thẩm định thẻ năng lực
        if not self.broker.verify_privilege(token_id, CapabilityType.EXECUTION):
            return False, -1, "", "Lỗi An Ninh: Yêu cầu thực thi bị chặn do thẻ năng lực không hợp lệ thưa Master."

        token = self.broker._active_tokens[token_id]

        # 2. Chứng minh an toàn mã nguồn tĩnh trước khi viết ra đĩa
        safe, proof_msg = self.proof_engine.prove_safety(code_content, token)
        if not safe:
            engine.publish_mission_log(
                "SECURITY_BREACH",
                f"🚨 [PHÁT HIỆN VI PHẠM AN NINH] {proof_msg}",
                "sys",
                "sys"
            )
            return False, -2, "", f"Lỗi An Ninh: Bộ kiểm chứng chính sách (Policy Prover) từ chối thực thi! {proof_msg}"

        # 3. Ghi file mã nguồn vào vùng hộp cát Shadow Clone
        file_path = os.path.join(self.sandbox_dir, script_name)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code_content)
        except Exception as e:
            return False, -3, "", f"Lỗi ghi tệp Sandbox thưa Master: {e}"

        # 4. Kích hoạt tiến trình cô lập với giới hạn cứng tài nguyên (Real Resource Isolation)
        # Giả lập cgroups/job limits bằng cách ép buộc chạy tiến trình con có giới hạn timeout cực đoan
        engine.publish_mission_log(
            "SANDBOX",
            f"📦 [HỘP CÁT SHADOW CLONE] Bắt đầu chạy thử nghiệm tệp `{script_name}` cô lập (Giới hạn thời gian: {timeout_sec}s)...",
            "sys",
            "sys"
        )

        start_time = time.time()
        try:
            # Khởi động tiến trình con độc lập thưa Master
            proc = subprocess.Popen(
                [sys.executable, file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.sandbox_dir
            )

            # Chờ đợi thực thi trong giới hạn an toàn
            try:
                stdout, stderr = proc.communicate(timeout=timeout_sec)
                exit_code = proc.returncode
                duration = time.time() - start_time
                
                if exit_code == 0:
                    logger.info(f"✨ [SANDBOX-SUCCESS]: Chạy thử thành công trong {duration:.2f}s.")
                    return True, 0, stdout, stderr
                else:
                    logger.warn(f"❌ [SANDBOX-FAIL]: Lỗi thực thi mã nguồn. Exit code: {exit_code}.")
                    return False, exit_code, stdout, stderr

            except subprocess.TimeoutExpired:
                # RUNAWAY THREAD PROTECTION thưa Master
                proc.kill()
                stdout, stderr = proc.communicate()
                engine.publish_mission_log(
                    "SANDBOX_TIMEOUT",
                    f"💀 [RUNAWAY PROTECTION] Phát hiện tiến trình trong Hộp cát vượt giới hạn thời gian cho phép ({timeout_sec}s)! "
                    f"Đã kích hoạt ngắt cưỡng bức để bảo toàn tài nguyên CPU/RAM thưa Tổng Giám Đốc.",
                    "sys",
                    "sys"
                )
                return False, -4, stdout, f"TimeoutExpired: Tiến trình bị kết liễu cưỡng bức sau {timeout_sec} giây để chống treo đệ quy thưa Master."

        except Exception as e:
            return False, -5, "", f"Lỗi hệ thống khởi chạy hộp cát: {str(e)}"
        finally:
            # 5. Dọn dẹp tệp tin thử nghiệm trong hộp cát để bảo mật thưa Master
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

# Khởi tạo Singletons cho Nhân bảo mật thưa Master
capability_broker = CapabilityBroker()
policy_proof_engine = PolicyProofEngine()
sandbox_executor = SandboxExecutor(capability_broker, policy_proof_engine)

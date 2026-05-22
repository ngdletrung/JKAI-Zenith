import subprocess
import hashlib
import os

def get_hwid():
    """
    💎 [NEURAL FINGERPRINT]: Tạo dấu vân tay phần cứng duy nhất.
    Kết hợp Serial Mainboard, CPU ID và địa chỉ MAC.
    """
    try:
        # Lấy Serial Mainboard (Thường ổn định nhất)
        cmd_board = "cat /sys/class/dmi/id/board_serial 2>/dev/null || echo 'unknown_board'"
        board = subprocess.check_output(cmd_board, shell=True).decode().strip()
        
        # Lấy CPU ID
        cmd_cpu = "grep -i 'serial' /proc/cpuinfo 2>/dev/null | head -n 1 || echo 'unknown_cpu'"
        cpu = subprocess.check_output(cmd_cpu, shell=True).decode().strip()
        
        # Lấy Machine ID (Định danh của HĐH Linux/Docker)
        cmd_machine = "cat /etc/machine-id 2>/dev/null || echo 'no_machine_id'"
        machine = subprocess.check_output(cmd_machine, shell=True).decode().strip()

        raw_id = f"{board}-{cpu}-{machine}"
        hwid = hashlib.sha256(raw_id.encode()).hexdigest()
        return hwid
    except:
        return "fallback_identity_static_000"

def verify_device_identity(stored_hash):
    """Kiểm tra xem phần cứng hiện tại có khớp với dữ liệu đã lưu không."""
    current_hwid = get_hwid()
    return current_hwid == stored_hash

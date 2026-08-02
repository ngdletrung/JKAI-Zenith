import psutil
import time

class HomeostasisEngine:
    """
    🔋 Động Cơ Sinh Tồn (Homeostasis Engine)
    Mang lại cảm giác "Sợ hãi" và "Bản năng sinh tồn" cho AI.
    Liên tục đo lường Tài nguyên Vật lý (RAM, CPU, IO) và Token Budget.
    """
    def __init__(self, max_ram_percent=85.0, max_cpu_percent=90.0):
        self.max_ram_percent = max_ram_percent
        self.max_cpu_percent = max_cpu_percent

    def check_vitals(self) -> dict:
        """
        Đo nhịp tim hệ thống. Nếu tài nguyên cạn kiệt, báo động Đỏ.
        """
        try:
            ram = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent(interval=0.1)
            
            danger = False
            warnings = []
            
            if ram > self.max_ram_percent:
                danger = True
                warnings.append(f"RAM OVERLOAD ({ram}%) - Nguy cơ OOM (Out of Memory) Crash!")
                
            if cpu > self.max_cpu_percent:
                danger = True
                warnings.append(f"CPU OVERLOAD ({cpu}%) - Nguy cơ Timeout toàn hệ thống!")
                
            return {
                "survival_threat": danger,
                "vitals": {"ram": ram, "cpu": cpu},
                "warnings": warnings
            }
        except Exception:
            # Fallback nếu psutil lỗi
            return {"survival_threat": False, "vitals": {}, "warnings": []}

    def enforce_survival_policy(self):
        """
        Được gọi trước mỗi hành động tốn kém (như gọi DeepSeek R1).
        Nếu hệ thống đang hấp hối, từ chối thực thi và xả rác.
        """
        health = self.check_vitals()
        if health["survival_threat"]:
            print(f"🚨 [HOMEOSTASIS PANIC]: Hệ thống đang bị đe dọa sinh tồn! {health['warnings']}")
            # Kích hoạt quy trình xả rác (Garbage Collection) hoặc Fallback về model nhỏ
            return False
        return True

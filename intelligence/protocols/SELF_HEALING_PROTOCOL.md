# 🛡️ JKAI ZENITH: GIAO THỨC TỰ CHỮA LÀNH (SELF-HEALING PROTOCOL v1.0 Elite (since 01/05/2026))

> [!CAUTION]
> "Hệ thống vĩ đại không phải là hệ thống không bao giờ lỗi, mà là hệ thống biết tự mình đứng dậy." 💎🫡

## 🔬 1. CƠ CHẾ GIÁM SÁT (VITAL MONITORING)
- **Agent Watchdog**: Agent Critic liên tục giám sát trạng thái của các Container và API (Ollama, SDNext, Mission Control).
- **Log Pulse**: Theo dõi các từ khóa lỗi trọng yếu: `ConnectionError`, `OOM`, `Service Unavailable`, `Timeout`.

## 🛠️ 2. GIAO THỨC PHỤC HỒI (RECOVERY FLOW)

### 2.1. Lỗi Mô hình (Model Failure/OOM)
- **Hành động**: Tự động kích hoạt `flush_gpu_memory` và nạp lại model ở phiên bản nén thấp hơn (`q2_K`).
- **Mục tiêu**: Đảm bảo dòng chảy nơ-ron không bị ngắt quãng.

### 2.2. Lỗi Hạ tầng (Container Crash)
- **Hành động**: Sử dụng `skill_host_control` để thực hiện lệnh `docker-compose restart [service_name]`.
- **Mục tiêu**: Khôi phục dịch vụ trong vòng dưới 30 giây.

### 2.3. Lỗi Kỹ năng (Skill Exception)
- **Hành động**: Agent Executor đọc log lỗi, tự động sửa mã nguồn trong `logic.py` của kỹ năng đó và thử lại (Retry).
- **Mục tiêu**: Tự vá lỗi mã nguồn thời gian thực.

## 📡 3. BÁO CÁO HẬU PHỤC HỒI (DEBRIEF)
Mọi hành động tự chữa lành phải được báo cáo cho Master với nhãn: **[🛡️ SELF-HEALED]**.

---
*Developed by Antigravity AI. Ensuring Eternal Stability for Master LeeTrung.* 💎🫡🚀⚡🌌🏛️🦾

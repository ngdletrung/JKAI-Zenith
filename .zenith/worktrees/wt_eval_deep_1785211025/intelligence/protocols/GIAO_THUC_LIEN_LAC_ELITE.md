# 📡 GIAO THỨC LIÊN LẠC NHẤT THỂ v42.0 (ZENITH CENTRALIZED GATEWAY)

Văn kiện này quy định luồng dữ liệu và giao tiếp kỹ thuật nhất thể hóa trong hệ sinh thái JKAI Zenith. 
Tôn chỉ: **NHẤT THỂ - THỐNG NHẤT - THẤU THỊ**.

---

### 🏛️ 1. MASTER ➡️ SIÊU GATEWAY (AI-CONTROL-PLANE)
- **Điểm tiếp nhận**: Dashboard (Web) và Telegram phải gửi yêu cầu qua `/api/submit_task` của Control Plane.
- **Yêu cầu**: Gateway phải ghi nhật ký tiếp nhận (`📥 [GATEWAY]`) trước khi đẩy vào Hàng đợi Nhiệm vụ (Redis).

### 🧠 2. SIÊU GATEWAY ➡️ NÃO BỘ TRUNG ƯƠNG (AI-BRAIN)
- **Luồng tư duy**: Chuyển tiếp Tokens thông qua `/api/stream` để đảm bảo Master có thể "thấu thị" luồng tư duy thời gian thực.
- **Quy tắc**: Não bộ phải sử dụng `engine.get_role_config` để đảm bảo phân bổ mô hình đúng theo `rule_hardware.md`.

### 🦾 3. NÃO BỘ ➡️ BAN THỰC THI (AI-EXECUTOR)
- **Cơ chế**: Thông qua `ai_task_queue` trong Redis.
- **Yêu cầu**: Ban Thực thi phải báo cáo trạng thái từng bước (`Step-by-Step Reporting`) về Gateway để đồng bộ UI.

### 👁️ 4. ĐẶC VỤ 🛰️ ➡️ GATEWAY THỊ GIÁC
- **Luồng Vision**: Mọi yêu cầu phân tích ảnh (từ Telegram/Browser) phải gửi về `/api/vision` của Control Plane.
- **Điều phối**: Gateway chuyển tiếp dữ liệu Base64 tới `ai-browser` để xử lý Moondream Cục bộ.

### 📡 5. NHẤT THỂ HÓA NHẬT KÝ (LOG RELAY)
- **Giao thức**: Mọi dịch vụ KHÔNG được ghi trực tiếp vào Redis mà phải gọi `/api/log` của Control Plane.
- **Mục đích**: Đảm bảo định dạng log luôn chuyên nghiệp (Sentence Case) và đồng bộ trên mọi kênh (Web/Tele).

---

### ⚠️ NGUYÊN TẮC VẬN HÀNH (OPERATIONAL RULES)
1. **CENTRALIZED AUTHORITY**: Không dịch vụ nào được tự ý "vượt cấp" gọi trực tiếp Ollama nếu đã có phương thức qua Engine/Gateway.
2. **DATA PARITY**: Mọi phản hồi từ đặc vụ phải được đồng bộ 1:1 giữa Dashboard và Telegram thông qua Relay Log.
3. **SOVEREIGN DISCIPLINE**: Sử dụng Task ID làm sợi chỉ đỏ xuyên suốt mọi luồng giao tiếp.

---
*VÌ MỘT ĐẾ CHẾ NHẤT THỂ VÀ TRƯỜNG TỒN!* 💎🫡🏛️🚀🌌

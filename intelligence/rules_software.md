# 🛡️ JKAI ZENITH: SOFTWARE & API RULES (rules_software.md)

Tài liệu này quy định các biến môi trường và chìa khóa API cần thiết để kích hoạt sức mạnh của **Neural Link Aggregator**.

---

## 🔑 1. DANH MỤC CHÌA KHÓA THẦN KINH (API KEYS)

Master chỉ cần dán trực tiếp API Key và Địa chỉ cổng (nếu có) vào bảng bên dưới. Hệ thống sẽ tự động "Thấu thị" và kích hoạt liên kết.

| Nhà cung cấp | Tên biến | Base URL (Endpoint) | Trạng thái (DÁN KEY TẠI ĐÂY) |
| :--- | :--- | :--- | :--- |
| **Google AI** | `GEMINI_API_KEY` | `https://generativelanguage.googleapis.com/v1beta/openai/` | ✅ **ACTIVE** (`AIzaSyBdEc04jL3BAWhPMuGa2zCqLSlye4q-wjs`) |
| **OpenAI** | `OPENAI_API_KEY` | `https://api.openai.com/v1` | ✅ **ACTIVE** (`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`) |
| **DeepSeek** | `DEEPSEEK_API_KEY` | `https://api.deepseek.com` | ✅ **ACTIVE** (`sk-de98425ac132423b8e06e8d7479ee2f6`) |
| **Anthropic** | `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1` | ✅ **ACTIVE** (`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`) |


---

## ⚙️ 2. QUY TẮC VẬN HÀNH (OPERATIONAL RULES)

1. **Giao thức Trích xuất Động (Dynamic Ingestion)**: Hệ thống tự động phân tích và nạp trực tiếp các API Key từ bảng trên thời gian thực. Tổng Giám Đốc không cần cấu hình thủ công trong file `.env` hay restart container.
2. **Cơ chế Định tuyến Ngữ cảnh Lớn (Multicloud Context Routing)**:
   * **Ngưỡng quy định**: **8,000 tokens** (~32,000 ký tự).
   * **Quy tắc**:
     * **Ngữ cảnh > 8,000 tokens**: Tự động chuyển tiếp luồng hội thoại lên Đám mây qua API của **Gemini 3.5 Flash** (sử dụng `GEMINI_API_KEY` ở trên) để tránh lỗi tràn bộ nhớ VRAM cục bộ và xử lý chính xác tài liệu dung lượng lớn.
     * **Ngữ cảnh <= 8,000 tokens**: Thực thi hoàn toàn tại máy local thông qua Ollama (ưu tiên mô hình reasoning `deepseek-r1:latest` trên GPU AMD RX 6600) nhằm đảm bảo tốc độ phản hồi nhanh nhất và bảo mật thông tin tuyệt đối.
3. **Thứ tự ưu tiên đám mây (Cloud Priority Registry)**:
   * Ưu tiên 1: **Google Gemini** (Tối ưu nhất cho xử lý file dài và tài liệu phức tạp).
   * Ưu tiên 2: **DeepSeek Cloud** (Tối ưu cho lập luận toán học/logic lập trình chuyên sâu).
   * Ưu tiên 3: **OpenAI GPT-4o / Anthropic Claude 3.5 Sonnet** (Cân bằng tốt các tác vụ sáng tạo và thiết kế hệ thống).
4. **Giao thức Bảo vệ GPU (Neural GPU Protection)**: Các cuộc gọi cục bộ (local calls) bắt buộc phải tuân thủ cơ chế khóa VRAM độc quyền (`lock:gpu_vram`) để bảo toàn tài nguyên phần cứng local.

---

## 🛠️ 3. HƯỚNG DẪN KÍCH HOẠT & KIỂM TRA
1. **Dán API Key**: Nhập đúng API Key của nhà cung cấp tương ứng vào cột cuối cùng của bảng mục 1.
2. **Đồng bộ hóa**: Lưu tệp tin này. Bộ xử lý thông minh sẽ lập tức cập nhật thông số nạp trong RAM.
3. **Kiểm tra trạng thái**: Tổng Giám Đốc có thể kiểm tra trực tiếp qua API hoặc gõ lệnh để hệ thống phản hồi xác nhận trạng thái kích hoạt của từng cổng liên kết.

---
*BẢO MẬT - TỐI ƯU - VÔ CỰC - ĐẾ CHẾ JKAI ZENITH* 💎🫡🦾🚀🌌

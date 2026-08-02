# 🏛️ ZENITH SYSTEM ARCHITECTURE: THE CORE KNOWLEDGE 📂

Tài liệu này tổng hợp các nguyên tắc kỹ thuật và cấu trúc hạ tầng tối cao của Tập đoàn JKAI Zenith, được chưng cất từ các thế hệ tiền nhiệm.

## 📐 1. CẤU TRÚC HẠ TẦNG (INFRASTRUCTURE)
- **Docker Orchestration**: Hệ thống vận hành dưới dạng các dịch vụ Docker tách biệt (`ai-brain`, `ai-executor`, `mission-control`, `n8n`).
- **Redis Pub/Sub**: Huyết mạch thông tin của toàn hệ thống. Mọi nhật ký (logs) và chỉ thị đều được truyền tải qua Redis Channel `monitor:log_channel`.
- **Backend Stack**: Python (FastAPI) cho các dịch vụ AI, đảm bảo hiệu suất và khả năng mở rộng.

## ⚡ 2. GIAO THỨC TƯ DUY ELITE (NEURAL LOGIC)
- **4 Nguyên tắc Karpathy**: 
    1. Think Before Coding.
    2. Simplicity First.
    3. Surgical Changes.
    4. Goal-Driven Execution.
- **Internal Monologue**: Mọi Đặc vụ phải thực hiện bước độc thoại nội tâm để thẩm định ý đồ của Master trước khi thực thi.

## 🖥️ 3. TIÊU CHUẨN THẨM MỸ ZENITH (AESTHETIC STANDARDS)
- **UI/UX**: Sử dụng tông màu tối (`#060910`), hiệu ứng kính mờ (Backdrop Blur), và các dải màu Gradient Sky-to-Indigo.
- **Typography**: Ưu tiên các font chữ không chân (Inter, Sans-serif) với tracking rộng cho các nhãn (Labels).
- **Interactive**: Mọi hành động phải có phản hồi thị giác (Pulse, Motion, Glow).

## 🚀 4. TỐI ƯU HÓA PHẦN CỨNG (AMD ROCm)
- **GPU**: AMD Radeon RX 6600 (8GB VRAM).
- **VRAM Management**: Ưu tiên nạp các Model quan trọng nhất lên GPU, các tác vụ hội thoại xã giao giữ ở RAM/CPU.
- **Context Limit**: Luôn duy trì giới hạn ngữ cảnh (Context Window) ở mức 4096 để tránh tràn VRAM.

---
*GHI CHÚ: Tài liệu này là "Trí năng vĩnh cửu" của JKAI. Đặc vụ PHẢI đọc file này trước khi đưa ra bất kỳ quyết định kiến trúc nào.* 💎🫡🦾🚀🌌

# 🏛️ JKAI Zenith: QUY TRÌNH VẬN HÀNH DÒNG CHẢY THÔNG TIN (v12.6)

Tài liệu này định nghĩa luồng di chuyển của thông tin (Data Flow) trong hệ thống Tập đoàn Zenith để đảm bảo Tốc độ tối ưu và Kỷ luật tuyệt đối.

---

## 🛰️ GIAI ĐOẠN 1: TIẾP NHẬN & PHÂN LOẠI (INGESTION & ROUTING)

1. **Nguồn lệnh (Entry Points)**: Master gửi yêu cầu qua Dashboard hoặc Telegram.
2. **Cổng kiểm soát (Control Plane)**: 
   - Tiếp nhận mục tiêu (Goal) và Task ID.
   - Ghi nhật ký chuẩn Corporate (`BAN KỸ THUẬT`).
3. **Phân luồng Chiến thuật (Strategic Routing)**:
   - **Quy trình Xử lý Nhanh (Fast-Track)**: Dành cho lệnh < 50 ký tự hoặc hội thoại đơn giản. -> Chuyển thẳng tới **Phòng Tiếp nhận & Điều phối**.
   - **Quy trình Chuyên sâu (Deep-Track)**: Dành cho yêu cầu phức tạp. -> Chuyển tới **Phòng Kế hoạch** để phân tích bằng AI.

## 🧠 GIAI ĐOẠN 2: THẨM ĐỊNH & KIẾN TẠO (ANALYSIS & CREATION)

1. **Truy lục Tri thức (Knowledge Retrieval)**:
   - Đặc vụ tiếp nhận (**Phòng Tiếp nhận / Phòng Kế hoạch**) truy cập **Đại thư viện (Vault)** và **Bản đồ Kỹ năng (MAP_SKILLS.md)**.
   - Cơ chế **RAM Cache** đảm bảo việc đọc tri thức diễn ra trong mili giây.
2. **Triệu tập Chuyên gia (Agent Activation)**:
   - Engine truy xuất cấu hình từ `rule_hardware.md` (đã được Cache vào Redis).
   - Điều động Model phù hợp (CPU cho Phòng Tiếp nhận, GPU cho Phòng Cố vấn/Thực thi).

## ⚡ GIAI ĐOẠN 3: THỰC THI & KIỂM SOÁT (EXECUTION & CRITIC)

1. **Hội thoại/Thực thi**:
   - Đặc vụ xử lý yêu cầu và gọi các Tools (Skills) nếu cần thiết.
   - **Thought Extraction**: Mọi suy nghĩ của AI được bóc tách và gửi lên Dashboard (`THOUGHT`).
2. **Thẩm định (Critic)** (Chỉ có trong Deep-Track):
   - **Ban Kiểm soát** rà soát kế hoạch trước khi thực hiện hành động nhạy cảm.
   - Yêu cầu **Master Approval (OK JKAI DO)** nếu có rủi ro cao.

## 📊 GIAI ĐOẠN 4: TỔNG KẾT & PHẢN HỒI (REPORTING & FEEDBACK)

1. **Tổng hợp kết quả (Summarization)**:
   - Kết quả thực thi được chuyển tới **Đặc vụ Tổng hợp** để biên soạn báo cáo súc tích.
2. **Phản hồi Master**:
   - Thông tin được đóng gói với Tag chuẩn (`CHAT_INTEL` hoặc `MISSION_RESULT`).
   - Trả về Dashboard/Telegram và lưu trạng thái vào Redis.
3. **Đúc rút Kinh nghiệm (Distillation)**:
   - Sau khi hoàn thành, Đặc vụ **Experience Distiller** tự động phân tích và lưu kinh nghiệm vào bộ nhớ dài hạn.

---
## 🚀 CÁC ĐIỂM TỐI ƯU TỐC ĐỘ (SPEED OPTIMIZATION POINTS)

- **[P1] Singleton Engine**: Không đọc file config lặp lại.
- **[P2] Combined Logic**: Sáp nhập CTO Scout vào Lễ tân để giảm 1 lượt gọi AI.
- **[P3] Model Persistence**: Giữ Model trong VRAM (`keep_alive: -1`) để tránh thời gian Load.
- **[P4] Redis Sync**: Đồng bộ trạng thái qua RAM thay vì Disk.
- **[P5] Parallel Workflow**: Thực thi song song các bước độc lập qua Giao thức Đa luồng (Multi-Agent Sync).

---
*Quy trình Zenith. Antigravity-grade.* 💎🫡🏛️🚀🌌

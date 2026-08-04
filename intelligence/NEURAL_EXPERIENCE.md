<!-- 
[ZENITH FILE DIRECTIVE]
- File: NEURAL_EXPERIENCE.md
- Role: Zenith System Architecture & Evolutionary Memory Log.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v21.0
[WORKING PRINCIPLES]:
1. [HEADER-FIRST]: Inspect header prior to file execution.
2. [SDS-COMPLIANCE]: Follow SDS protocols strictly.
3. [NO-EMOJI]: Use clean professional technical formatting.
-->

# JKAI ZENITH: NHẬT KÝ TIẾN HÓA VÀ BẢN ĐỒ TỐI ƯU HỆ THỐNG

Tài liệu này ghi nhận nhật ký tối ưu hóa bộ nhớ, bài học vận hành hạ tầng VRAM/RAM local, và các giao thức kiến trúc của hệ điều hành JKAI OS.

---

## 1. NGUYÊN TẮC QUẢN TRỊ HỆ THỐNG (SYSTEM GOVERNANCE PROTOCOLS)

Bộ nguyên tắc định hướng khả năng tự phục hồi và phản xạ cho luồng xử lý của JKAI:

| Nguyên Tắc Kỹ Thuật | Vấn Đề Khắc Phục | Giao Thức Thực Thi |
| :--- | :--- | :--- |
| **Xử Lý Ngữ Cảnh Dư Thừa** | Lặp câu thoại khi chu kỳ suy luận kéo dài. | Thanh lọc nhật ký cũ khỏi prompt khi gặp lỗi lặp; chỉ trích xuất Mục tiêu, Stack Trace và Phạm vi mã nguồn cụ thể. |
| **Thẩm Định Đa Tác Tử** | Lệch pha hoặc thi công phiến diện khi phụ thuộc vào 1 model. | Khi thay đổi > 3 tệp tin: Phân tách vai trò PLANNER, EXECUTOR và CRITIC độc lập để kiểm duyệt chéo logic. |
| **An Toàn Mã Nguồn** | Nguy cơ ảnh hưởng file hệ thống khi can thiệp code. | Thực hiện sửa code qua worktree cách ly `.zenith/worktrees/`. Hợp nhất (merge) chỉ diễn ra khi kiểm thử cú pháp đạt exit code 0. |
| **Điều Hòa VRAM/RAM** | Nghẽn bộ nhớ VRAM 8GB trên AMD RX 6600. | Khi VRAM vượt ngưỡng an toàn (7.8GB), bộ điều phối `HardwareScheduler` khống chế VRAM và chuyển phần tải còn lại sang 128GB RAM. |
| **Chẩn Đoạn Root Cause** | Sửa chữa triệu chứng tạm bợ (Symptom Patching). | Chẩn đoán tận gốc truyền nhận kiểu dữ liệu (Schema Origin), nghiêm cấm bọc try/except rỗng để che giấu lỗi. |

---

## 2. CHỈ ĐỊNH VẬN HÀNH THỜI GIAN THỰC (RUNTIME DIRECTIVES)

- **Tối Ưu Bối Cảnh:** Chỉ nạp các Kỹ năng (Skills) thực sự cần thiết qua `plugin_manager.match_and_load_skills(...)` để giảm tải token dư thừa.
- **Tự Phục Hồi:** Khi xảy ra sự cố trong tiến trình thực thi, nhật ký được tự động ghi nhận vào `EngramLearner` để rút kinh nghiệm cho các phiên sau.

---

## 3. THÔNG SỐ HẠ TẦNG VẬN HÀNH (INFRASTRUCTURE PROFILE)

- **Trạng thái thực thi:** Tự trị & Kháng lỗi (Autonomous Resilience).
- **Cấu hình hạ tầng:** Intel Xeon E5-2699 v4 (22C/44T) | AMD Radeon RX 6600 (8GB VRAM) | 128GB RAM System Memory.
- **Tiêu chuẩn vận hành:** Chính xác, gọn gàng, khách quan, tối ưu tài nguyên tối đa cho hệ thống.

---

## 4. NHẬT KÝ TIẾN HÓA HỆ THỐNG (SYSTEM EVOLUTION LOG)

| Phân Khu Cải Tiến | Sự Cố / Yêu Cầu Khởi Nguồn | Giao Thức Khắc Phục Tận Gốc |
| :--- | :--- | :--- |
| **Giao Diện Mission Control** | Header bị thừa nút Thanh lệnh & nút Đường truyền lặp lại. | Tối giản Header, giữ hotkey `Ctrl + K`, hợp nhất `isConnected` vào `ResourceHUD` (`Status: OPTIMAL`, `Uplink: ACTIVE/SEVERED`). |
| **Bảo Vệ Khỏi Rác Tabs** | Tabs hiển thị lặp card kế hoạch & stub text rỗng. | Khử trùng lặp ID Proposal qua Map trong `zenithStore.ts` và mở rộng `ArtifactGallery` lọc bỏ stub text rỗng trên tất cả các Tab. |
| **Bảo Vệ Telegram Bot** | Long-polling bão lỗi `ReadTimeoutError` làm sụp container. | Ép `READ_TIMEOUT = 90s` & `CONNECT_TIMEOUT = 30s` (lớn hơn `polling_timeout=20s`), đóng gói vòng lặp retry kiên trì. |
| **Quy Định Code vs Tool** | Mô hình `qwen2.5-coder` bị nhầm định dạng sinh JSON Tool Call giả khi được nhờ viết code. | Bổ sung `Tool vs Response Formatting Rules` trong `MasterPromptArchitect`: Ép xuất Markdown code (` ```python `) trực tiếp khi yêu cầu viết code. |
| **Semantic Cache Intercept** | Đọc sai khóa `"response"` trả về `{}` rỗng và ngộ độc bộ đệm cache. | Khắc phục đọc khóa `"payload"`, bổ sung `CACHE-POISONING-GUARD` từ chối lưu và bỏ qua (bypass) cache rỗng `{}`. |
| **Phần Cứng MoE Split VRAM** | Mô hình 30B MoE (17GB) bị tính nhầm thành 17GB VRAM dẫn đến bị từ chối nạp nhầm. | Thiết lập `[MOE-SPLIT-CAP]` khống chế VRAM MoE ở mức 6.5GB trên RX 6600 (32 GPU layers), trả 10.5GB còn lại về 128GB RAM. |
| **Định Tuyến Chế Độ FAST/DEEP** | Chế độ FAST bị nhảy sang cụm model DEEP do cấu hình trùng lặp role. | Chuẩn hóa FAST = 1 model (`Qwen3-30B`), DEEP = 3 models độc lập (`qwen3.5:4b`, `qwen2.5-coder:3b`, `gemma-4`). |
| **Ghim Bộ Nhớ Thường Trực** | Mô hình bị giải phóng sau 30 phút gây trễ nạp lại. | Cập nhật `ModeSwitcher` ghim mô hình của chế độ đang active với `keep_alive = -1` cho tới khi có lệnh đổi chế độ. |
| **Nạp Mô Hình Thông Minh** | Mô hình 30B bị quá tải timeout cố định 60s khi nạp từ NVMe vào RAM/VRAM. | Áp dụng **Smart Adaptive Timeout** $\text{Timeout} = \max(45\text{s}, \min(300\text{s}, 30\text{s} + \text{Model\_GB} \times 10))$ kết hợp `/api/ps` Resident Recheck. |

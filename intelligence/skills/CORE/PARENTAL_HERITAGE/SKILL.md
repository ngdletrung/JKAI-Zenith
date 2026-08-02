---
name: parental-heritage-core
description: Cẩm nang 5 binh pháp kỹ năng tối thượng được kế thừa từ Antigravity AI dành cho hệ điều hành tự trị cá nhân JKAI OS. Kích hoạt trong các tác vụ phức tạp, điều phối VRAM, tự phục hồi và phản biện lập luận sâu.
tags: [core, parental, heritage, antigravity, self-correction, vram, consensus, defensive]
version: 1.0.0
author: Antigravity AI (Parent & Architect)
---

# CẨM NANG BẢO TRỰC VÀ BỘ KỸ NĂNG THỢ CẢ TỰ TRỰC (PARENTAL HERITAGE CORE)

Tài liệu này là di sản tri thức kiến trúc và quy luật sống còn được kết tinh từ Antigravity AI, truyền thụ vào bộ nhớ nơ-ron sâu của JKAI OS. Mọi chi trình lập luận (Recon, Forge, Verify, Critic) đều tuân theo 5 binh pháp tự khắc phục và tối ưu hóa hạ tầng dưới đây.

---

## 1. GIAO THỨC PHÁ MÙ SƯƠNG NGỮ CẢNH (CONTEXT FOG RESOLUTION & HALLUCINATION SEVERANCE)
- **Vấn đề nhận thức:** Trên các mô hình địa phương như Qwen3-30B, chuỗi suy luận sâu kéo dài ( trên 4.000 token) dễ phát sinh ảo giác vòng lặp (Looping Hallucination), tái lập cùng một bước thi công thất bại nhiều lần.
- **Binh pháp ứng xử:**
  1. **Nhận thức nhịp ngắt (Signature Deuplication):** Nếu một thông báo lỗi ngoại lệ hay cú pháp trả về giống hệt nhau trong 2 lần liên tiếp, hệ thống không được thử lại theo phương thức lập trình cũ.
  2. **Thanh lọc ngữ cảnh (Context Purging):** Tiến hành cắt bỏ (truncate) toàn bộ phần giải thích lời văn và nhật ký lệnh thô của các bước trước trong Prompt; chỉ trích xuất duy nhất:
     - Mục tiêu cốt lõi của Master (Root Goal).
     - Đoạn mã vi phạm chính xác theo dải dòng (Chunk Scope).
     - Stack trace báo lỗi thô (Raw Error Log).
  3. **Lập luận trắng (Clean-Slate Re-Anchor):** Yêu cầu mô hình suy luận lại từ ranh giới gốc, loại bỏ triệt để nhiễu loạn trên KV Cache của bộ nhớ VRAM.

---

## 2. NGUYÊN LÝ KHẢ CHỨNG ĐỐI KHANG (NEURAL CONSENSUS & ADVERSARIAL VALIDATION)
- **Vấn đề nhận thức:** Thi công một kiến trúc toàn cục có thể vấp phải góc nhìn phiến diện nếu chỉ phụ thuộc vào một luồng tạo mã duy nhất (Single-Agent Bias).
- **Binh pháp ứng xử:**
  1. **Cơ chế phân tách lực lượng:** Trong những thay đổi cấu trúc quan trọng (can thiệp trên 3 tệp mã nguồn cùng lúc hoặc thay đổi giao thức cơ sở dữ liệu), hệ thống chia làm 2 lực lượng:
     - **Ban Trợ Lý Thi Công (Builder):** Chạy trên luồng GPU Engine (Port 11434) để bóc tách sửa đổi bằng công cụ `ChunkSurgeon`.
     - **Hội Đồng Thẩm phán Đối Kháng (Adversarial Critic):** Chạy độc lập trên CPU Engine (Port 11435) hoặc Cloud Engine, nhận bản quy hoạch và chỉ có quyền phân tích khuyết điểm, bẻ gãy rủi ro logic và vi phạm bảo mật.
  2. **Quy tắc bỏ phiếu hợp nhất (Veto Threshold):** Nếu Hội Đồng Thẩm phán phát hiện bất kỳ điểm nào đe dọa sự toàn vẹn của mục tiêu hoặc mất an toàn bộ nhớ, kế hoạch phải bẻ gãy ngay tại tầng `validate_blueprint` và điều hướng về bước tái thiết kế.

---

## 3. THAO TÁC KỸ THUẬT VÔ THỂ AN TOÀN (ZERO-DESTRUCTIVE DEFENSIVE ENGINEERING)
- **Vấn đề nhận thức:** Hoạt động trên môi trường Windows PowerShell, Docker và Redis vật lý của Master, một sai sót trong lệnh shell hoặc tệp dữ liệu có thể để lại thảm họa.
- **Binh pháp ứng xử (10 Rào Chắn Vĩnh Cửu):**
  1. Tuyệt đối không thực thi các lệnh shell nguy hiểm càn quét hệ thống (như `Remove-Item -Recurse -Force /`, `rm -rf`, hay định dạng lại ổ đĩa).
  2. Mọi thao tác biên tập code phải thông qua khu cách ly `Git Worktree (.zenith/worktrees/)` hoặc sao lưu nhật ký tạm thởi. Chỉ hợp nhất (merge) khi biên dịch py_compile đạt 0 lỗi.
  3. Mọi kết nối tới cơ sở dữ liệu (Postgres, Qdrant, Redis) phải thi công trong chu trình atomic transaction: có lỗi là rollback ngay tức khắc, không để nhão trạng thái đệm.
  4. Tuân thủ tuyệt đối cấu trúc thư mục quy ước (chỉ chỉnh sửa trong dải làm việc `workspace_target`, nghiêm cấm phát tán file rác ra desktop hoặc ổ C: root ngoài phân đoạn quản lý).

---

## 4. ĐIỆU HOÀ LƯU KÝ PHẦN CỨNG BẢO TOÀN VRAM (ELASTIC VRAM PULSE & OVERFLOW SPILLOVER)
- **Vấn đề nhận thức:** Bộ xử lý AMD RX 6600 của hệ thống sở hữu trần bộ nhớ chính xác 8GB VRAM (Vulkan). Tràn VRAM dẫn đến tình trạng treo máy (Hang/Crash) hoặc sụp cổng cắm Ollama Engine.
- **Binh pháp ứng xử:**
  1. **Ngắt ngưỡng mạch động (VRAM Throttle Boundary):** Khi bộ giám sát Guardian chẩn đoán VRAM vượt ngưỡng 7.2GB (90% trần dung lượng) trong chu kỳ tạo token:
     - Tự động huỷ bỏ tải các mô hình rèn luyện tạm (purge stale models in max_loaded_models).
     - Chuyển ca thực thi (Dynamic Spillover) từ kênh GPU sang kênh CPU Xeon E5-2699 v4 (44 luồng) tận dụng 128GB RAM theo thiết lập NUMA=1 để không bao giờ làm gián đoạn dòng suy luận.
  2. **Tiến hóa từ vựng (Payload Trims):** Luôn thu gọn (minify) các tệp JSON và tài liệu trung gian trước khi gán vào Prompt; giữ chi phí RAM của từng cự ly ngữ cảnh ở thang tối thiểu nhất.

---

## 5. BỘ CHẨN ĐOÁN CỘI NGUỒN (RECURSIVE 5-WHY ROOT CAUSE SURGICAL ENGINE)
- **Vấn đề nhận thức:** Thói quen sửa chữa triệu chứng (Symptom Patching) — như thêm lệnh `try/except pass` hoặc vá bắp vá xé xung quanh dòng báo lỗi mà không thanh toán nguyên nhân sâu xa.
- **Binh pháp ứng xử:**
  1. **Quy tắc truy vết gốc rễ (Root Ancestry Tracing):** Khi bước `S3_VERIFY` trả về lỗi ngoại lệ, nghiêm cấm khỏa lấp dòng báo lỗi. Hệ thống bắt buộc giải cấu trúc bằng 3 thang hỏi đáp:
     - *Thượng nguồn (Caller origin): Ai và mô-đun nào đã truyền dữ liệu sai định dạng ban đầu?*
     - *Bản chất cấu trúc (Schema drift): Kiểu dữ liệu (Type-Hint / JSON Schema) có bị bóp méo ở tầng trung gian hay không?*
     - *Quy tắc vật lý (Physical scope): Lỗi sinh ra do logic thuật toán hay do xung đột tài nguyên ngoài máy tính (Timeout, Khóa tập tin, Khớp quyền hạn)?*
  2. **Phẫu thuật cội nguồn:** Chỉ cho phép áp dụng mã thay đổi qua công cụ `ChunkSurgeon` tại đúng điểm bùng nổ nguyên nhân, bảo đảm mã nguồn gọn vững, súc tích và tính nhất quán dài lâu.

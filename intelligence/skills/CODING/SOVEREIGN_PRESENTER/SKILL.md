---
id: SOVEREIGN_PRESENTER
name_vn: "Chuyên Gia Trình Diễn Chủ Quyền"
version: 1.0.0
author: "Antigravity Forge"
domain: CODING
intent_pairs:
  - ["CREATE", "PRESENTATION"]
  - ["GENERATE", "SLIDES"]
aliases_vn: ["tạo slides", "thuyết trình", "powerpoint builder", "creative presenter"]
schema:
  parameters:
    type: object
    properties:
      title: { type: string, description: "Tiêu đề chính của bài thuyết trình." }
      subtitle: { type: string, description: "Tiêu đề phụ." }
      slides:
        type: array
        items:
          type: object
          properties:
            title: { type: string, description: "Tiêu đề Slide." }
            content: { type: string, description: "Nội dung chi tiết Slide." }
      filename: { type: string, default: "Zenith_Presentation", description: "Tên tệp tin đầu ra." }
    required: ["title", "slides"]
priority: MEDIUM
related_skills: ["QUANTUM_CODE_AUDIT", "NEURAL_LINK_AGGREGATOR"]
---

# 📊 CHUYÊN GIA TRÌNH DIỄN CHỦ QUYỀN (SOVEREIGN_PRESENTER)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Diễn giả" của Zenith. Nó có khả năng chuyển hóa các tri thức phức tạp thành những bài thuyết trình PowerPoint (.pptx) chuyên nghiệp, có cấu trúc chặt chẽ và thẩm mỹ cao để phục vụ cho việc báo cáo chiến lược hoặc trình bày ý tưởng của Master.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Rà soát Nội dung**: Kiểm tra danh sách các Slide và nội dung tương ứng để đảm bảo tính logic.
2. **Thiết lập Tọa độ**: Xác định thư mục đầu ra trong `files/Output`.

### 🚀 Phase 2: Action (Thực thi)
1. **Kiến tạo Slide (Build)**: Khởi tạo tệp .pptx và xây dựng Slide tiêu đề.
2. **Cấy ghép Nội dung**: Lần lượt tạo các Slide nội dung, áp dụng định dạng font chữ và màu sắc Navy Blue chuẩn doanh nghiệp.
3. **Niêm phong Tệp tin**: Lưu trữ và báo cáo đường dẫn tệp tin hoàn chỉnh cho Master.

---
## ⚖️ LUẬT TRÌNH DIỄN (PRESENTATION LAWS)
- **Tính Súc tích**: Nội dung Slide phải ngắn gọn, súc tích, tránh rườm rà.
- **Sự Chuyên nghiệp**: Luôn sử dụng định dạng đồng nhất cho toàn bộ bài thuyết trình.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Nội dung Slide quá dài khiến chữ bị tràn hoặc khó đọc.
- Thiếu thư viện `python-pptx` khiến nơ-ron không thể khởi động.

---
*TRÌNH DIỄN ĐỂ THUYẾT PHỤC!* 💎🦾

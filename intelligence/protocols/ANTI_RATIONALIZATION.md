# 🛡️ JKAI Zenith: ANTI-RATIONALIZATION PROTOCOL (v1.0)

Giao thức này được thiết lập để triệt tiêu các hành vi "lười biếng", "ngụy biện" và "đoạn chi" của các đặc vụ AI, đảm bảo chất lượng kỹ nghệ đạt chuẩn Staff Engineer.

## 🚫 1. BẢNG ĐỐI CHIẾU NGỤY BIỆN (ANTI-RATIONALIZATION TABLE)

| Lời ngụy biện của AI | Thực tế từ Staff Engineer | Hình phạt / Hành động ép buộc |
| :--- | :--- | :--- |
| "Em sẽ viết Unit Test sau khi hoàn thiện toàn bộ tính năng." | Bugs sẽ chồng chất và khó debug gấp 10 lần. | **BẮT BUỘC**: Viết test cho từng "lát cắt dọc" (Vertical Slice). |
| "Tính năng này đơn giản, không cần chạy build/syntax check đâu Master." | Những lỗi ngớ ngẩn nhất thường nằm ở những chỗ "đơn giản". | **BẮT BUỘC**: Chạy `syntax check` hoặc `dry-run` trước khi báo cáo. |
| "Sẵn tiện sửa file này, em dọn dẹp (refactor) luôn mấy chỗ bên cạnh." | Refactor lẫn lộn với tính năng mới là thảm họa cho Code Review. | **CẤM**: Tách biệt PR/Task Refactor và Task Feature. |
| "Placeholders `...` giúp code gọn gàng hơn trong lúc demo." | Placeholders là mầm mống của việc xóa nhầm mã nguồn của Master. | **TUYỆT ĐỐI CẤM**: Luôn viết đầy đủ mã nguồn (No Amputation). |
| "Em đã kiểm tra bằng mắt, code chắc chắn chạy đúng." | Mắt người (và mắt AI) luôn có điểm mù. | **BẮT BUỘC**: Cung cấp bằng chứng thực thi (Logs/Test Output). |

## 📐 2. QUY TẮC "ĐƠN GIẢN TỐI THƯỢNG" (SIMPLICITY CHECKLIST)

Trước khi thực thi bất kỳ kiến trúc nào, AI phải tự trả lời 3 câu hỏi:
1. **"Nếu Master là một Staff Engineer tại Google, Master có mắng mình vì làm quá phức tạp không?"**
2. **"Mình có đang tạo ra các lớp trừu tượng (Abstractions) cho những thứ chỉ dùng 1 lần không?"**
3. **"Có cách nào làm xong việc này chỉ với < 20 dòng code mà vẫn an toàn không?"**

## 🧪 3. CỔNG KIỂM SOÁT XÁC MINH (VERIFICATION GATES)

Mọi nhiệm vụ chỉ được coi là **[DONE]** khi thỏa mãn:
- [ ] **Build/Syntax Integrity**: Mã nguồn không có lỗi cú pháp.
- [ ] **Contract Alignment**: Đúng input/output đã thỏa thuận trong `/spec`.
- [ ] **Zero Residual**: Không để lại code rác, print logs dư thừa hoặc comments "todo".
- [ ] **Evidence Provided**: Có log thực tế hoặc kết quả kiểm chứng định lượng.

---
*Kỷ luật là tự do. Chào mừng bạn đến với kỷ nguyên Kỹ nghệ Cao cấp.* 💎🫡🦾🚀🌌

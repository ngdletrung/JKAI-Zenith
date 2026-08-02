# DOSSIER: SKILL_IMAGE_PROCESSING

## 🌌 Overview
Đây là "Xưởng Chế tác Hình ảnh" (Visual Purification Workshop) của Zenith. Kỹ năng này cung cấp khả năng xử lý hình ảnh cơ bản nhưng cực kỳ quan trọng: tự động loại bỏ nền trắng và tạo ra các tệp PNG trong suốt, giúp Master LeeTrung chuẩn bị các tài nguyên đồ họa một cách nhanh chóng và chuyên nghiệp.

## 🛠️ Detailed Features
- **Neural Background Purifier**: Thuật toán quét điểm ảnh (Pixels) thông minh để phát hiện và loại bỏ các vùng có màu trắng (Background) với ngưỡng (Threshold) tùy chỉnh.
- **Batch Processing Architecture**: Khả năng quét toàn bộ thư mục và xử lý hàng loạt hàng trăm tấm ảnh chỉ trong một phiên làm việc.
- **Standardized Output**: Luôn chuyển đổi và lưu trữ kết quả dưới định dạng PNG (RGBA) để đảm bảo chất lượng hiển thị tốt nhất trên mọi nền giao diện.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master cung cấp một bộ ảnh có nền trắng và muốn sử dụng chúng trong các thiết kế giao diện (UI) hiện đại.
2. Cần chuẩn bị các icon, logo hoặc ảnh sản phẩm để đẩy lên web mà không bị lộ viền trắng.
3. Muốn tối ưu hóa kích thước và tính thẩm mỹ cho các tài nguyên hình ảnh trong dự án.

## 💎 Strategic Value
Nâng cao "Thẩm mỹ Thị giác" (Visual Aesthetics) cho các sản phẩm của Zenith. Khả năng xử lý ảnh tự động giúp Master tiết kiệm hàng giờ làm việc với các phần mềm đồ họa chuyên nghiệp, đẩy nhanh tốc độ hoàn thiện giao diện.

## ⚠️ Edge Cases & Risks
- **Threshold Sensitivity**: Nếu ảnh có các chi tiết màu trắng quan trọng (như áo trắng, mây), chúng có thể bị biến thành trong suốt một cách không mong muốn.
- **Format Limitation**: Hiện tại tập trung chủ yếu vào việc loại bỏ nền trắng, chưa hỗ trợ các thuật toán tách nền phức tạp (AI Background Removal v3).
- **Dependency**: Yêu cầu thư viện `Pillow` phải được cài đặt trong môi trường Python của hệ thống.

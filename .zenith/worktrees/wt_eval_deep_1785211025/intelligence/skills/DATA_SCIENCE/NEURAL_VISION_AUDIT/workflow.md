# 🔄 SOP: QUY TRÌNH TÁC CHIẾN MẮT THẦN (WORKFLOW #130)

## 🌀 GIAO THỨC KHỞI ĐỘNG (PRE-FLIGHT)
1. Xác định URL mục tiêu (Mặc định Dashboard: `http://host.docker.internal:9999`).
2. Kiểm tra trạng thái Satellite `ai-browser`.

## 🛰️ GIAO THỨC THỰC THI (EXECUTION)
1. **Bước 1**: Gọi lệnh `capture_vision` với URL và Objective.
2. **Bước 2**: Đợi Satellite phản hồi trạng thái `captured`.
3. **Bước 3**: Lấy đường dẫn tệp tin ảnh từ phản hồi JSON.
4. **Bước 4**: Lưu tệp tin vào thư mục lưu trữ `/app/screenshots`.

## 🧐 GIAO THỨC KIỂM ĐỊNH (POST-FLIGHT)
1. Phân tích hình ảnh:
   - Dashboard có hiển thị màu xanh (Health OK)?
   - Các biểu đồ có bị đứt gãy?
   - Các nút bấm có bị lệch Layout?
2. **Báo cáo**: Trình diện kết quả trực quan cho Master.

---
*Elite Protocol v31.0 - The Quantum Leap.* 💎🫡🚀⚡🌌🏛️🦾

# 📋 QUY TRÌNH: CHẨN ĐOÁN HỆ THỐNG (DOCTOR SOP)

Quy trình chuẩn để AI thực hiện kiểm tra sức khỏe hệ thống Zenith.

## Bước 1: Thu thập dữ liệu (Data Collection)
- Gọi hàm `get_gpu_info()` để lấy thông số RX 6600.
- Gọi hàm `get_system_ram()` để lấy thông số RAM hệ thống.
- Gọi hàm `get_docker_status()` để liệt kê các container.
- Gọi hàm `get_loaded_models()` để kiểm tra các nơ-ron đang hoạt động.

## Bước 2: Phân tích & Bắt bệnh (Analysis)
- Đối chiếu trạng thái Container: Tìm các container không có trạng thái "Up".
- Đối chiếu VRAM: Kiểm tra xem có tình trạng "OOM" (Out of Memory) tiềm tàng không.
- Kiểm tra Error Logs: Truy xuất 50 log gần nhất từ Redis để tìm mã lỗi `ERROR`.

## Bước 3: Đề xuất giải pháp (Prescription)
- Nếu Container chết: Đề xuất lệnh `docker restart`.
- Nếu VRAM đầy: Đề xuất lệnh `purge_vram` hoặc xả các model không cần thiết.
- Nếu hệ thống ổn định: Báo cáo trạng thái **HEALTHY**.

## Bước 4: Báo cáo Master
- Trình bày báo cáo dưới dạng cấu trúc Markdown chuyên nghiệp.
- Nhấn mạnh các chỉ số Critical (nếu có).

---
*Mọi hành động đều phải được Master phê duyệt trước khi thực thi sửa lỗi.* 💎🫡

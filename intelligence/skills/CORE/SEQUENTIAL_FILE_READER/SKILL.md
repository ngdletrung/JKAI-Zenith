---
aliases_vn:
- skill sequential read
- doc file lon
- phan tich file lon
author: Antigravity Architect
domain: CORE
id: ANALYZE_LARGE_FILE
intent_pairs:
- - EXECUTE
  - ANALYZE_LARGE_FILE
name_vn: Kỹ năng đọc và phân tích tệp tin siêu lớn tuần tự
priority: HIGH
related_skills: []
version: 1.0.0
---

# Kỹ năng Phân Tích Tuần Tự Tệp Tin Siêu Lớn (ANALYZE_LARGE_FILE)

## 📖 TỔNG QUAN
Kỹ năng này cho phép AI OS tự động đọc và phân tích các tệp tin cực lớn (từ hàng chục KB đến hàng trăm MB, tương đương 1-2 triệu tokens) một cách tuần tự (Map-Reduce) mà không gây tràn cửa sổ ngữ cảnh (Context Window) hoặc quá tải VRAM GPU.

## 🛠️ CÁC HÀM CỐT LÕI
- `execute(file_path, query)`: Tự động phân mảnh động dựa trên `num_ctx` của mô hình chạy hiện tại, quét song song trên GPU và hợp nhất đệ quy kết quả cuối cùng.

## ⚖️ GIAO THỨC VẬN HÀNH
* Tự động điều chỉnh kích thước phân mảnh theo cấu hình mô hình hiện tại để đảm bảo hiệu suất tốt nhất trên GPU 8GB VRAM.

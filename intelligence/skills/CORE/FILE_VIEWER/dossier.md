# 🏛️ HỒ SƠ CHIẾN LƯỢC: FILE_VIEWER

## 🎯 Bối cảnh sử dụng (Trigger Conditions)
Sử dụng khi cần đọc nhanh nội dung của một tệp cấu hình, mã nguồn, hoặc tệp văn bản cỡ nhỏ/trung bình để phân tích lỗi cú pháp hoặc tìm hiểu kiến trúc.

## 🛠️ Hướng dẫn thực thi
1. Ưu tiên cung cấp đường dẫn tương đối (ví dụ: `services/ai-executor/executor.py`).
2. Nếu tệp tin quá dài, hãy chia nhỏ và đọc theo từng phân đoạn dòng (ví dụ: `start_line=1`, `end_line=150`) để tránh làm tràn ngữ cảnh của các mô hình LLM nhỏ.

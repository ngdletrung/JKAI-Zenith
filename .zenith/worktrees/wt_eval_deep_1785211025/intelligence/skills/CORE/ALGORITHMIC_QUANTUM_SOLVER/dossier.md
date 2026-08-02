# DOSSIER: ALGORITHMIC_QUANTUM_SOLVER

## 🌌 Overview
Đây là trung tâm tính toán logic và giải thuật của Zenith. Nó cung cấp khả năng xử lý các bài toán từ số học cơ bản đến các thuật toán phức tạp thông qua môi trường thực thi an toàn.

## 🛠️ Detailed Features
- **Math Calculator**: 
  - Thực thi các biểu thức toán học bằng thư viện `math` của Python.
  - Hỗ trợ đầy đủ các hàm lượng giác, logarit, và hằng số toán học.
  - Cơ chế `eval` được giới hạn trong phạm vi các hàm toán học an toàn, ngăn chặn thực thi lệnh hệ thống trái phép.
- **Python Logic Execution**:
  - Cho phép chạy các đoạn mã Python tùy chỉnh để giải quyết các vấn đề logic không thể thực hiện bằng biểu thức đơn lẻ.
  - Sử dụng cơ chế `subprocess` để tách biệt tiến trình, đảm bảo tính ổn định cho Kernel chính.
  - Có giới hạn `timeout=30s` để tránh treo hệ thống do vòng lặp vô tận.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Gặp các yêu cầu về tính toán chính xác mà mô hình ngôn ngữ có thể sai sót (Hallucination).
2. Cần thực hiện các thuật toán xử lý dữ liệu hàng loạt.
3. Cần chuyển đổi đơn vị hoặc giải phương trình phức tạp.

## 💎 Strategic Value
Đảm bảo tính "Xác thực" và "Chính xác" cho các quyết định của Zenith. Một đế chế không thể vận hành nếu các con số không chuẩn xác.

## ⚠️ Edge Cases & Risks
- **Resource Exhaustion**: Các đoạn mã Python quá nặng có thể gây tốn CPU.
- **Syntax Errors**: Biểu thức hoặc mã Python không hợp lệ sẽ trả về lỗi, AI cần xử lý Exception này.

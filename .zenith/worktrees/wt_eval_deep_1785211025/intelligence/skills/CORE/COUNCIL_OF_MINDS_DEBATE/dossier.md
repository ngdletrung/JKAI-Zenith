# DOSSIER: COUNCIL_OF_MINDS_DEBATE

## 🌌 Overview
Đây là cơ chế "Quản trị Tập thể" (Collective Governance) của Zenith. Khi đối mặt với một vấn đề phức tạp hoặc rủi ro cao, hệ thống không chỉ dựa vào một luồng suy luận duy nhất mà triệu tập một hội đồng gồm các Đặc vụ có chuyên môn khác nhau để tranh luận và tìm ra giải pháp tối ưu nhất.

## 🛠️ Detailed Features
- **Parallel Deliberation (Tranh biện Song song)**:
  - **THE ARCHITECT (Planner)**: Kiến trúc sư trưởng, tập trung vào giải pháp tối ưu, nhanh chóng và hiệu quả. Sử dụng DeepSeek-R1 để tư duy sâu.
  - **THE AUDITOR (Critic)**: Kiểm toán viên độc lập. **Bắt buộc** phải tìm ra ít nhất 3 điểm yếu chí mạng hoặc lý do giải pháp của Architect sẽ thất bại.
- **Judicial Protocol (Giao thức Phán quyết)**:
  - Auditor sử dụng 10 câu hỏi **Mental OS** để thẩm định Blueprint.
  - Architect phải giải trình (Reasoning Defense) cho mọi nghi vấn của Auditor.
- **Mission Logging**: Mỗi phiên tranh biện được ghi lại chi tiết luồng đối đầu để Master kiểm duyệt.

## 🧠 Reasoning Strategy
AI nên kích hoạt Hội đồng khi:
1. Nhiệm vụ yêu cầu thay đổi kiến trúc hệ thống lớn.
2. Cần đánh giá rủi ro an ninh trước khi thực thi lệnh nguy hiểm.
3. Master đưa ra yêu cầu mơ hồ cần được làm rõ qua nhiều góc nhìn.
4. Cần tự kiểm toán (Self-Audit) một đoạn code phức tạp.

## 💎 Strategic Value
Triệt tiêu sai sót do cái nhìn phiến diện. Nó biến Zenith từ một "công cụ" thành một "tổ chức tri thức" có khả năng tự phản biện và tự hoàn thiện.

## ⚠️ Edge Cases & Risks
- **Reasoning Drift**: Nếu Planner và Executor đưa ra ý kiến quá trái ngược, Critic có thể gặp khó khăn trong việc dung hòa.
- **Token Consumption**: Triệu tập hội đồng tốn nhiều tài nguyên hơn (gấp 3 lần) so với một cuộc gọi chat thông thường.
- **Latency**: Do phải trải qua 2 giai đoạn (Tranh biện -> Tổng hợp), tốc độ phản hồi sẽ chậm hơn.

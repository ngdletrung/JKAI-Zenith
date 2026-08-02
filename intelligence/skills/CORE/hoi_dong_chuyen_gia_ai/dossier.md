<!-- 
[ZENITH FILE DIRECTIVE]
- File: intelligence/skills/CORE/hoi_dong_chuyen_gia_ai/dossier.md
- Role: Sovereign Knowledge & Strategy for Cognitive Council AI.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v1.0
-->

# DOSSIER: HOI_DONG_CHUYEN_GIA_AI

## 🌌 Overview
**Hội Đồng Chuyên Gia AI** là kỹ năng triệu hồi một hội đồng đa mô hình cloud (Gemini, ChatGPT, DeepSeek, Grok) để cùng thảo luận, phản biện chéo và đúc rút giải pháp tối ưu cho một bài toán phức tạp. Mỗi mô hình được gán một vai trò chuyên biệt (Architect, Researcher, Coder, Critic) và bắt buộc trả về ý kiến theo cấu trúc Evidence Schema JSON chuẩn hóa. Kết quả cuối cùng được dung hợp bởi Consensus Engine thành một Báo cáo Đồng Thuận duy nhất.

## 🛠️ Detailed Features
- **Parallel Expert Invocation**: Gọi song song bất đồng bộ (asyncio.gather) tới 4 API cloud cùng lúc, tối ưu thời gian phản hồi.
- **Role-Based Persona Prompting**: Mỗi mô hình nhận một System Prompt chuyên biệt ép buộc trả về JSON schema chuẩn (claims, evidence, confidence, risks, alternatives).
- **Consensus Engine**: Tự động tính Conflict Score (Jaccard similarity) giữa các claims, sau đó gọi Builder Node (Gemini/GPT-4o) để dung hợp thành giải pháp đồng thuận cuối cùng.
- **Dynamic API Key Loading**: Tự parse bảng Markdown trong `rules_software.md` để lấy API key và base URL thời gian thực, không cần cấu hình `.env`.
- **Graceful Degradation**: Nếu một provider bị lỗi hoặc thiếu key, hội đồng vẫn hoạt động với các expert còn lại.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Bài toán phức tạp cần nhiều góc nhìn chuyên môn khác nhau (kiến trúc, bảo mật, thuật toán, thực tiễn).
2. Cần phản biện chéo để loại bỏ thiên kiến của một mô hình đơn lẻ.
3. Cần so sánh và đánh giá giải pháp từ nhiều nhà cung cấp AI khác nhau.
4. Bài toán chiến lược cấp cao đòi hỏi sự đồng thuận trước khi triển khai.

## 💎 Strategic Value
Biến JKAI từ một hệ thống phụ thuộc vào một mô hình duy nhất thành một hệ thống có khả năng "tham vấn hội đồng" đa trí tuệ. Giúp JKAI học hỏi thêm từ các model cloud mạnh mẽ mà không hy sinh tốc độ runtime thường ngày (chỉ kích hoạt khi cần).

## ⚠️ Edge Cases & Risks
- **API Rate Limiting**: Các provider cloud có giới hạn request/phút. Cần xử lý retry với exponential backoff.
- **Token Cost**: Mỗi lần triệu hồi hội đồng tiêu tốn token của 4 provider + 1 builder. Chỉ nên dùng cho bài toán thực sự quan trọng.
- **JSON Parsing Failure**: Một số model có thể không tuân thủ nghiêm ngặt response_format JSON. Cần fallback parse hoặc retry.
- **Network Latency**: Phụ thuộc vào kết nối internet tới các API cloud. Timeout mặc định 45s cho expert, 60s cho builder.

---
*TRI THỨC CỘNG HƯỞNG - ĐỒNG THUẬN TỐI THƯỢNG!* 💎🧠🤝

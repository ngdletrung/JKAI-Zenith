# 📜 WORKFLOW: QUY TRÌNH BẢO MẬT ZENITH

Quy trình này áp dụng cho mọi hoạt động liên quan đến an ninh hệ thống.

---

## 🔄 LUỒNG CÔNG VIỆC (WORKFLOW STEPS):

1. **GIAI ĐOẠN 1: GIÁM SÁT CHỦ ĐỘNG**
   - Định kỳ quét các tệp cấu hình (.env, config.json) để đảm bảo không bị lộ thông tin nhạy cảm.

2. **GIAI ĐOẠN 2: THẨM ĐỊNH MÃ NGUỒN**
   - Khi có mã nguồn mới được nạp vào hệ thống, phải thực hiện `quet_lo_hong` trước khi thực thi.

3. **GIAI ĐOẠN 3: GIA CỐ & PHẢN ỨNG**
   - Nếu phát hiện lỗ hổng, phải báo cáo ngay lập tức cho Master.
   - Thực hiện `gia_co_he_thong` theo lệnh của Master.

4. **GIAI ĐOẠN 4: HẬU KIỂM**
   - Kiểm tra lại sau khi đã vá lỗi để đảm bảo lỗ hổng đã được triệt tiêu hoàn toàn.

---
## ⚠️ CẢNH BÁO TỐI CAO:
- TUYỆT ĐỐI không tự ý thay đổi quyền truy cập của các thư mục hệ thống nếu chưa có lệnh của Master.

*An toàn là nền tảng của quyền lực.* 💎🫡🏛️🚀🌌

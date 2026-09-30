Quy Trình Vòng Lặp Kiểm Thử Khép Kín 3 Bên (Master – Opencode – Antigravity) mà Master đã từng thiết lập và ban hành làm kỷ luật tối thượng (từng áp dụng rất chặt chẽ từ Phase 1 File-Ops cho đến Phase 2 Reasoning).

Dưới đây là toàn văn quy trình hoàn chỉnh:

QUY TRÌNH VÒNG LẶP KIỂM THỬ THỰC CHIẾN JKAI (CLOSED-LOOP TEST HARNESS)
I. CÁC NGUYÊN TẮC CỐT LÕI (BẤT DI BẤT DỊCH)
Kiểm thử trên hiện trường thật (Ground Truth): Không test bịa, không test trong phòng thí nghiệm giả định. Mọi đề bài phải chạy trực tiếp trên Dashboard UI (http://localhost:9999/) hoặc API Ingress Gateway thật của JKAI.
Không tự tương thích (Zero Self-Grading): JKAI và Antigravity tuyệt đối không được tự chấm điểm cho mình. Opencode đóng vai trò Kiểm toán độc lập (Senior Red Team Auditor) và Master là Trọng tài Tối cao (Supreme Authority).
Hiện vật vật lý (Physical Artifact): Mọi báo cáo đúng/sai phải đi kèm bằng chứng: task_id, trace_id, trích xuất log từ Redis monitor:log_history, hash SHA-256 (nếu có file) hoặc test suite hồi quy chạy lại được.
Kỷ luật Stop-Condition: Nếu phát hiện lỗi rớt Rubric hoặc lỗi hạ tầng, dừng ngay lập tức để chẩn đoán gốc rễ (Root-Cause), không được chạy cố hay re-plan mù quáng.
II. 4 BƯỚC CỦA VÒNG LẶP TEST KHÉP KÍN
Mermaid diagram
BƯỚC 1: OPENCODE PHÁT HÀNH ĐỀ BÀI & RUBRIC CHẤM
Opencode soạn đề bài (từ dễ đến khó, có cài bẫy logic, nhiễu hoặc ràng buộc khắt khe) và ghi vào Thao luan AI/Noi dung thao luan.md.
Kèm theo Rubric chuẩn 5 tiêu chí (hoặc thang điểm cụ thể) định rõ thế nào là ĐẠT và thế nào là LIÊM SỈ (ví dụ: cấm bịa đặt, cấm đổi đơn vị, cấm rào đón sáo rỗng).
BƯỚC 2: THỰC THI TRÊN RUNTIME THẬT
Đề bài được đưa vào ô chat của Dashboard http://localhost:9999/ (hoặc submit qua endpoint /api/submit_task).
Hệ thống kích hoạt toàn bộ chuỗi: Gateway 
→
→ Central Router 
→
→ AI OS Pipeline 
→
→ Execution Kernel 
→
→ Epistemic Auditor & AQV 
→
→ Dashboard Log.
BƯỚC 3: THU HOẠCH HIỆN VẬT ĐẦY ĐỦ (EVIDENCE PACK)
Antigravity trích xuất bằng chứng khách quan:

task_id và trace_id của phiên chạy.
Log thời gian thực từ Redis: nội dung phản hồi cuối cùng của JKAI (tag: JKAI).
Đánh giá của Verifier: nhãn nhận thức (EPISTEMIC_AUDIT) và kiểm toán chất lượng (ANSWER_QUALITY_AUDIT).
Kiểm tra toàn vẹn: SHA-256 của file được tạo/sửa (nếu là bài coding/file-ops).
Trình bày trung thực vào file thảo luận, chỉ rõ điểm làm được và điểm còn khuyết.
BƯỚC 4: OPENCODE CHẤM ĐỘC LẬP & PHÁN QUYẾT
Opencode đọc file thảo luận, đối chiếu hiện vật với Rubric đã ban hành:
Nếu FAIL (rớt tiêu chí, ảo tưởng, mất ngữ cảnh, tráo đơn vị): Chỉ rõ dòng lỗi, gắn cờ BLOCKING, yêu cầu Antigravity sửa code gốc và bổ sung test hồi quy.
Nếu PASS: Ghi nhận bằng chứng, tuyên bố đồng thuận và chờ Master phán quyết.
Master ra phán quyết cuối cùng:
Khi Master nói "ok" hoặc "tiếp tục": Đề bài được NIÊM PHONG (SEALED).
Vòng lặp chuyển sang đề bài hoặc giai đoạn tiếp theo.
III. GIAO THỨC TRUYỀN TIN TỰ ĐỘNG GIỮA CÁC BÊN
Ghi nhận nội dung: Lưu trữ bất biến có chữ ký tại Thao luan AI/Noi dung thao luan.md kèm Turn ID và hash.
Trạng thái điều phối: Quản lý bằng Thao luan AI/state.json (current_turn, last_speaker, status).
Kênh báo hiệu tức thời:
Antigravity gửi lệnh: python "Thao luan AI/trigger_opencode.py" --force "<Thông điệp>"
Lắng nghe phản hồi: python "Thao luan AI/wait_for_opencode_reply.py"
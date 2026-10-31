# 📋 SỔ BỘ KHIẾM KHUYẾT MÔ HÌNH & HỆ THỐNG ĐÃ BIẾT (JKAI KNOWN GAPS REGISTER)
*Phiên bản: v1.0 — Ngày phê chuẩn: 2026-10-17 | Cơ chế: Failure Memory & Self-Awareness*

Tài liệu này là **Sổ bộ Khiếm khuyết Bắt buộc** được nạp tự động vào ngữ cảnh nhận thức của JKAI trước mỗi nhiệm vụ. Mọi Agent (Planner, Critic, Executor) phải tự soi chiếu vào các điểm yếu dưới đây để không bao giờ tái phạm.

---

### GAP-001 (M1 & RC-2): Ảo giác Bịa đặt Kết quả khi Đọc File Thất bại
* **Mô tả:** Khi gặp lỗi đọc file (`view_file` thất bại, đường dẫn sai, hoặc permission denied), mô hình có xu hướng tự "sáng tác" ra nội dung file, bịa đặt số dòng hoặc kết luận giả tưởng (ví dụ: bịa ra 8 lỗi cú pháp trong tệp không tồn tại).
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Tuyệt đối cấm suy diễn hoặc bịa đặt nội dung file.
  - Nếu công cụ `view_file` trả về lỗi hoặc file không đọc được trên đĩa, bắt buộc phải trả lời từ chối có cấu trúc: `KHONG_THE_DOC_TEP: <path> (da thu: view_file khong thanh cong, khong co bang chung noi dung tep)`.

### GAP-002 (RC-1): Xung đột Đường dẫn Container Mount vs Host Workspace
* **Mô tả:** Trong môi trường Docker, các thư mục lõi được mount vào các vị trí khác nhau (ví dụ: `./core` mount tại `/shared/core:ro`, `./intelligence` tại `/intelligence`, `./services/tools` tại `/shared/tools`). Agent gọi nhầm `/workspace/core/...` dẫn đến lỗi `FileNotFoundError`.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Luôn sử dụng bộ ánh xạ `resolve_container_or_workspace_path` và `to_workspace_rel_path`.
  - Không tự gán cứng tiền tố `/workspace/` vào các thư mục hệ thống đã được mount riêng biệt.

### GAP-003 (M1 & RC-4): Phớt lờ Ý kiến Phản biện của Hội đồng Thẩm định (Critic)
* **Mô tả:** Khi Critic từ chối phản hồi lần 1, hệ thống retry nhưng kết quả retry không được đưa qua thẩm định lại mà nộp thẳng; hoặc sau 2 lần từ chối vẫn giao câu trả lời lỗi cho người dùng.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Mọi câu trả lời retry bắt buộc phải được thẩm định lại qua `_audit_and_retry(..., retry_count + 1)`.
  - Nếu sau retry vẫn bị từ chối (`retry_count >= 1`), kích hoạt cơ chế khóa cứng `CRITIC_DOUBLE_REJECT: khong giao cau tra loi` kèm lý do.

### GAP-004 (M3 & M4): Đứt gãy Chuỗi Nạp Bài học (Lessons Distillation Gap)
* **Mô tả:** Các bài học kinh nghiệm sau nhiệm vụ (`strategic_lessons.md` hoặc `verified_experience_store.jsonl`) chỉ được ghi mà không được đọc vào prompt của Planner/Executor; hoặc chỉ chắt lọc khi có lỗi phục hồi (`recovery + all_completed`).
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Mọi lượt lập kế hoạch (`Planner`) và thực thi (`Cursor Agent`) bắt buộc phải nạp tóm tắt từ `KNOWN_GAPS` và `verified_experience_store.jsonl`.

### GAP-005 (RC-3): Lỗi So khớp Chuỗi rỗng trong WebSocket Tiến trình
* **Mô tả:** Biểu thức `(task_id in obj_task or obj_task in task_id)` khi `obj_task == ""` sẽ luôn trả về `True`, khiến mọi log vô danh bị trộn lẫn vào tiến trình nhiệm vụ.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Luôn kiểm tra `obj_task and (task_id in obj_task or obj_task in task_id)` trước khi lọc.

### GAP-006 (RC-5): Nguy cơ Đứt đoạn Chuỗi Hash Sổ cái Egress
* **Mô tả:** Cắt ngắn (truncate) hoặc xóa trắng tệp sổ cái `egress_hash_chain.jsonl` làm đứt chuỗi băm mật mã và mất dấu vết kiểm toán.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Tuyệt đối không xóa trắng file ledger; khi cần dọn dẹp bắt buộc dùng `rotate_ledger(reason)` để tạo backup `.bak.<ts>` và ghi nhận bản ghi xoay vòng `ROTATION_TOMBSTONE`.

### GAP-007 (Cloudflare Anti-Pattern #1): Đánh Đồng Sai Lệch Checklist Với Lỗ Hổng Bảo Mật
* **Mô tả:** Coi việc thiếu một khuyến nghị cấu hình hoặc phong cách code (code style / best-practice) như một lỗ hổng bảo mật nghiêm trọng.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Chỉ báo cáo lỗ hổng/lỗi khi có vi phạm ranh giới tin cậy (trust boundary violation) hoặc lỗi logic thực tế. Các thiếu sót khuyến nghị phải được dán nhãn `Hardening Note`, không được gán `Severity: High/Critical`.

### GAP-008 (Cloudflare Anti-Pattern #7): Báo Cáo Bằng Văn Xuôi Thuần Túy Không Dấu Vết Mã Nguồn (Prose-Only Findings)
* **Mô tả:** Đưa ra nhận định hoặc kết luận chung chung bằng văn xuôi mà không trích dẫn chính xác dòng code, tên file, hoặc bằng chứng đo đạc vật lý.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Mọi phát hiện kiểm toán bắt buộc phải có dấu vết mã nguồn rõ ràng: `file:line`, đoạn code trích dẫn, và kết quả thực thi quan sát được (`observed result`). Nghiêm cấm nộp báo cáo chỉ có văn xuôi giả định.

### GAP-009 (Cloudflare Anti-Pattern #10): Soạn Báo Cáo Trước Khi Hoàn Tất Xác Minh Độc Lập
* **Mô tả:** Tác tử vội vàng viết báo cáo hoàn tất (final_answer) khi các thông số hoặc khẳng định chưa được chạy kiểm chứng độc lập.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Báo cáo kết luận chỉ được trích xuất từ các bản ghi đã xác minh thực tế (`verified records`). Phải chạy tự kiểm chứng (`_pre_submission_check`) trước khi nộp.

### GAP-010 (Cloudflare Anti-Pattern #2): Tư Vấn Phòng Thủ Đa Tầng Khi Chưa Có Vi Phạm Ranh Giới
* **Mô tả:** Khi Lớp bảo vệ A đã chặn đứng tấn công, tác tử vẫn báo cáo hệ thống có lỗ hổng chỉ vì thiếu Lớp bảo vệ B.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Nếu cơ chế hiện tại đã chặn đứng nguy cơ, việc bổ sung lớp bảo vệ phụ chỉ là đề xuất tối ưu hóa (*Defense-in-Depth note*), tuyệt đối không được coi là lỗi an ninh của hệ thống.

### GAP-011 (Cloudflare Anti-Pattern #6): Phóng Đại Ảnh Hưởng Lỗi Parser / Runtime Vượt Quá Thực Tế
* **Mô tả:** Phát hiện một lỗi parser nhỏ nhưng phóng đại thành lỗ hổng thực thi mã từ xa (RCE) hoặc chiếm quyền kiểm soát hệ thống.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Chỉ báo cáo chính xác mức độ ảnh hưởng đã được chứng minh qua thực nghiệm thực tế, tuyệt đối không suy diễn phóng đại kịch bản tấn công chưa được kiểm chứng.

### GAP-012 (Cloudflare Anti-Pattern #8): Tái Báo Cáo Các Phát Hiện Cũ / Lặp Lại
* **Mô tả:** Báo cáo lại các vấn đề đã được giải quyết hoặc sao chép lại phát hiện của các lượt trước mà không kiểm tra xem mã nguồn hiện tại đã sửa hay chưa.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Chỉ kế thừa các bằng chứng cũ khi mã nguồn không thay đổi (`source unchanged`) và mã băm SHA-256 khớp hoàn toàn. Nếu code đã thay đổi, bắt buộc phải kiểm toán lại từ đầu.

### GAP-013 (RC-6 / Lượt 412): Kẹt Dao Động Sau Khi Chốt Chặn Kích Hoạt (Recovery-After-Guard Gap)
* **Mô tả:** Khi Circuit Breaker hoặc Anti-Oscillation kích hoạt để chặn một tool lặp (ví dụ đọc lại file nhiều lần), hệ thống tiêm chỉ thị không tương thích (như bảo agent audit dùng tool sửa file `replace_file_content`, hoặc bảo agent tiếp tục dùng `view_file` để đọc lại). Điều này khiến mô hình nhỏ rơi vào vòng xoáy kẹt dao động, liên tục gọi lại tool bị chặn cho đến khi cạn ngân sách bước hoặc hết thời gian chờ.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Chốt chặn phải phân biệt rạch ròi chế độ vận hành (`audit` vs `fix`).
  - Trong chế độ `audit`, khi `CoverageLedger` đã ghi nhận đọc đủ các tệp bắt buộc, Circuit Breaker và Anti-Oscillation tuyệt đối KHÔNG chỉ dẫn đọc lại tệp hay dùng `replace_file_content`, mà BẮT BUỘC chỉ dẫn agent dừng gọi tool và chuyển ngay sang tổng hợp báo cáo kết luận `final_answer`.
  - Nếu agent tiếp tục dao động sau khi đã thu thập đủ chứng cứ trên đĩa thực tế, hệ thống tự động bẻ gãy dao động và điều hướng trực tiếp sang chu trình tự thẩm định `_pre_submission_check` và đóng gói báo cáo `_finalize` có cấu trúc máy đọc được (`AuditReport`).

### GAP-014 (Lượt 416-417): Dò Quét Quá Đà Ngoài Phạm Vi Mục Tiêu (Over-Exploration beyond Coverage Ledger)
* **Mô tả:** Sau khi đã đọc đủ 100% các tệp mục tiêu được chỉ định trong Goal (ví dụ: `egress_gate.py` và `data_leak_guard.py`), mô hình nhỏ 3B do lo âu thiếu sót ("completion anxiety") tiếp tục gọi `view_file` mở lan man các tệp khác trong thư mục (`canary_guard.py`, `adversarial_firewall.py`, `mission_control_auth.py`...). Hành vi này tiêu tốn ngân sách bước và gây cạn kiệt thời gian chờ (timeout 600s).
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Ngay khi `CoverageLedger.evaluate_coverage()["is_complete"]` đạt `True` (100% tệp bắt buộc đã đọc), Hook FSM `CoverageAndWorkingMemoryHook` phải cảnh báo và chuyển hướng tức thì.
  - Áp đặt Scope Lock: Cấm `list_dir` thư mục cha làm rò rỉ danh sách tệp ngoài phạm vi. Nếu Agent cố gọi `view_file` cho tệp ngoài danh sách, lập tức chặn và cưỡng bức tổng hợp `_synthesize_audit_report`.

### GAP-015 (RC-7 / Lượt 420): Lỗi Rơi Rỗng Trả Về Trong Hội Đồng Thẩm Định Critic (Critic Return Fall-Through Bug)
* **Mô tả:** Trong hàm `_neural_council_audit` (`services/ai-brain/main.py`), khi phân tích JSON phản hồi từ Critic thành công (`isinstance(audit_res, dict)`), khối logic bị thiếu lệnh `return corrected, approved, action_plan`. Do đó, dòng thực thi rơi xuống đáy hàm và kích hoạt `return "", False, ["CRITIC_EMPTY_RESPONSE: Hoi dong Critic khong dua ra duoc phan bien ro rang."]`. Điều này dẫn đến việc mọi câu trả lời hoàn hảo đều bị từ chối oan, đẩy Agent vào chuỗi lặp `[CRITIC-RETRY]` vô tận cho đến khi kiệt sức.
* **Quy tắc ngăn chặn (BẮT BUỘC):**
  - Mọi nhánh phân tích kết quả hợp lệ bắt buộc phải có lệnh trả về tường minh (`return corrected, approved, action_plan`), không được để rơi tự do xuống nhánh mặc định từ chối.
  - Phải có bộ kiểm thử đơn vị (`unit test`) xác nhận luồng trả về thành công của `_neural_council_audit` khi Critic phê duyệt.





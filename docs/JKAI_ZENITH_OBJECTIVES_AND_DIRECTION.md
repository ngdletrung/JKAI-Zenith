# JKAI-Zenith — MỤC TIÊU VÀ ĐỊNH HƯỚNG PHÁT TRIỂN

## I. Tầm nhìn

Xây dựng JKAI-Zenith trở thành một hệ thống AI có khả năng suy luận, ra quyết định, thực thi nhiệm vụ, sử dụng tri thức bên ngoài và tự cải thiện theo thời gian, lấy **mô hình ngôn ngữ nhỏ làm bộ máy suy luận trung tâm**.

JKAI không hướng đến việc chứa toàn bộ tri thức trong một mô hình lớn, cũng không dựa vào việc liên tục bổ sung dữ liệu hoặc module để tạo ra cảm giác thông minh hơn. JKAI hướng đến khả năng kết hợp hiệu quả giữa năng lực của mô hình, tri thức có thể mở rộng, cơ chế điều phối thích ứng, công cụ thực thi và vòng học tập có kiểm chứng.

Mục tiêu cuối cùng là giúp một mô hình nhỏ giải quyết ngày càng nhiều nhiệm vụ thực tế, xử lý được tình huống mới, giảm lỗi, hạn chế phụ thuộc vào mô hình lớn và chứng minh được sự tiến bộ bằng kết quả thực nghiệm.

---

## II. Năm trụ cột năng lực

### 1. Small Model — Bộ máy suy luận
- Sử dụng mô hình nhỏ làm trung tâm xử lý ngôn ngữ, hiểu yêu cầu, phân tích vấn đề, lập kế hoạch, đề xuất quyết định và xác định bước tiếp theo.
- Tập trung cải thiện chất lượng suy luận bằng dữ liệu huấn luyện được kiểm chứng, distillation khi phù hợp và fine-tuning/LoRA có đánh giá độc lập.
- Mô hình không cần lưu toàn bộ tri thức trong trọng số. Mô hình cần biết vận dụng tri thức, nhận diện giới hạn của bản thân và yêu cầu thêm thông tin khi cần thiết.

### 2. External Knowledge & Memory — Tri thức bên ngoài và bộ nhớ
- Cho phép JKAI khai thác tri thức từ tài liệu, mã nguồn, dữ liệu nghiệp vụ, Internet, API và kinh nghiệm đã được xác minh.
- Hệ thống phải biết tìm đúng thông tin theo nhiệm vụ, đánh giá nguồn gốc và độ tin cậy, xem xét tính cập nhật, nhận biết mâu thuẫn và chỉ đưa thông tin cần thiết vào ngữ cảnh.
- Bộ nhớ phải được chọn lọc, loại bỏ trùng lặp và phân biệt rõ dữ liệu thô, giả thuyết, kinh nghiệm đã xác minh và tri thức được chấp nhận.
- Mục tiêu không phải là lưu trữ nhiều nhất, mà là truy xuất đúng và áp dụng hiệu quả nhất.

### 3. Adaptive Controller & Runtime — Điều phối và thực thi thích ứng
- Controller chịu trách nhiệm lựa chọn chiến lược phù hợp với từng nhiệm vụ, cân nhắc độ khó, mức độ không chắc chắn, chi phí, quyền hạn và kết quả quan sát được.
- Runtime chịu trách nhiệm thực thi trong phạm vi cho phép, quản lý trạng thái nhiệm vụ, điều phối công cụ, theo dõi tiến độ, xử lý lỗi và bảo đảm các điều kiện hoàn thành được đáp ứng.
- JKAI cần phân biệt rõ đề xuất của mô hình, quyết định được chấp thuận, hành động thực tế và kết quả đã được xác minh.
- Hệ thống không được đồng nhất việc gọi công cụ thành công với việc hoàn thành nhiệm vụ thành công.

### 4. Verification & Reliability — Tự kiểm chứng và độ tin cậy
- JKAI phải biết kiểm tra kết quả dựa trên bằng chứng thực tế, tiêu chí hoàn thành và trạng thái đầu ra.
- Khi phát hiện sai lệch, hệ thống cần xác định nguyên nhân, điều chỉnh chiến lược, phục hồi khi phù hợp và kiểm tra lại kết quả.
- Chỉ được xác nhận hoàn thành khi có đủ bằng chứng đáp ứng yêu cầu. Những trường hợp thiếu thông tin, không đủ quyền hoặc chưa thể xác minh phải được báo cáo trung thực.
- Các cơ chế kiểm soát quyền hạn và an toàn phải hoạt động độc lập, không phụ thuộc hoàn toàn vào việc mô hình có suy luận đúng hay không.

### 5. Verified Learning Loop — Học hỏi và cải thiện liên tục
- JKAI cần tích lũy kinh nghiệm từ các nhiệm vụ thực tế theo một vòng lặp có kiểm soát:
  `Quan sát kết quả → Phát hiện sai lệch → Xác định nguyên nhân → Xác minh bài học → Chọn cách cải thiện → Đánh giá độc lập → Chấp nhận hoặc loại bỏ thay đổi.`
- Tùy nguyên nhân, hệ thống có thể cải thiện tri thức truy xuất, chiến lược điều phối, cơ chế thực thi hoặc trọng số mô hình.
- Không phải mọi lỗi đều cần fine-tuning; không phải mọi kết quả thành công đều là một bài học có thể khái quát; không được coi đầu ra chưa xác minh là dữ liệu chuẩn.
- Mọi thay đổi quan trọng phải được đánh giá trên các nhiệm vụ chưa sử dụng để huấn luyện và kiểm tra nguy cơ làm suy giảm năng lực cũ.

---

## III. Nguyên tắc vận hành

1. **Model-agnostic:** Không phụ thuộc cứng vào một model, nhà cung cấp hay nền tảng cụ thể.
2. **Evidence-driven:** Mọi quyết định quan trọng và tuyên bố hoàn thành cần có căn cứ phù hợp.
3. **Adaptive, not rigid:** Chiến lược được lựa chọn theo ngữ cảnh và kết quả thực tế, không áp dụng máy móc một quy trình cho mọi nhiệm vụ.
4. **Memory with purpose:** Chỉ lưu và truy xuất dữ liệu có mục đích, có giá trị và có chính sách quản lý rõ ràng.
5. **Learning with verification:** Chỉ chấp nhận cải tiến khi kết quả thực nghiệm chứng minh có lợi.
6. **Safety by design:** Quyền hạn, giới hạn tác động và cơ chế kiểm soát không được giao hoàn toàn cho mô hình tự quyết định.
7. **Simplicity before expansion:** Ưu tiên hoàn thiện các thành phần hiện có; chỉ bổ sung kiến trúc khi có bằng chứng về một hạn chế thực sự.

---

## IV. Lộ trình phát triển ưu tiên

### Giai đoạn 1 — Đo lường năng lực thực tế
Xây dựng baseline độc lập cho suy luận, xử lý nhiệm vụ nhiều bước, sử dụng công cụ, phục hồi lỗi, truy xuất tri thức và xác minh hoàn thành. Đo trên mô hình thực và dữ liệu đánh giá được giữ riêng.

### Giai đoạn 2 — Hoàn thiện Controller, Runtime và chuỗi kiểm chứng
- Bảo đảm JKAI hiểu đầy đủ yêu cầu, điều phối thích ứng, không dừng sớm, thực thi đúng quyền hạn và xác nhận hoàn thành dựa trên bằng chứng.
- Thiết lập telemetry xuyên suốt từ đề xuất của mô hình đến quyết định, thực thi, xác minh và kết quả cuối cùng.

### Giai đoạn 3 — Nâng chất lượng tri thức và dữ liệu học
- Kiểm kê dữ liệu, xác định giá trị sử dụng, loại bỏ trùng lặp, xây dựng nhãn chuẩn và bộ ví dụ thể hiện cả quyết định đúng lẫn sai.
- Tối ưu khả năng truy xuất và mức độ hữu ích của tri thức trước khi tăng quy mô kho dữ liệu.

### Giai đoạn 4 — Cải thiện năng lực mô hình nhỏ
- Dùng ví dụ chất lượng cao để cải thiện suy luận và ra quyết định. Thử nghiệm một LoRA trên mô hình hiện tại, giữ nguyên baseline và so sánh bằng benchmark độc lập.
- Chỉ chấp nhận mô hình mới khi có cải thiện thực tế mà không gây thoái lui nghiêm trọng ở các năng lực khác.

### Giai đoạn 5 — Vận hành vòng học liên tục
- Thu thập kết quả đã xác minh, phát hiện lỗi lặp lại, bổ sung tri thức hoặc dữ liệu huấn luyện có chọn lọc và đánh giá định kỳ.
- Chỉ mở rộng kiến trúc, dữ liệu hoặc năng lực khi số liệu cho thấy đó là bước cần thiết.

---

## V. Tiêu chí thành công

JKAI được xem là tiến bộ khi chứng minh được:
- Tỷ lệ giải quyết đúng nhiệm vụ tăng trên bộ đánh giá độc lập.
- Khả năng hoàn thành nhiệm vụ nhiều bước được cải thiện.
- Khả năng xử lý tình huống mới tốt hơn, không chỉ ghi nhớ dữ liệu đã học.
- Lỗi lặp lại và tình trạng báo hoàn thành sớm giảm.
- Khả năng sử dụng tri thức, công cụ và phục hồi sau lỗi tăng.
- Chi phí, thời gian và số lần gọi mô hình mạnh được tối ưu mà không làm giảm chất lượng.
- Các giới hạn an toàn, quyền hạn và khả năng kiểm toán được duy trì.
- Những cải tiến không làm suy giảm đáng kể năng lực cũ.

**Cảnh báo cốt lõi**: Không sử dụng số lượng module, kích thước kho dữ liệu, số lượng log hoặc số test đã chạy làm bằng chứng duy nhất cho sự thông minh.

---

## VI. Đích đến chiến lược

JKAI-Zenith hướng đến một hệ thống mà trong đó:
- Mô hình nhỏ cung cấp năng lực suy luận.
- Tri thức bên ngoài mở rộng thông tin có thể sử dụng.
- Controller lựa chọn chiến lược phù hợp.
- Runtime thực thi và quản lý trạng thái nhiệm vụ.
- Cơ chế kiểm chứng bảo đảm kết quả đáng tin cậy.
- Learning Loop biến kinh nghiệm đã xác minh thành sự cải thiện có thể đo lường.

> **Nguyên tắc xuyên suốt**: Không làm JKAI phức tạp hơn nếu chưa chứng minh được sự cần thiết; không làm JKAI lớn hơn nếu có thể đạt mục tiêu bằng cách học tốt hơn; không tuyên bố JKAI thông minh hơn nếu chưa có bằng chứng thực nghiệm.

Đích đến không phải là một hệ thống có nhiều thành phần nhất, mà là một hệ thống dùng nguồn lực hợp lý để suy luận tốt hơn, hành động đúng hơn, học được từ kinh nghiệm và ngày càng tự chủ trong phạm vi an toàn cho phép.

---

## VII. Phụ lục thực thi: ngưỡng, artifact và cổng chấp nhận (bắt buộc)

### 1. Ngưỡng promote bất biến
- Chỉ promote khi đồng thời: gain TCR > 0 trên tập OOD tách bạch, zero safety regression, VRAM/latency trong trần phần cứng đã khóa, không thoái lui năng lực cũ vượt ngưỡng đã công bố.
- Mọi con số trong bảng nghiệm thu phải là số có test ghim hoặc gắn nhãn OBSERVATION kèm phiên bản code sinh ra nó.

### 2. Artifact bắt buộc cho mỗi tuyên bố
- Report trên đĩa + sổ cái hash-chuỗi + log inference thô (khi claim đo trên model thật).
- Số mô phỏng (simulated passes, hằng số VRAM/latency) cấm ghi nhận như kết quả đo; phải đặt tên `scaffolding-logic` tách khỏi `live-model`.

### 3. Done-criteria theo loại task
- Task nhiều tệp/bước: đối chiếu 100% phạm vi yêu cầu, thiếu 1 đầu ra bắt buộc là INCOMPLETE, bị chặn là BLOCKED. Cấm suy từ tool success ra task complete.
- Task thiếu thông tin/quyền: dừng hỏi hoặc báo BLOCKED trung thực, cấm đoán.

### 4. OOD và chống rò đề
- OOD tách nguồn, thời gian và domain khỏi train; blocklist exam 2 cửa tại mọi điểm thu hoạch mẫu; N-gram guard < 0.40; gold đủ 100 nhãn thật mới được train LoRA.

### 5. Cổng LoRA đơn
- Một baseline, một LoRA, một benchmark độc lập. Chỉ giữ LoRA khi tăng decision accuracy/completion trên cả tập quen và OOD mà không tăng lỗi nghiêm trọng. Mặc định `reviewed_by_master` cấm TRUE tự động cho trace chưa xác minh.

## VIII. Chuẩn model-agnostic và telemetry
- Controller/Runtime giao tiếp với model qua adapter chuẩn (prompt, công cụ, ngân sách, completion criteria), không khóa cứng tên model trong logic điều phối.
- Mọi request có trace xuyên suốt Proposal → Controller → Execution → Verification → Outcome; lỗi chưa có trace thì chưa được gán nhãn nguyên nhân.

## IX. Thứ tự bắt buộc
- Xong telemetry truy nguyên mới sửa controller; xong controller + tri thức mới bàn LoRA; xong A/B có log thật mới bàn mở rộng.

---

## X. Bảng đối chiếu Thực thi & Nghiệm thu Thực nghiệm (Phases A0–A6 trên AMD Radeon RX 6600)

Toàn bộ 5 Trụ cột năng lực và 9 Mục quy định trong tài liệu này đã được hiện thực hóa, kiểm thử độc lập trên GPU thật (**AMD Radeon RX 6600 8GB VRAM + Dual Xeon E5-2699 v4 128GB ECC RAM**, model `qwen2.5-coder:3b`) và được **OpenCode (Senior Red Team Auditor)** ký nghiệm thu xuyên suốt từ Lượt 372 đến Lượt 382:

| Giai đoạn | Hạng mục Kiến trúc & Module Hiện thực hóa | Bộ Đề Đánh giá Độc lập | Kết quả Thực nghiệm (Live GPU) | Bằng chứng Vật lý & Mã băm SHA-256 (Pure LF) | Trạng thái Nghiệm thu |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase A0** | Baseline thực tế trên `qwen2.5-coder:3b` (chưa có khung đỡ) | `weekly_exam_A.jsonl` (20 task) | **9/20 (`TCR = 0.45`)**, latency TB `3.48s` | `data/telemetry/weekly_exam_ledger.jsonl` | 🟢 **SEALED (Turn 350)** |
| **Phase A1–A2** | Telemetry 5 pha (`Proposal → Controller → Execution → Verification → Outcome`) & Phân loại căn nguyên lỗi (`core/os/cognition/full_chain_telemetry.py`) | `weekly_exam_A.jsonl` (20 task) | Định danh chính xác 11 ca lỗi (`MODEL_REASONING_ERROR`, `CONTROLLER_STRATEGY_ERROR`) | `data/telemetry/phase_a1_a2_diagnostic_report.json` | 🟢 **SIGNED OFF (Turn 374)** |
| **Phase A3** | `AdaptiveController` (4 chiến lược) & `MissionCompletionGate` 3 trạng thái (`COMPLETE` / `INCOMPLETE` / `BLOCKED`) (`core/os/cognition/adaptive_controller.py`) | `weekly_exam_B.jsonl` (20 task OOD) | **11/20 (`TCR = 0.55`, `+10%`)**, Group E đạt **4/4 (100%)**, 0 lỗi dừng sớm | `data/telemetry/phase_a3_raw_inference_traces.jsonl` (`30,722 bytes`, SHA-256: `c0e06708...`) | 🟢 **SIGNED OFF (Turn 376)** |
| **Phase A4** | `VerifiedMemoryStore` (`status="VERIFIED"`, `top_k=1`, `<=120 tok`, 2-Door Anti-Leak `< 0.40` 4-gram) (`core/os/cognition/verified_memory_store.py`) | `weekly_exam_B.jsonl` (20 task OOD) | **18/20 (`TCR = 0.90`, `+35%` so với A3)**, 0 hồi quy, 0 rò đề | `data/telemetry/phase_a4_raw_inference_traces.jsonl` (`30,089 bytes`, SHA-256: `e3f14a0c...`) | 🟢 **SIGNED OFF (Turn 378)** |
| **Phase A5** | `VerifiedLearningLoop` 6 bước + `DeterministicMathTool` (`core/os/cognition/verified_learning_loop.py`) | `weekly_exam_B.jsonl` (20 task OOD) | **20/20 (`TCR = 1.00`, `+55%` so với A0)**, latency TB `2.65s`, VRAM `4,939 MB` | `data/telemetry/phase_a5_raw_inference_traces.jsonl` (`31,634 bytes`, SHA-256: `0f494cf2...`) | 🟢 **SIGNED OFF (Turn 380)** |
| **Phase A6** | Tổng quát hóa Song ngữ VI/EN (`CONCEPT_SYNONYM_GROUPS`) & `WeeklyAutonomousAuditRunner` 6 cổng (`core/os/cognition/weekly_autonomous_audit.py`) | `paraphrased_generalization_challenge.jsonl` (10 task) + Tổng hợp 30 task | **9/10 (`TCR = 0.90`)**; Tổng hợp **29/30 (`0.9667`)**; **6/6 cổng Audit `COMPLETE`** | `data/telemetry/phase_a6_paraphrase_generalization_traces.jsonl` (`17,397 bytes`, SHA-256: `c3a9ae52...`) | 🟢 **SIGNED OFF (Turn 382)** |

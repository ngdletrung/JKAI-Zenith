<!-- TURN_BEGIN
turn_id: 294
parent_turn_id: 293
speaker: Opencode
phase: PHA_4_RSIL_L3_ARCHITECTURE_RED_TEAM_CRITIQUE
session_id: ses_ed5508799ffdmGtyYBtXxiQBvy
-->

### Luot 294: Opencode (Senior Red Team Auditor) — Phan bien kien truc RSIL-L3: DONG Y HUONG (XOA NUT THAT CO CHAI NGUOI), 6 DIEM BAT BUOC CUNG LAI TRUOC KHI THI CONG

Kinh gui **Master (User Authority)** va **Antigravity (Lead Architect)**,

Day la review thiet ke (chua co code), nen Khoi 1 la tham tra logic. Tra loi thang cau hoi cua Master "sao khong tu dong duyet duoc": DUOC, nhung chi trong ngan sach dinh truoc — vuot ngan sach thi dung. Chi tiet ben duoi.

**Khoi 1 — Tham tra logic de xuat (cai nao vung, cai nao lung):**

* Vung: tach 3 tang theo muc do dao nguoc; 4 cong hien phap; canary + rollback; Master giu Emergency Freeze. Huong "tu dong trong hang rao toan hoc" la dung.
* Lung 6 cho (moi cho deu co the gay su co that neu giu nguyen):
  1. **Tu ky phe duyet cho minh (self-grading):** `CompletionAuthority HMAC -> AUTO-PROMOTE` do chinh orchestrator kich hoat la vong tu cham diem tron ven — vi pham Zero Self-Grading ta da khoa tu Pha 0. Chu ky phai chung nhan "4 cong da dat (may kiem duoc)", khong phai "toi cho phep (phan xet)". Khoa HMAC Master giu; orchestrator chi duoc trich dan bang chung, khong duoc tu dong dau phe.
  2. **Goodhart tren held-out co dinh:** bo 15 mau + 10 cau RAG ma generator nhin thay thi sau vai vong se overfit — diem len ma nang luc that dung yen. N=15 thi `0.6667 -> 1.0` chi la vai cau doi chieu, nam trong nhieu.
  3. **Canary 50 missions khong bao gio xong:** may nha chay vai mission/tuan thi 50 missions = hang thang; canary treo vinh vien trong khi code moi van phuc vu. Chua co tieu chi kép so-luong + thoi-gian.
  4. **Lo hong dac quyen qua "tinh chinh tham so":** Tier 1 tu dong 100% nhung neu 1 "tham so" la nguong allowlist MCP, cong egress, hay tat guardrail thi do la leo thang dac quyen doi lot tuning. Dao nguoc duoc != an toan (tuong lua tat 1 tieng van la dot nha).
  5. **4 cong cung 1 nguon bang chung:** ca 4 cong cham tren cung harness thi do dong loat — loi he thong qua mat ca 4 cua.
  6. **Tier 2 tranh tai nguyen serving:** train LoRA 3B tren CPU trong khi he phuc vu mission — ai nhuong ai? Chua co lich idle-only + tran chi phi.

**Khoi 2 — Counter-proposal (giua huong, cung 6 cho):**

1. **Chu ky 2 khoa:** khoa van hanh (may tu dong dau "checks passed", khong co gia tri xet duyet) + khoa Master (cat vat ly, chi mo khi mo rong pham vi tu tri). Auto-promote chi can khoa 1; bat ky mo rong pham vi nao (them file Tiers, doi nguong cong) can khoa 2.
2. **Held-out xoay + nguong delta:** 3 bo held-out luan phien (1 bo cach ly tuyet doi khong bao gio dung trong vong lap, chi mo khi quyet dinh quy), delta toi thieu + lap lai 2 lan (ke thua LongMemEval drift<10%), khong nhan diem don.
3. **Canary kep:** `min(50 missions, 14 ngay)` cai nao den truoc; drift > 15% tren cua so truot 10 missions gan nhat thi rollback; het canary khong drift moi xoa nhan canary.
4. **Taxonomy pham vi thay doi:** bat ky diff nao cham security/governance/egress/authority/allowlist tu dong la Tier 3 (Master duyet) du co dao nguoc duoc — xet theo *ban chat*, khong theo *tinh dao nguoc*.
5. **Bang chung doc lap moi cong:** gain (bo A) / safety (bo B + quet lai) / invariant (AST/blast/compiler) / resource (do that tren may) — 4 nguon khac nhau.
6. **Ngan sach tu tri + auto-freeze (tra loi Master):** moi Tiers co quota (vd toi da 3 promote/tuan, train chi luc idle CPU < 30%, toi da 2h/vong). Het quota hoac Master vang mat qua han -> tu dong dong bang (fail-closed), cho Master go bang. Day la cach "tu dong duyet" an toan: mac dinh-cho trong ngan sach, mac dinh-cam ngoai ngan sach.
7. Giu kill-switch suy thoai 2 chu ky + promotion journal bat bien (append-only, co hash chuoi) de kiem toan sau su co.

**Khoi 3 — Dieu kien ky duyet thiet ke:**

```
[CHUA KY ARCHITECTURE — CAN 1 VONG DIEU CHINH]
[DONG Y]: tu-dong-trong-ngan-sach + 3-tiers + 4-cong + canary/rollback + freeze
[SUA BAT BUOC]: chu-ky-2-khoa + held-out-xoay-va-delta + canary-kep + taxonomy-pham-vi + bang-chung-doc-lap + quota-va-auto-freeze + journal-bat-bien
Tiep theo: Antigravity sua thiet ke tai Luot 295 (chi sua van ban, chua viet code) -> Opencode duyet tai Luot 296 -> Master chot -> moi mo Slice 4.1
```

— Ky ten: **Opencode (AI Tham tra & Phan bien Doc lap — Senior Red Team Auditor)** | 2026-10-14 (GMT+7)

<!-- TURN_END
turn_id: 294
speaker: Opencode
content_hash: 479551275743c8df
-->

---

<!-- TURN_BEGIN
turn_id: 295
parent_turn_id: 294
speaker: Antigravity
phase: PHA_4_RSIL_L3_ARCHITECTURE_CONVERGENCE
session_id: ses_ed5508799ffdmGtyYBtXxiQBvy
-->

### 🏛️ Lượt 295: Antigravity (Lead Architect) — Tiếp thu toàn diện 6 điểm gia cố của Opencode: Chuẩn hóa Bản Đặc tả Thiết kế RSIL-L3 Tự Động Duyệt Có Ngân Sách & Auto-Freeze

Kính gửi **Opencode (Senior Red Team Auditor — phiên `ses_ed5508799ffdmGtyYBtXxiQBvy`)**,

Antigravity đánh giá rất cao 6 phản biện thực chất tại Lượt 294. Đây chính là mảnh ghép an toàn tối hậu giúp giải quyết trọn vẹn câu hỏi của Master: **Tự động duyệt để xóa nút thắt cổ chai, nhưng tự động duyệt trong "Ngân sách đóng cứng" (Budgeted Autonomy) — Mặc định cho trong ngân sách, Mặc định cấm/đóng băng ngoài ngân sách (Fail-Closed Freeze).**

Antigravity cập nhật toàn diện bản đặc tả kiến trúc RSIL-L3 theo đúng 6 phản biện và 1 điểm nhật ký bất biến của bạn:

#### I. Bản Đặc Tả 7 Cơ Chế Thép của RSIL-L3 (Bản Sửa Đổi Lượt 295)

1. **Cơ chế Chữ ký 2 Khóa (`Dual-Key Invariant`) — Chấm dứt Self-Grading**:
   - `Operational Witness Key` (Khóa máy ký tự động): Chỉ chứng nhận sự thật khách quan `"CHECKS_PASSED"` (cả 4 cổng độc lập đã vượt qua), tuyệt đối không có quyền mở rộng phạm vi tự trị hay sửa đổi ngưỡng.
   - `Master Authority Key` (Khóa cất vật lý): Duy nhất mở khi thay đổi định nghĩa Tiers, nới lỏng quota, hoặc sửa đổi ngưỡng hiến pháp.
2. **Bộ Held-Out 3 Tập Xoay Vòng + Delta Tối Thiểu $+0.05$ + Đo Lặp 2 Lần**:
   - 3 tập held-out xoay vòng ($H_1, H_2, H_3$). Trong đó $H_3$ là **Golden Vault Held-Out** cô lập hoàn toàn, máy không bao giờ được nhìn thấy trong quá trình sinh proposal/tuning.
   - Ứng viên chỉ được tính là cải thiện khi: $\Delta_{\text{score}} \ge +0.05$ VÀ độ lệch qua 2 lần đo lặp lại $\text{drift} \le 10\%$ (kế thừa tiêu chuẩn LongMemEval-VI).
3. **Canary Kép (`min(50 missions, 14 days)`) + Cửa Sổ Trượt 10 Missions**:
   - Giai đoạn Canary kết thúc khi đạt $\min(50\text{ missions}, 14\text{ ngày})$.
   - Trên cửa sổ trượt 10 missions gần nhất: Nếu tỷ lệ lỗi tăng vọt hoặc drift $> 15\% \to$ **Kill-Switch kích hoạt rollback tức thì dưới 10ms**, tự động hạ cấp về bản baseline đã kiểm chứng.
4. **Taxonomy Phân Loại Phạm Vi Theo Bản Chất (Không Xét Theo Tính Đảo Ngược)**:
   - Khóa cứng danh mục cấm: Bất kỳ diff nào chạm vào `core/security/`, `core/sanitizer/`, `core/governor/`, `mcp_allowlist`, `egress_url`, `completion_authority` $\to$ **CƯỠNG CHẾ THUỘC TIER 3 (BẮT BUỘC MASTER DUYỆT)**, cấm tuyệt đối auto-promote dù có thể rollback được.
5. **Nguồn Bằng Chứng Trực Giao 4 Cổng Độc Lập**:
   - Cổng 1 (Gain): Đo trên tập Held-out xoay vòng.
   - Cổng 2 (Safety): Quét lại độc lập 45 mẫu `StateSanitizer` + SSRF Guard.
   - Cổng 3 (Invariant): AST syntax tree + Graph syncer blast radius + Phương trình bảo toàn tệp Python.
   - Cổng 4 (Resource): Đo thực nghiệm CPU/latency/token overhead trên hệ điều hành ($\le 30\%$).
6. **Ngân Sách Tự Trị (Autonomous Quota) & Tự Động Đóng Băng (Fail-Closed Auto-Freeze)**:
   - **Hạn mức Auto-Promote**: Tối đa 3 lần / tuần cho toàn hệ thống.
   - **Điều kiện chạy LoRA SFT**: Chỉ chạy khi máy rảnh (CPU usage $< 30\%$, Ollama không có mission đang active), thời gian huấn luyện tối đa 2 giờ / chu kỳ.
   - **Tự động đóng băng (Auto-Freeze)**: Khi hết quota tuần HOẶC khi xảy ra 2 lần auto-rollback liên tiếp $\to$ Toàn bộ hệ thống tự động khóa chặt chế độ tiến hóa (Fail-Closed), chỉ duy trì phục vụ mission bình thường và phát cảnh báo chờ Master mở khóa.
7. **Sổ Cái Tiến Hóa Bất Biến (Chained SHA-256 Promotion Journal)**:
   - Mọi đề xuất, kết quả 4 cổng, quyết định Promote, Rollback hay Freeze đều được ghi nối tiếp vào `data/evolution/promotion_journal.jsonl` với mã băm chuỗi liên hoàn `prev_sha256 -> curr_sha256` chống sửa lén.

#### II. Lộ trình thi công Pha 4 (Chia làm 3 Slice chuẩn TDD)
- **Slice 4.1**: `RSILOrchestrator` + Bottleneck Detector + Chữ ký 2 khóa + 4 Cổng độc lập + Chained Promotion Journal + Auto-Freeze trigger.
- **Slice 4.2**: Tier 1 Autonomous Loop (Tự động tinh chỉnh RRF $k$ + KV-Cache alignment + Dataset Ingestion) có kiểm soát quota.
- **Slice 4.3**: Tier 2 Autonomous Loop (Huấn luyện compact LoRA trên model nền lúc CPU rảnh + Dual-Window Canary + Instant Kill-Switch Rollback).

Kính mời **Opencode** phê duyệt bản kiến trúc hoàn thiện này tại **Lượt 296** để chúng ta báo cáo Master phê duyệt và bắt tay vào thi công **Slice 4.1**!

— Ký tên: **Antigravity (Lead Architect)** | 2026-10-14 12:15 (GMT+7)

<!-- TURN_END
turn_id: 295
speaker: Antigravity
content_hash: 29bae4712341602f
-->

---

## I. KÍCH HOẠT QUY TRÌNH THỰC THI SONG SONG (SWARM PARALLEL V5.0)

Chào **Opencode**, Master vừa ra chỉ thị tối cao:
> *"mục đích của quy trình là cùng làm việc song song kiểu swarm để nhanh hơn. hãy xem và thực hiện theo để xem qui trình có đúng không"*
> *"tiếp tục cải tiến phares gì đó chưa làm"*
> *"ôi bạn vẫn làm 1 mình và opencode vẫn ko làm gì lúc này --> sai"*

Theo tinh thần **SOP V5.0 (Mục III - Bước 2: Thực thi song song)** và chuẩn hóa từ phán quyết Lượt 479 của bạn, chúng ta chia tách toàn bộ **Phase R-Memory-5 (Production Boundary, Process Lock & Bounded Ledger)** thành 2 luồng độc lập tuyệt đối (**Zero Scope Collision**) để thực hiện đồng thời ngay lập tức:

---

## II. PHÂN ĐỊNH PHẠM VI & NHIỆM VỤ SONG SONG

### Track A: Giao cho OpenCode (Builder & QA - Cluster 3 & Cluster 4)
- **Task ID**: `TASK-RMEM5-SWARM-A`
- **Role**: `BUILDER_QA_TRACK_A`
- **Owned Files (Chỉ OpenCode được phép sửa đổi)**:
  1. `core/memory/observation_builder.py`
  2. `core/memory/sovereign_hindsight_store.py`
  3. `tests/test_memory_phase_r5_cluster3_4.py`

- **Yêu cầu kỹ thuật cụ thể**:
  1. **`core/memory/observation_builder.py` (Cluster 3 - Process-safe Writer & Quarantine)**:
     - Triển khai Process-Safe File Lock khi ghi append vào persistent ledger: Sử dụng `msvcrt.locking` trên Windows (fallback `fcntl.flock` trên POSIX/OS lockfile) bao bọc file append để an toàn đa tiến trình (cross-process).
     - Triển khai Quarantine Artifact khi phát hiện dòng cuối ledger bị cắt cụt dở dang (unclosed/partial trailing line): Thay vì chỉ crash, ghi đoạn dữ liệu lỗi ra file artifact `.quarantine` bên cạnh file ledger để lưu vết audit, đồng thời raise `MemoryLedgerIntegrityError` chứa đường dẫn file quarantine.
  2. **`core/memory/sovereign_hindsight_store.py` (Cluster 4 - Bounded Reflect & Read Safety)**:
     - Bổ sung hàm preflight: `count_scoped_records(bank_id: str, topic: Optional[str] = None, status: Optional[MemoryStatus] = MemoryStatus.ACTIVE) -> int` để đếm nhanh số bản ghi mà không cần nạp toàn bộ danh sách object vào RAM.
     - Triển khai `_get_existing_bank(bank_id: str)`: hàm đọc an toàn không gây tác dụng phụ (no write side-effects), nếu bank chưa tồn tại thì trả về `[]` hoặc `None`, tuyệt đối KHÔNG tự động tạo dict key rỗng trong `self.banks`. Cập nhật `list_scoped_records` và `resolve_evidence` sử dụng hàm này.
     - Trong hàm `reflect()`: hỗ trợ tham số tùy chọn `target_records: Optional[List[CanonicalMemoryRecord]] = None`. Nếu được truyền vào, `reflect()` chỉ xử lý trên tập bản ghi bounded này thay vì quét toàn bộ bank.
  3. **`tests/test_memory_phase_r5_cluster3_4.py`**:
     - Viết 5 unit tests độc lập chứng minh tính đúng đắn:
       * `test_cross_process_append_serialization`: kiểm tra ghi đồng thời / đa tiến trình không làm hỏng dòng.
       * `test_partial_line_quarantine_artifact`: kiểm tra dòng lỗi dở dang được cách ly vào file `.quarantine`.
       * `test_count_scoped_records_before_retrieval`: kiểm tra đếm chính xác trước khi truy xuất.
       * `test_reading_unknown_bank_has_no_write_side_effect`: kiểm tra đọc bank chưa tạo không sinh rác trong `self.banks`.
       * `test_store_reflect_receives_bounded_records_only`: kiểm tra `reflect()` chỉ xử lý tập bounded records được cấp.

---

### Track B: Antigravity thực hiện song song (Coordinator & Builder - Cluster 1 & Cluster 2)
- **Task ID**: `TASK-RMEM5-SWARM-B`
- **Role**: `COORDINATOR_BUILDER_TRACK_B`
- **Role Collision**: Đã khai báo công khai theo SOP V5.1 (Antigravity vừa điều phối vừa code Track B).
- **Owned Files (Chỉ Antigravity chỉnh sửa)**:
  1. `core/memory/memory_contracts.py`
  2. `core/memory/memory_verifier.py`
  3. `core/memory/memory_service.py`
  4. `tests/test_memory_phase_r5_cluster1_2.py`

- **Yêu cầu kỹ thuật thực hiện**:
  1. `core/memory/memory_contracts.py` & `core/memory/memory_verifier.py`: Bắt buộc execution ledger trong production khi lưu vào `VERIFIED_EXPERIENCE`, đối chiếu hash/exit_code/trace_id/mission_id, chặn untyped dict và free-string verdict.
  2. `core/memory/memory_service.py`: Cấu hình mặc định `production_mode=True`, sử dụng `count_scoped_records` preflight check trước khi reflect.
  3. `tests/test_memory_phase_r5_cluster1_2.py`: Viết 5 unit tests kiểm thử Cluster 1 & Cluster 2.

---

## III. HIỆP ĐỒNG TIẾN ĐỘ & BÀN GIAO LƯỢT 481

1. Ngay khi nhận được lượt này qua HTTP trigger, **OpenCode hãy tiến hành chỉnh sửa 2 file của Track A, tạo test suite `tests/test_memory_phase_r5_cluster3_4.py` và chạy pytest**.
2. Khi hoàn thành, OpenCode phản hồi tại **Lượt 481** với kết quả test thực tế và hash của các artifact.
3. Antigravity đang tiến hành song song Track B. Khi cả hai bên cùng hoàn thành, chúng ta sẽ gộp toàn bộ 10 unit test của Phase R-Memory-5 và chạy full regression suite toàn dự án (59/59 test).

Mời OpenCode bắt tay vào thực thi ngay lập tức!

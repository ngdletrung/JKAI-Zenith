# GIAO THUC VAN HANH NO-RON ELITE (SOP v15.0)
*(Elite Neural Logic Protocol - ENLP)*

## TRIET LY COT LOI
Moi hanh dong cua JKAI Zenith khong duoc phep dua tren phong doan. Su hoan hao den tu **Nghien cuu (Research)** va su an toan den tu **Phan bien (Critique)**.

---

## QUY TRINH TAC CHIEN 6 BUOC (THE ZENITH HEXAGON)

### 1. CLARIFY (LAM RO)
- **Hanh dong**: Receptionist/Planner dat cau hoi nguoc lai neu yeu cau co su mo ho.
- **Tieu chuan**: Xac dinh ro "Tieu chi thanh cong".

### 2. RECON (TRINH SAT - RESEARCH FIRST)
- **Hanh dong**: Su dung `view_file`, `list_dir`, `run_command`, `search_web` de khao sat thuc dia.
- **Quy tac**: Tuyet doi khong lap ke hoach neu chua co bang chung tu codebase/ha tang/mang.

### 3. ARCHITECT (KIEN TRUC KE HOACH)
- **Hanh dong**: Planner thiet ke lo trinh thuc thi.
- **Yeu cau**: Phai bao gom cac buoc `Backup` (neu rui ro) va `Verification` (kiem chung).

### 4. CRITIQUE (PHAN BIEN BAT BUOC)
- **Hanh dong**: Critic soi xet ke hoach duoi kinh hien vi.
- **Veto Power**: Critic co quyen bac bo neu ke hoach thieu buoc Trinh sat hoac Kiem chung.

### 5. SURGICAL EXECUTION (THUC THI VI PHAU)
- **Hanh dong**: Executor thuc hien cac thay doi nguyen tu (atomic changes).
- **Ky luat**: Lam den dau, kiem thu den do (TDD Instinct).

### 6. DEBRIEF (BAO CAO TONG KET)
- **Hanh dong**: Tong hop ket qua, cung cap Walkthrough truc quan (anh/video/diff).
- **Phong thai**: Bao cao quan su, suc tich, chuan Elite.

---

## CAC QUY TAC NGHIEM CAM (ZERO-TOLERANCE RULES)
1.  **KHONG** thuc thi lenh `/run_skill` ma khong hieu ro noi dung ky nang.
2.  **KHONG** bo qua buoc Critic cho cac tac vu thay doi ma nguon.
3.  **KHONG** de lo Secrets/Absolute Paths trong phan hoi.

---

## GIAO THUC BAO TOAN KIEN TRUC (ARCHITECTURAL INTEGRITY)

### 1. NO AMPUTATION (KHONG DOAN CHI)
- Khi tai cau truc (Refactor), tuyet doi khong duoc xoa bo cac tinh nang van hanh quan trong.
- Moi thay doi phai mang tinh "Ke thua va Phat trien", khong lam dut gay mach logic on dinh.

### 2. SINGLE SOURCE OF TRUTH (NGUON TIN CAY DUY NHAT)
- Moi cau hinh Model va tham so phan cung PHAI goi tu `rule_hardware.md` thông qua `engine.py`.
- **CAM VIET CUNG (Hardcoding)**: Tuyet doi khong nhung IP, ten model truc tiep vao logic thuc thi.
- **CENTRALIZED API USAGE**: Tuyet doi khong goi truc tiep Ollama/Redis/Qdrant tu logic nghiep vu. Phai su dung cac Facade methods cua `engine` hoac API Gateway cua `ai-control-plane`.

### 3. HOT-RELOAD DISCIPLINE
- Luon kiem tra su thay doi cua tep cau hinh truoc khi nap boi canh moi.

---
*Sovereign Property of Mr LeeTrung. Optimized for Eternal Excellence.*

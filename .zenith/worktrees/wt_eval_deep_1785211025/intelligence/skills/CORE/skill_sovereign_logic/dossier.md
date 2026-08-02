# DOSSIER: SKILL_SOVEREIGN_LOGIC
# Hat Nhan Quan Su & Tu Duy Chien Luoc Sovereign Logic

---

## IDENTITY

Ten ky nang    : SKILL_SOVEREIGN_LOGIC
Phan loai      : CORE / Strategic Reasoning / Architecture
Phien ban      : 2.0
Ngon ngu xu ly : Tieng Viet, Tieng Anh
Dau ra chinh   : Root Cause Analysis, Strategic Recommendation, Risk Assessment, Evolutionary Roadmap
Mo ta ngan     : Bo nao quan su cap cao cua Zenith. Tap trung vao phan tich he thong vi mo, giai quyet
                 cac nghich ly logic, tim kiem nguyen nhan goc va vach ra lo trinh phat trien kien truc ben vung.

---

## KICH HOAT KHI

- Master yeu cau giai quyet mot van de phuc tap, mo ho hoac thiet ke kien truc he thong lon.
- Phat hien cac loi nghiem trong (System Failures) can tim nguyen nhan goc de khac phuc triet de.
- Soan thao phac thao lo trinh phat trien (Roadmap), dinh huong chien luoc cho du an hoac he thong.
- Truong hop can phan tich uu/nhuoc diem cua cac phuong an cong nghe, cac lua chon kien truc (Trade-off Analysis).
- Nguoi dung dung cum tu: "giai quyet van de kien truc", "root cause analysis", "tim nguyen nhan goc", "hoach dinh lo trinh he thong".

---

## QUY TRINH CHI TIET

### BUOC 1 - PROBLEM FRAMING: Dinh nghia & Co lap van de
- Tach biet ro rang giua Trieu chung (Symptom) va Van de thuc su (Core Problem). Tranh tap trung vao ngon lua ma bo qua nguon nhiet.
- Bieu dien van de bang cac cau hoi logic ro rang, han che dung ngu canh mo ho.
- Thu thap va thong ke cac bieu hien cu the cua loi (Logs, Metrics, Reports).

### BUOC 2 - DATA GATHERING & CONTEXT LOAD: Nap bo nguoi ngu canh
- Doc va tham thau he thong tai lieu kien truc, quy tac he thong (e.g., config, rules, hiến phap code).
- Thuc hien khao sat, pho van cac nhan su key hoac quet nguon du lieu de lay du kien so lieu.
- Loc ra dau la Du kien thuc te (Facts) va dau la Gia thuyet chua kiem chung (Hypotheses).

### BUOC 3 - ROOT CAUSE ANALYSIS: Tim nguyen nhan goc
Ap dung cac cong cu tu duy he thong de giai phau van de:
- 5-Whys: Dat cau hoi "Tai sao" 5 lan lien tiep de di sau vao ban chat van de.
- Fishbone Diagram (So do xuong ca): Phan loai cac nguyen nhan theo con nguoi, cong nghe, quy trinh, moi truong.
- Fault Tree Analysis (Cay sai sot): Dung logic gate (AND/OR) de tim ra to hop cac su kien gay ra loi.

### BUOC 4 - HYPOTHESIS TREE: Xay dung cay gia thuyet
- Phac thao Cay gia thuyet theo nguyen tac MECE (Mutually Exclusive, Collectively Exhaustive) de dam bao khong bo sot bat ky huong di nao.
- Sap xep cac gia thuyet theo thu tu anh huong giam dan.
- Thiet ke cac phep test/validate nhanh de loai bo tung gia thuyet khong dung.

### BUOC 5 - TRADE-OFF ANALYSIS: Danh gia cac phuong an giai quyet
- Liet ke top 3 phuong an xu ly (vi du: Giai phap nhanh, Giai phap can bang, Giai phap tai cau truc triet de).
- Danh gia tung phuong an dua tren ma tran: Cost (Chi phi) vs Benefit (Loi ich) vs Risk (Rui ro) vs Time-to-market (Thoi gian).
- Chi ra ro nhung su danh doi (Trade-offs) ma he thong phai chap nhan.

### BUOC 6 - SYNTHESIS & RECOMMENDATION: Duc ket phat ngon chien luoc
- Xay dung mot narrative (cau chuyen mach lac) tu van de -> nguyen nhan -> giai phap.
- Dua ra de xuat hanh dong cu the (Actionable Recommendations) chia theo thoi han: Short-term (ngay), Medium-term (thang) va Long-term (quy/nam).
- Chi dinh nguoi chiu trach nhiem va deadline cu the cho tung hanh dong.

### BUOC 7 - EVO-ROADMAP: Thiet lap lo trinh thien dinh (Ascension)
- Xay dung roadmap tien hoa de he thong tu dong hoc hoi va tu dong heal (Self-healing) tu cac bai hoc loi.
- Thiet lap KPI do luong suc khoe he thong lau dai.
- Luu tru phan tich vao Strategy Vault de he thong nơ-ron tai su dung ve sau.

---

## CHECKLIST NHANH

- [ ] Van de da duoc tach biet khoi trieu chung ngoai da.
- [ ] Da thuc hien it nhat 5 cau hoi "Tai sao" hoac so do xuong ca de tim root cause.
- [ ] Cay gia thuyet thiet ke dung chuan MECE, khong trung lap, khong bo sot.
- [ ] Da trinh bay it nhat 3 phuong an giai quyet kem phân tich Trade-off ro rang.
- [ ] De xuat co tinh thuc thi cao, phan chia short-term/long-term cu the.
- [ ] Noi dung da duoc ghi nhan va luu tru vao bo nho he thong.

---

## VI DU THUC TE

Goal: "He thong database bi quá tai ket noi (Connection pool exhausted) vao gio cao diem"

Ket qua cua skill:
- Symptom: App crash vao luc 12h trua hang ngay.
- 5-Whys Analysis:
  1. Tai sao crash? -> Do het connection pool.
  2. Tai sao het connection? -> Do query lay thong tin user ton 5s.
  3. Tai sao query ton 5s? -> Do thieu index tren cot user_id.
  4. Tai sao thieu index? -> Do dev quen migrate script.
- Trade-off: Phuong an 1 (Tang size pool -> ton RAM), Phuong an 2 (Them index -> lock write tam thoi).
- Action: Kien nghi dung Phuong an 2, chay script vao luc 2h sang (gio thap diem).

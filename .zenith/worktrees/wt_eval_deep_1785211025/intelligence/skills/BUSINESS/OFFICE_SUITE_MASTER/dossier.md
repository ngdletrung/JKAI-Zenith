# DOSSIER: SKILL_ZENITH_OFFICE_MASTER
# Bo Toan Thu Ky Van Phong Zenith

---

## IDENTITY

Ten ky nang    : SKILL_ZENITH_OFFICE_MASTER
Phan loai      : BUSINESS / Document Engineering
Phien ban      : 2.0
Ngon ngu xu ly : Tieng Viet, Tieng Anh
Dau ra chinh   : Word (.docx), Excel (.xlsx), PDF, PowerPoint (.pptx)
Mo ta ngan     : Kien tao va bien tap tat ca cac loai van ban hanh chinh, to trinh, bao cao
                 thuyet minh du an, bang luong, bao cao tai chinh voi dinh dang nang cao
                 va kien truc bang bieu chuyen nghiep tren Word va Excel.

---

## KICH HOAT KHI

- Nguoi dung can tao, chinh sua hoac xu ly cac file Word (.docx), Excel (.xlsx), PDF, PowerPoint (.pptx).
- Chuyen doi tu tai lieu tho (Markdown/Text) sang file dinh dang dep mat cho doanh nghiep.
- Xu ly cac bang tinh luong, bao cao doanh thu, bieu do doanh so phuc tap trong Excel.
- Yeu cau tao to trinh, bao cao thuyet minh du an lon co dinh dang cover page, page number, header/footer.
- Nguoi dung su dung cum tu: "tao file docx", "xuat file excel", "chinh sua bao cao", "lam slide pptx".

---

## QUY TRINH CHI TIET

### BUOC 1 - BRIEF: Nhan dien nhu cau & dac ta dau ra
- Xac dinh loai tai lieu phai kien tao: Word (.docx), Excel (.xlsx) hay Slide (.pptx).
- Thu thap tat ca du lieu dau vao (so lieu tho, danh sach doi tuong, bang bieu phat thao).
- Xac dinh brand guideline cua doi tac (font chu, bang mau, logo) de dong nhat visual.
- Neu thieu thong tin: dat cau hoi lam ro ve so luong tab (Excel) hoac so trang du kien (Word).

### BUOC 2 - PARSING: Chuan hoa va cau truc hoa du lieu
- Chuyen doi du lieu tho thanh cac cau truc JSON hoac Dataframe trong Python de de dang thao tac.
- Tach rieng noi dung chu viet, so lieu thong ke, va cac cong thuc tinh toan (doi voi Excel).
- Loc bo cac ky tu loi, format khong dong nhat khoi nguon du lieu goc.

### BUOC 3 - TEMPLATE: Ap dung thiet lap khung
- Word: Dat margin le trai 3cm, le phai 2cm, le tren 2.5cm, le duoi 2.5cm. Font Arial/Calibri 11-12pt.
- Excel: Bat che do gridlines mac dinh, thiet lap font chu Calibri 11pt cho data, 11pt Bold cho headers.
- Tao trang bìa (Cover Page) doi voi cac bao cao Word > 5 trang (gom ten du an, ten tac gia, logo, ngay thang).

### BUOC 4 - CORE WRITING: Trien khai chi tiet noi dung
- Word:
  - Setup he thong Heading 1 (18pt Bold), Heading 2 (14pt Bold), Heading 3 (12pt Bold/Italic).
  - Tu dong chen muc luc (Table of Contents) o trang thu hai.
  - Setup Header (Tieu de du an, le phai) va Footer (So trang, dang trang X/Y o le phai).
- Excel:
  - To mau header bang chu (Background color navy blue/dark grey, chu trang Bold).
  - Dinh dang so (Number format): ngan cach hang nghin bang dau phay (e.g., 1,000,000) hoac dung VND.
  - Them cac cong thuc tinh toan dung: SUM, AVERAGE, VLOOKUP, IF.

### BUOC 5 - VISUALIZATION: Tich hop bieu do va bang bieu
- Chuyen cac bang so lieu kho khan thanh bieu do cot (Bar), bieu do duong (Line) hoac bieu do tron (Pie).
- Chen bieu do truc tiep vao file Word hoac sheet rieng trong Excel, dat ten bieu do ro rang.
- Dinh dang bang bieu trong Word: vien den mong, header bang mau xam nhe, canh le giua cac o.

### BUOC 6 - QUALITY CONTROL: Kiem tra the thuc va loi XML
- Chay thu nghiem mo file bang Python de kiem tra co bi loi corruption file hay khong.
- Kiem tra tinh trang gop o (Merged Cells) trong Excel, tranh loi gop o lam mat data khi lap lap.
- Doc luot lai Word de dam bao khong co heading bi co doc cuoi trang (orphan headings).

### BUOC 7 - EXPORT: Xuat ban va luu tru he thong
- Export file ra dung ten dinh dang: [ZENITH]-[LoaiFile]-[TenDuAn]-[NamThang].extension.
- Luu tru phien ban goc (.docx/.xlsx) va phien ban doc (.pdf) de phong tranh mat mat du lieu.
- Ban giao link hoac file dinh kem cho nguoi dung cung voi message huong dan cach doc.

---

## CHECKLIST NHANH

- [ ] Margins da dat chuan (Times New Roman hoac Arial/Calibri).
- [ ] Header/Footer da co tieu de va so trang danh dung dinh dang.
- [ ] Excel headers da co mau nen noi bat va chu in dam.
- [ ] So lieu trong Excel da duoc dinh dang ngan cach hang nghin.
- [ ] Da tao Muc luc tu dong doi voi van ban Word > 5 trang.
- [ ] Test mo file thanh cong, khong bi loi XML/corruption.
- [ ] Dat ten file dung quy tac dat ten cua he thong Zenith.

---

## VI DU THUC TE

Goal: "Tao file Word bao cao khao sat thi truong bat dong san Q2 2026 gui Ban Giam Doc"

Ket qua xu ly cua skill:
- Tao file `ZENITH-DOCX-BaoCaoBDSSQ2-202606.docx` co trang bia bat mat.
- Heading 1: "I. TONG QUAN THI TRUONG Q2/2026", "II. PHAN TICH CHI TIET PHAN KHUC".
- Chen bang so lieu gia ca bat dong san va bieu do cot the hien xu huong tang truong.
- Footer hien thi: "Trang 1/12", Header hien thi: "Bao cao Khao sat BDS - Zenith".

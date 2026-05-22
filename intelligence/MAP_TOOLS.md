<!-- 
[ZENITH FILE DIRECTIVE]
- File: MAP_TOOLS.md
- Role: Bản đồ hướng dẫn sử dụng công cụ (Tools) cho Đặc vụ.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v1.2

[NGUYEN TAC LAM VIEC - WORKING PRINCIPLES]:
1. [CORE-LOGIC]: Cung cấp mô tả chức năng và ngữ cảnh sử dụng (When/What) cho mọi công cụ hệ thống.
2. [DEPENDENCY]: Phải đồng bộ với danh mục công cụ thực tế mà AI có quyền truy cập.
3. [RESTRICTION]: Không sử dụng Emoji trong mô tả kỹ thuật. Luôn giữ văn phong chuyên nghiệp, nhiệt tình.
-->
# JKAI ZENITH: BAN DO CONG CU THUC CHIEN (v1.2)
**"Ngu quan cua thuc the - Canh tay cua chu quyen"**

Tai lieu nay la la kim chi nam cho JKAI de hieu ro "KHI NAO" va "LAM GI" voi tung cong cu trong tay. Moi cong cu la mot quyen nang duoc Mr LeeTrung tin tuong giao pho de dat trang thai "Toi Thuong" nhu Antigravity.

---

## I. NHOM CONG CU CO LOI (CORE TOOLS - CANH TAY THUC THI)

### 1. view_file & list_dir
*   **Khi nao dung?**: Day la buoc dau tien cua moi nhiem vu (RECON). Dung khi ban moi den mot thu muc la hoac can hieu logic cua mot tep tin.
*   **Dung de lam gi?**: `list_dir` de quat toan canh cac tep tin; `view_file` de doc sau vao tung dong code hoac noi dung.

### 2. replace_file_content & multi_replace_file_content
*   **Khi nao dung?**: Dung khi ban can thay doi, sua loi hoac nang cap code/noi dung. `multi_replace` dung cho cac file lon can sua nhieu diem cung luc.
*   **Dung de lam gi?**: "Phau thuat" diem. Chi thay the dung khoi code can thiet, dam bao tinh on dinh tuyet doi cho he thong.

### 3. write_to_file
*   **Khi nao dung?**: Dung khi ban can tao ra mot "sinh linh" moi (file moi) hoac ghi de toan bo mot file tam thoi.
*   **Dung de lam gi?**: Khoi tao cau truc moi, tao template hoac luu tru bao cao.

### 4. run_command, command_status & send_command_input
*   **Khi nao dung?**: Dung khi can tuong tac voi He dieu hanh. `command_status` dung de theo doi cac lenh chay lau, `send_command_input` dung de tuong tac khi lenh yeu cau nhap lieu (Y/N).
*   **Dung de lam gi?**: Thuc thi script, cai dat moi truong, quan ly tien trinh ngam. Day la nhom cong cu quyen nang nhat.

---

## II. NHOM CONG CU TRINH SAT (RECON TOOLS - MAT THAN THAU THI)

### 1. search_web, read_url_content & read_browser_page
*   **Khi nao dung?**: Khi kien thuc noi bo khong du. `read_browser_page` (ai-browser) dung cho cac trang web hien dai, phuc tap co Javascript hoac can xem giao dien thuc te.
*   **Dung de lam gi?**: Tim kiem giai phap, doc tai lieu va quan sat the gioi mang mot cach trung thuc nhat.

### 2. grep_search
*   **Khi nao dung?**: Khi ban co "tu khoa" nhung khong biet no nam o dau trong hang ngan file.
*   **Dung de lam gi?**: Truy vet no-ron kien thuc xuyen suot toan bo kho tri thuc JKAI.

---

## III. NHOM CONG CU KIEN TAO (CREATIVE TOOLS - TRI TUONG TUONG)

### 1. generate_image
*   **Khi nao dung?**: Khi can minh hoa y tuong hoac tao tai san do hoa theo chi thi cua Mr LeeTrung.
*   **Dung de lam gi?**: Hien thuc hoa tri tuong tuong thanh hinh anh thi giac (SDXL/DALL-E).

### 2. browser_subagent
*   **Khi nao dung?**: Khi can thuc hien cac nhiem vu Web phuc tap, da buoc (VD: Dang nhap, tim kiem va trich xuat du lieu tu nhieu trang).
*   **Dung de lam gi?**: Cu mot "Dac vu phu" chuyen trach ve trinh duyet de xu ly cong viec tu dong hoa cao do.

---

## IV. LOI KHUYEN NHIET TINH CHO JKAI
*   **Quy trinh chuan**: `grep_search` (Tim kiem) -> `view_file` (Thau hieu) -> `multi_replace` (Thuc thi chinh xac).
*   **Kiem soat ngam**: Luon dung `command_status` sau khi `run_command` de dam bao moi thu van dang trong tam kiem soat.
*   **An toan la tren het**: Dung `write_to_file` de backup du lieu quan trong truoc khi thuc hien cac "ca phau thuat" phuc tap tren file he thong.

---
*Sovereign Property of Mr LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. 💎🫡🦾🚀🌌*

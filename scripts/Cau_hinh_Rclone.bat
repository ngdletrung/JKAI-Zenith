@echo off
title JKAI Zenith - Cấu hình Kết nối Rclone
CHCP 65001 > nul
echo =====================================================================
echo ⚡ ĐANG KHỞI ĐỘNG RClONE ĐỂ THIẾT LẬP KẾT NỐI ĐÁM MÂY (GOOGLE/MICROSOFT)...
echo =====================================================================
echo.
echo [HƯỚNG DẪN]:
echo 1. Nhập 'n' để tạo kết nối mới (New remote).
echo 2. Đặt tên gợi nhớ (Ví dụ: my-gdrive, my-onedrive).
echo 3. Chọn số tương ứng với dịch vụ (Ví dụ: Google Drive là 18, OneDrive là 32 tùy phiên bản).
echo 4. Khi Rclone hỏi dùng trình duyệt để đăng nhập, chọn 'y' (Yes).
echo 5. Trình duyệt sẽ mở, bạn đăng nhập tài khoản của mình và nhấn 'Cho Phép'.
echo.
echo Bấm phím bất kỳ để bắt đầu cấu hình...
pause > nul
data\rclone.exe --config data\rclone\rclone.conf config

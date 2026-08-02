# ⚡ HARDWARE TUNING: AMD ROCm & VRAM OPTIMIZATION 🏎️

Tài liệu này cung cấp các bí thuật để JKAI Zenith vận hành mượt mà trên hạ tầng phần cứng của Master, đặc biệt là tối ưu hóa cho AMD Radeon RX 6600.

## 🏎️ 1. CẤU HÌNH GPU (AMD RADEON RX 6600 - 8GB VRAM)
- **ROCm Integration**: Sử dụng nền tảng ROCm để tận dụng sức mạnh tính toán song song của nhân AMD.
- **VRAM Budgeting**: 
    - **GPU Primary**: Dành riêng cho Model thực thi (Gemma 4/SDXL). Giới hạn VRAM sử dụng ở mức 7.2GB để tránh tràn bộ nhớ.
    - **RAM Fallback**: Các Model nhẹ (Lễ tân/Điều phối) được nạp vào RAM hệ thống để giữ cho GPU luôn "Sạch".

## 🛠️ 2. TINH CHỈNH OLLAMA & ENGINE
- **Num_Ctx (Context Window)**: Luôn giữ ở mức **4096**. Việc tăng quá cao sẽ làm tiêu tốn VRAM theo cấp số nhân và gây lag Dashboard.
- **Layers Offloading**: Chỉnh định số lớp (Layers) nạp vào GPU sao cho khớp 100% với dung lượng VRAM hiện có.
- **Keep-Alive**: Thiết lập thời gian sống của Model trên GPU là 5 phút để tối ưu hóa tốc độ phản hồi cho các yêu cầu liên tục.

## ❄️ 3. QUẢN TRỊ NHIỆT & HIỆU NĂNG
- **Cooling Priority**: Khi chạy các tác vụ nặng (Stable Diffusion), hệ thống phải ý thức được nhiệt độ của card đồ họa.
- **Hybrid Processing**: Tận dụng CPU cho các tác vụ Logic và Regex để giảm tải cho các nhân xử lý AI trên GPU.

---
*PHẦN CỨNG MẠNH MẼ - PHẦN MỀM TINH ANH!* 💎🫡🦾🚀🌌

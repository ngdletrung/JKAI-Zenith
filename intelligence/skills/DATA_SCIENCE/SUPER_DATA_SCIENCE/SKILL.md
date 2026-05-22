---
id: SUPER_DATA_SCIENCE
name_vn: "Siêu Năng Lực Khoa Học Dữ Liệu"
version: 5.0.0
author: "Antigravity Forge"
domain: DATA_SCIENCE
intent_pairs:
  - ["ANALYZE", "DATA"]
  - ["TRAIN", "AI"]
aliases_vn: ["phân tích dữ liệu", "auto ml", "thị giác máy tính", "khoa học dữ liệu", "data science elite"]
schema:
  parameters:
    type: object
    properties:
      action: { type: string, enum: ["phan_tich_du_lieu_elite", "huan_luyen_ai_cap_toc", "thi_giac_may_tinh"], description: "Hành động khoa học dữ liệu." }
      data_path: { type: string, description: "Đường dẫn đến tệp dữ liệu." }
      image_path: { type: string, description: "Đường dẫn đến tệp ảnh (cho Computer Vision)." }
    required: ["action"]
priority: HIGH
related_skills: ["NEURAL_LINK_AGGREGATOR", "NEURAL_SANDBOX_STAGING"]
---

# 📊 SIÊU NĂNG LỰC KHOA HỌC DỮ LIỆU (SUPER_DATA_SCIENCE)

## 🌟 TỔNG QUAN
Đây là nơ-ron đa năng, chịu trách nhiệm xử lý các tác vụ phức tạp về toán học và dữ liệu. Nó bao hàm 3 trụ cột sức mạnh:
1. **Phân tích Ưu việt**: Tự động rà soát, thống kê và phát hiện xu hướng trong các tập dữ liệu lớn.
2. **AutoML & Training**: Huấn luyện cấp tốc các mô hình AI để dự báo tương lai.
3. **Thị giác Máy tính**: Nhận diện và phân tích đối tượng trong hình ảnh với độ chính xác tuyệt đối.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Thẩm định Tệp tin**: Đảm bảo tệp dữ liệu (CSV/Excel) hoặc hình ảnh tồn tại và hợp lệ.
2. **Xác định Mục tiêu**: Lựa chọn thuật toán phù hợp nhất (Phân loại, Hồi quy, hoặc Nhận diện).

### 🚀 Phase 2: Action (Thực thi)
1. **Phẫu thuật Dữ liệu**: Thực hiện tính toán các thông số thống kê vĩ mô và xử lý dữ liệu thiếu.
2. **Huấn luyện Mô hình**: Kích hoạt tiến trình huấn luyện mô hình AI chuân Elite.
3. **Đúc kết Báo cáo**: Xuất kết quả dưới dạng JSON minh bạch để Master dễ dàng nắm bắt.

---
## ⚖️ LUẬT DỮ LIỆU (DATA LAWS)
- **Tính Chính xác**: Tuyệt đối không được bỏ sót các biến số quan trọng.
- **Tính Hiệu quả**: Luôn chọn con đường tính toán ngắn nhất để tiết kiệm tài nguyên.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Đường dẫn tệp tin không chính xác khiến nơ-ron bị lỗi.
- Dữ liệu quá "bẩn" hoặc thiếu hụt nghiêm trọng dẫn đến kết quả phân tích sai lệch.

---
*DỮ LIỆU LÀ MÁU CỦA ĐẾ CHẾ!* 💎🦾

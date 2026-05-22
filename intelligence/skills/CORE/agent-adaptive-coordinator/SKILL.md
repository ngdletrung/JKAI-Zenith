---
id: AGENT-ADAPTIVE-COORDINATOR
name_vn: "Điều phối Đặc vụ Thích ứng"
version: 2.0.0
author: "Antigravity Forge"
domain: AI_AGENT
intent_pairs:
  - ["COORDINATE", "AGENTS"]
  - ["MANAGE", "SWARM"]
aliases_vn: ["điều phối đặc vụ", "adaptive coordinator", "quản lý swarm"]
schema:
  parameters:
    type: object
    properties:
      task_description: { type: string, description: "Mô tả nhiệm vụ cần điều phối." }
      agent_list: { type: array, items: { type: string }, description: "Danh sách các đặc vụ tham gia." }
    required: ["task_description"]
priority: HIGH
related_skills: ["PLANNER_ELITE", "SWARM_MANAGEMENT"]
---

# 🏛️ ĐIỀU PHỐI ĐẶC VỤ THÍCH ỨNG (AGENT-ADAPTIVE-COORDINATOR)

## 🌟 TỔNG QUAN
Kỹ năng này chịu trách nhiệm điều phối sự phối hợp giữa các Đặc vụ trong một Swarm (Bầy đàn), đảm bảo các nhiệm vụ được phân bổ một cách thông minh và tối ưu dựa trên năng lực của từng thực thể.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Phân tích Nhiệm vụ**: Thấu hiểu mục tiêu vĩ mô từ `task_description`.
2. **Kiểm kê Nguồn lực**: Kiểm tra trạng thái sẵn sàng của các đặc vụ trong `agent_list`.

### 🚀 Phase 2: Action (Thực thi)
1. **Triệu hồi `adaptive_coordinator`**: Phân chia nhiệm vụ và thiết lập kênh liên lạc giữa các đặc vụ.
2. **Giám sát Swarm**: Theo dõi tiến độ và tự động điều chỉnh nếu có Đặc vụ gặp sự cố.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Phân bổ quá nhiều đặc vụ cho một tác vụ đơn giản gây nhiễu nơ-ron.
- Thiếu cơ chế đồng bộ dữ liệu giữa các đặc vụ Alpha và Beta.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾

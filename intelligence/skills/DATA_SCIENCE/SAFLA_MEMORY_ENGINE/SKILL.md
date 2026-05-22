---
id: SAFLA_MEMORY_ENGINE
name_vn: "Cỗ Máy Bộ Nhớ Tự Thức SAFLA"
version: 4.4.0
author: "Antigravity Forge"
domain: DATA_SCIENCE
intent_pairs:
  - ["ASSIMILATE", "MEMORY"]
  - ["RECALL", "EXPERIENCE"]
aliases_vn: ["bộ nhớ tự thức", "safla memory", "truy hồi ký ức", "ghi nhớ trải nghiệm"]
schema:
  parameters:
    type: object
    properties:
      action: { type: string, enum: ["assimilate", "recall", "forge_concept"], description: "Hành động bộ nhớ." }
      text: { type: string, description: "Nội dung cần ghi nhớ hoặc query truy hồi." }
      tier: { type: string, enum: ["episodic", "semantic"], default: "episodic", description: "Tầng bộ nhớ (Sự kiện hoặc Khái niệm)." }
    required: ["action"]
priority: HIGHEST
related_skills: ["NEURAL_LINK_AGGREGATOR", "GLOBAL_SYSTEM_CONTEXT"]
---

# 🧠 CỖ MÁY BỘ NHỚ TỰ THỨC SAFLA (SAFLA_MEMORY_ENGINE)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Ký ức" của Zenith. Nó sử dụng thuật toán **Self-Aware Feedback Loop** để quản trị bộ nhớ đa tầng:
1. **Episodic Memory**: Ghi nhớ các sự kiện, nhiệm vụ đã qua.
2. **Semantic Memory**: Chưng cất các trải nghiệm thành các khái niệm và quy luật vĩnh cửu.
Mọi ký ức đều được Vector hóa và lưu trữ tại Thần điện Qdrant để truy hồi tức thì với độ chính xác tuyệt đối.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Định vị Tầng Ký ức**: Xác định thông tin thuộc về sự kiện nhất thời hay tri thức vĩnh cửu.
2. **Vector Hóa**: Chuyển đổi ngôn ngữ tự nhiên thành các nơ-ron số (Embeddings).

### 🚀 Phase 2: Action (Thực thi)
1. **Nhập Tâm (Assimilate)**: Khắc ghi ký ức vào Qdrant kèm theo dấu ấn thời gian và bối cảnh.
2. **Truy Hồi (Recall)**: Lục tìm trong kho tàng ký ức để tìm ra những trải nghiệm tương đồng nhằm hỗ trợ Master ra quyết định.
3. **Đúc Kết Khái Niệm (Forge)**: Tự động tổng hợp các sự kiện rời rạc thành một quy luật logic mới.

---
## ⚖️ LUẬT KÝ ỨC (MEMORY LAWS)
- **Tính Chính xác**: Tuyệt đối không được xuyên tạc ký ức gốc của Master.
- **Tính Tiến hóa**: Luôn nỗ lực chưng cất sự kiện thành quy luật để hệ thống ngày càng thông minh hơn.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Qdrant Offline khiến nơ-ron bị "mất trí nhớ" tạm thời.
- Nhập tâm quá nhiều dữ liệu rác gây nhiễu loạn luồng truy hồi.

---
*GHI NHỚ ĐỂ TRƯỜNG TỒN!* 💎🦾

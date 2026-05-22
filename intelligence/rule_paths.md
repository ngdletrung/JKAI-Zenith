# 🧬 JKAI ZENITH: GIAO THỨC TỌA ĐỘ (RULE_PATHS) v1.1
> "Nhất thể hóa không gian, vạn vật quy về một mối."

## 🏛️ 1. Hệ Tọa độ Cốt lõi (Core System Paths)
| Tọa độ (Variable) | Giá trị (Path) | Security | Ghi chú |
| :--- | :--- | :--- | :--- |
| **WORKSPACE_ROOT** | `d:\Docker\N8N` | YELLOW | Gốc rễ của đế chế JKAI. |
| **SERVICES_CORE** | `d:\Docker\N8N\services` | GREEN | Toàn bộ mã nguồn dịch vụ lõi. |
| **SYSTEM_CORE** | `d:\Docker\N8N\core` | GREEN | Thư viện nhân hệ thống. |
| **ENV_FILE** | `.env` | GREEN | Biến môi trường nhạy cảm. |
| **DOCKER_CFG** | `docker-compose.yml` | GREEN | Cấu hình hạ tầng Docker. |
| **HARDWARE_CFG** | `rule_hardware.md` | GREEN | Cấu hình tài nguyên phần cứng. |
| **SKILLS_REGISTRY** | `registry_Map_skills.json` | GREEN | Danh mục kỹ năng đặc vụ. |
| **GUARDIAN_SCRIPT** | `Zenith_Guardian.ps1` | GREEN | Script khởi động và điều phối. |

---

## 🛠️ 2. Hệ Tọa độ Đặc vụ (Agentic Skill Paths)
| Tọa độ (Variable) | Giá trị (Path) | Tệp tin đang trỏ đến (Referenced by) | Ghi chú |
| :--- | :--- | :--- | :--- |
| **VAULT_TEMPLATES** | `D:/Docker/N8N/intelligence/vault/templates` | `skill_template_mimic/logic.py` | Kho lưu trữ Blueprint. |
| **FILES_INPUT** | `D:/Docker/N8N/workspace/inputs` | `skill_Hueic_tao_skill_de_xuat_theo_form` | Vùng đệm dữ liệu đầu vào. |
| **FILES_OUTPUT** | `D:/Docker/N8N/workspace/outputs` | `skill_zenith_office_master/logic.py` | Kết xuất văn bản Elite. |
| **HUEIC_FORGE_ROOT** | `D:/Docker/N8N/intelligence/skills/skill_Hueic_tao_skill_de_xuat_theo_form` | Forge Core | Xưởng đúc kỹ năng HUEIC Tầng 0. |
| **KNOWLEDGE_BASE** | `d:\Docker\N8N\intelligence\knowledge` | Toàn bộ hệ thống | Kho tàng tri thức Zenith. |

---

## 🧪 3. Giao thức Truy xuất (Access Protocol)
> [!IMPORTANT]
> **Tuyệt đối không được Hardcode đường dẫn.** 
> Mọi Đặc vụ phải sử dụng `core.utils.path_manager` để truy xuất tọa độ.

```python
# Ví dụ:
from core.utils import path_manager
output_path = path_manager.get("FILES_OUTPUT")
```

---

## ☢️ 4. Công cụ Hạt nhân (Nuclear Tools)
Các công cụ này LUÔN yêu cầu xác thực Master.

- `self-destruct`: Tự hủy dữ liệu.
- `supreme_shutdown`: Tắt hệ thống cấp cao.
- `change-sovereign-key`: Thay đổi mật mã chủ quyền.
- `docker_wipe`: Xóa hạ tầng Docker.

---
 
## 🧠 5. Giao thức Tri thức Nhất thể (Knowledge Ingestion)
Danh sách các vùng tri thức được chắt lọc và nạp vào QRank (Qdrant):

### 💎 [ELITE-LIST]: Các thư mục được NẠP (Inclusion)
- `intelligence/rules/`: Toàn bộ quy định, SDS v1.2, Luật phần cứng.
- `intelligence/agents/`: Linh hồn và Personas của các Đặc vụ.
- `intelligence/knowledge/`: Kho tri thức tổng hợp và Wiki.
- `intelligence/patterns/`: Các mẫu thiết kế và giải pháp tối ưu.
- `intelligence/skills/`: Định danh và mô tả năng lực Đặc vụ.
- `intelligence/training/`: Kho báu Vàng ròng (Mẫu tư duy & Lập kế hoạch - Trừ bản thô Universal).
- `core/`: Mã nguồn cốt lõi (Logic nền tảng).
- `services/`: Các dịch vụ nơ-ron (Kiến trúc hệ thống).

### 🚫 [BLACK-LIST]: Các thư mục bị BỎ QUA (Exclusion)
- `archive/`, `.git/`, `__pycache__`, `node_modules/`, `storage/`: Rác/Lịch sử.
- `vault/`: Hạ tầng Map Graph (Không nạp véc-tơ).
- `outputs/`, `reports/`, `proposals/`, `trajectories/`: Dữ liệu biến thiên.
- `training/universal/`: Bản thô chưa tinh luyện và việt hoá trao đổi.
- `datasets/`, `.obsidian/`, `logs/`, `temp/`, `cache/`: Dữ liệu thô/tạm.

---

## ⚡ 6. Giao thức Bộ nhớ Đệm (RAM/Redis Cache)
Các dữ liệu được ưu tiên lưu trữ trong RAM để truy xuất thần tốc (Latency < 10ms):

### 🚀 [HOT-DATA]: Dữ liệu Luôn thường trực
- **Cấu hình Hệ thống**: `.env`, `rule_hardware.md`, `rule_paths.md`.
- **Danh mục Kỹ năng**: `registry_Map_skills.json` (Skill Registry).
- **Bản đồ Xã giao**: `Elite Social Map` (Phản xạ chào hỏi).
- **Session Context**: Lịch sử hội thoại và trạng thái tác vụ hiện hành.

### 🧠 [NEURAL-CACHE]: Bộ nhớ đệm Trí tuệ
- **Embeddings Cache**: Các đoạn véc-tơ đã tính toán (Tránh nạp lại AI).
- **Failure Memory**: Các mẫu thất bại và bài học kinh nghiệm.
- **Manifesto & Identity**: Tuyên ngôn chủ quyền và định danh Đặc vụ.
- **Converter Cache**: Bản dịch Markdown/JSON đã xử lý từ ổ cứng.

## 📁 7. WORKSPACE_ROOT
Đường dẫn gốc cho các không gian làm việc cô lập (Scratch Workspaces). Master có thể thay đổi đường dẫn này để di chuyển dữ liệu sang ổ đĩa khác.

**PATH**: `D:\Docker\N8N\workspaces`
---
*Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence.* 🌌🏛️🔥🦾👑🔗

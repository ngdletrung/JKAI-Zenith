<!-- 
[ZENITH FILE DIRECTIVE]
- File: path_rules.md
- Role: Filesystem Governance & Organization Rules.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v19.9
[WORKING PRINCIPLES]:
1. [STRUCTURE-INTEGRITY]: Tuyệt đối không tạo folder rác ngoài 12 phân khu chính.
2. [RELATIVE-PATHS]: Luôn dùng đường dẫn tương đối để đảm bảo tính di động.
3. [NAMING-ELITE]: Tên file phải tuân thủ chuẩn Snake Case hoặc Uppercase đặc thù.
-->
# 🧬 JKAI ZENITH: GIAO THỨC TỌA ĐỘ (PATH_RULES) v2.0
> "Nhất thể hóa không gian, vạn vật quy về một mối."

## 🏛️ 1. Hệ Tọa độ Cốt lõi (Core System Paths)
| Tọa độ (Variable) | Giá trị (Path) | Security | Ghi chú |
| :--- | :--- | :--- | :--- |
| **WORKSPACE_ROOT** | `d:\Docker\JKAI` | YELLOW | Gốc rễ của hệ thống JKAI. |
| **SERVICES_CORE** | `d:\Docker\JKAI\services` | GREEN | Toàn bộ mã nguồn dịch vụ lõi. |
| **SYSTEM_CORE** | `d:\Docker\JKAI\core` | GREEN | Thư viện nhân hệ thống. |
| **ENV_FILE** | `.env` | GREEN | Biến môi trường nhạy cảm. |
| **DOCKER_CFG** | `docker-compose.yml` | GREEN | Cấu hình hạ tầng Docker. |
| **HARDWARE_CFG** | `rule_hardware.md` | GREEN | Cấu hình tài nguyên phần cứng. |
| **SKILLS_REGISTRY** | `registry_Map_skills.json` | GREEN | Danh mục kỹ năng đặc vụ. |
| **GUARDIAN_SCRIPT** | `Zenith_Guardian.ps1` | GREEN | Script khởi động và điều phối. |

---

## 🛠️ 2. Hệ Tọa độ Không gian Tri thức & Kỹ năng (Knowledge & Skill Coordinates)
| Tọa độ (Variable) | Giá trị (Path) | Tệp tin đang trỏ đến (Referenced by) | Ghi chú |
| :--- | :--- | :--- | :--- |
| **INTELLIGENCE_DIR** | `d:\Docker\JKAI\intelligence` | YELLOW | Thánh địa tri thức tổng thể. |
| **AGENTS_DIR** | `d:\Docker\JKAI\intelligence\agents` | GREEN | Hồ sơ đặc tả vai trò nhận thức Đặc vụ. |
| **SKILLS_DIR** | `d:\Docker\JKAI\intelligence\skills` | GREEN | Thư mục chứa các kỹ năng vật lý thực thi. |
| **CONTEXT_DIR** | `d:\Docker\JKAI\intelligence\context` | GREEN | Bối cảnh tác vụ và trạng thái. |
| **RULES_DIR** | `d:\Docker\JKAI\intelligence\rules` | GREEN | Quy trình SOP và hướng dẫn lập quy. |
| **RULES_SOFTWARE** | `d:\Docker\JKAI\intelligence\rules_software.md` | GREEN | Cấu hình API keys và Base URLs. |
| **KNOWLEDGE_BASE** | `d:\Docker\JKAI\intelligence\wiki` | Toàn bộ hệ thống | Kho tàng tri thức Zenith. |
| **NEURAL_CACHE_DIR** | `d:\Docker\JKAI\intelligence\wiki\neural_cache` | `OMNI_SEARCH_ENGINE/logic.py` | Bộ nhớ đệm nhận thức nơ-ron lưu trữ trên đĩa. |
| **VAULT_DIR** | `d:\Docker\JKAI\intelligence\vault` | `PREMIUM_UI_ENGINE/logic.py` | Vùng lưu trữ dữ liệu hệ thống an toàn. |
| **VAULT_TEMPLATES** | `d:\Docker\JKAI\intelligence\vault\templates` | `skill_template_mimic/logic.py` | Kho lưu trữ Blueprint/Templates. |
| **IMPORT_DUMP_DIR** | `d:\Docker\JKAI\intelligence\archive\import_dump` | `IMPORT_SKILL/logic.py` | Thư mục chứa mã nguồn kỹ năng thô nhập khẩu. |
| **QUARANTINE_DIR** | `d:\Docker\JKAI\intelligence\archive\quarantine` | RED | Cách ly mã nguồn nguy hiểm. |
| **REPORTS_DIR** | `d:\Docker\JKAI\intelligence\reports` | `skill_sovereign_logic/logic.py` | Thư mục lưu trữ báo cáo phân tích chiến lược. |
| **STRATEGIC_LESSONS_FILE** | `d:\Docker\JKAI\intelligence\strategic_lessons.md` | `skill_neural_audit/logic.py` | Nhật ký tiến hóa và các bài học kinh nghiệm hệ thống. |
| **FILES_INPUT** | `d:\Docker\JKAI\files\Import` | `import_pipeline.py` | Vùng đệm dữ liệu đầu vào (drop point cho người dùng). |
| **FILES_DELETE** | `d:\Docker\JKAI\files\Delete` | `import_pipeline.py` | File lỗi/quá ngắn được move vào đây. |
| **FILES_OUTPUT** | `d:\Docker\JKAI\workspace\outputs` | `skill_zenith_office_master/logic.py` | Kết xuất văn bản và tài liệu đầu ra. |
| **WIKI_DIR** | `d:\Docker\JKAI\intelligence\wiki` | `import_pipeline.py` | SSOT Wiki — tri thức tổng hợp. |
| **WIKI_SYSTEM** | `d:\Docker\JKAI\intelligence\wiki\system` | `import_pipeline.py` | Kiến trúc, thiết kế hệ thống. |
| **WIKI_DECISIONS** | `d:\Docker\JKAI\intelligence\wiki\decisions` | `import_pipeline.py` | ADR, quyết định kỹ thuật. |
| **WIKI_BUGS** | `d:\Docker\JKAI\intelligence\wiki\bugs` | `import_pipeline.py` | Bug history + fix. |
| **WIKI_ROADMAP** | `d:\Docker\JKAI\intelligence\wiki\roadmap` | `import_pipeline.py` | Kế hoạch, lộ trình. |
| **WIKI_DEVOPS** | `d:\Docker\JKAI\intelligence\wiki\devops` | `import_pipeline.py` | Docker, CI/CD, deploy. |
| **WIKI_CODING** | `d:\Docker\JKAI\intelligence\wiki\coding` | `import_pipeline.py` | Coding patterns, standards. |
| **WIKI_AI** | `d:\Docker\JKAI\intelligence\wiki\ai` | `import_pipeline.py` | LLM, model, prompt engineering. |
| **WIKI_BUSINESS** | `d:\Docker\JKAI\intelligence\wiki\business` | `import_pipeline.py` | Nghiệp vụ, domain. |
| **WIKI_SECURITY** | `d:\Docker\JKAI\intelligence\wiki\security` | `import_pipeline.py` | Bảo mật. |
| **WIKI_DATA_SCIENCE** | `d:\Docker\JKAI\intelligence\wiki\data_science` | `import_pipeline.py` | Data, ML, quantum. |
| **WIKI_RESEARCH** | `d:\Docker\JKAI\intelligence\wiki\research` | `import_pipeline.py` | Nghiên cứu. |
| **WIKI_FINANCE** | `d:\Docker\JKAI\intelligence\wiki\finance` | `import_pipeline.py` | Tài chính. |
| **WIKI_REFERENCES** | `d:\Docker\JKAI\intelligence\wiki\references` | `import_pipeline.py` | Tài liệu tham khảo ngoài. |

---

## 🧪 3. Giao thức Truy xuất (Access Protocol)
> [!IMPORTANT]
> **Tuyệt đối không được Hardcode đường dẫn.** 
> Mọi Đặc vụ và Kỹ năng phải sử dụng `core.utils.path_manager` để truy xuất tọa độ động.

```python
# Ví dụ truy xuất đường dẫn động:
from core.utils import path_manager
output_path = path_manager.get("FILES_OUTPUT")
```

---

## 🧠 4. Giao thức Tri thức Nhất thể (Knowledge Ingestion)
Danh sách các vùng tri thức được chắt lọc và nạp vào Qdrant:

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
- `wiki/`: Được xử lý riêng bởi Import Pipeline → `jkai_wiki`, không scan chung.

---

*Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence.* 🌌🏛️🔥🦾👑🔗

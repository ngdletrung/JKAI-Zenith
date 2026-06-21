<!-- 
[ZENITH FILE DIRECTIVE]
- File: MAP_INTELLIGENCE.md
- Role: Zenith Intelligence Documentation.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v19.21
[WORKING PRINCIPLES]:
1. [HEADER-FIRST]: Antigravity BAT BUOC phai doc khoi header nay truoc khi thao tac.
2. [SDS-COMPLIANCE]: Moi thay doi phai tuan thu Giao thuc SDS moi nhat.
3. [NO-EMOJI]: Cam dung emoji trong noi dung tep cau hinh va logic.
-->
# 🗺️ JKAI ZENITH: INTELLIGENCE MAP (Mục lục Thần kinh)

> [!TIP]
> Đây là bản đồ dẫn đường cho các Đặc vụ AI truy xuất tri thức hệ thống theo đúng **12 Chỉ mục Chủ quyền (12 Sovereign Indices)**.

---

## 🏛️ 1. HẠT NHÂN BẢN SẮC (CORE IDENTITY)
- **[ZENITH_IDENTITY.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_IDENTITY.md)**: Bản sắc và ý chí tối cao của Master LeeTrung.
- **[ZENITH_MANIFESTO.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_MANIFESTO.md)**: Tầm nhìn AGI và triết lý Sovereign AI.
- **[SUPREME_TRINITY.md](file:///d:/Docker/JKAI/intelligence/identity/SUPREME_TRINITY.md)**: Triết lý Nhất Thể Tam Vị.

---

## 🧬 2. HỆ THỐNG 12 CHỈ MỤC CHỦ QUYỀN (12 SOVEREIGN INDICES)

### 🧩 [INDEX 1] SKILLS (Trình điều khiển)
- **[MAP_SKILLS.md](file:///d:/Docker/JKAI/intelligence/MAP_SKILLS.md)**: Danh mục nơ-ron kỹ năng Elite.
- **Proactive Backend Probe**: Cơ chế chủ động kiểm tra sức khỏe các backend tìm kiếm (Tavily, DDG, Jina, Crawl4AI) trước khi gọi để tránh trễ timeout.
- **Context Engineering**: Tự động quản lý bối cảnh và dọn dẹp token dư thừa thưa Master (ID: #4007).
- **Source-Driven Development**: Tự động tra cứu tài liệu hướng dẫn chính thức trước khi code (ID: #4008).
- **[BATCH ASSIMILATION - agent-skills v1.0]**: 22 ky nang duoc dong hoa tu du an agent-skills (Addy Osmani), phan loai theo domain:
  - **CORE (#1083-1085)**: Using Agent Skills, Interview Me, Doubt-Driven Development.
  - **DEVOPS (#3502-3512)**: Incremental Implementation, TDD, Frontend UI Engineering, API Design, Browser DevTools, Debugging, Git Workflow, CI-CD, Deprecation, Observability, Shipping.
  - **RESEARCH (#4009-4012)**: Idea Refine, Spec-Driven Development, Planning & Task Breakdown, Documentation & ADRs.
  - **SECURITY (#6015-6018)**: Code Review & Quality, Code Simplification, Security & Hardening, Performance Optimization.
  - **Sovereign Governance (#4007-4008)**: Context Engineering, Source-Driven Development (da dang ky o tren).
  - **Tong so ky nang tu dong hoa**: 24 ky nang (2 da co + 22 moi).
  - **Ban quyen**: MIT License - Addy Osmani. Xem chi tiet tai LICENSES/agent-skills-MIT.txt va NOTICE.md.
- **[SSM UNIVERSAL SKILL AUTO-ACTIVATION - v10.4]**: Hệ thống tự động nhận diện ý định và kích hoạt skill phù hợp:
  - **SemanticSkillMatcher** (`core/utils/semantic_skill_matcher.py`): Token-overlap engine quét 163 skill, score >= 0.40 thì inject dossier.md vào context. TP=88%, FP=0%.
  - **Hook 3 tầng**: `dispatcher.py` (threshold=0.40) → `ingress_skill_gate.py` → `receptionist_core.py` (threshold=0.42).
  - **Trigger Enrichment**: Từ 108 skill có `triggers=0` xuống còn 8. 84 skill sync từ manifest, 132 skill được enrich manual triggers.
  - **Registry**: `intelligence/registry_Map_skills.json` là SSoT cho trigger data.
- **[NON-TECHNICAL SKILL DOSSIERS ENRICHMENT - v10.5]**: Hoàn chỉnh 14 tệp dossier.md cho các kỹ năng phi-technical (Executive Forge, Strategic Writer, Presentation, Office Master, Marketing, Viral, Brand, Social, SEO, Email, Copywriting, PR & Crisis, v.v.) đạt chuẩn độ dài 80-120 dòng với cấu trúc 7 bước chi tiết. Đồng bộ đường dẫn vật lý phù hợp với Registry mapping.
- **[SKILL COMPLIANCE ALIGNMENT - v10.6]**: Cập nhật và chuẩn hóa cấu trúc kỹ năng `CODE_REVIEW_AND_QUALITY` theo chuẩn 5-file Elite của Zenith. Đồng bộ YAML header trong SKILL.md, thiết lập hàm `execute` chuẩn trong logic.py, điều hướng và tái cấu trúc tệp dossier.md.

### 🧩 [INDEX 2] AGENTS (Đặc vụ)
- **[ZENITH_AGENT_PROFILES.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_AGENT_PROFILES.md)**: Đặc tả vai trò và linh hồn Đặc vụ.

### 🧩 [INDEX 3] RULES (Quy chế)
- **[ZENITH_SOVEREIGN_RULES.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_SOVEREIGN_RULES.md)**: Hiến chương vận hành và bảo mật JKAI.

### 🧩 [INDEX 4] KNOWLEDGE (Tri thức VFS)
- **[ZENITH_KNOWLEDGE_SPEC.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_KNOWLEDGE_SPEC.md)**: Đặc tả hệ tệp ảo ngữ nghĩa và Vector DB.
- **Cognitive Distillation (Hệ tiêu hóa)**: Cơ chế chưng cất tri thức 3 tầng (RAM/QRank BM25-CP/MapGraph) tích hợp tại `receptionist_core.py` và các Skill tìm kiếm để tối ưu hóa trích xuất ngữ cảnh.
- **Wiki SSOT (`intelligence/wiki/`)**: Single Source of Truth cho tri thức wiki. Gồm 13 phân khu: `system`, `decisions`, `bugs`, `roadmap`, `devops`, `coding`, `ai`, `business`, `security`, `data_science`, `research`, `finance`, `references`. Dữ liệu cũ từ `knowledge/` và `vault/01_Knowledge/` đã được migration vào đây.
- **Sync Pipeline (`core/tools/sync_pipeline.py`)**: Unified pipeline 8 phases: `migrate` → `import` → `assimilate` → `knowledge_brain` → `distill` → `rag_ingest` → `registry` → `cleanup`. Gọi qua `/sync` hoặc auto-trigger khi phát hiện file mới trong `files/Import/`.
- **Import Pipeline (`core/tools/import_pipeline.py`)**: Xử lý file từ `files/Import/` → detect category (13 loại) → chunk/embed → upsert Qdrant `jkai_wiki` → move vào `intelligence/wiki/{category}/`. File lỗi → `files/Delete/`.
- **Path Governance**: Mọi đường dẫn được định nghĩa trong `intelligence/path_rules.md` và truy xuất qua `core.utils.path_manager`. Tuyệt đối không hardcode path.

### 🧩 [INDEX 5] PROMPTS (Tập lệnh ISA)
- **[ZENITH_PROMPT_ISA.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_PROMPT_ISA.md)**: Kiến trúc tập lệnh tư duy.

### 🧩 [INDEX 6] COMMANDS (Siêu lệnh)
- **[MAP_COMMANDS.md](file:///d:/Docker/JKAI/intelligence/MAP_COMMANDS.md)**: Danh mục lệnh Terminal.

### 🧩 [INDEX 7] TOOLS (Kết nối API)
- **[MAP_TOOLS.md](file:///d:/Docker/JKAI/intelligence/MAP_TOOLS.md)**: Danh mục công cụ ngoại vi.

### 🧩 [INDEX 8] PROTOCOLS (Giao thức)
- **[ZENITH_SOVEREIGN_OPERATIONS.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_SOVEREIGN_OPERATIONS.md)**: Quy trình tác chiến 6 giai đoạn.
- **[Homunculus Manager](file:///d:/Docker/JKAI/core/homunculus/manager.py)**: Hạ tầng quản lý vùng làm việc dự án riêng biệt.

### 🧩 [INDEX 9] TRAINING (Huấn luyện)
- **Thư mục `/data/training/`**: Phân vùng nén kinh nghiệm và ML Compiler.

### 🧩 [INDEX 10] VAULT (Bộ nhớ đệm L1)
- **[ZENITH_VAULT.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_VAULT.md)**: Thanh ghi phiên và cache tác vụ.

### 🧩 [INDEX 11] HISTORY (Lịch sử tiến hóa)
- **[GLOBAL_SYSTEM_CONTEXT.md](file:///d:/Docker/JKAI/intelligence/identity/GLOBAL_SYSTEM_CONTEXT.md)**: Nhật ký tiến hóa và kiểm toán hệ thống.

### 🧩 [INDEX 12] HARDWARE (Lớp vật lý)
- **[ZENITH_INFRASTRUCTURE_SPEC.md](file:///d:/Docker/JKAI/intelligence/identity/ZENITH_INFRASTRUCTURE_SPEC.md)**: Đặc tả hạ tầng và định tuyến phần cứng.

---

## ⚠️ VÙNG TẠM THỜI (TEMPORARY ZONE)
- **/intelligence/archive/**: Phân vùng lưu trữ tệp cũ chờ xóa hoặc kỹ năng mới chờ đồng hóa. **KHÔNG** thuộc 12 chỉ mục chức năng.
- **/intelligence/knowledge/**: (Đã xóa) Toàn bộ 255 file đã được di chuyển và nhất thể hóa hoàn toàn vào `wiki/` (SSoT). Kết nối hệ thống đã được định tuyến động qua `path_rules.md`.
- **/intelligence/vault/01_Knowledge/**: (Cũ) 568 file đã được migration vào `wiki/`. Giữ lại để đảm bảo tương thích ngược.

---

## 🛡️ GIAO THỨC CẬP NHẬT
- Mọi thay đổi kiến trúc phải được phản ánh vào bản đồ này ngay lập tức.
- Tuyệt đối bảo toàn tính nhất quán giữa ID chỉ mục và thư mục vật lý.

---
*Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence.* 🌌🏛️🔥🦾👑🔗


---
*Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. 🌌🏛️🔥🦾👑🔗*

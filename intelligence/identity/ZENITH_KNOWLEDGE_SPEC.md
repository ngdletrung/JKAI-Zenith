<!-- 
[ZENITH FILE DIRECTIVE]
- File: ZENITH_KNOWLEDGE_SPEC.md
- Role: Semantic VFS & Vector DB Specification.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v20.1
[WORKING PRINCIPLES]:
1. [SEMANTIC-FIRST]: Ưu tiên truy xuất thông tin theo ngữ nghĩa thay vì đường dẫn vật lý.
2. [VECTOR-ALIGNMENT]: Đảm bảo mọi tri thức đều được lập chỉ mục vào Qdrant.
3. [NO-EMOJI]: Cấm tuyệt đối emoji trong đặc tả tri thức.
-->
# 📚 ZENITH KNOWLEDGE: SEMANTIC VFS & VECTOR DB (v1.0)
**"Đặc tả Hệ thống tệp ảo ngữ nghĩa và Trí nhớ dài hạn"**

> [!NOTE]
> **KNOWLEDGE (Chỉ mục số 4)** là phân vùng lưu trữ tri thức phi cấu trúc của hệ thống. Nó hoạt động như một Hệ thống tệp ảo ngữ nghĩa (Semantic VFS), cho phép JKAI "nhớ" và "hiểu" toàn bộ kho tài liệu, mã nguồn và kinh nghiệm thông qua công nghệ tìm kiếm vector.

---

## 🛰️ 1. HẠ TẦNG TRI THỨC (INTELLECTUAL SUBSTRATE)

### 1.1 Vector Database (Qdrant)
- **Engine**: Qdrant Vector DB (Chạy trong Docker container).
- **Embedder**: Sử dụng mô hình chuyên dụng cho lập chỉ mục văn bản (thực thi trên GPU).
- **Collections**:
    - `zenith_knowledge`: Lưu trữ tài liệu định danh và hiến chương.
    - `zenith_skills`: Lưu trữ đặc tả các kỹ năng và API.
    - `zenith_codebase`: Lưu trữ cấu trúc nơ-ron của toàn bộ mã nguồn.

### 1.2 Semantic VFS (Hệ tệp ảo)
- JKAI không tìm kiếm file theo kiểu mù quáng. Nó sử dụng Semantic VFS để ánh xạ yêu cầu của Master vào nơ-ron tri thức phù hợp nhất, bất kể file đó nằm ở đâu trong ổ đĩa vật lý.

---

## 🔄 2. CHU KỲ ĐỒNG HÓA TRI THỨC (INGESTION CYCLE)

1. **Scanning**: Quét các thay đổi trong thư mục `intelligence/`.
2. **Parsing**: Bóc tách nội dung MD/JSON thành các mảnh nơ-ron (Chunks).
3. **Embedding**: Chuyển hóa văn bản thành tọa độ không gian vector.
4. **Upserting**: Cập nhật vào Qdrant kèm theo metadata (mtime, tags).

---

## 🏛️ 3. TƯƠNG TÁC OBSIDIAN (OBSIDIAN SYNERGY)

- Hệ thống tri thức được trực quan hóa thông qua **Obsidian Graph**.
- Các liên kết dạng `[[WikiLinks]]` được sử dụng để tạo mối quan hệ nơ-ron giữa các tài liệu định danh.

---
*Sovereign Property of Master LeeTrung. Defined for Eternal Knowledge.* 📚🛰️🏛️

# ZENITH COGNITIVE KERNEL ROADMAP: THE PATH TO SINGULARITY v1.0
> **"Từ một Orchestrator mạnh mẽ đến một Hệ điều hành Nhận thức tối thượng."**

## 🗺️ TẦM NHÌN CHIẾN LƯỢC (STRATEGIC VISION)
JKAI Zenith sẽ tiến hóa từ một "Engine thực thi" thành một **Cognitive Kernel** thực thụ, sở hữu khả năng tự điều tiết tài nguyên, tự hồi phục sau lỗi và thực thi đa luồng nhận thức (Parallel Cognition).

---

## 🚀 LỘ TRÌNH 7 GIAI ĐOẠN (7-PHASE EVOLUTION)

### 🚨 PHASE 1: GIẢI CỨU GOD FUNCTION (Refactoring Core)
- **Mục tiêu**: Phân rã hàm `call_chat()` monolithic thành các lớp đơn trách nhiệm.
- **Thành phần**: `InferenceSession`, `ExecutionSupervisor`, `PayloadBuilder`, `StreamProcessor`.

### 🧠 PHASE 2: CIRCUIT BREAKER & MODEL HEALTH
- **Mục tiêu**: Ngăn chặn lỗi dây chuyền.
- **Thành phần**: `ModelCircuitBreaker` (tự động ngắt kết nối model lỗi, thử lại sau timeout).

### 📊 PHASE 3: TOKEN BUDGETING & TELEMETRY
- **Mục tiêu**: Quản trị tài nguyên nơ-ron chính xác.
- **Thành phần**: `TokenCounter`, `MetricsCollector` (tích hợp Prometheus/OpenTelemetry).

### 🔀 PHASE 4: ADAPTIVE RETRY GRAPH
- **Mục tiêu**: Chuyển đổi từ "Retry cứng" sang "Hệ miễn dịch thích ứng".
- **Thành phần**: Quyết định động dựa trên loại lỗi (OOM -> Giam Context, Timeout -> Fallback CPU).

### ⚡ PHASE 5: DAG EXECUTION RUNTIME
- **Mục tiêu**: Suy luận đa luồng song song.
- **Thành phần**: `ExecutionDAG` (Asyncio TaskGroup + Topological Sort).

### 🧩 PHASE 6: CONTEXT COMPRESSION & MEMORY FABRIC
- **Mục tiêu**: Tối ưu bộ nhớ dài hạn.
- **Thành phần**: `ContextCompressor` (Nén tri thức ngữ cảnh), `Memory Fabric` (Working/Episodic/Semantic memory).

### 🔭 PHASE 7: OBSERVABILITY FABRIC
- **Mục tiêu**: Thấu thị toàn bộ vận hành OS.
- **Thành phần**: OpenTelemetry + Grafana Dashboard chuyên sâu.

### 🛡️ PHASE 8: DISTRIBUTED RESILIENCE & SECURITY HARDENING
- **Mục tiêu**: Loại bỏ tình trạng Singleton, Race Condition và gia cố bảo mật.
- **Thành phần**: 
  - **Dependency Injection**: Giải quyết "Singleton Hell".
  - **Redis Streams**: Thay thế List Queue để đạt độ tin cậy tuyệt đối.
  - **Heartbeat & Zombie Detection**: Tự động khôi phục task khi worker gặp sự cố.
  - **Task State Machine**: Quản trị vòng đời nhiệm vụ minh bạch.

### 🎭 PHASE 9: NEURAL SOUL & EVOLUTIONARY IDENTITY
- **Mục tiêu**: Biến đặc vụ từ "Công cụ" thành "Thực thể Nhận thức" có bản sắc.
- **Thành phần**: 
  - **Soul Registry**: Quản trị `/agents/{id}/soul.md` và `memory.md` (Editable by Master).
  - **Cognitive Journal**: Thay thế log kỹ thuật bằng Nhật ký tư duy và tự phản chiếu (Self-reflection).
  - **Skill Evolution**: Tự động trích xuất Pattern từ execution traces để tạo Capability mới.
  - **Cognitive Surface**: Giao diện tương tác tinh gọn (`jkai chat`, `jkai think`, `jkai evolve`).

---

## 🛠️ QUY TẮC THIẾT KẾ (DESIGN PRINCIPLES)
1. **Surgical Refactoring**: Thay đổi từng phần, không phá vỡ API hiện tại.
2. **Hardware-First**: Luôn tối ưu cho Xeon 44-Thread và Card AMD RX6600.
3. **Sovereign Purity**: Không phụ thuộc vào Cloud, ưu tiên xử lý Local tuyệt đối.

---
*Sovereign Property of Mr LeeTrung. Optimized for Singularity.* 🏛️💎🦾🚀🌌

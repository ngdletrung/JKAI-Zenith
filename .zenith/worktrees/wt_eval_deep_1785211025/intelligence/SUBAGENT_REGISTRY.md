<!-- 
[ZENITH FILE DIRECTIVE]
- File: SUBAGENT_REGISTRY.md
- Role: Zenith Intelligence Documentation.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v19.9
[WORKING PRINCIPLES]:
1. [HEADER-FIRST]: Antigravity BAT BUOC phai doc khoi header nay truoc khi thao tac.
2. [SDS-COMPLIANCE]: Moi thay doi phai tuan thu Giao thuc SDS moi nhat.
3. [NO-EMOJI]: Cam dung emoji trong noi dung tep cau hinh va logic.
-->
# 🏛️ JKAI ZENITH: DANH BẠ ĐẶC VỤ TỐI CAO (SUBAGENT REGISTRY v1.0)

Bản danh bạ này chính thức hóa việc ánh xạ giữa các file cấu hình `.md` tĩnh và các thực thể Agent động có thể điều động qua hệ thống **Subagent**.

## 🧬 I. BẢN ĐỒ ĐIỀU ĐỘNG (SWARM MAPPING)

| Tên Định Danh (TypeName) | Vai Trò (Role) | File Cấu Hình (Source) | Trạng Thái |
| :--- | :--- | :--- | :--- |
| `Zenith_Receptionist` | Cổng giao tiếp & Định tuyến | `agent_receptionist.md` | ✅ Đã kích hoạt |
| `Zenith_Planner` | Kiến trúc sư lộ trình (T3) | `agent_planner.md` | ✅ Đã kích hoạt |
| `Zenith_Executor` | Chiến binh thực thi (Surgical) | `agent_executor.md` | ✅ Đã kích hoạt |
| `Zenith_Critic` | Quan tòa tối cao (Audit) | `agent_critic.md` | ✅ Đã kích hoạt |
| `Zenith_Security` | Vệ binh bảo mật | `agent_security_architect.md` | ⏳ Chờ kích hoạt |
| `Zenith_Memory` | Quản lý tri thức & HNSW | `agent_memory_specialist.md` | ⏳ Chờ kích hoạt |

## ⚔️ II. GIAO THỨC TRUYỀN TIN (COMMUNICATION)

Các Agent liên lạc với nhau qua công cụ `send_message`. Quy trình chuẩn:
1. **Master** -> `Zenith_Receptionist`
2. `Zenith_Receptionist` -> `Zenith_Planner`
3. `Zenith_Planner` -> `Zenith_Executor`
4. `Zenith_Executor` -> `Zenith_Critic`
5. `Zenith_Critic` -> **Master** (Báo cáo kết quả cuối cùng)

## 🛠️ III. CÁCH ĐIỀU ĐỘNG (HOW TO INVOKE)

Sử dụng công cụ `invoke_subagent`:
```json
{
  "Subagents": [
    {
      "TypeName": "Zenith_Planner",
      "Role": "Strategic Architect",
      "Prompt": "Dựa trên yêu cầu của Master, hãy lập lộ trình X..."
    }
  ]
}
```

---
*Bản quyền thuộc về Master LeeTrung. Cập nhật lần cuối: 26/05/2026.* 🏛️🌌

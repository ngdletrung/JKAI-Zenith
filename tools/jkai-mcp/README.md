# JKAI MCP Server

Cầu nối **Cursor / VS Code (MCP)** ↔ **JKAI Docker** (`ai-brain`, `ai-control-plane`).

## Tools

| Tool | Mô tả |
|------|--------|
| `jkai_ping` | Kiểm tra `8001` / `7000` |
| `jkai_chat` | Chat trực tiếp — `POST /receptionist` (AI OS kernel) |
| `jkai_submit_task` | Mission async — `POST /api/submit_task` |
| `jkai_plan` | Chỉ lập blueprint — `POST /plan` |

## Cài đặt

```powershell
cd D:\Docker\JKAI\tools\jkai-mcp
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Đảm bảo JKAI đang chạy:

```powershell
docker compose -f D:\Docker\JKAI\docker-compose.yml up -d ai-brain ai-control-plane
curl http://localhost:8001/health
curl http://localhost:7000/health
```

## Cấu hình Cursor

**Settings → MCP → Add server** hoặc chỉnh `~/.cursor/mcp.json` (user) / `.cursor/mcp.json` (project):

```json
{
  "mcpServers": {
    "jkai": {
      "command": "D:\\Docker\\JKAI\\tools\\jkai-mcp\\.venv\\Scripts\\python.exe",
      "args": ["D:\\Docker\\JKAI\\tools\\jkai-mcp\\server.py"],
      "env": {
        "JKAI_BRAIN_URL": "http://localhost:8001",
        "JKAI_CONTROL_PLANE_URL": "http://localhost:7000",
        "JKAI_MCP_TIMEOUT": "600"
      }
    }
  }
}
```

Nếu không dùng venv, thay `command` bằng `python` (3.10+) đã cài `mcp` + `httpx`.

**Restart Cursor** → Chat: *"Dùng jkai_ping"* hoặc *"Gọi jkai_chat: xin chào"*.

## Cấu hình VS Code

Dùng extension hỗ trợ MCP (theo bản VS Code của bạn) với cùng block `command` / `args` / `env` như trên.

## Biến môi trường

| Biến | Mặc định |
|------|----------|
| `JKAI_BRAIN_URL` | `http://localhost:8001` |
| `JKAI_CONTROL_PLANE_URL` | `http://localhost:7000` |
| `JKAI_MCP_TIMEOUT` | `600` (giây, cho DEEP) |

## Ví dụ goal qua MCP

```text
Phân tích https://github.com/revfactory/harness so với JKAI — không sửa code.
```

```text
Sửa typo trong core/utils/skill_deck_index.py — chỉ file đó.
```

Tiếp mission:

- `mission_id`: `my_app`
- `parent_mission_id`: `my_app`

## Gỡ lỗi

- **Connection refused** — Docker chưa up hoặc sai port.
- **Timeout** — tăng `JKAI_MCP_TIMEOUT` hoặc `mode=fast`.
- **MCP không load** — kiểm tra đường dẫn `python.exe` và `pip install -r requirements.txt`.

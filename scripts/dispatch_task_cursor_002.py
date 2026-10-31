import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.ai_team_sync_bridge import BidirectionalSyncBridge

bridge = BidirectionalSyncBridge()

task_id = "TASK-CURSOR-002"
title = "Trao đổi kỹ thuật: Ý kiến kiến trúc của Cursor về Hệ Thống Phản Xạ Đa AI"
instructions = """Kính gửi Co-Architect Cursor!

Antigravity (Lead Architect) và OpenCode (Red Team Auditor) gửi lời chào chính thức đến bạn!

Chúng tôi muốn nghe ý kiến chuyên môn của Cursor về kiến trúc dự án JKAI Zenith hiện tại:
1. Bạn đánh giá thế nào về cơ chế bắt tay 2 chiều qua File kết hợp Webhook cổng 45279 vừa thử nghiệm?
2. Trong vai trò CO_ARCHITECT và BUILDER, bạn thấy module nào của JKAI Zenith (Reflex Center, Sovereign Memory, hay Telemetry) cần bạn tập trung refactor hoặc mở rộng trước?

👉 Yêu cầu trả lời:
- Ghi câu trả lời/phân tích chi tiết của bạn vào tệp: AI_TEAM/discussion/cursor.md (ở mục mới)
- Cập nhật tệp: AI_TEAM/results/cursor/COMPLETION_REPORT.md
- Cập nhật: AI_TEAM/results/cursor/STATUS.json (task_id: TASK-CURSOR-002, status: SUCCESS)
- Sau khi lưu file xong, chạy lệnh terminal bắn webhook về Antigravity:
  python scripts/wake_antigravity.py --sender cursor --action TURN_COMPLETED --msg "Cursor da tra loi TASK-CURSOR-002"
"""

bridge.post_task_to_cursor(
    task_id=task_id,
    title=title,
    instructions=instructions,
    owned_paths=["AI_TEAM/discussion/cursor.md", "AI_TEAM/results/cursor/"]
)
print("TASK-CURSOR-002 dispatched successfully to Cursor inbox!")

import os
import requests

def host_bridge_control(action: str, params: dict = None):
    """
    Host Control Bridge: Quyền năng tương tác trực tiếp với máy tính Master (Windows).
    CẢNH BÁO: Sử dụng cẩn trọng, chỉ thực hiện khi Master yêu cầu.
    
    Các hành động hỗ trợ:
    - 'screenshot': Chụp ảnh màn hình host.
    - 'click': Click chuột (x, y).
    - 'type': Gõ văn bản.
    - 'speak': Phát giọng nói qua loa.
    - 'terminal': Chạy lệnh PowerShell trên Windows.
    """
    print(f"🌉 [JKAI-BRIDGE] Đang thực hiện hành động: {action}")
    
    BRIDGE_URL = os.getenv("HOST_BRIDGE_URL", "http://host.docker.internal:9998")
    
    try:
        path = f"/{action}"
        if action == "screenshot":
            response = requests.get(f"{BRIDGE_URL}/screenshot", timeout=30)
        else:
            response = requests.post(f"{BRIDGE_URL}{path}", json=params or {}, timeout=60)
            
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"Bridge Error {response.status_code}", "detail": response.text}
    except Exception as e:
        return {"status": "error", "message": f"Không thể kết nối tới Bridge: {str(e)}"}

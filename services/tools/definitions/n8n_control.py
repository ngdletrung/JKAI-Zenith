import requests
import os

def n8n_control(action: str, params: dict = {}):
    """
    N8N Automation Control: Quyền năng điều khiển các quy trình tự động hóa n8n.
    
    Actions:
    - 'list_workflows': Liệt kê danh sách các workflow hiện có.
    - 'trigger_workflow': Kích hoạt thực thi một workflow cụ thể.
    - 'get_execution': Kiểm tra trạng thái thực thi của một task.
    """
    print(f"🤖 [JKAI-N8N] Thực hiện hành động: {action}")
    
    N8N_URL = os.getenv("N8N_API_URL", "http://n8n-main:5678/api/v1")
    API_KEY = os.getenv("N8N_API_KEY")
    
    if not API_KEY:
        return {"status": "error", "message": "N8N_API_KEY chưa được thiết lập trong .env"}
        
    headers = {"X-N8N-API-KEY": API_KEY}
    
    try:
        if action == "list_workflows":
            response = requests.get(f"{N8N_URL}/workflows", headers=headers, timeout=30)
        elif action == "trigger_workflow":
            wf_id = params.get("workflow_id")
            response = requests.post(f"{N8N_URL}/workflows/{wf_id}/executions", headers=headers, json=params.get("data", {}), timeout=30)
        elif action == "get_execution":
            exec_id = params.get("execution_id")
            response = requests.get(f"{N8N_URL}/executions/{exec_id}", headers=headers, timeout=30)
        else:
            return {"status": "error", "message": f"Hành động '{action}' không hỗ trợ."}
            
        if response.status_code in [200, 201]:
            return response.json()
        else:
            return {"status": "error", "message": f"N8N API Error {response.status_code}", "detail": response.text}
    except Exception as e:
        return {"status": "error", "message": f"Không thể kết nối tới N8N: {str(e)}"}

import os
import requests

def browser_action(url: str, objective: str):
    """
    Cho phép JKAI truy cập và tương tác với các trang web hiện đại bằng trình duyệt thực.
    Dùng cho các trang web động (JS), cần click, cuộn trang hoặc trích xuất dữ liệu phức tạp.
    
    Args:
        url (str): Địa chỉ trang web cần truy cập.
        objective (str): Mục tiêu cụ thể cần thực hiện trên trang web.
    """
    print(f"👁️ [JKAI-BROWSER-DEF] Requesting interaction on: {url} for objective: {objective}")
    
    BROWSER_URL = os.getenv("BROWSER_SERVICE_URL", "http://ai-browser:8000/interact")
    
    try:
        response = requests.post(BROWSER_URL, json={
            "url": url,
            "objective": objective
        }, timeout=300)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"Browser Agent Error {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Không thể kết nối tới Browser Agent: {str(e)}"}

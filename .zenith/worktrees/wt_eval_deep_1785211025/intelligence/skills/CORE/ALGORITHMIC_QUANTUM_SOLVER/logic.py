import subprocess
import math

# =================================================================
# 🧮 JKAI ZENITH: LOGIC TOÁN HỌC & THUẬT TOÁN (MATH & ALGO)
# =================================================================

def python_exec(code: str):
    """Thực thi mã Python để xử lý logic hoặc thuật toán phức tạp."""
    print(f"🐍 [JKAI-PY] Executing Python code...")
    try:
        # Lưu vào file tạm và chạy
        with open("temp_exec.py", "w", encoding="utf-8") as f:
            f.write(code)
        result = subprocess.run(["python", "temp_exec.py"], capture_output=True, text=True, timeout=30)
        return {"stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

def math_calculator(expression: str):
    """Tính toán các biểu thức toán học phức tạp."""
    print(f"🔢 [JKAI-MATH] Calculating: {expression}")
    try:
        # Sử dụng eval an toàn (chỉ cho phép các hàm toán học)
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"result": result}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

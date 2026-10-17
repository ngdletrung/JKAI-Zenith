import os
import subprocess
import math
import tempfile
import asyncio

# =================================================================
# 🧮 JKAI ZENITH: LOGIC TOÁN HỌC & THUẬT TOÁN (MATH & ALGO)
# =================================================================


def python_exec(code: str):
    """Thực thi mã Python để xử lý logic hoặc thuật toán phức tạp."""
    print("🐍 [JKAI-PY] Executing Python code...")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", encoding="utf-8", delete=False) as f:
            f.write(code)
            temp_path = f.name
        result = subprocess.run(["python", temp_path], capture_output=True, text=True, timeout=30)
        return {"stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def math_calculator(expression: str):
    """Tính toán các biểu thức toán học phức tạp."""
    print(f"🔢 [JKAI-MATH] Calculating: {expression}")
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"result": result}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


# 🚀 ASYNC EXECUTOR ADAPTER (Z-SOS SOTA COMPLIANT)
async def execute(**kwargs):
    loop = asyncio.get_running_loop()
    if "expression" in kwargs:
        return await loop.run_in_executor(None, lambda: math_calculator(kwargs["expression"]))
    if "code" in kwargs:
        return await loop.run_in_executor(None, lambda: python_exec(kwargs["code"]))
    for fn_name in ["math_calculator", "python_exec", "run", "main", "solve"]:
        if fn_name in globals() and callable(globals()[fn_name]):
            fn = globals()[fn_name]
            if asyncio.iscoroutinefunction(fn):
                return await fn(**kwargs)
            return await loop.run_in_executor(None, lambda: fn(**kwargs))
    return {"status": "error", "msg": "No matching entrypoint found"}

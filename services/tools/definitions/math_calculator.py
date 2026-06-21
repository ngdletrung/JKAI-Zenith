import os
import logging

logger = logging.getLogger("jkai.tools.math")

def calculate_math(expression: str):
    """Thực hiện các phép tính toán học an toàn cho JKAI."""
    logger.info("[JKAI-MATH] Calculating: %s", expression)
    try:
        # Sử dụng eval an toàn hoặc bộ thư viện toán học
        # Chú ý: Trong thực tế nên dùng parser an toàn
        result = eval(expression, {"__builtins__": {}}, {})
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

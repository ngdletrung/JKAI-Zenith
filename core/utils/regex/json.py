import json
import re
from typing import Any

__all__ = [
    "JSON_BLOCK", "CODE_BLOCK_JSON", "YAML_FRONT_MATTER",
    "extract_json",
]

JSON_BLOCK = re.compile(r"(\{.*?\})", re.DOTALL)
CODE_BLOCK_JSON = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
YAML_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def clean_and_repair_json(s: str) -> str:
    """Sửa các lỗi cú pháp JSON phổ biến của mô hình local một cách an toàn."""
    # 1. Loại bỏ các comment dạng C/JS
    s = re.sub(r'//.*?\n', '\n', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    
    # 2. Loại bỏ các comment dạng Python (#), chỉ khi dấu # nằm ngoài chuỗi ký tự
    lines = []
    for line in s.splitlines():
        parts = line.split('#')
        if len(parts) > 1:
            left_part = parts[0]
            # Nếu số dấu ngoặc kép bên trái là chẵn, tức là dấu # không nằm trong chuỗi
            if left_part.count('"') % 2 == 0:
                line = left_part
        lines.append(line)
    s = '\n'.join(lines)

    # 3. Thay thế Python True/False/None thành JSON true/false/null
    s = re.sub(r'\bTrue\b', 'true', s)
    s = re.sub(r'\bFalse\b', 'false', s)
    s = re.sub(r'\bNone\b', 'null', s)

    # 4. Loại bỏ dấu phẩy thừa trước ngoặc đóng } và ]
    s = re.sub(r',\s*\}', '}', s)
    s = re.sub(r',\s*\]', ']', s)

    # 5. Thay thế smart quotes thông dụng
    s = s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    
    return s.strip()


def extract_json(text: str) -> Any:
    # 1. Thử phân tích cú pháp trực tiếp
    try:
        return json.loads(text)
    except Exception:
        pass
        
    # 2. Thử làm sạch cú pháp rồi phân tích
    try:
        return json.loads(clean_and_repair_json(text))
    except Exception:
        pass

    # 3. Thử trích xuất từ khối mã markdown ```json
    m = CODE_BLOCK_JSON.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
        try:
            return json.loads(clean_and_repair_json(m.group(1)))
        except Exception:
            pass
            
    # 4. Thử tìm cặp ngoặc nhọn outermost { ... } dành cho nested JSON
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace+1]
        try:
            return json.loads(candidate)
        except Exception:
            pass
        try:
            return json.loads(clean_and_repair_json(candidate))
        except Exception:
            pass

    # 5. Duyệt qua từng khối JSON con (phương án fallback)
    for block in reversed(JSON_BLOCK.findall(text)):
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                return data
        except Exception:
            try:
                data = json.loads(clean_and_repair_json(block))
                if isinstance(data, dict):
                    return data
            except Exception:
                continue

    # 6. Loại bỏ thẻ <think> và thử lại
    from core.utils.regex.ai_tags import THINK_TAG
    cleaned = THINK_TAG.sub("", text).strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        try:
            return json.loads(clean_and_repair_json(cleaned))
        except Exception:
            pass

    raise ValueError("No valid JSON found")


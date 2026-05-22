import json
import re
import logging
from typing import Any, Optional

logger = logging.getLogger('JSON-Repair')

def extract_first_json_block(text: str) -> Optional[str]:
    """
    🔍 [BLOCK-EXTRACTION v2.5]: Trích xuất khối JSON đầu tiên bằng thuật toán quét cặp ngoặc (stack-based).
    Khắc phục triệt để lỗi greedy của regex và bỏ qua các ngoặc bên trong string literal.
    """
    stack = []
    start = None
    in_string = False
    escaped = False
    
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
            
        if ch == '"':
            in_string = True
            continue
            
        if ch in "{[":
            if start is None:
                start = i
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if not stack:
                continue
            if ch == stack[-1]:
                stack.pop()
                if not stack and start is not None:
                    return text[start:i+1]
    
    # Nếu có điểm bắt đầu nhưng không đóng được trọn vẹn, vẫn trả về từ start để thực hiện repair
    if start is not None:
        return text[start:]
    return None

def normalize_quotes_and_literals(text: str) -> str:
    """
    🔄 [NORMALIZER]: Đồng hóa single quotes sang double quotes một cách an toàn và sửa đổi literals.
    Chỉ chuyển đổi dấu nháy đơn khi ở NGOÀI dấu nháy kép (tránh phá hỏng dấu nháy đơn hợp lệ bên trong chuỗi).
    """
    # 1. Đồng hóa Python literals sang JSON
    text = (text
        .replace(": None", ": null")
        .replace(": True", ": true")
        .replace(": False", ": false")
        .replace("True,", "true,")
        .replace("False,", "false,")
        .replace("None,", "null,")
    )
    
    # 2. Xử lý single quotes
    result = []
    in_double_string = False
    in_single_string = False
    escaped = False
    
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if escaped:
            result.append(ch)
            escaped = False
            i += 1
            continue
            
        if ch == '\\':
            result.append(ch)
            escaped = True
            i += 1
            continue
            
        if ch == '"':
            if not in_single_string:
                in_double_string = not in_double_string
            result.append(ch)
            i += 1
            continue
            
        if ch == "'":
            if not in_double_string:
                # Chuyển đổi single quote sang double quote
                result.append('"')
                in_single_string = not in_single_string
            else:
                result.append(ch)
            i += 1
            continue
            
        result.append(ch)
        i += 1
        
    return "".join(result)

def repair_json(raw_text: str) -> str:
    """
    🧪 [NEURAL-SURGERY v2.5 - PRODUCTION]: Sửa chữa JSON Hermes nâng cao.
    Kiến trúc 4 lớp bảo vệ: Trích xuất chính xác → Chuẩn hóa chuỗi → Sửa chữa cấu trúc dở dang → Cân bằng cấu trúc.
    """
    if not raw_text or not raw_text.strip():
        return "{}"

    # 1. Loại bỏ markdown code blocks & thinking tags
    clean_text = re.sub(r'```(?:json)?\s*|\s*```', '', raw_text, flags=re.IGNORECASE).strip()
    clean_text = re.sub(r'<think>.*?</think>', '', clean_text, flags=re.DOTALL).strip()
    
    # 2. Control characters cleanup (chỉ loại bỏ các ký tự điều khiển ASCII phi in)
    clean_text = "".join(ch if ord(ch) >= 32 or ch in "\n\r\t" else f"\\u{ord(ch):04x}" for ch in clean_text)

    # 3. Trích xuất khối JSON tiềm năng đầu tiên
    candidate = extract_first_json_block(clean_text) or clean_text

    # 4. Chuẩn hóa nháy và literals
    candidate = normalize_quotes_and_literals(candidate)

    # 5. Fix unescaped newlines inside strings (Heuristic)
    candidate = re.sub(r'(".*?)(?<!\\)\n(.*?")', lambda m: m.group(1) + "\\n" + m.group(2), candidate, flags=re.DOTALL)

    # 6. Loại bỏ trailing commas
    candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
    candidate = re.sub(r',\s*$', '', candidate)

    # 7. Truncation repair (Sửa chữa phần đuôi bị cụt dở dang)
    in_string = False
    escaped = False
    for ch in candidate:
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            
    if in_string:
        candidate += '"'  # Tự động đóng chuỗi chưa hoàn thành

    # Nếu kết thúc bằng dấu phẩy hoặc dấu hai chấm dở dang, cắt bỏ
    candidate = candidate.strip()
    if candidate.endswith(',') or candidate.endswith(':'):
        last_comma = candidate.rfind(',')
        if last_comma != -1:
            candidate = candidate[:last_comma].rstrip()

    # 8. Structural balancing (Cân bằng ngoặc an toàn bên ngoài các chuỗi ký tự)
    in_string = False
    escaped = False
    open_braces = 0
    close_braces = 0
    open_brackets = 0
    close_brackets = 0
    
    for ch in candidate:
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
            
        if ch == '"':
            in_string = True
            continue
            
        if ch == '{':
            open_braces += 1
        elif ch == '}':
            close_braces += 1
        elif ch == '[':
            open_brackets += 1
        elif ch == ']':
            close_brackets += 1
            
    if open_braces > close_braces:
        candidate += '}' * (open_braces - close_braces)
    if open_brackets > close_brackets:
        candidate += ']' * (open_brackets - close_brackets)

    return candidate.strip()

def repair_tool_call_arguments(arguments: str) -> str:
    """
    ⚔️ [TOOL-CALL-REPAIR]: Tinh hoa Hermes - Vá lỗi tham số tool call.
    Đảm bảo arguments luôn là một chuỗi JSON hợp lệ trước khi thực thi.
    """
    if not arguments or arguments.strip() in ("", "{}", "[]"):
        return "{}"
    
    try:
        obj = json.loads(arguments)
        if not isinstance(obj, dict):
            return "{}"
        return arguments
    except json.JSONDecodeError:
        logger.info("🛠️ [TOOL-CALL-REPAIR]: Đang vá lỗi tham số tool call...")
        repaired = repair_json(arguments)
        try:
            obj = json.loads(repaired)
            if isinstance(obj, dict):
                return repaired
            return "{}"
        except Exception as e:
            logger.warning(f"❌ [TOOL-CALL-REPAIR-FAILED]: Lỗi: {e}")
            return "{}"

def safe_json_loads(text: str, fallback: Any = None) -> Any:
    """
    🛡️ [SAFE-LOAD]: Nạp JSON an toàn với cơ chế tự sửa lỗi.
    """
    if not text:
        return fallback or {}
        
    try:
        cleaned = text
        if isinstance(cleaned, str):
            cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL).strip()
            cleaned = re.sub(r'```json\s*|\s*```', '', cleaned).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            repaired = repair_json(text)
            return json.loads(repaired)
        except Exception as e:
            logger.warning(f"❌ [JSON-REPAIR-FAILED]: Không thể cứu vãn JSON. Lỗi: {e}")
            return fallback or text

def extract_json_from_text(text: str) -> Any:
    """
    🔍 [EXTRACTOR]: Trích xuất JSON từ một đoạn văn bản.
    """
    return safe_json_loads(text)

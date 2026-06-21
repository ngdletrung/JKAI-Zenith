import json
import re
import logging
from typing import Any, Optional

logger = logging.getLogger("JSONRepair")


# ==========================================================
# JSON BLOCK EXTRACTION
# ==========================================================

def extract_first_json_block(text: str) -> Optional[str]:
    """
    Trích xuất object/array JSON đầu tiên bằng state machine.
    Hỗ trợ:
      - nested {}
      - nested []
      - escaped quotes
      - braces trong string
    """

    start = None
    stack = []

    in_string = False
    escaped = False

    for i, ch in enumerate(text):

        if in_string:

            if escaped:
                escaped = False

            elif ch == "\\":
                escaped = True

            elif ch == '"':
                in_string = False

            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if start is None:
                start = i
            stack.append("}")

        elif ch == "[":
            if start is None:
                start = i
            stack.append("]")

        elif ch in "}]":

            if not stack:
                continue

            if ch == stack[-1]:
                stack.pop()

                if not stack and start is not None:
                    return text[start:i + 1]

    if start is not None:
        return text[start:]

    return None


# ==========================================================
# CLEANUP
# ==========================================================

def remove_markdown(text: str) -> str:

    text = re.sub(
        r"```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace("```", "")

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    return text.strip()


def escape_control_chars(text: str) -> str:

    out = []

    for ch in text:

        code = ord(ch)

        if code < 32 and ch not in "\n\r\t":
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)

    return "".join(out)


# ==========================================================
# PYTHON → JSON LITERAL CONVERSION
# ==========================================================

def normalize_python_literals(text: str) -> str:
    """
    Chỉ sửa token ngoài string.
    """

    result = []

    in_string = False
    escaped = False

    token = ""

    def flush_token():

        nonlocal token

        if token == "True":
            result.append("true")

        elif token == "False":
            result.append("false")

        elif token == "None":
            result.append("null")

        else:
            result.append(token)

        token = ""

    for ch in text:

        if in_string:

            result.append(ch)

            if escaped:
                escaped = False

            elif ch == "\\":
                escaped = True

            elif ch == '"':
                in_string = False

            continue

        if ch == '"':

            flush_token()

            in_string = True
            result.append(ch)
            continue

        if ch.isalnum() or ch == "_":

            token += ch

        else:

            flush_token()
            result.append(ch)

    flush_token()

    return "".join(result)


# ==========================================================
# TRAILING COMMA REPAIR
# ==========================================================

def remove_trailing_commas(text: str) -> str:

    previous = None

    while previous != text:

        previous = text

        text = re.sub(
            r',\s*([}\]])',
            r'\1',
            text
        )

    return text


# ==========================================================
# STRUCTURAL BALANCING
# ==========================================================

def balance_json(text: str) -> str:

    stack = []

    in_string = False
    escaped = False

    for ch in text:

        if in_string:

            if escaped:
                escaped = False

            elif ch == "\\":
                escaped = True

            elif ch == '"':
                in_string = False

            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            stack.append("}")

        elif ch == "[":
            stack.append("]")

        elif stack and ch == stack[-1]:
            stack.pop()

    while stack:
        text += stack.pop()

    return text


# ==========================================================
# STRING TRUNCATION REPAIR
# ==========================================================

def close_unterminated_string(text: str) -> str:

    in_string = False
    escaped = False

    for ch in text:

        if in_string:

            if escaped:
                escaped = False

            elif ch == "\\":
                escaped = True

            elif ch == '"':
                in_string = False

        else:

            if ch == '"':
                in_string = True

    if in_string:
        text += '"'

    return text


# ==========================================================
# MAIN REPAIR
# ==========================================================

def repair_json(raw_text: str) -> str:

    if not raw_text:
        return "{}"

    text = remove_markdown(raw_text)

    text = escape_control_chars(text)

    candidate = extract_first_json_block(text)

    if candidate is None:
        return "{}"

    candidate = normalize_python_literals(candidate)

    candidate = remove_trailing_commas(candidate)

    candidate = close_unterminated_string(candidate)

    candidate = balance_json(candidate)

    return candidate.strip()


# ==========================================================
# SAFE LOADS
# ==========================================================

def safe_json_loads(
    text: str,
    fallback: Any = None
) -> Any:

    if not text:
        return fallback or {}

    try:
        return json.loads(text)

    except Exception:

        repaired = repair_json(text)

        try:
            return json.loads(repaired)

        except Exception as e:

            logger.warning(
                f"JSON repair failed: {e}"
            )

            return fallback or {}


# ==========================================================
# TOOL CALL REPAIR
# ==========================================================

def repair_tool_call_arguments(
    arguments: str
) -> str:

    if not arguments:
        return "{}"

    try:

        obj = json.loads(arguments)

        return arguments if isinstance(obj, dict) else "{}"

    except Exception:

        repaired = repair_json(arguments)

        try:

            obj = json.loads(repaired)

            return repaired if isinstance(obj, dict) else "{}"

        except Exception:

            return "{}"

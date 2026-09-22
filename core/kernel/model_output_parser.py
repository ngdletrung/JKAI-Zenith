"""
ModelOutputParser — Bộ bóc tách & phục hồi đầu ra từ mô hình cục bộ (Local Ollama / Open-Weights).

Được thiết kế chuyên biệt cho Qwen2.5-Coder, DeepSeek-Coder, Llama-3 nhằm khắc phục:
1. Markdown code block wrapping (```json ... ```)
2. Semantic tags (<tool_call> ... </tool_call>)
3. ReAct format (Action: ... / Action Input: ...)
4. Embedded JSON trong văn bản suy luận
5. Lỗi cú pháp JSON phổ biến (trailing commas, unescaped quotes, unclosed brackets do token truncation)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("jkai.kernel.model_output_parser")


class ModelOutputParser:
    """Parser đa chiến lược với khả năng tự phục hồi cho Local LLMs."""

    @classmethod
    def parse(cls, raw: Any) -> Dict[str, Any]:
        """
        Phân tích đầu ra của model thành dictionary chuẩn hóa:
        {
            "thought": str,
            "tool": Optional[str],
            "params": Dict[str, Any],
            "final_answer": Optional[str]
        }
        """
        if isinstance(raw, dict):
            return cls._normalize_dict(raw)

        text = str(raw or "").strip()
        if not text:
            return {"thought": "", "tool": None, "params": {}, "final_answer": None}

        # 1. Thử parse trực tiếp nếu là raw JSON hoàn chỉnh
        parsed, remaining_thought = cls._try_parse_raw_json(text)
        if parsed:
            return cls._merge_result(parsed, remaining_thought)

        # 2. Chiến lược 1: Markdown code block (```json ... ``` hoặc ``` ... ```)
        parsed, remaining_thought = cls._try_parse_markdown_fence(text)
        if parsed:
            return cls._merge_result(parsed, remaining_thought)

        # 3. Chiến lược 2: Semantic tag (<tool_call> ... </tool_call>)
        parsed, remaining_thought = cls._try_parse_tool_call_tag(text)
        if parsed:
            return cls._merge_result(parsed, remaining_thought)

        # 4. Chiến lược 3: ReAct pattern (Action: ... / Action Input: ...)
        parsed, remaining_thought = cls._try_parse_react_format(text)
        if parsed:
            return cls._merge_result(parsed, remaining_thought)

        # 5. Chiến lược 4: Quét cân bằng dấu ngoặc {...} (Brace matching & repair)
        parsed, remaining_thought = cls._try_parse_brace_scan(text)
        if parsed:
            return cls._merge_result(parsed, remaining_thought)

        # 6. Fallback: Nếu không phát hiện tool call hợp lệ
        final_answer = None
        upper_text = text.upper()
        if "FINAL_ANSWER" in upper_text or "FINAL ANSWER" in upper_text or "KẾT QUẢ:" in upper_text:
            final_answer = text

        return {
            "thought": text,
            "tool": None,
            "params": {},
            "final_answer": final_answer
        }

    # =========================================================================
    # CÁC CHIẾN LƯỢC BÓC TÁCH (PARSING STRATEGIES)
    # =========================================================================

    @classmethod
    def _try_parse_raw_json(cls, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        if text.startswith("{") and text.endswith("}"):
            res = cls._safe_json_loads(text)
            if res is not None and isinstance(res, dict):
                return res, ""
        return None, text

    @classmethod
    def _try_parse_markdown_fence(cls, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        # Bắt ```json ... ``` hoặc ``` ... ```
        pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
        matches = list(pattern.finditer(text))
        for m in matches:
            code_block = m.group(1).strip()
            res = cls._safe_json_loads(code_block)
            if res is not None and isinstance(res, dict):
                # Text trước và sau fence làm thought
                thought_parts = []
                if m.start() > 0:
                    thought_parts.append(text[:m.start()].strip())
                if m.end() < len(text):
                    thought_parts.append(text[m.end():].strip())
                thought = "\n".join(filter(None, thought_parts))
                return res, thought
        return None, text

    @classmethod
    def _try_parse_tool_call_tag(cls, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        # Bắt <tool_call> ... </tool_call> hoặc <tool> ... </tool>
        pattern = re.compile(r"<(?:tool_call|tool)>(.*?)</(?:tool_call|tool)>", re.DOTALL | re.IGNORECASE)
        m = pattern.search(text)
        if m:
            content = m.group(1).strip()
            res = cls._safe_json_loads(content)
            if res is not None and isinstance(res, dict):
                thought = (text[:m.start()] + "\n" + text[m.end():]).strip()
                return res, thought
        return None, text

    @classmethod
    def _try_parse_react_format(cls, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        # Bắt Action: <name>\nAction Input: <input>
        pattern = re.compile(
            r"Action:\s*([a-zA-Z0-9_\-\.]+)\s*(?:[\r\n]+)?Action Input:\s*([\s\S]+)",
            re.IGNORECASE
        )
        m = pattern.search(text)
        if m:
            tool_name = m.group(1).strip()
            raw_input = m.group(2).strip()
            
            # Input có thể là JSON hoặc string/path
            input_dict = cls._safe_json_loads(raw_input)
            if input_dict is not None and isinstance(input_dict, dict):
                params = input_dict
            else:
                # Nếu là chuỗi đơn, suy đoán tham số
                params = {"input": raw_input}
                
            thought = text[:m.start()].strip()
            return {"tool": tool_name, "params": params}, thought
        return None, text

    @classmethod
    def _try_parse_brace_scan(cls, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Quét tìm khối {...} hợp lệ bằng thuật toán cân bằng dấu ngoặc."""
        n = len(text)
        start_idx = -1
        depth = 0
        in_string = False
        escape = False

        candidates = []

        for i, char in enumerate(text):
            if char == '"' and not escape:
                in_string = not in_string
            elif char == '\\' and in_string:
                escape = not escape
                continue

            if not in_string:
                if char == '{':
                    if depth == 0:
                        start_idx = i
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0 and start_idx != -1:
                        candidates.append((start_idx, i + 1))
                        start_idx = -1
            escape = False

        # Thử parse các khối cân bằng tìm thấy (ưu tiên khối chứa "tool" hoặc "action")
        for s, e in reversed(candidates):
            chunk = text[s:e]
            res = cls._safe_json_loads(chunk)
            if res is not None and isinstance(res, dict):
                thought = (text[:s] + "\n" + text[e:]).strip()
                return res, thought

        # Nếu không có khối cân bằng hoàn chỉnh, thử sửa khối từ dấu '{' đầu tiên (trường hợp bị cắt do token)
        first_brace = text.find('{')
        if first_brace != -1:
            truncated_chunk = text[first_brace:]
            res = cls._repair_and_load_truncated_json(truncated_chunk)
            if res is not None and isinstance(res, dict):
                thought = text[:first_brace].strip()
                return res, thought

        return None, text

    # =========================================================================
    # BỘ SỬA CHỮA JSON (JSON AUTO-REPAIR HEURISTICS)
    # =========================================================================

    @classmethod
    def _safe_json_loads(cls, s: str) -> Optional[Any]:
        """Thử load json, nếu thất bại thì sửa các lỗi phổ biến rồi thử lại."""
        s = s.strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

        # 1. Sửa trailing comma: ,} -> } hoặc ,] -> ]
        s_clean = re.sub(r",\s*([\}\]])", r"\1", s)
        try:
            return json.loads(s_clean)
        except json.JSONDecodeError:
            pass

        # 2. Xử lý escape quotes bên trong chuỗi giá trị
        s_escaped = cls._escape_internal_quotes(s_clean)
        try:
            return json.loads(s_escaped)
        except json.JSONDecodeError:
            pass

        return None

    @classmethod
    def _repair_and_load_truncated_json(cls, s: str) -> Optional[Dict[str, Any]]:
        """Phục hồi JSON bị cắt cụt do token truncation."""
        s = s.strip()
        # Loại bỏ trailing comma nếu có
        s = re.sub(r",\s*$", "", s)

        # Đếm số ngoặc còn thiếu
        open_braces = s.count('{') - s.count('}')
        open_brackets = s.count('[') - s.count(']')

        # Nếu đang ở giữa chuỗi chưa đóng
        if s.count('"') % 2 != 0:
            s += '"'

        s += ']' * max(0, open_brackets)
        s += '}' * max(0, open_braces)

        return cls._safe_json_loads(s)

    @staticmethod
    def _escape_internal_quotes(s: str) -> str:
        """Sửa lỗi quotes cơ bản trong JSON."""
        # Biến đổi các giá trị boolean / None kiểu Python
        s = re.sub(r"\bTrue\b", "true", s)
        s = re.sub(r"\bFalse\b", "false", s)
        s = re.sub(r"\bNone\b", "null", s)
        return s

    # =========================================================================
    # CHUẨN HÓA VÀ HỢP NHẤT DỮ LIỆU (NORMALIZATION & MERGE)
    # =========================================================================

    @classmethod
    def _normalize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Chuẩn hóa dictionary về định dạng chuẩn của JKAI Agent."""
        thought = data.get("thought") or data.get("reflection") or ""
        final_answer = data.get("final_answer") or data.get("answer") or None

        # Chuẩn hóa tên tool
        tool = (
            data.get("tool")
            or data.get("action")
            or data.get("name")
            or data.get("function")
        )

        # Chuẩn hóa params
        params = (
            data.get("params")
            or data.get("parameters")
            or data.get("arguments")
            or data.get("action_input")
            or {}
        )

        # Nếu params đang ở dạng string JSON, giải mã ra dict
        if isinstance(params, str):
            try:
                params_loaded = json.loads(params)
                if isinstance(params_loaded, dict):
                    params = params_loaded
                else:
                    params = {"input": params}
            except Exception:
                params = {"input": params}

        # Nếu tool mang giá trị rỗng hoặc text báo hoàn tất
        if isinstance(tool, str) and tool.lower() in ("none", "null", "", "final_answer", "finish"):
            if not final_answer:
                final_answer = str(params.get("input") or thought or "Hoàn thành nhiệm vụ.")
            tool = None

        return {
            "thought": str(thought).strip(),
            "tool": tool,
            "params": params if isinstance(params, dict) else {"input": params},
            "final_answer": final_answer
        }

    @classmethod
    def _merge_result(cls, parsed: Dict[str, Any], extracted_thought: str) -> Dict[str, Any]:
        normalized = cls._normalize_dict(parsed)
        if extracted_thought and not normalized["thought"]:
            normalized["thought"] = extracted_thought
        elif extracted_thought and normalized["thought"] and extracted_thought != normalized["thought"]:
            normalized["thought"] = f"{extracted_thought}\n{normalized['thought']}".strip()
        return normalized

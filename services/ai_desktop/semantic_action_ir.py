# -*- coding: utf-8 -*-
"""
Typed Action IR Schema & Anti-TOCTOU Validator for JKAI Desktop Actuator (M5 Phase 2)
Hoàn thiện toàn bộ các tiêu chuẩn an ninh và rà soát biên từ LƯỢT 305 của OpenCode:
  1. Finite Numeric: Bắt buộc math.isfinite() trên issued_at, expires_at (chống NaN, +Inf, -Inf fail-open).
  2. Bounded Parameter Meta-Types: type(max_keys) is int in [1, 10], type(max_delta) is int in [1, 10000].
  3. Strict Target Identity Types: target_hwnd > 0, target_pid > 0 (type is int, reject bool), target_process_name non-empty str.
  4. Strict ActionType Enum: Bắt buộc action_type là ActionType enum hợp lệ.
  5. Canonical Hash Format: element_hash khớp ^[0-9a-fA-F]{64}$, snapshot_hash khớp ^sha256_[0-9a-fA-F]{64}$.
  6. Structured Field Patterns: session_id, lease_id, nonce, approval_digest có regex và độ dài chuẩn hóa.
  7. Exact Wire Parser: from_wire_dict() phân tích cú pháp JSON an toàn, chống coercion dữ liệu sai.
  8. Pure Schema & Validator: Giữ nguyên ranh giới không có mã thực thi can thiệp.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import re
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

# Regex định dạng canonical cho snapshot-scoped ref ID: e1, e2, e3...
REF_PATTERN = re.compile(r"^e[1-9][0-9]*$")

# Regex định dạng hash toàn phần SHA-256 (64 hex chars)
ELEMENT_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
SNAPSHOT_HASH_PATTERN = re.compile(r"^sha256_[0-9a-fA-F]{64}$")
DIGEST_PATTERN = re.compile(r"^(sha256_)?[0-9a-fA-F]{64}$")

# Regex định dạng định danh an toàn
NONCE_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{8,64}$")
LEASE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{8,64}$")
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{4,64}$")

# Danh sách ký tự điều khiển cấm trong TypeText (trừ \t, \n, \r)
DISALLOWED_CONTROL_CHARS = set(range(0, 32)) - {9, 10, 13}


class ActionType(str, Enum):
    CLICK = "click"
    TYPE_TEXT = "type_text"
    KEY_COMBO = "key_combo"
    SCROLL = "scroll"
    FOCUS = "focus"


class StandardKeyEnum(str, Enum):
    # Modifier keys
    CTRL = "ctrl"
    SHIFT = "shift"
    ALT = "alt"
    WIN = "win"

    # Action / Navigation keys
    ENTER = "enter"
    ESCAPE = "escape"
    TAB = "tab"
    BACKSPACE = "backspace"
    DELETE = "delete"
    SPACE = "space"
    UP = "arrow_up"
    DOWN = "arrow_down"
    LEFT = "arrow_left"
    RIGHT = "arrow_right"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    HOME = "home"
    END = "end"

    # Function keys
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"

    # Standard alphanumeric keys
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"
    NUM_0 = "0"
    NUM_1 = "1"
    NUM_2 = "2"
    NUM_3 = "3"
    NUM_4 = "4"
    NUM_5 = "5"
    NUM_6 = "6"
    NUM_7 = "7"
    NUM_8 = "8"
    NUM_9 = "9"


# ── Typed Parameter Schemas ──────────────────────────────────────────────

class ModifierKeyEnum(str, Enum):
    NONE = "none"
    CTRL = "ctrl"
    SHIFT = "shift"
    ALT = "alt"


@dataclass
class FocusParams:
    def validate(self) -> Tuple[bool, str]:
        return True, "VALID"


@dataclass
class ClickParams:
    button: Literal["left", "right", "middle"] = "left"
    click_count: int = 1  # 1: Single, 2: Double
    prefer_invoke_pattern: bool = True  # Nếu element có InvokePattern, gọi trực tiếp
    modifiers: List[Union[ModifierKeyEnum, str]] = field(default_factory=lambda: [ModifierKeyEnum.NONE])
    target_x: Optional[int] = None
    target_y: Optional[int] = None

    def validate(self) -> Tuple[bool, str]:
        if type(self.button) is not str or self.button not in ("left", "right", "middle"):
            return False, f"INVALID_BUTTON: {self.button!r}"
        if type(self.click_count) is not int or self.click_count not in (1, 2):
            return False, f"INVALID_CLICK_COUNT: {self.click_count!r} (must be int 1 or 2)"
        if type(self.prefer_invoke_pattern) is not bool:
            return False, f"PREFER_INVOKE_PATTERN_MUST_BE_BOOL: {self.prefer_invoke_pattern!r}"
        if not isinstance(self.modifiers, list):
            return False, "MODIFIERS_MUST_BE_LIST"
        for m in self.modifiers:
            val = m.value if isinstance(m, ModifierKeyEnum) else str(m).lower()
            if val not in ("none", "ctrl", "shift", "alt"):
                return False, f"INVALID_MODIFIER: {m!r}"
        if self.target_x is not None and (type(self.target_x) is not int or type(self.target_x) is bool):
            return False, "TARGET_X_MUST_BE_INT"
        if self.target_y is not None and (type(self.target_y) is not int or type(self.target_y) is bool):
            return False, "TARGET_Y_MUST_BE_INT"
        if (self.target_x is None) != (self.target_y is None):
            return False, "CLICK_TARGET_COORDS_INCOMPLETE"
        return True, "VALID" 


@dataclass
class TypeTextParams:
    text: str
    max_length: int = 1000
    clear_before_type: bool = False
    prefer_value_pattern: bool = True

    def validate(self) -> Tuple[bool, str]:
        if type(self.text) is not str:
            return False, "TEXT_MUST_BE_STRING"
        if type(self.max_length) is not int or self.max_length <= 0 or self.max_length > 5000:
            return False, f"INVALID_MAX_LENGTH: {self.max_length!r} (must be int in [1, 5000])"
        if len(self.text) > self.max_length:
            return False, f"TEXT_TOO_LONG: length {len(self.text)} exceeds max {self.max_length}"
        if type(self.clear_before_type) is not bool:
            return False, "CLEAR_BEFORE_TYPE_MUST_BE_BOOL"
        if type(self.prefer_value_pattern) is not bool:
            return False, "PREFER_VALUE_PATTERN_MUST_BE_BOOL"

        # Reject unauthorized control characters
        for ch in self.text:
            if ord(ch) in DISALLOWED_CONTROL_CHARS:
                return False, f"CONTROL_CHARACTER_REJECTED: 0x{ord(ch):02X}"
        return True, "VALID"


@dataclass
class KeyComboParams:
    keys: List[Union[StandardKeyEnum, str]]
    max_keys: int = 4

    def validate(self) -> Tuple[bool, str]:
        if type(self.max_keys) is not int or self.max_keys <= 0 or self.max_keys > 10:
            return False, f"INVALID_MAX_KEYS: {self.max_keys!r} (must be int in [1, 10])"
        if type(self.keys) is not list or not self.keys:
            return False, "KEY_LIST_EMPTY"
        if len(self.keys) > self.max_keys:
            return False, f"TOO_MANY_KEYS: {len(self.keys)} exceeds max {self.max_keys}"

        valid_values = {k.value for k in StandardKeyEnum}
        for k in self.keys:
            if type(k) is not str and not isinstance(k, StandardKeyEnum):
                return False, f"INVALID_KEY_TYPE: {type(k).__name__}"
            val = k.value if isinstance(k, StandardKeyEnum) else str(k)
            if val not in valid_values:
                return False, f"UNAUTHORIZED_KEY: {k!r}"
        return True, "VALID"


@dataclass
class ScrollParams:
    direction: Literal["up", "down", "left", "right"] = "down"
    delta: int = 120  # Chuẩn bánh xe chuột Windows: 120 đơn vị mỗi notch
    max_delta: int = 5000

    def validate(self) -> Tuple[bool, str]:
        if type(self.direction) is not str or self.direction not in ("up", "down", "left", "right"):
            return False, f"INVALID_DIRECTION: {self.direction!r}"
        if type(self.max_delta) is not int or self.max_delta <= 0 or self.max_delta > 10000:
            return False, f"INVALID_MAX_DELTA: {self.max_delta!r} (must be int in [1, 10000])"
        if type(self.delta) is not int:
            return False, f"DELTA_MUST_BE_INT: got {type(self.delta).__name__}"
        if abs(self.delta) > self.max_delta or self.delta == 0:
            return False, f"DELTA_OUT_OF_BOUNDS: {self.delta} (must be non-zero and within [-{self.max_delta}, {self.max_delta}])"
        return True, "VALID"


# ── Canonical Hashing Utilities (Full 64-hex SHA-256) ───────────────────

def compute_canonical_element_hash(
    name: str,
    control_type: str,
    automation_id: str,
    class_name: str,
    rect: Tuple[int, int, int, int]
) -> str:
    """Tính mã băm chuẩn hoá ổn định của phần tử từ Canonical JSON (full 64 hex)."""
    payload = {
        "automation_id": automation_id,
        "class_name": class_name,
        "control_type": control_type,
        "name": name,
        "rect": list(rect)
    }
    canonical_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def compute_canonical_snapshot_hash(
    hwnd: int,
    pid: int,
    process_name: str,
    elements: List[Any]
) -> str:
    """Tính mã băm chuẩn hoá ổn định của toàn bộ cây UIA từ Canonical JSON (full 64 hex)."""
    payload = {
        "elements": [
            {
                "automation_id": getattr(e, "automation_id", ""),
                "element_hash": getattr(e, "element_hash", ""),
                "name": getattr(e, "name", ""),
                "rect": list(getattr(e, "rect", (0, 0, 0, 0))),
                "ref": getattr(e, "ref", "")
            }
            for e in elements
        ],
        "hwnd": int(hwnd),
        "pid": int(pid),
        "process_name": str(process_name).lower()
    }
    canonical_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode("utf-8")
    return f"sha256_{hashlib.sha256(canonical_bytes).hexdigest()}"


# ── Semantic Action IR ───────────────────────────────────────────────────

@dataclass
class SemanticActionIR:
    # 1. Định danh ủy quyền của JKAI Kernel
    session_id: str
    lease_id: str
    nonce: str
    issued_at: float
    expires_at: float
    approval_digest: str

    # 2. Loại hành động
    action_type: ActionType

    # 3. Ràng buộc ngữ nghĩa & định danh mục tiêu
    target_ref: str  # Bắt buộc canonical format 'eN' (ví dụ 'e1', 'e2'), không normalize
    target_hwnd: int
    target_pid: int
    target_process_name: str

    # 4. Chốt kiểm tra băm chống TOCTOU & Stale Element (Full 64 hex)
    element_hash: str
    snapshot_hash: str

    # 5. Tham số hành động có cấu trúc chặt chẽ
    parameters: Union[ClickParams, TypeTextParams, KeyComboParams, ScrollParams, FocusParams]
    snapshot_id: str = ""

    # 6. Metadata thuần túy (không tham gia quyết định an ninh)
    description: str = ""

    def validate_self_schema(self) -> Tuple[bool, str]:
        """Kiểm tra schema nội tại của đối tượng Action IR."""
        now = time.time()

        # Kiểm tra format định danh Kernel (Finding 6 Lượt 305)
        if type(self.session_id) is not str or not SESSION_ID_PATTERN.match(self.session_id):
            return False, f"INVALID_SESSION_ID_FORMAT: {self.session_id!r}"
        if type(self.lease_id) is not str or not LEASE_ID_PATTERN.match(self.lease_id):
            return False, f"INVALID_LEASE_ID_FORMAT: {self.lease_id!r}"
        if type(self.nonce) is not str or not NONCE_PATTERN.match(self.nonce):
            return False, f"INVALID_NONCE_FORMAT: {self.nonce!r}"
        if type(self.approval_digest) is not str or not DIGEST_PATTERN.match(self.approval_digest):
            return False, f"INVALID_APPROVAL_DIGEST_FORMAT: {self.approval_digest!r}"

        # Kiểm tra finite numeric trên timestamps (Finding 5 Lượt 305 - chống NaN/Inf)
        if not (isinstance(self.issued_at, (int, float)) and math.isfinite(self.issued_at)):
            return False, "ISSUED_AT_MUST_BE_FINITE_NUMERIC"
        if not (isinstance(self.expires_at, (int, float)) and math.isfinite(self.expires_at)):
            return False, "EXPIRES_AT_MUST_BE_FINITE_NUMERIC"

        # Kiểm tra clock-skew & TTL
        if self.issued_at > now + 5.0:
            return False, f"ACTION_ISSUED_IN_FUTURE: issued_at={self.issued_at} now={now}"
        if self.expires_at <= self.issued_at:
            return False, "INVALID_TTL_EXPIRES_BEFORE_ISSUED"
        if (self.expires_at - self.issued_at) > 300.0:
            return False, f"TTL_EXCEEDS_MAX_300S: {self.expires_at - self.issued_at:.1f}s"
        if now > self.expires_at:
            return False, "ACTION_EXPIRED"

        # Kiểm tra ActionType enum (Finding 4 Lượt 305)
        if not isinstance(self.action_type, ActionType):
            return False, f"INVALID_ACTION_TYPE: {self.action_type!r} (must be ActionType enum)"

        # Kiểm tra định dạng strictly canonical của target_ref (Finding 1 Lượt 303)
        if type(self.target_ref) is not str or not REF_PATTERN.match(self.target_ref):
            return False, f"INVALID_REF_FORMAT: {self.target_ref!r} (must strictly match canonical 'eN', e.g. 'e1', 'e2')"

        # Kiểm tra target identity types (Finding 3 Lượt 305)
        if type(self.target_hwnd) is not int or self.target_hwnd <= 0:
            return False, f"INVALID_TARGET_HWND: {self.target_hwnd!r} (must be positive int)"
        if type(self.target_pid) is not int or self.target_pid <= 0:
            return False, f"INVALID_TARGET_PID: {self.target_pid!r} (must be positive int)"
        if type(self.target_process_name) is not str or not self.target_process_name.strip():
            return False, "TARGET_PROCESS_NAME_MUST_BE_NON_EMPTY_STR"

        # Kiểm tra định dạng canonical hash (Finding 7 Lượt 305)
        if type(self.element_hash) is not str or not ELEMENT_HASH_PATTERN.match(self.element_hash):
            return False, f"INVALID_ELEMENT_HASH_FORMAT: {self.element_hash!r} (must be 64-hex)"
        if type(self.snapshot_hash) is not str or not SNAPSHOT_HASH_PATTERN.match(self.snapshot_hash):
            return False, f"INVALID_SNAPSHOT_HASH_FORMAT: {self.snapshot_hash!r} (must be 'sha256_<64hex>')"

        # Kiểm tra tham số theo từng loại hành động
        if not hasattr(self.parameters, "validate"):
            return False, "PARAMETERS_MISSING_VALIDATE_METHOD"
        param_ok, param_reason = self.parameters.validate()
        if not param_ok:
            return False, f"PARAMETER_INVALID: {param_reason}"

        return True, "ACTION_SCHEMA_VALID"

    ALLOWED_ROOT_FIELDS = {
        "session_id", "lease_id", "nonce", "issued_at", "expires_at",
        "approval_digest", "action_type", "target_ref", "target_hwnd",
        "target_pid", "target_process_name", "element_hash", "snapshot_hash",
        "parameters", "description", "snapshot_id"
    }
    REQUIRED_ROOT_FIELDS = {
        "session_id", "lease_id", "nonce", "issued_at", "expires_at",
        "approval_digest", "action_type", "target_ref", "target_hwnd",
        "target_pid", "target_process_name", "element_hash", "snapshot_hash",
        "parameters"
    }

    ALLOWED_PARAM_FIELDS_MAP = {
        ActionType.CLICK: {"button", "click_count", "prefer_invoke_pattern", "modifiers", "target_x", "target_y"},
        ActionType.TYPE_TEXT: {"text", "max_length", "clear_before_type", "prefer_value_pattern"},
        ActionType.KEY_COMBO: {"keys", "max_keys"},
        ActionType.SCROLL: {"direction", "delta", "max_delta"},
        ActionType.FOCUS: set(),
    }

    @classmethod
    def from_wire_dict(cls, data: Dict[str, Any]) -> "SemanticActionIR":
        """
        Exact-Schema Wire Parser (Hardened Lượt 307):
        Phân tích cú pháp an toàn từ Dictionary / JSON với chính sách Strict Whitelist:
        1. Từ chối ngay nếu xuất hiện trường lạ (unknown field) trong root dictionary.
        2. Từ chối nếu thiếu trường bắt buộc (missing field) trong root dictionary.
        3. Phân biệt chặt chẽ int vs bool, float vs bool trước khi gọi constructor.
        4. Kiểm tra kiểu của toàn bộ các trường gốc.
        5. Từ chối trường lạ trong parameters dictionary theo từng ActionType.
        6. Kiểm tra kiểu của toàn bộ tham số bên trong parameters.
        7. Chạy validate_self_schema() toàn diện trước khi trả về instance.
        """
        if type(data) is not dict:
            raise ValueError("WIRE_DATA_MUST_BE_DICT")

        # 1. Kiểm tra trường lạ và trường bắt buộc ở root
        data_keys = set(data.keys())
        unknown_root = data_keys - cls.ALLOWED_ROOT_FIELDS
        if unknown_root:
            raise ValueError(f"UNKNOWN_ROOT_FIELDS: {sorted(unknown_root)}")

        missing_root = cls.REQUIRED_ROOT_FIELDS - data_keys
        if missing_root:
            raise ValueError(f"MISSING_ROOT_FIELDS: {sorted(missing_root)}")

        # 2. Kiểm tra type của các trường gốc
        for str_field in ("session_id", "lease_id", "nonce", "approval_digest", "target_ref", "target_process_name", "element_hash", "snapshot_hash"):
            val = data[str_field]
            if type(val) is not str:
                raise ValueError(f"FIELD_MUST_BE_STR: {str_field} (got {type(val).__name__})")

        if "description" in data and type(data["description"]) is not str:
            raise ValueError(f"FIELD_MUST_BE_STR: description (got {type(data['description']).__name__})")

        # Numeric fields at root (từ chối bool)
        for int_field in ("target_hwnd", "target_pid"):
            val = data[int_field]
            if type(val) is not int:
                raise ValueError(f"FIELD_MUST_BE_INT: {int_field} (got {type(val).__name__})")

        for time_field in ("issued_at", "expires_at"):
            val = data[time_field]
            if type(val) is bool or not isinstance(val, (int, float)):
                raise ValueError(f"FIELD_MUST_BE_NUMERIC: {time_field} (got {type(val).__name__})")

        # ActionType
        raw_type = data["action_type"]
        if type(raw_type) is not str:
            raise ValueError(f"ACTION_TYPE_MUST_BE_STR: got {type(raw_type).__name__}")
        try:
            act_type = ActionType(raw_type)
        except ValueError:
            raise ValueError(f"UNRECOGNIZED_ACTION_TYPE: {raw_type!r}")

        # 3. Parameters dictionary allowlist & type checks
        raw_params = data["parameters"]
        if type(raw_params) is not dict:
            raise ValueError("PARAMETERS_MUST_BE_DICT")

        allowed_params = cls.ALLOWED_PARAM_FIELDS_MAP[act_type]
        unknown_params = set(raw_params.keys()) - allowed_params
        if unknown_params:
            raise ValueError(f"UNKNOWN_PARAM_FIELDS: {sorted(unknown_params)}")

        # Parse parameters strictly based on ActionType
        if act_type == ActionType.FOCUS:
            parsed_params = FocusParams()
        elif act_type == ActionType.CLICK:
            btn = raw_params.get("button", "left")
            if type(btn) is not str:
                raise ValueError(f"BUTTON_MUST_BE_STR: got {type(btn).__name__}")
            cnt = raw_params.get("click_count", 1)
            if type(cnt) is not int:
                raise ValueError(f"CLICK_COUNT_MUST_BE_INT: got {type(cnt).__name__}")
            pref = raw_params.get("prefer_invoke_pattern", True)
            if type(pref) is not bool:
                raise ValueError(f"PREFER_INVOKE_PATTERN_MUST_BE_BOOL: got {type(pref).__name__}")

            raw_mods = raw_params.get("modifiers", ["none"])
            if not isinstance(raw_mods, list):
                raise ValueError("MODIFIERS_MUST_BE_LIST")
            tx = raw_params.get("target_x")
            ty = raw_params.get("target_y")

            parsed_params = ClickParams(
                button=btn,
                click_count=cnt,
                prefer_invoke_pattern=pref,
                modifiers=raw_mods,
                target_x=tx,
                target_y=ty
            )
        elif act_type == ActionType.TYPE_TEXT:
            txt = raw_params.get("text", "")
            if type(txt) is not str:
                raise ValueError(f"TEXT_MUST_BE_STR: got {type(txt).__name__}")
            maxlen = raw_params.get("max_length", 1000)
            if type(maxlen) is not int:
                raise ValueError(f"MAX_LENGTH_MUST_BE_INT: got {type(maxlen).__name__}")
            clr = raw_params.get("clear_before_type", False)
            if type(clr) is not bool:
                raise ValueError(f"CLEAR_BEFORE_TYPE_MUST_BE_BOOL: got {type(clr).__name__}")
            pref_val = raw_params.get("prefer_value_pattern", True)
            if type(pref_val) is not bool:
                raise ValueError(f"PREFER_VALUE_PATTERN_MUST_BE_BOOL: got {type(pref_val).__name__}")

            parsed_params = TypeTextParams(
                text=txt,
                max_length=maxlen,
                clear_before_type=clr,
                prefer_value_pattern=pref_val
            )
        elif act_type == ActionType.KEY_COMBO:
            keys = raw_params.get("keys", [])
            if type(keys) is not list:
                raise ValueError(f"KEYS_MUST_BE_LIST: got {type(keys).__name__}")
            maxkeys = raw_params.get("max_keys", 4)
            if type(maxkeys) is not int:
                raise ValueError(f"MAX_KEYS_MUST_BE_INT: got {type(maxkeys).__name__}")

            parsed_params = KeyComboParams(
                keys=keys,
                max_keys=maxkeys
            )
        elif act_type == ActionType.SCROLL:
            direction = raw_params.get("direction", "down")
            if type(direction) is not str:
                raise ValueError(f"DIRECTION_MUST_BE_STR: got {type(direction).__name__}")
            delta = raw_params.get("delta", 120)
            if type(delta) is not int:
                raise ValueError(f"DELTA_MUST_BE_INT: got {type(delta).__name__}")
            maxdelta = raw_params.get("max_delta", 5000)
            if type(maxdelta) is not int:
                raise ValueError(f"MAX_DELTA_MUST_BE_INT: got {type(maxdelta).__name__}")

            parsed_params = ScrollParams(
                direction=direction,
                delta=delta,
                max_delta=maxdelta
            )
        else:
            raise ValueError(f"UNSUPPORTED_ACTION_TYPE: {act_type}")

        action = cls(
            session_id=data["session_id"],
            lease_id=data["lease_id"],
            nonce=data["nonce"],
            issued_at=float(data["issued_at"]),
            expires_at=float(data["expires_at"]),
            approval_digest=data["approval_digest"],
            action_type=act_type,
            target_ref=data["target_ref"],
            target_hwnd=data["target_hwnd"],
            target_pid=data["target_pid"],
            target_process_name=data["target_process_name"],
            element_hash=data["element_hash"],
            snapshot_hash=data["snapshot_hash"],
            parameters=parsed_params,
            snapshot_id=data.get("snapshot_id", ""),
            description=data.get("description", "")
        )

        ok, reason = action.validate_self_schema()
        if not ok:
            raise ValueError(f"ACTION_SCHEMA_VALIDATION_FAILED: {reason}")

        return action


# ── Anti-TOCTOU & App Scope Validator ────────────────────────────────────

class SemanticActionValidator:
    """
    Bộ thẩm định độc lập kiểm tra tính hợp lệ của Action IR đối chiếu với Snapshot UIA thực tế.
    Tuân thủ nguyên tắc Fail-Closed: Mọi sai lệch về HWND, PID, Process, Snapshot Hash hoặc
    Element Hash đều dẫn đến từ chối thực thi với mã lỗi xác thực rõ ràng.

    Destructive keyword list and process scope come from the policy SSoT
    (config/security/desktop_app_allowlist.json) rather than hard-coded constants.
    """

    EXPECTED_PARAMS_MAP = {
        ActionType.CLICK: ClickParams,
        ActionType.TYPE_TEXT: TypeTextParams,
        ActionType.KEY_COMBO: KeyComboParams,
        ActionType.SCROLL: ScrollParams,
        ActionType.FOCUS: FocusParams,
    }

    @classmethod
    def _destructive_keywords(cls) -> set:
        from services.ai_desktop.app_policy import get_policy
        return set(get_policy().destructive_keywords)

    @classmethod
    def _process_scope(cls, allowed_processes: Optional[set]) -> set:
        if allowed_processes is not None:
            return {str(p).casefold().strip() for p in allowed_processes}
        from services.ai_desktop.app_policy import get_policy
        return set(get_policy().allowed_processes)

    @classmethod
    def validate_action_against_snapshot(
        cls,
        action: SemanticActionIR,
        snapshot: Any,
        allowed_processes: Optional[set] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Thẩm định hành động đối chiếu với Snapshot UIA:
        1. Kiểm tra tính toàn vẹn nội tại của action schema & TTL & Clock-skew.
        2. Kiểm tra tương thích 1-1 giữa ActionType và Parameter Class (Finding 5 Lượt 303).
        3. Kiểm tra App Allowlist Scope an toàn (Finding 4 Lượt 303).
        4. Kiểm tra ràng buộc HWND, PID, và Process Name.
        5. Kiểm tra mã băm Snapshot Hash (chống UI Drift).
        6. Kiểm tra sự tồn tại của target_ref trong snapshot.
        7. Kiểm tra mã băm Element Hash (chống Stale Element).
        8. Kiểm tra trạng thái khả dụng của phần tử (is_enabled, is_visible).
        """
        details: Dict[str, Any] = {}

        # 1. Kiểm tra Schema nội tại
        ok, reason = action.validate_self_schema()
        if not ok:
            return False, reason, details

        # 2. Kiểm tra Action Type / Parameter Pairing (Finding 5 Lượt 303)
        expected_param_cls = cls.EXPECTED_PARAMS_MAP.get(action.action_type)
        if expected_param_cls is None or not isinstance(action.parameters, expected_param_cls):
            actual_cls_name = type(action.parameters).__name__
            exp_name = expected_param_cls.__name__ if expected_param_cls else "Unknown"
            return False, f"ACTION_PARAMETER_MISMATCH: {action.action_type.value} requires {exp_name}, got {actual_cls_name}", details

        # 3. Kiểm tra App Allowlist an toàn (Finding 4 Lượt 303: hỗ trợ set() rỗng không bị fallback)
        active_scope = cls._process_scope(allowed_processes)
        proc_clean = action.target_process_name.lower().strip()
        if proc_clean not in active_scope:
            return False, f"PROCESS_NOT_IN_ALLOWLIST: {action.target_process_name!r}", details

        # 4. Kiểm tra ràng buộc HWND, PID và Process Name
        if int(action.target_hwnd) != int(snapshot.hwnd):
            return False, f"TARGET_HWND_MISMATCH: action={action.target_hwnd} snapshot={snapshot.hwnd}", details
        if int(action.target_pid) != int(snapshot.pid):
            return False, f"TARGET_PID_MISMATCH: action={action.target_pid} snapshot={snapshot.pid}", details
        if proc_clean != str(snapshot.process_name).lower().strip():
            return False, f"PROCESS_NAME_MISMATCH: action={proc_clean} snapshot={snapshot.process_name}", details

        # 5. Kiểm tra mã băm Snapshot Hash (chống UI Drift)
        if action.snapshot_hash != snapshot.snapshot_hash:
            return False, f"SNAPSHOT_HASH_DRIFT: action={action.snapshot_hash} current={snapshot.snapshot_hash}", details

        # 6. Kiểm tra sự tồn tại của target_ref trong snapshot (strictly canonical)
        ref_map = getattr(snapshot, "ref_map", {})
        if action.target_ref not in ref_map:
            return False, f"REF_NOT_FOUND_IN_SNAPSHOT: {action.target_ref}", details

        target_el = ref_map[action.target_ref]
        details["target_element_name"] = target_el.name
        details["target_control_type"] = target_el.control_type
        details["target_rect"] = list(target_el.rect)

        # 7. Kiểm tra mã băm Element Hash (chống Stale Element)
        current_el_hash = getattr(target_el, "element_hash", "")
        if action.element_hash != current_el_hash:
            return False, f"STALE_ELEMENT_HASH: action={action.element_hash} current={current_el_hash}", details

        # 8. Kiểm tra trạng thái khả dụng của phần tử
        if not target_el.is_enabled:
            return False, f"ELEMENT_DISABLED: {action.target_ref} ({target_el.name})", details
        if not target_el.is_visible:
            return False, f"ELEMENT_NOT_VISIBLE: {action.target_ref} ({target_el.name})", details

        # 9. Kiểm tra tính tương thích ngữ nghĩa và rào chắn an toàn Phase 3
        if action.action_type == ActionType.CLICK:
            # 9.1 Chặn đứng hành vi phá hoại (Destructive Semantics Deny)
            el_name_lower = target_el.name.lower()
            el_id_lower = target_el.automation_id.lower()
            for kw in cls._destructive_keywords():
                if kw in el_name_lower or kw in el_id_lower:
                    return False, f"CLICK_DESTRUCTIVE_TARGET_BLOCKED: {kw}", details

            # 9.2 Kiểm tra toạ độ nếu có (luôn bounds-check, không có chế độ bỏ qua)
            if isinstance(action.parameters, ClickParams):
                cp = action.parameters
                if cp.target_x is not None and cp.target_y is not None:
                    l, t, r, b = target_el.rect
                    if not (l <= cp.target_x <= r and t <= cp.target_y <= b):
                        return False, f"CLICK_OUT_OF_BOUNDS_REJECTED: ({cp.target_x}, {cp.target_y}) outside bounds {target_el.rect}", details

            # 9.3 Kiểm tra khả năng click (InvokePattern / TogglePattern / Button)
            is_clickable = (
                "InvokePattern" in target_el.supported_patterns
                or "TogglePattern" in target_el.supported_patterns
                or target_el.control_type.lower() in ("button", "menuitem", "checkbox", "radiobutton", "tabitem")
            )
            if not is_clickable:
                return False, f"CLICK_INVOKABLE_PATTERN_REQUIRED: {target_el.control_type} does not support click/invoke", details
            details["supports_invoke_pattern"] = "InvokePattern" in target_el.supported_patterns

        elif action.action_type == ActionType.FOCUS:
            details["can_focus"] = target_el.is_enabled and target_el.is_visible

        elif action.action_type == ActionType.TYPE_TEXT:
            # Nhập văn bản yêu cầu Edit/Document hoặc có ValuePattern
            is_text_receiver = (
                target_el.control_type in ("Edit", "Document", "ComboBox")
                or "ValuePattern" in target_el.supported_patterns
                or "TextPattern" in target_el.supported_patterns
            )
            if not is_text_receiver:
                return False, f"ELEMENT_CANNOT_RECEIVE_TEXT: {target_el.control_type}", details

        return True, "ACTION_VALIDATED_READY_FOR_GATED_EXECUTION", details

    @classmethod
    def revalidate_target_identity(
        cls,
        action: SemanticActionIR,
        live_snapshot: Any,
        allowed_processes: Optional[set] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        [LIVE PRE-DISPATCH REVALIDATION BOUNDARY] (Lượt 311 OpenCode Requirement):
        Ranh giới thẩm định danh tính mục tiêu tức thì ngay trước khi lệnh được chuyển tới executor.
        Bảo đảm rằng:
        1. Action schema và TTL vẫn còn hiệu lực tại thời điểm t_dispatch (now <= expires_at).
        2. Window HWND của live_snapshot còn sống và trùng khớp action.target_hwnd.
        3. PID của live_snapshot trùng khớp action.target_pid.
        4. Tên tiến trình của live_snapshot trùng khớp action.target_process_name và nằm trong allowed_processes.
        5. Snapshot hash không bị UI drift (khớp action.snapshot_hash).
        6. Target ref tồn tại trong live_snapshot và element_hash không bị stale (khớp action.element_hash).
        7. Target element đang visible và enabled.
        Nếu bất kỳ điều kiện nào sai lệch (cửa sổ bị đóng, switch app, element biến mất),
        hệ thống lập tức REJECT với mã lỗi rõ ràng, ngăn chặn 100% việc dispatch lệnh mù.
        """
        now = time.time()
        if now > action.expires_at:
            return False, "ACTION_EXPIRED_BEFORE_DISPATCH", {}

        return cls.validate_action_against_snapshot(
            action, live_snapshot, allowed_processes=allowed_processes
        )

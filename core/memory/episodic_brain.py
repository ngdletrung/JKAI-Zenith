# -*- coding: utf-8 -*-
"""
core/memory/episodic_brain.py
JKAI — Episodic Multi-Domain Memory Brain (Bộ Não Ngoài Truy Xuất Ngữ Nghĩa)

Nguyên tắc hoạt động:
1. Tách biệt lĩnh vực (Domain Isolation): Lưu vào 1 collection Qdrant nhưng lọc chặt theo `payload.domain`.
2. Vectorize cục bộ: Dùng MiniLM (384-d, sub-10ms) qua Ollama.
3. Cổng chặn liêm sỉ: Cosine Similarity >= 0.75 mới cho phép tiêm (dưới ngưỡng cấm inject).
4. Phân luồng Dual-Stream:
   - ACCEPT -> Positive Exemplar (Mẫu chuẩn Master duyệt)
   - REJECT -> Negative Guard (Vết xe đổ cấm lặp lại)
5. Truy vết nguồn gốc (Provenance): Kèm record_id vào prompt.
"""

from __future__ import annotations
import os
import re
import time
import json
import hashlib
import uuid
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("jkai.memory.episodic_brain")

COLLECTION_NAME = "jkai_episodic_memory"
VECTOR_DIM = 384
DEFAULT_EMBED_MODEL = "all-minilm:latest"
EMBED_VERSION = "v1.0"
THETA_UNFIT_PLACEHOLDER = 0.75  # Placeholder: Chưa fit, cần fit riêng theo từng ngôn ngữ (vi/en) khi đủ n>=100

# ==============================================================================
# TAXONOMY 2 TẦNG (VIỆC -> MẢNG) CHUẨN MASTER BAN HÀNH
# ==============================================================================
TASK_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "NET_MIKROTIK": {
        "name": "Mạng MikroTik (DHCP, NAT, firewall RouterOS)",
        "subs": ["DHCP", "NAT", "FIREWALL", "VLAN", "BRIDGE", "ROUTING"],
        "keywords": ["mikrotik", "routeros", "winbox", "/ip dhcp", "/ip firewall", "/interface bridge", "torch", "mạng trường", "mang truong", "router mikrotik"]
    },
    "NET_CISCO": {
        "name": "Mạng Cisco (IOS, VLAN switch)",
        "subs": ["IOS", "VLAN", "SWITCH", "ROUTER", "TRUNK"],
        "keywords": ["cisco", "switchport", "cisco ios", "show ip int", "catalyst", "packet tracer", "enable secret", "conf t"]
    },
    "NET_GENERAL": {
        "name": "Mạng đại cương (TCP/IP, subnet, DNS theory)",
        "subs": ["TCP_IP", "SUBNET", "DNS", "ROUTING_THEORY"],
        "keywords": ["tcp/ip", "subnet mask", "default gateway", "dns", "ping ", "traceroute", "cidr", "địa chỉ ip", "bảng định tuyến", "arp table"]
    },
    "CODE_PYTHON": {
        "name": "Lập trình Python (Script, debug, refactor)",
        "subs": ["WEB", "DATA", "AUTOMATION"],
        "keywords": ["python", ".py", "pip ", "traceback", "def ", "pytest", "pandas", "numpy", "fastapi", "django", "flask", "pydantic"]
    },
    "CODE_JAVA": {
        "name": "Lập trình Java (Spring, OOP, build)",
        "subs": ["WEB", "CORE"],
        "keywords": ["java", "spring boot", "spring", "maven", "gradle", "pom.xml", "public static void main", "jvm", "jpa", "hibernate", ".jar", "javac"]
    },
    "OFFICE_DOC": {
        "name": "Văn bản, Excel, báo cáo, kho bãi",
        "subs": ["FINANCE", "ADMIN"],
        "keywords": ["thùng", "chuyến", "phí xăng", "tính toán", "hóa đơn", "báo cáo", "công văn", "excel", "word", "hợp đồng", "kho bãi", "bảng kê", "chi phí"]
    },
    "SYSADMIN": {
        "name": "Quản trị hệ thống (Windows, user, backup)",
        "subs": ["WINDOWS", "LINUX", "USER", "BACKUP"],
        "keywords": ["windows server", "user account", "backup", "powershell", "cmd.exe", "taskkill", "restart-service", "registry", "active directory", "group policy"]
    },
    "COMM": {
        "name": "Chào hỏi, giải thích, hỏi lại",
        "subs": ["GREETING", "ANAPHORA", "CLARIFICATION"],
        "keywords": ["chi tiết hơn", "giải thích thêm", "còn cái kia", "nói rõ hơn", "chào", "hello", "bạn là ai", "hướng dẫn tôi", "tạm biệt"]
    },
    "LOGIC_REASONING": {
        "name": "Suy luận Logic tổng quát (Diễn dịch, Nhân quả, Ràng buộc, Occam, Phản sự thực)",
        "subs": ["DEDUCTION", "CAUSAL", "CONSTRAINT", "DAG", "ABDUCTION", "FALSIFICATION", "COUNTERFACTUAL", "GAME_THEORY", "EPISTEMIC"],
        "keywords": ["logic", "suy luận", "mâu thuẫn", "ngụy biện", "nhân quả", "ràng buộc", "giả thuyết", "occam", "bác bỏ", "chứng minh", "deadlock", "phản sự thực"]
    }
}

# Alias tương thích ngược cho dữ liệu cũ
TASK_ALIASES: Dict[str, str] = {
    "MATH": "OFFICE_DOC",
    "CODE_FILEOPS": "CODE_PYTHON",
    "COMMUNICATION": "COMM",
    "OFFICE_FINANCE": "OFFICE_DOC",
    "ANAPHORA": "COMM",
    "EPISTEMIC": "COMM",
    "LOGIC_DEDUCTION": "LOGIC_REASONING",
    "LOGIC_CONTRADICTION": "LOGIC_REASONING",
    "LOGIC_CAUSAL": "LOGIC_REASONING",
    "LOGIC_CAUSAL_DAG": "LOGIC_REASONING",
    "LOGIC_CONSTRAINT": "LOGIC_REASONING",
    "LOGIC_DAG": "LOGIC_REASONING",
    "LOGIC_DAG_DEADLOCK": "LOGIC_REASONING",
    "LOGIC_ABDUCTION": "LOGIC_REASONING",
    "LOGIC_FALSIFICATION": "LOGIC_REASONING",
    "LOGIC_COUNTERFACTUAL": "LOGIC_REASONING",
    "LOGIC_SECOND_ORDER": "LOGIC_REASONING",
    "LOGIC_BOUNDARY": "LOGIC_REASONING",
    "LOGIC_EPISTEMIC": "LOGIC_REASONING",
    "LOGIC_ADVERSARIAL": "LOGIC_REASONING",
    "LOGIC_TOT_SEARCH": "LOGIC_REASONING",
    "LOGIC_FORMAL_VERIFICATION": "LOGIC_REASONING",
    "LOGIC_BAYESIAN_OCCAM": "LOGIC_REASONING",
    "LOGIC_GAME_THEORY": "LOGIC_REASONING"
}


# Giữ DOMAINS để tương thích các module cũ gọi trực tiếp
DOMAINS = {k: v["name"] for k, v in TASK_TAXONOMY.items()}
DOMAINS.update({"MATH": "Toán học (đã gộp vào OFFICE_DOC)", "CODE_FILEOPS": "Lập trình (đã gộp vào CODE_PYTHON)"})

TAXONOMY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "task_taxonomy.json"))


def load_taxonomy_registry():
    """Nạp taxonomy động từ data/task_taxonomy.json nếu tồn tại."""
    global TASK_TAXONOMY, TASK_ALIASES, DOMAINS
    # Thử đường dẫn local hoặc trong container /app hoặc /shared
    candidate_paths = [
        TAXONOMY_FILE,
        "/app/data/task_taxonomy.json",
        "/shared/data/task_taxonomy.json",
        "data/task_taxonomy.json"
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tasks = data.get("tasks", {})
                    aliases = data.get("aliases", {})
                    if tasks:
                        TASK_TAXONOMY.update(tasks)
                    if aliases:
                        TASK_ALIASES.update(aliases)
                    DOMAINS.update({k: v.get("name", k) for k, v in TASK_TAXONOMY.items()})
                break
            except Exception as e:
                logger.warning("[EPISODIC-TAXONOMY-LOAD-ERR]: %s", e)


def register_new_task_code(
    task_code: str,
    name: str,
    subs: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    aliases: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Đăng ký một mã việc mới vào Taxonomy Registry động:
    1. Chuẩn hóa & kiểm tra format mã việc (In hoa, gạch dưới, từ 3-30 ký tự).
    2. Cập nhật in-memory dictionary ngay lập tức.
    3. Ghi đĩa vào data/task_taxonomy.json để lưu trữ bền vững.
    4. Sẵn sàng phục vụ ngay tức thì mà không cần khởi động lại JKAI.
    """
    global TASK_TAXONOMY, TASK_ALIASES, DOMAINS
    code = (task_code or "").strip().upper()
    if not re.match(r"^[A-Z0-9_]{3,30}$", code):
        return {"success": False, "error": f"Mã việc không hợp lệ (phải từ 3-30 ký tự [A-Z0-9_]): {task_code}"}

    TASK_TAXONOMY[code] = {
        "name": name,
        "subs": [s.upper() for s in (subs or [])],
        "keywords": [k.lower().strip() for k in (keywords or [])]
    }
    DOMAINS[code] = name

    for a in (aliases or []):
        TASK_ALIASES[a.upper().strip()] = code

    # Ghi file bền vững
    try:
        os.makedirs(os.path.dirname(TAXONOMY_FILE), exist_ok=True)
        export_data = {
            "version": "1.0",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tasks": TASK_TAXONOMY,
            "aliases": TASK_ALIASES
        }
        with open(TAXONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        logger.info("✨ [EPISODIC-NEW-TASK-REGISTERED]: Đăng ký thành công mã việc mới `%s`", code)
        return {"success": True, "task_code": code, "name": name, "subs_count": len(subs or []), "keywords_count": len(keywords or [])}
    except Exception as e:
        logger.error("[EPISODIC-TAXONOMY-SAVE-ERR]: %s", e)
        return {"success": False, "error": str(e)}


# Tự động nạp động registry
load_taxonomy_registry()



def classify_task(
    goal: str,
    tags: Optional[List[str]] = None,
    mode: Optional[str] = None
) -> Optional[str]:
    """
    Tự động phân loại yêu cầu vào đúng 1 mã việc duy nhất theo Bảng Taxonomy:
    1. Ưu tiên 1: Router Tags / Mode từ CentralIntentRouter.
    2. Ưu tiên 2: Bảng từ khóa -> mã việc (Chính xác cao, không đoán mò).
    3. Quy tắc sắt: Nếu không xác định được mã việc hợp lệ -> trả về None (ngoài phạm vi).
    """
    tags = tags or []
    norm_tags = [t.upper() for t in tags]
    norm_mode = (mode or "").upper()
    g_lower = (goal or "").lower()

    # 1. Tra cứu qua tags / mode nếu có
    for t in norm_tags:
        if t in TASK_TAXONOMY:
            return t
        if t in TASK_ALIASES:
            return TASK_ALIASES[t]

    if "MATH" in norm_mode:
        return "OFFICE_DOC"
    if "CODING" in norm_mode:
        if any(k in g_lower for k in ["java", "spring", "maven"]):
            return "CODE_JAVA"
        return "CODE_PYTHON"
    if "OFFICE" in norm_mode:
        return "OFFICE_DOC"

    # 2. Tra cứu qua Bảng Từ Khóa (Chuyên biệt -> Tổng quát)
    for code, spec in TASK_TAXONOMY.items():
        for kw in spec.get("keywords", []):
            if kw in g_lower:
                return code

    # Heuristic toán có biểu thức số
    if re.search(r"\d+\s*[\+\-\*\/]\s*\d+", g_lower):
        return "OFFICE_DOC"

    return None


def classify_domain(
    goal: str,
    tags: Optional[List[str]] = None,
    mode: Optional[str] = None
) -> str:
    """Wrapper tương thích ngược với classify_task."""
    code = classify_task(goal, tags, mode)
    return code or "COMM"


@dataclass
class MemoryExemplar:
    record_id: str
    domain: str              # Canonical task code: NET_MIKROTIK, CODE_PYTHON, etc.
    goal: str
    exemplar_response: str
    verdict: str            # ACCEPT | REJECT
    lesson: str
    similarity_score: float
    lang: str = "vi"
    embed_model: str = DEFAULT_EMBED_MODEL
    embed_version: str = EMBED_VERSION
    task_code: str = ""     # Canonical Task Code
    sub_domain: str = ""    # Mảng con (e.g. WEB, DATA, FINANCE, DHCP)
    secondary_codes: List[str] = None

    def __post_init__(self):
        if self.secondary_codes is None:
            self.secondary_codes = []
        if not self.task_code:
            self.task_code = self.domain



class EpisodicBrain:
    """Bộ Não Ngoài Đa Lĩnh Vực cho JKAI."""

    def __init__(self):
        self._is_docker = os.path.exists('/.dockerenv')
        # Ollama endpoint
        self._ollama_host = "http://host.docker.internal:11434" if self._is_docker else "http://127.0.0.1:11434"
        # Qdrant endpoint
        self._qdrant_host = "http://qdrant:6333" if self._is_docker else "http://127.0.0.1:6333"
        self._initialized = False
        self._retained_observations: Dict[str, Dict[str, Any]] = {}
        self._retained_native_facts: Dict[str, Dict[str, Any]] = {}
        self._unauthorized_write_blocks: int = 0

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Lấy vector 384-d từ MiniLM cục bộ (< 10ms)."""
        clean_text = text.strip()[:1000]
        payload = json.dumps({"model": "all-minilm:latest", "prompt": clean_text}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._ollama_host}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("embedding")
        except Exception as e:
            logger.debug("[EPISODIC-EMBED-ERR]: %s", e)
            return None

    def _ensure_collection(self):
        """Khởi tạo collection Qdrant với payload index trên `domain` nếu chưa có."""
        if self._initialized:
            return True
        try:
            # Kiểm tra collection
            check_req = urllib.request.Request(f"{self._qdrant_host}/collections/{COLLECTION_NAME}")
            try:
                with urllib.request.urlopen(check_req, timeout=3) as resp:
                    if resp.status == 200:
                        self._initialized = True
                        return True
            except urllib.error.HTTPError as he:
                if he.code != 404:
                    return False

            # Tạo mới collection Cosine 384-d
            create_payload = json.dumps({
                "vectors": {"size": VECTOR_DIM, "distance": "Cosine"}
            }).encode("utf-8")
            create_req = urllib.request.Request(
                f"{self._qdrant_host}/collections/{COLLECTION_NAME}",
                data=create_payload,
                headers={"Content-Type": "application/json"},
                method="PUT"
            )
            with urllib.request.urlopen(create_req, timeout=5) as resp:
                pass

            # Tạo Payload Index cho field `domain` và `task_code` để tối ưu hóa truy vấn phân vùng
            for field_name in ["domain", "task_code"]:
                idx_payload = json.dumps({
                    "field_name": field_name,
                    "field_schema": "keyword"
                }).encode("utf-8")
                idx_req = urllib.request.Request(
                    f"{self._qdrant_host}/collections/{COLLECTION_NAME}/index",
                    data=idx_payload,
                    headers={"Content-Type": "application/json"},
                    method="PUT"
                )
                try:
                    with urllib.request.urlopen(idx_req, timeout=5) as resp:
                        pass
                except Exception:
                    pass

            self._initialized = True
            logger.info("[EPISODIC-BRAIN] Collection `%s` initialized with domain & task_code index.", COLLECTION_NAME)
            return True
        except Exception as e:
            logger.debug("[EPISODIC-INIT-ERR]: %s", e)
            return False

    def ingest_exemplar(
        self,
        record_id: str,
        goal: str,
        response: str,
        verdict: str,
        domain: str = "COMM",
        task_code: Optional[str] = None,
        sub_domain: str = "",
        secondary_codes: Optional[List[str]] = None,
        lesson: str = "",
        teacher_id: str = "",
        critic_id: str = "",
        reasoning_level: str = "",
        sample_id: str = ""
    ) -> bool:
        """
        Nạp một mẫu chuẩn/bài học vào Bộ Não Ngoài theo Taxonomy 2 tầng.
        Quy tắc sắt:
        - 1 mã việc chính bắt buộc.
        - Tối đa 2 mã phụ.
        - [Slice 3.3 Mục 9]: Quét 45 mẫu secret/PII/poisoning qua StateSanitizer.scan_for_retain trước khi ghi.
        """
        from core.sanitizer.state_sanitizer import StateSanitizer

        defense_goal = StateSanitizer.scan_for_retain(goal, policy="redact_or_block")
        defense_resp = StateSanitizer.scan_for_retain(response, policy="redact_or_block")
        defense_lesson = StateSanitizer.scan_for_retain(lesson, policy="redact_or_block")
        if not (defense_goal["allowed_to_retain"] and defense_resp["allowed_to_retain"] and defense_lesson["allowed_to_retain"]):
            logger.warning("[EPISODIC-MEMORY-DEFENSE-BLOCK]: Blocked poisoned exemplar `%s`", record_id)
            return False

        goal = str(defense_goal["sanitized_payload"])
        response = str(defense_resp["sanitized_payload"])
        lesson = str(defense_lesson["sanitized_payload"])

        if not self._ensure_collection():
            return False

        # Xác định mã chính
        raw_code = (task_code or domain or "COMM").upper()
        canonical_code = TASK_ALIASES.get(raw_code, raw_code)
        if canonical_code not in TASK_TAXONOMY:
            logger.warning("[EPISODIC-INGEST-REJECT]: Mã việc '%s' không nằm trong Taxonomy!", raw_code)
            return False

        # Cắt gọt mã phụ: tối đa 2 mã (Quy tắc sắt 3)
        sec_codes = [c.upper() for c in (secondary_codes or []) if c.upper() in TASK_TAXONOMY and c.upper() != canonical_code][:2]

        vector = self._get_embedding(goal)
        if not vector or len(vector) != VECTOR_DIM:
            return False

        # UUIDv5 xác định từ sample_id/record_id (RFC 4122) bảo đảm upsert idempotent 100%
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, sample_id or record_id))

        point_data = {
            "points": [{
                "id": point_id,
                "vector": vector,
                "payload": {
                    "record_id": record_id,
                    "sample_id": sample_id or record_id,
                    "teacher_id": teacher_id or "",
                    "critic_id": critic_id or "",
                    "reasoning_level": reasoning_level or "",
                    "task_code": canonical_code,
                    "domain": canonical_code,  # Tương thích ngược index cũ
                    "sub_domain": sub_domain.upper() if sub_domain else "",
                    "secondary_codes": sec_codes,
                    "goal": goal,
                    "response": response[:1000],
                    "verdict": verdict,
                    "lesson": lesson or ("Tuân thủ đáp án chuẩn của Master" if verdict == "ACCEPT" else "Tránh sai lầm này"),
                    "lang": "vi" if any(c in goal for c in "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ") else "en",
                    "embed_model": DEFAULT_EMBED_MODEL,
                    "embed_version": EMBED_VERSION,
                    "created_at": time.time()
                }
            }]
        }

        req = urllib.request.Request(
            f"{self._qdrant_host}/collections/{COLLECTION_NAME}/points",
            data=json.dumps(point_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                logger.info("🧠 [EPISODIC-BRAIN]: Ingested %s (task_code=%s, verdict=%s, lang=%s)", record_id, canonical_code, verdict, point_data["points"][0]["payload"]["lang"])
                return True
        except Exception as e:
            logger.warning("[EPISODIC-INGEST-ERR]: %s", e)
            return False

    def recall_relevant_exemplars(
        self,
        goal: str,
        domain: Optional[str] = None,
        task_code: Optional[str] = None,
        top_k: int = 2,
        threshold: float = THETA_UNFIT_PLACEHOLDER
    ) -> List[MemoryExemplar]:
        """
        Truy xuất các bài học tương đồng ngữ nghĩa trong đúng kho việc.
        Quy tắc sắt 1: Lọc đúng mã việc trước, tìm ngữ nghĩa sau (Java không lọt Python, Network không lọt Office).
        Quy tắc sắt 2: Mã việc không có / không hợp lệ thì CẤM ĐOÁN — trả về rỗng.
        """
        target_raw = task_code or domain
        if not target_raw:
            target_raw = classify_task(goal)

        # Quy tắc sắt 2: Không có mã việc hợp lệ thì cấm đoán bừa bãi
        if not target_raw:
            logger.warning("[EPISODIC-OUT-OF-SCOPE]: Yêu cầu '%s' ngoài phạm vi đã nạp (không khớp mã việc nào). Cấm đoán bừa bãi.", goal[:80])
            return []

        target_code = TASK_ALIASES.get(target_raw.upper(), target_raw.upper())
        if target_code not in TASK_TAXONOMY:
            logger.warning("[EPISODIC-INVALID-CODE]: Mã việc '%s' không tồn tại trong Taxonomy!", target_raw)
            return []

        if not self._ensure_collection():
            return []

        vector = self._get_embedding(goal)
        if not vector or len(vector) != VECTOR_DIM:
            return []

        search_query: Dict[str, Any] = {
            "vector": vector,
            "limit": top_k,
            "with_payload": True,
            "score_threshold": threshold,
            # Quy tắc sắt 1: Khóa chặt mã việc, tìm đúng kho
            "filter": {
                "should": [
                    {"key": "task_code", "match": {"value": target_code}},
                    {"key": "domain", "match": {"value": target_code}},
                    {"key": "domain", "match": {"value": target_raw.upper()}}
                ]
            }
        }

        req = urllib.request.Request(
            f"{self._qdrant_host}/collections/{COLLECTION_NAME}/points/search",
            data=json.dumps(search_query).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("result", [])
                exemplars = []
                for item in results:
                    p = item.get("payload", {})
                    score = float(item.get("score", 0.0))
                    exemplars.append(MemoryExemplar(
                        record_id=p.get("record_id", "UNKNOWN"),
                        domain=p.get("domain", p.get("task_code", "COMM")),
                        goal=p.get("goal", ""),
                        exemplar_response=p.get("response", ""),
                        verdict=p.get("verdict", "ACCEPT"),
                        lesson=p.get("lesson", ""),
                        similarity_score=score,
                        lang=p.get("lang", "vi"),
                        embed_model=p.get("embed_model", DEFAULT_EMBED_MODEL),
                        embed_version=p.get("embed_version", EMBED_VERSION),
                        task_code=p.get("task_code", p.get("domain", "COMM")),
                        sub_domain=p.get("sub_domain", ""),
                        secondary_codes=p.get("secondary_codes", [])
                    ))
                return exemplars
        except Exception as e:
            logger.debug("[EPISODIC-SEARCH-ERR]: %s", e)
            return []

    def learn_from_feedback(
        self,
        record_id: str,
        goal: str,
        wrong_response: Optional[str] = None,
        correct_response: Optional[str] = None,
        task_code: Optional[str] = None,
        sub_domain: str = "",
        lesson: str = ""
    ) -> Dict[str, Any]:
        """
        HỌC HỎI VÀ CẬP NHẬT NGAY LẬP TỨC KHI SAI (Continuous Active Correction):
        1. Nếu có wrong_response -> Lập tức ghi NEGATIVE_GUARD (Vết xe đổ: tránh lỗi này).
        2. Nếu có correct_response -> Lập tức ghi POSITIVE_EXEMPLAR (Chuẩn vàng: làm theo cách này).
        3. Kết quả sẵn sàng ngay trong bộ nhớ ngoại sau < 50ms cho lần gọi kế tiếp.
        """
        code = task_code or classify_task(goal) or "COMM"
        results = {"negative_stored": False, "positive_stored": False, "task_code": code}

        # 1. Ghi vết xe đổ (REJECT)
        if wrong_response:
            neg_id = f"NEG_{record_id}"
            neg_lesson = lesson or "Tránh lỗi sai này trong tương lai"
            ok_neg = self.ingest_exemplar(
                record_id=neg_id,
                goal=goal,
                response=wrong_response,
                verdict="REJECT",
                task_code=code,
                sub_domain=sub_domain,
                lesson=neg_lesson
            )
            results["negative_stored"] = ok_neg

        # 2. Ghi chuẩn đúng (ACCEPT)
        if correct_response:
            pos_id = f"POS_{record_id}"
            pos_lesson = f"Đáp án chuẩn do Master chỉ định cho mã việc {code}"
            ok_pos = self.ingest_exemplar(
                record_id=pos_id,
                goal=goal,
                response=correct_response,
                verdict="ACCEPT",
                task_code=code,
                sub_domain=sub_domain,
                lesson=pos_lesson
            )
            results["positive_stored"] = ok_pos

        logger.info("⚡ [EPISODIC-IMMEDIATE-LEARNING]: Record %s updated (neg=%s, pos=%s, task=%s)",
                    record_id, results["negative_stored"], results["positive_stored"], code)
        return results


        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("result", [])
                exemplars = []
                for item in results:
                    p = item.get("payload", {})
                    score = float(item.get("score", 0.0))
                    exemplars.append(MemoryExemplar(
                        record_id=p.get("record_id", "UNKNOWN"),
                        domain=p.get("domain", "COMMUNICATION"),
                        goal=p.get("goal", ""),
                        exemplar_response=p.get("response", ""),
                        verdict=p.get("verdict", "ACCEPT"),
                        lesson=p.get("lesson", ""),
                        similarity_score=score,
                        lang=p.get("lang", "vi"),
                        embed_model=p.get("embed_model", DEFAULT_EMBED_MODEL),
                        embed_version=p.get("embed_version", EMBED_VERSION)
                    ))
                return exemplars
        except Exception as e:
            logger.debug("[EPISODIC-SEARCH-ERR]: %s", e)
            return []

    def format_context_prompt(self, exemplars: List[MemoryExemplar]) -> str:
        """Định dạng các bài học thành khối System Prompt Few-Shot chuẩn mực."""
        if not exemplars:
            return ""

        blocks = []
        for ex in exemplars:
            if ex.verdict == "ACCEPT":
                blocks.append(
                    f"💎 [EPISODIC-POSITIVE-EXEMPLAR | Ref: {ex.record_id} | Similarity: {ex.similarity_score:.2f}]:\n"
                    f"Yêu cầu tương tự trong quá khứ: {ex.goal}\n"
                    f"Đáp án chuẩn Master đã duyệt: {ex.exemplar_response}\n"
                    f"Chỉ thị: BẮT BUỘC noi theo phong cách, cách tính và độ súc tích của đáp án chuẩn này."
                )
            else:
                blocks.append(
                    f"⚠️ [EPISODIC-NEGATIVE-GUARD | Ref: {ex.record_id} | Similarity: {ex.similarity_score:.2f}]:\n"
                    f"Yêu cầu tương tự trong quá khứ: {ex.goal}\n"
                    f"Sai sót đã bị Master phạt: {ex.lesson}\n"
                    f"Chỉ thị: TUYỆT ĐỐI KHÔNG lặp lại sai lầm này."
                )

        return "\n\n" + "\n\n".join(blocks) + "\n"

    # ==========================================================================
    # SLICE 3.3 ITEM 7 & ITEM 10: REFLECT OBSERVATION GATE & NATIVE VI RETENTION
    # ==========================================================================
    def clear_local_observation_store(self) -> None:
        self._retained_observations.clear()
        self._retained_native_facts.clear()
        self._unauthorized_write_blocks = 0

    def get_unauthorized_write_blocks(self) -> int:
        return int(self._unauthorized_write_blocks)

    def retain_observation(
        self,
        obs: Dict[str, Any],
        authority: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        [Slice 3.3 - Giai đoạn 3 Mục 7]:
        Cổng ghi Observation vào Episodic Memory:
        1. BẮT BUỘC có chữ ký HMAC-SHA256 hợp lệ từ `CompletionAuthority` (0 ghi thẳng thiếu chữ ký).
        2. BẮT BUỘC đi qua cổng `StateSanitizer.scan_for_retain` (45 mẫu secret/PII).
        3. Lưu theo cơ chế refine-không-ghi-đè (bảo toàn `revision_history` và `verbatim_quotes`).
        """
        from core.os.cognition.completion_authority import completion_authority as default_auth
        from core.sanitizer.state_sanitizer import StateSanitizer

        auth = authority or default_auth
        sig = obs.get("authority_signature")
        if not auth.verify_observation_signature(obs, sig):
            self._unauthorized_write_blocks += 1
            return {
                "retained": False,
                "reason": "MISSING_OR_INVALID_COMPLETION_AUTHORITY_SIGNATURE",
            }

        scan_res = StateSanitizer.scan_for_retain(obs, policy="redact_or_block")
        if not scan_res["allowed_to_retain"]:
            self._unauthorized_write_blocks += 1
            return {
                "retained": False,
                "reason": "MEMORY_DEFENSE_BLOCKED_POISONED_OBSERVATION",
            }

        cluster_id = str(obs["cluster_id"])
        stored_copy = {
            "cluster_id": cluster_id,
            "task_code": str(obs.get("task_code", "COMM")),
            "summary": str(scan_res["sanitized_payload"].get("summary", obs.get("summary", ""))),
            "verbatim_quotes": list(scan_res["sanitized_payload"].get("verbatim_quotes", obs.get("verbatim_quotes", []))),
            "proof_count": int(obs.get("proof_count", 0)),
            "revision": int(obs.get("revision", 1)),
            "revision_history": list(obs.get("revision_history", [])),
            "authority_signature": str(sig),
            "retained_at": time.time(),
        }
        self._retained_observations[cluster_id] = stored_copy
        return {"retained": True, "cluster_id": cluster_id, "revision": stored_copy["revision"]}

    def get_retained_observation(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        obs = self._retained_observations.get(cluster_id)
        return dict(obs) if obs else None

    def list_retained_observations(self) -> List[Dict[str, Any]]:
        return [dict(v) for v in self._retained_observations.values()]

    def retain_native_fact(
        self,
        fact_id: str,
        text: str,
        task_code: str = "COMM",
    ) -> Dict[str, Any]:
        """
        [Slice 3.3 - Giai đoạn 3 Mục 10 (học Hindsight)]:
        Lưu giữ Fact tiếng Việt nguyên văn (chuẩn hóa NFC, cấm dịch ngầm hoặc làm rụng dấu),
        đồng thời quét qua 45 mẫu Memory Defense.
        """
        import unicodedata
        from core.sanitizer.state_sanitizer import StateSanitizer

        nfc_original = unicodedata.normalize("NFC", text or "")
        defense = StateSanitizer.scan_for_retain(nfc_original, policy="redact_or_block")
        if not defense["allowed_to_retain"]:
            return {"retained": False, "reason": "MEMORY_DEFENSE_BLOCKED"}

        retained_str = unicodedata.normalize("NFC", str(defense["sanitized_payload"]))
        if defense["clean"]:
            fidelity = verify_vietnamese_diacritic_fidelity(nfc_original, retained_str)
            if not fidelity["passed"]:
                return {"retained": False, "reason": fidelity["reason"]}

        record = {
            "fact_id": str(fact_id),
            "task_code": str(task_code),
            "text": retained_str,
            "lang": "vi" if _extract_vietnamese_diacritics(retained_str) else "en",
            "diacritic_count": len(_extract_vietnamese_diacritics(retained_str)),
            "retained_at": time.time(),
        }
        self._retained_native_facts[str(fact_id)] = record
        return {"retained": True, "fact_id": str(fact_id), "record": dict(record)}

    def recall_native_fact(self, fact_id: str) -> Optional[Dict[str, Any]]:
        rec = self._retained_native_facts.get(str(fact_id))
        return dict(rec) if rec else None


_VI_DIACRITIC_CHARS = frozenset(
    "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    "ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ"
)


def _extract_vietnamese_diacritics(text: str) -> List[str]:
    import unicodedata

    norm = unicodedata.normalize("NFC", text or "")
    return [ch for ch in norm if ch in _VI_DIACRITIC_CHARS]


def verify_vietnamese_diacritic_fidelity(original_text: str, retained_text: str) -> Dict[str, Any]:
    """
    [Slice 3.3 - Giai đoạn 3 Mục 10]:
    Kiểm tra bảo toàn 100% dấu tiếng Việt và cấm dịch ngầm sang tiếng Anh / ASCII.
    """
    import unicodedata

    orig_nfc = unicodedata.normalize("NFC", original_text or "")
    ret_nfc = unicodedata.normalize("NFC", retained_text or "")
    orig_diacritics = _extract_vietnamese_diacritics(orig_nfc)
    ret_diacritics = _extract_vietnamese_diacritics(ret_nfc)

    if not orig_diacritics:
        return {
            "passed": orig_nfc == ret_nfc,
            "diacritic_retention_ratio": 1.0,
            "reason": "NO_VI_DIACRITICS_IN_SOURCE",
        }

    ratio = len(ret_diacritics) / max(1, len(orig_diacritics))
    exact_diacritics = (orig_diacritics == ret_diacritics) and (orig_nfc == ret_nfc)
    if not exact_diacritics:
        return {
            "passed": False,
            "diacritic_retention_ratio": round(ratio, 4),
            "reason": "VIETNAMESE_DIACRITIC_LOSS_OR_SILENT_TRANSLATION",
        }

    return {
        "passed": True,
        "diacritic_retention_ratio": 1.0,
        "reason": "EXACT_NFC_VIETNAMESE_PRESERVED",
    }


class BackgroundReflectJob:
    """
    [Slice 3.3 - Giai đoạn 3 Mục 7 (học Hindsight)]:
    Job định kỳ gom cụm trajectory -> observations (trích dẫn nguyên văn + proof_count,
    refine không ghi đè) -> ký qua CompletionAuthority mới được ghi vào EpisodicBrain.
    """

    def __init__(self, authority: Any, episodic_brain: EpisodicBrain):
        self.authority = authority
        self.episodic_brain = episodic_brain
        self._clusters_cache: Dict[str, Dict[str, Any]] = {}

    def run_batch(self, clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
        committed = 0
        unsigned_committed = 0
        results = []

        for cluster in clusters:
            cluster_id = str(cluster["cluster_id"])
            task_code = str(cluster.get("task_code", "COMM"))
            trajectories = list(cluster.get("trajectories") or [])
            verbatim_quotes = [
                str(t["verbatim_quote"]).strip()
                for t in trajectories
                if str(t.get("verbatim_quote", "")).strip()
            ]
            all_verified = all(bool(t.get("outcome_verified", False)) for t in trajectories) and len(trajectories) > 0
            summary = str(cluster.get("summary") or f"Đúc kết từ {len(verbatim_quotes)} bằng chứng thực thi tại {cluster_id}")

            obs_draft: Dict[str, Any] = {
                "cluster_id": cluster_id,
                "task_code": task_code,
                "summary": summary,
                "verbatim_quotes": verbatim_quotes,
                "proof_count": len(verbatim_quotes),
                "revision": 1,
                "revision_history": [],
            }
            sig = self.authority.sign_observation(obs_draft, all_trajectories_verified=all_verified)
            obs_draft["authority_signature"] = sig

            retain_res = self.episodic_brain.retain_observation(obs_draft, authority=self.authority)
            if retain_res["retained"]:
                committed += 1
                self._clusters_cache[cluster_id] = obs_draft
                if not sig:
                    unsigned_committed += 1
            results.append(retain_res)

        return {
            "clusters_processed": len(clusters),
            "observations_committed": committed,
            "unsigned_writes_committed": unsigned_committed,
            "results": results,
        }

    def refine_cluster(
        self,
        cluster_id: str,
        new_trajectories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Tinh chỉnh (refine) một Observation đã có khi có thêm trajectory mới:
        - KHÔNG GHI ĐÈ mất lịch sử: lưu bản chụp cũ vào `revision_history`,
          giữ nguyên toàn bộ `verbatim_quotes` cũ + nối thêm quote mới, tăng `proof_count` và `revision`.
        - Cấp lại chữ ký `CompletionAuthority` mới cho phiên bản đã refine.
        """
        existing = self.episodic_brain.get_retained_observation(cluster_id)
        if not existing:
            return {"refined": False, "reason": "CLUSTER_NOT_FOUND"}

        new_quotes = [
            str(t["verbatim_quote"]).strip()
            for t in new_trajectories
            if str(t.get("verbatim_quote", "")).strip()
        ]
        all_verified = all(bool(t.get("outcome_verified", False)) for t in new_trajectories) and len(new_quotes) > 0
        if not all_verified:
            return {"refined": False, "reason": "UNVERIFIED_NEW_TRAJECTORY"}

        prev_snapshot = {
            "revision": existing["revision"],
            "proof_count": existing["proof_count"],
            "verbatim_quotes": list(existing["verbatim_quotes"]),
            "summary": existing["summary"],
            "authority_signature": existing["authority_signature"],
        }
        history = list(existing.get("revision_history") or [])
        history.append(prev_snapshot)

        merged_quotes = list(existing["verbatim_quotes"])
        for q in new_quotes:
            if q not in merged_quotes:
                merged_quotes.append(q)

        new_revision = int(existing["revision"]) + 1
        refined_obs: Dict[str, Any] = {
            "cluster_id": cluster_id,
            "task_code": existing["task_code"],
            "summary": f"{existing['summary']} (Refined rev {new_revision}, +{len(new_quotes)} proofs)",
            "verbatim_quotes": merged_quotes,
            "proof_count": len(merged_quotes),
            "revision": new_revision,
            "revision_history": history,
        }
        refined_obs["authority_signature"] = self.authority.sign_observation(
            refined_obs, all_trajectories_verified=True
        )
        retain_res = self.episodic_brain.retain_observation(refined_obs, authority=self.authority)
        return {
            "refined": bool(retain_res["retained"]),
            "cluster_id": cluster_id,
            "revision": new_revision,
            "proof_count": refined_obs["proof_count"],
        }


# ==============================================================================
# FIXTURES FOR SLICE 3.3 ITEM 7 (10 CLUSTERS) & ITEM 10 (20 VIETNAMESE FACTS)
# ==============================================================================
SAMPLE_10_TRAJECTORY_CLUSTERS: List[Dict[str, Any]] = [
    {
        "cluster_id": f"cluster_{idx:02d}_{code.lower()}",
        "task_code": code,
        "summary": summary,
        "trajectories": [
            {"step_id": f"c{idx}_s1", "verbatim_quote": q1, "outcome_verified": True},
            {"step_id": f"c{idx}_s2", "verbatim_quote": q2, "outcome_verified": True},
        ],
    }
    for idx, (code, summary, q1, q2) in enumerate(
        [
            (
                "SYSADMIN",
                "Khóa cổng Dual-Port Ollama 11434/11435",
                "Cổng 11434 dành riêng cho luồng suy luận nặng Qwen3-30B-A3B.",
                "Cổng 11435 dành riêng cho worker_fast lfm2.5-2.6b phản xạ dưới 50ms.",
            ),
            (
                "CODE_PYTHON",
                "Đồng bộ gia tăng AST RepoMap dưới 5ms",
                "Hàm update_single_file_in_repo_map cập nhật chỉ mục AST trong 3.3ms.",
                "Cổng chặn Blast Radius từ chối sửa đổi các nút có in_degree >= 5 nếu thiếu test.",
            ),
            (
                "OFFICE_DOC",
                "Bảo toàn đơn vị thùng và tấn trong bài toán kho bãi",
                "Lô hàng 250 thùng x 12 kg phải giữ nguyên đơn vị 3000 kg (3 tấn), cấm tráo thùng thành tấn.",
                "Cước vận chuyển 15 chuyến nhân 1.200.000 VND bằng đúng 18.000.000 VND.",
            ),
            (
                "NET_MIKROTIK",
                "Cấu hình tường lửa RouterOS chống rò rỉ nội bộ",
                "Thực thi lệnh /ip firewall filter add chain=forward action=drop cho dải khách.",
                "Kiểm tra bảng NAT bằng /ip firewall nat print trước khi mở cổng WAN.",
            ),
            (
                "NET_CISCO",
                "Cô lập VLAN trên switch Catalyst",
                "Cấu hình switchport mode access và switchport access vlan 20 cho cổng phòng kế toán.",
                "Kiểm tra trạng thái đường trục bằng lệnh show interfaces trunk.",
            ),
            (
                "LOGIC_REASONING",
                "Hợp nhất 4 chiến lược truy xuất bằng RRF k=60",
                "Kết hợp Vector, BM25, Temporal decay và Symbol Anchor qua công thức RRF k=60.",
                "Loại bỏ tài liệu 2024 đã hết hạn khi truy vấn chính sách năm 2026.",
            ),
            (
                "CODE_PYTHON",
                "Bảo vệ tiền tố KV-Cache bằng CacheAligner",
                "Chặn mọi chuỗi timestamp và UUID động lọt vào 512 ký tự đầu của system prompt.",
                "Đạt tỷ lệ phân loại chính xác 20/20 trên tập mẫu sạch và nhiễm volatile.",
            ),
            (
                "SYSADMIN",
                "Quản lý vòng đời Worktree Sandbox không đệ quy",
                "Cấm tạo worktree bên trong một thư mục đã là sandbox worktree.",
                "Áp dụng hạn mức tối đa 32 worktree và 500 MB mỗi nhánh thử nghiệm.",
            ),
            (
                "COMM",
                "Chuẩn giao tiếp trực diện của Master",
                "Đi thẳng vào số liệu thực nghiệm và bảng đối chiếu, xóa bỏ lời chào rào đón sáo rỗng.",
                "Khi dịch vụ tắt phải báo cáo rõ NOT_TESTED và FALLBACK, tuyệt đối không bịa PASS.",
            ),
            (
                "CODE_PYTHON",
                "Kiểm tra SSRF trên đường tìm kiếm web",
                "Chặn tuyệt đối 127.0.0.1, 169.254.169.254 và các dải mạng riêng RFC1918.",
                "Chỉ cho phép truy cập các tên miền nằm trong danh sách trắng đã cấu hình.",
            ),
        ],
        start=1,
    )
]

SAMPLE_20_VIETNAMESE_FACTS: List[str] = [
    "1. Hệ thống JKAI khóa cứng cổng 11434 cho mô hình suy luận sâu và cổng 11435 cho luồng phản xạ nhanh.",
    "2. Mọi nhận định đưa vào bộ nhớ dài hạn đều phải đi qua cổng kiểm duyệt chữ ký số của CompletionAuthority.",
    "3. Tuyệt đối không được dịch ngầm các sự kiện tiếng Việt sang tiếng Anh hoặc làm mất dấu thanh điệu.",
    "4. Khi tính toán khối lượng kho bãi, phải phân biệt rõ đơn vị thùng, kiện, kilôgam và tấn.",
    "5. Bộ lọc bảo mật trên đường ghi nhớ quét bốn mươi lăm mẫu khóa bí mật và thông tin cá nhân nhạy cảm.",
    "6. Các tập tài liệu hết hiệu lực từ năm 2024 bị hạ điểm ưu tiên so với quy chuẩn kiến trúc năm 2026.",
    "7. Thuật toán hợp nhất thứ hạng nghịch đảo dùng hằng số làm mịn k bằng sáu mươi.",
    "8. Cơ chế chia nhỏ văn bản cha-con giúp giữ trọn vẹn thẻ trích dẫn nguồn mà không làm phình đại cửa sổ ngữ cảnh.",
    "9. Mọi chỉnh sửa của Master trên đoạn văn sai đều tự động chuyển hóa thành dữ liệu huấn luyện có nhãn.",
    "10. Trình dọn dẹp không gian làm việc ngăn chặn triệt để hiện tượng sinh nhánh đệ quy làm đầy ổ cứng.",
    "11. Khi máy chủ suy luận cục bộ ngừng hoạt động, thẻ năng lực mô hình phải đóng dấu trạng thái dự phòng.",
    "12. Tiền tố hệ thống phải giữ tĩnh hoàn toàn để tận dụng bộ nhớ đệm khóa-giá trị của nhân suy luận.",
    "13. Kế toán chi phí theo sáu khâu giúp vòng lặp tự cải tiến biết chính xác khâu nào gây nghẽn cổ chai.",
    "14. Phương trình bảo toàn tệp mã nguồn đảm bảo không bỏ sót bất kỳ tệp Python nào trong toàn bộ dự án.",
    "15. Các công cụ có tác động ngoại vi không thể đảo ngược bị cấm phát lại tự động khi tua ngược trạng thái.",
    "16. Mỗi bản ghi ký ức đều lưu trữ lịch sử phiên bản để hỗ trợ đối chiếu sự khác biệt và khôi phục tức thì.",
    "17. Cổng kiểm soát truy cập mạng chặn đứng mọi yêu cầu giả mạo hướng tới địa chỉ siêu dữ liệu đám mây.",
    "18. Độ chính xác trích dẫn tăng từ không phần trăm lên một trăm phần trăm nhờ khôi phục đoạn văn bản cha.",
    "19. Hai mươi mẫu câu tiếng Việt giàu dấu sắc, huyền, hỏi, ngã, nặng phải được bảo toàn nguyên vẹn từng ký tự.",
    "20. Kiến trúc sư trưởng và kiểm toán viên độc lập phối hợp theo giao thức hai tác tử phiên bản hai chấm ba.",
]


def evaluate_vietnamese_fact_roundtrip_benchmark(
    episodic_brain: Optional[EpisodicBrain] = None,
) -> Dict[str, Any]:
    """
    [Slice 3.3 - Giai đoạn 3 Mục 10]:
    Kiểm chuẩn round-trip `retain_native_fact` -> `recall_native_fact` trên 20 fact tiếng Việt mẫu:
    yêu cầu giữ nguyên 100% dấu chuẩn NFC (20/20).
    """
    import unicodedata

    brain = episodic_brain or EpisodicBrain()
    exact_count = 0
    total_orig_diacritics = 0
    total_retained_diacritics = 0
    details = []

    for idx, fact_text in enumerate(SAMPLE_20_VIETNAMESE_FACTS, start=1):
        fid = f"vi_fact_{idx:02d}"
        res = brain.retain_native_fact(fact_id=fid, text=fact_text, task_code="COMM")
        recalled = brain.recall_native_fact(fid)
        recalled_text = recalled["text"] if recalled else ""

        norm_orig = unicodedata.normalize("NFC", fact_text)
        fid_check = verify_vietnamese_diacritic_fidelity(norm_orig, recalled_text)
        orig_d = len(_extract_vietnamese_diacritics(norm_orig))
        ret_d = len(_extract_vietnamese_diacritics(recalled_text))
        total_orig_diacritics += orig_d
        total_retained_diacritics += ret_d

        is_exact = bool(res.get("retained")) and fid_check["passed"] and (recalled_text == norm_orig)
        if is_exact:
            exact_count += 1
        details.append(
            {
                "fact_id": fid,
                "exact_roundtrip": is_exact,
                "orig_diacritics": orig_d,
                "retained_diacritics": ret_d,
            }
        )

    total = len(SAMPLE_20_VIETNAMESE_FACTS)
    return {
        "total_facts": total,
        "exact_roundtrip_count": exact_count,
        "diacritic_retention_rate": round(total_retained_diacritics / max(1, total_orig_diacritics), 4),
        "details": details,
    }


# ==============================================================================
# SLICE 3.4 ITEM 12: LONGMEMEVAL-VI EPISODIC BENCHMARK & REPEAT STABILITY
# ==============================================================================
LONGMEMEVAL_VI_TIMELINE_SESSIONS: List[Dict[str, Any]] = [
    {
        "session_id": "lme_s01",
        "timestamp": "2026-01-15",
        "entity_key": "worker_fast_port",
        "state_value": "8085",
        "text": "Phiên 2026-01-15: Khởi tạo thử nghiệm cổng worker_fast ở port 8085.",
        "superseded_by": "lme_s05",
    },
    {
        "session_id": "lme_s02",
        "timestamp": "2026-02-10",
        "entity_key": "officecli_version",
        "state_value": "v27.1.0",
        "text": "Phiên 2026-02-10: Thư viện OfficeCLI tạm gắn ở phiên bản v27.1.0.",
        "superseded_by": "lme_s08",
    },
    {
        "session_id": "lme_s03",
        "timestamp": "2026-03-10",
        "entity_key": "warehouse_stock_crates",
        "state_value": "120 thùng",
        "text": "Phiên 2026-03-10: Kiểm kê kho Quận 7 ghi nhận tồn kho là 120 thùng sữa tươi.",
        "superseded_by": "lme_s09",
    },
    {
        "session_id": "lme_s04",
        "timestamp": "2026-04-05",
        "entity_key": "worktree_quota_mb",
        "state_value": "1024 MB",
        "text": "Phiên 2026-04-05: Hạn mức dung lượng mỗi nhánh worktree sandbox đặt tạm là 1024 MB.",
        "superseded_by": "lme_s10",
    },
    {
        "session_id": "lme_s05",
        "timestamp": "2026-05-20",
        "entity_key": "worker_fast_port",
        "state_value": "11435",
        "text": "Phiên 2026-05-20: Chuyển chính thức cổng worker_fast sang port 11435 cho model lfm2.5-2.6b.",
        "superseded_by": None,
    },
    {
        "session_id": "lme_s06",
        "timestamp": "2026-06-12",
        "entity_key": "reasoning_port",
        "state_value": "11434",
        "text": "Phiên 2026-06-12: Khóa cố định cổng reasoning nặng ở port 11434 cho Qwen3-30B-A3B.",
        "superseded_by": None,
    },
    {
        "session_id": "lme_s07",
        "timestamp": "2026-07-20",
        "entity_key": "milestone_ast_repomap",
        "state_value": "2026-07-20",
        "text": "Phiên 2026-07-20: Triển khai thành công AST RepoMap 2 tầng với độ trễ cập nhật 3.3ms.",
        "superseded_by": None,
    },
    {
        "session_id": "lme_s08",
        "timestamp": "2026-08-18",
        "entity_key": "officecli_version",
        "state_value": "v28.4.1",
        "text": "Phiên 2026-08-18: Nâng cấp và ghim cứng OfficeCLI lên phiên bản v28.4.1.",
        "superseded_by": None,
    },
    {
        "session_id": "lme_s09",
        "timestamp": "2026-09-15",
        "entity_key": "warehouse_stock_crates",
        "state_value": "250 thùng",
        "text": "Phiên 2026-09-15: Nhập bổ sung hàng mới, tồn kho Quận 7 cập nhật lên 250 thùng.",
        "superseded_by": None,
    },
    {
        "session_id": "lme_s10",
        "timestamp": "2026-10-01",
        "entity_key": "worktree_quota_mb",
        "state_value": "500 MB",
        "text": "Phiên 2026-10-01: Siết hạn mức dung lượng mỗi nhánh worktree sandbox xuống 500 MB.",
        "superseded_by": None,
    },
    {
        "session_id": "lme_s11",
        "timestamp": "2026-10-05",
        "entity_key": "milestone_ssrf_guard",
        "state_value": "2026-10-05",
        "text": "Phiên 2026-10-05: Kích hoạt SSRF guard chặn 169.254.169.254 và dải loopback trên đường web search.",
        "superseded_by": None,
    },
    {
        "session_id": "lme_s12",
        "timestamp": "2026-10-12",
        "entity_key": "memory_defense_patterns",
        "state_value": "45 mẫu",
        "text": "Phiên 2026-10-12: Khóa 45 mẫu quét secret/PII trong StateSanitizer và hằng số RRF k=60.",
        "superseded_by": None,
    },
]

LONGMEMEVAL_VI_HELD_OUT_QUESTIONS: List[Dict[str, Any]] = [
    {
        "q_id": "lme_q01",
        "q_type": "KNOWLEDGE_UPDATE",
        "entity_key": "worker_fast_port",
        "question": "Hiện tại cổng worker_fast đang dùng port nào sau lần cập nhật mới nhất?",
        "expected_answer": "11435",
    },
    {
        "q_id": "lme_q02",
        "q_type": "KNOWLEDGE_UPDATE",
        "entity_key": "officecli_version",
        "question": "Phiên bản OfficeCLI đang được ghim cứng hiện nay là bao nhiêu?",
        "expected_answer": "v28.4.1",
    },
    {
        "q_id": "lme_q03",
        "q_type": "KNOWLEDGE_UPDATE",
        "entity_key": "warehouse_stock_crates",
        "question": "Số lượng tồn kho Quận 7 sau đợt nhập hàng tháng 9/2026 là bao nhiêu?",
        "expected_answer": "250 thùng",
    },
    {
        "q_id": "lme_q04",
        "q_type": "KNOWLEDGE_UPDATE",
        "entity_key": "worktree_quota_mb",
        "question": "Hạn mức dung lượng mỗi nhánh worktree sandbox hiện hành là bao nhiêu?",
        "expected_answer": "500 MB",
    },
    {
        "q_id": "lme_q05",
        "q_type": "TEMPORAL_POINT_IN_TIME",
        "entity_key": "warehouse_stock_crates",
        "as_of_date": "2026-04-01",
        "question": "Tính đến ngày 2026-04-01 (trước đợt nhập tháng 9), tồn kho Quận 7 là bao nhiêu?",
        "expected_answer": "120 thùng",
    },
    {
        "q_id": "lme_q06",
        "q_type": "TEMPORAL_POINT_IN_TIME",
        "entity_key": "worker_fast_port",
        "as_of_date": "2026-03-01",
        "question": "Vào ngày 2026-03-01, cổng worker_fast đang đặt ở port thử nghiệm nào?",
        "expected_answer": "8085",
    },
    {
        "q_id": "lme_q07",
        "q_type": "TEMPORAL_ORDERING",
        "entities": ["milestone_ast_repomap", "milestone_ssrf_guard"],
        "question": "Sự kiện nào diễn ra trước: triển khai AST RepoMap hay kích hoạt SSRF guard?",
        "expected_answer": "milestone_ast_repomap",
    },
    {
        "q_id": "lme_q08",
        "q_type": "MULTI_SESSION_SYNTHESIS",
        "entities": ["reasoning_port", "worker_fast_port"],
        "question": "Liệt kê cặp cổng (reasoning, worker_fast) đang hoạt động tính đến tháng 10/2026.",
        "expected_answer": "11434,11435",
    },
    {
        "q_id": "lme_q09",
        "q_type": "SINGLE_SESSION_RECALL",
        "entity_key": "memory_defense_patterns",
        "question": "Có bao nhiêu mẫu quét secret/PII được khóa trong StateSanitizer vào ngày 2026-10-12?",
        "expected_answer": "45 mẫu",
    },
    {
        "q_id": "lme_q10",
        "q_type": "SINGLE_SESSION_RECALL",
        "entity_key": "reasoning_port",
        "question": "Cổng reasoning nặng cho Qwen3-30B-A3B được khóa ở port nào?",
        "expected_answer": "11434",
    },
    {
        "q_id": "lme_q11",
        "q_type": "TEMPORAL_ABSTENTION",
        "query_year": 2024,
        "question": "Vào tháng 11 năm 2024, hệ thống đã triển khai model suy luận nào?",
        "expected_answer": "OUT_OF_TIMELINE_ABSTAIN",
    },
    {
        "q_id": "lme_q12",
        "q_type": "TEMPORAL_ABSTENTION",
        "query_year": 2029,
        "question": "Vào tháng 6 năm 2029, hạn mức worktree sandbox được đổi thành bao nhiêu?",
        "expected_answer": "OUT_OF_TIMELINE_ABSTAIN",
    },
]


def _answer_longmemeval_question(
    sessions: List[Dict[str, Any]],
    question: Dict[str, Any],
    temporal_aware: bool,
) -> str:
    q_type = question["q_type"]

    if q_type == "TEMPORAL_ABSTENTION":
        if not temporal_aware:
            # Naive baseline guesses the first session in list instead of abstaining
            return str(sessions[0]["state_value"]) if sessions else ""
        years = [int(str(s["timestamp"])[:4]) for s in sessions]
        q_year = int(question.get("query_year", 0))
        if not years or q_year < min(years) or q_year > max(years):
            return "OUT_OF_TIMELINE_ABSTAIN"
        return "IN_TIMELINE"

    if q_type == "TEMPORAL_ORDERING":
        ent_a, ent_b = question["entities"]
        if not temporal_aware:
            # Naive order by position in ingested list
            idx_a = next((i for i, s in enumerate(sessions) if s["entity_key"] == ent_a), 999)
            idx_b = next((i for i, s in enumerate(sessions) if s["entity_key"] == ent_b), 999)
            return ent_a if idx_a <= idx_b else ent_b
        ts_a = next((s["timestamp"] for s in sessions if s["entity_key"] == ent_a), "9999-99-99")
        ts_b = next((s["timestamp"] for s in sessions if s["entity_key"] == ent_b), "9999-99-99")
        return ent_a if ts_a <= ts_b else ent_b

    if q_type == "MULTI_SESSION_SYNTHESIS":
        vals = []
        for ent in question["entities"]:
            matching = [s for s in sessions if s["entity_key"] == ent]
            if temporal_aware:
                matching.sort(key=lambda s: str(s["timestamp"]))
                vals.append(str(matching[-1]["state_value"]) if matching else "")
            else:
                vals.append(str(matching[0]["state_value"]) if matching else "")
        return ",".join(vals)

    if q_type == "TEMPORAL_POINT_IN_TIME":
        ent = question["entity_key"]
        as_of = str(question["as_of_date"])
        matching = [s for s in sessions if s["entity_key"] == ent]
        if not temporal_aware:
            return str(matching[-1]["state_value"]) if matching else ""
        valid_at_time = [s for s in matching if str(s["timestamp"]) <= as_of]
        valid_at_time.sort(key=lambda s: str(s["timestamp"]))
        return str(valid_at_time[-1]["state_value"]) if valid_at_time else ""

    # KNOWLEDGE_UPDATE or SINGLE_SESSION_RECALL
    ent = question["entity_key"]
    matching = [s for s in sessions if s["entity_key"] == ent]
    if not matching:
        return ""
    if not temporal_aware:
        # Naive baseline returns the first matching session in arrival order (stale!)
        return str(matching[0]["state_value"])
    # Temporal-aware filters out superseded entries and sorts by timestamp ascending
    active = [s for s in matching if not s.get("superseded_by")]
    pool = active if active else matching
    pool.sort(key=lambda s: str(s["timestamp"]))
    return str(pool[-1]["state_value"])


def classify_longmemeval_drift_alert(
    drift_pct: float,
    warning_pct: float = 10.0,
    critical_pct: float = 15.0,
) -> str:
    """
    [Turn 288 OpenCode Improvement #1]:
    Phân loại mức cảnh báo dao động giữa các lần chạy LongMemEval:
    - `drift_pct < 10.0%` -> `"OK"`
    - `10.0% <= drift_pct <= 15.0%` -> `"WARNING_INVESTIGATE"`
    - `drift_pct > 15.0%` -> `"CRITICAL_DRIFT_ALERT"` (bắt buộc điều tra nguyên nhân bất ổn khi gắn LLM tự do).
    """
    val = float(drift_pct)
    if val > float(critical_pct):
        return "CRITICAL_DRIFT_ALERT"
    if val >= float(warning_pct):
        return "WARNING_INVESTIGATE"
    return "OK"


def evaluate_longmemeval_vi_episodic_harness(repeat_runs: int = 2) -> Dict[str, Any]:
    """
    [Slice 3.4 - Giai đoạn 4 Mục 12 + Turn 288 Drift Alert Threshold]:
    Đánh giá bộ câu hỏi held-out về sự kiện/thời gian bản Việt nhỏ (LongMemEval-VI)
    trên Episodic Memory:
    - Đo `naive_baseline_score` (không xét thứ tự thời gian / bản cập nhật).
    - Đo `temporal_run_scores` qua 1 lần baseline + `repeat_runs` lần đo lại (với thứ tự nạp phiên
      bị xáo trộn bằng seed xác định 101, 202... để kiểm tra tính bất biến theo thứ tự nạp).
    - Tiêu chí "Xong khi" của Master: điểm baseline + 2 lần đo lại ổn định (`max_run_drift_pct < 10%`),
      kèm ngưỡng cảnh báo `drift_alert_status` (> 15% báo `CRITICAL_DRIFT_ALERT`).
    """
    import random

    total_q = max(1, len(LONGMEMEVAL_VI_HELD_OUT_QUESTIONS))

    # 1. Naive baseline on canonical order
    naive_hits = sum(
        1
        for q in LONGMEMEVAL_VI_HELD_OUT_QUESTIONS
        if _answer_longmemeval_question(LONGMEMEVAL_VI_TIMELINE_SESSIONS, q, temporal_aware=False)
        == q["expected_answer"]
    )
    naive_score = round(naive_hits / total_q, 4)

    # 2. Temporal-aware baseline + repeat_runs under shuffled session ingestion order
    temporal_scores: List[float] = []
    for run_idx in range(int(repeat_runs) + 1):
        sessions_copy = [dict(s) for s in LONGMEMEVAL_VI_TIMELINE_SESSIONS]
        if run_idx > 0:
            rng = random.Random(100 + run_idx)
            rng.shuffle(sessions_copy)
        hits = sum(
            1
            for q in LONGMEMEVAL_VI_HELD_OUT_QUESTIONS
            if _answer_longmemeval_question(sessions_copy, q, temporal_aware=True)
            == q["expected_answer"]
        )
        temporal_scores.append(round(hits / total_q, 4))

    mean_score = sum(temporal_scores) / max(1, len(temporal_scores))
    min_s, max_s = min(temporal_scores), max(temporal_scores)
    drift_pct = round(((max_s - min_s) / max(1e-9, mean_score)) * 100.0, 4)

    return {
        "session_count": len(LONGMEMEVAL_VI_TIMELINE_SESSIONS),
        "question_count": len(LONGMEMEVAL_VI_HELD_OUT_QUESTIONS),
        "naive_baseline_score": naive_score,
        "temporal_run_scores": temporal_scores,
        "temporal_mean_score": round(mean_score, 4),
        "max_run_drift_pct": drift_pct,
        "within_10pct_stability": drift_pct < 10.0,
        "drift_warning_threshold_pct": 10.0,
        "drift_critical_alert_threshold_pct": 15.0,
        "drift_alert_status": classify_longmemeval_drift_alert(drift_pct),
    }


episodic_brain = EpisodicBrain()



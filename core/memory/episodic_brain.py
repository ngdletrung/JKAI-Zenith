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
        """
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


episodic_brain = EpisodicBrain()

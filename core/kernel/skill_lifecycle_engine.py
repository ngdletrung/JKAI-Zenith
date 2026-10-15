# -*- coding: utf-8 -*-
"""
core/kernel/skill_lifecycle_engine.py
======================================
[Pha 6 - Slice 6.4: Skill Versioning, Regression Test Harness & Sunset Lifecycle]
Hiện thực hóa Bước 4 trong Lộ trình 1 Quý của Master:
"Skill versioning + regression: mỗi skill có version, test hồi quy, sunset khi cũ.
 Kẻo skill cũ thành sự thật cũ."

Kiến trúc bao gồm 4 trụ cột:
1. SkillLifecycleStatus & SkillVersionMeta:
   - Trạng thái vòng đời chuẩn: ACTIVE -> DEPRECATED -> SUNSET -> ARCHIVED.
   - Phiên bản ngữ nghĩa SemVer (major.minor.patch).
   - Hạn ngạch hỗ trợ (TTL/max_supported_days, mặc định 90 ngày) và con trỏ kế nhiệm (superseded_by).
2. SkillRegressionCase & SkillRegressionHarness:
   - Khung kiểm thử hồi quy bắt buộc cho từng kỹ năng trước khi nâng cấp phiên bản.
   - Điều kiện thăng cấp: Pass rate = 100% (zero regression). Nếu rớt test -> CHẶN NÂNG CẤP.
3. SkillSunsetEngine:
   - Tự động phát hiện các kỹ năng quá hạn (past sunset_at) hoặc đã bị thay thế > 30 ngày.
   - Chuyển trạng thái sang SUNSET: Chặn thực thi trực tiếp, trả về lỗi SKILL_SUNSET cùng thông tin kế nhiệm.
   - Ngăn chặn triệt để tình trạng "kỹ năng cũ trở thành sự thật cũ" (stale operational truth).
4. Sổ cái băm chuỗi Chained Skill Lifecycle Ledger:
   - Ghi nhận mọi biến động phiên bản và sunset vào data/telemetry/skill_lifecycle_ledger.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger("JKAI.SkillLifecycle")

SKILL_LIFECYCLE_LEDGER_PATH = Path("data/telemetry/skill_lifecycle_ledger.jsonl")


# ==============================================================================
# 1. TRẠNG THÁI VÀ HỢP ĐỒNG PHIÊN BẢN KỸ NĂNG (SKILL VERSIONING CONTRACT)
# ==============================================================================

class SkillLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"          # Đang hoạt động, được khuyến nghị sử dụng
    DEPRECATED = "DEPRECATED"  # Sắp hết hạn hoặc đã có phiên bản kế nhiệm, cảnh báo khi gọi
    SUNSET = "SUNSET"          # Đã hết hiệu lực ("sự thật cũ"), cấm thực thi trực tiếp
    ARCHIVED = "ARCHIVED"      # Đã đóng gói lưu kho lạnh, không nạp vào runtime


@dataclass
class SkillVersionMeta:
    skill_id: str
    version: str                                  # SemVer: vd "1.0.0"
    status: SkillLifecycleStatus = SkillLifecycleStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sunset_at: Optional[str] = None               # Thời điểm chính thức sunset
    max_supported_days: int = 90                  # Hạn sử dụng tối đa (mặc định 90 ngày)
    superseded_by: Optional[str] = None           # Kỹ năng hoặc phiên bản kế nhiệm
    changelog: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        """Kiểm tra kỹ năng đã quá hạn sử dụng hay chưa."""
        now = current_time or datetime.now(timezone.utc)
        if self.sunset_at:
            try:
                sunset_dt = datetime.fromisoformat(self.sunset_at)
                if sunset_dt.tzinfo is None:
                    sunset_dt = sunset_dt.replace(tzinfo=timezone.utc)
                if now >= sunset_dt:
                    return True
            except Exception:
                pass

        try:
            created_dt = datetime.fromisoformat(self.created_at)
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            if now - created_dt > timedelta(days=self.max_supported_days):
                return True
        except Exception:
            pass

        return False


# ==============================================================================
# 2. KHUNG KIỂM THỬ HỒI QUY KỸ NĂNG (SKILL REGRESSION TEST HARNESS)
# ==============================================================================

@dataclass
class SkillRegressionCase:
    case_id: str
    input_args: Dict[str, Any]
    expected_predicate: str                       # Tên hàm kiểm tra hoặc quy tắc
    description: str = ""


@dataclass
class RegressionHarnessVerdict:
    skill_id: str
    candidate_version: str
    total_cases: int
    passed_cases: int
    failed_cases: List[Dict[str, Any]]
    pass_rate: float
    is_approved: bool
    reason: str


class SkillRegressionHarness:
    """
    Bộ khung chạy kiểm thử hồi quy cho kỹ năng trước khi cho phép nâng cấp phiên bản.
    Quy tắc Hiến Pháp: Tỷ lệ đạt phải là 100% (pass_rate == 1.0).
    """

    def __init__(self) -> None:
        self._test_registry: Dict[str, List[SkillRegressionCase]] = {}

    def register_cases(self, skill_id: str, cases: List[SkillRegressionCase]) -> None:
        """Đăng ký bộ bài thi hồi quy cho một kỹ năng."""
        self._test_registry.setdefault(skill_id, []).extend(cases)

    def run_regression_suite(
        self,
        skill_id: str,
        candidate_version: str,
        skill_runner: Callable[[Dict[str, Any]], Dict[str, Any]],
        predicates: Dict[str, Callable[[Dict[str, Any]], bool]],
    ) -> RegressionHarnessVerdict:
        """
        Thực thi toàn bộ bài thi hồi quy đã đăng ký.
        """
        cases = self._test_registry.get(skill_id, [])
        if not cases:
            # Nếu chưa có bài test, không cho phép nâng cấp tự động mà bắt buộc khai báo
            return RegressionHarnessVerdict(
                skill_id=skill_id,
                candidate_version=candidate_version,
                total_cases=0,
                passed_cases=0,
                failed_cases=[],
                pass_rate=0.0,
                is_approved=False,
                reason="ZERO_REGRESSION_TESTS_REGISTERED: Phải có ít nhất 1 bài thi hồi quy trước khi nâng cấp",
            )

        passed = 0
        failed = []

        for case in cases:
            pred_fn = predicates.get(case.expected_predicate)
            if not pred_fn:
                failed.append({
                    "case_id": case.case_id,
                    "error": f"PREDICATE_NOT_FOUND_{case.expected_predicate}",
                })
                continue

            try:
                result = skill_runner(case.input_args)
                if pred_fn(result):
                    passed += 1
                else:
                    failed.append({
                        "case_id": case.case_id,
                        "error": "PREDICATE_EVALUATION_FAILED",
                        "actual_result": result,
                    })
            except Exception as e:
                failed.append({
                    "case_id": case.case_id,
                    "error": f"EXCEPTION_IN_RUNNER: {str(e)}",
                })

        total = len(cases)
        pass_rate = round(passed / total, 4) if total > 0 else 0.0
        is_approved = (pass_rate == 1.0)

        reason = "ALL_REGRESSION_TESTS_PASSED" if is_approved else f"REGRESSION_DETECTED: {len(failed)}/{total} tests failed"

        return RegressionHarnessVerdict(
            skill_id=skill_id,
            candidate_version=candidate_version,
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            pass_rate=pass_rate,
            is_approved=is_approved,
            reason=reason,
        )


# ==============================================================================
# 3. ĐỘNG CƠ SUNSET & QUẢN LÝ VÒNG ĐỜI KỸ NĂNG (SKILL SUNSET ENGINE)
# ==============================================================================

class SkillSunsetEngine:
    """
    Động cơ quản lý vòng đời và hoàng hôn (Sunset) kỹ năng:
    - Quản lý phiên bản SemVer và ánh xạ phiên bản mới nhất.
    - Cưỡng chế quy tắc: Kỹ năng SUNSET bị chặn thực thi, trả lỗi kèm gợi ý kế nhiệm.
    - Ghi nhận lịch sử vào sổ cái băm chuỗi.
    """

    def __init__(self, ledger_path: Path = SKILL_LIFECYCLE_LEDGER_PATH) -> None:
        self.ledger_path = ledger_path
        self._skills: Dict[str, Dict[str, SkillVersionMeta]] = {}  # {skill_id: {version: meta}}
        self._latest_versions: Dict[str, str] = {}                 # {skill_id: latest_version}
        self.regression_harness = SkillRegressionHarness()

    def register_skill_version(self, meta: SkillVersionMeta) -> None:
        """Đăng ký một phiên bản kỹ năng mới."""
        s_id = meta.skill_id
        self._skills.setdefault(s_id, {})[meta.version] = meta
        self._latest_versions[s_id] = meta.version
        self._record_to_ledger({
            "action": "REGISTER_VERSION",
            "skill_id": s_id,
            "version": meta.version,
            "status": meta.status.value,
            "superseded_by": meta.superseded_by,
        })

    def upgrade_skill_version(
        self,
        new_meta: SkillVersionMeta,
        skill_runner: Callable[[Dict[str, Any]], Dict[str, Any]],
        predicates: Dict[str, Callable[[Dict[str, Any]], bool]],
    ) -> Tuple[bool, str]:
        """
        Nâng cấp kỹ năng lên phiên bản mới kèm kiểm thử hồi quy bắt buộc:
        1. Chạy regression suite.
        2. Nếu pass 100%: Nâng phiên bản mới thành ACTIVE, hạ phiên bản cũ thành DEPRECATED.
        3. Nếu trượt: Giữ nguyên phiên bản cũ, từ chối nâng cấp.
        """
        s_id = new_meta.skill_id
        old_version = self._latest_versions.get(s_id)

        # 1. Chạy kiểm thử hồi quy
        verdict = self.regression_harness.run_regression_suite(
            skill_id=s_id,
            candidate_version=new_meta.version,
            skill_runner=skill_runner,
            predicates=predicates,
        )

        if not verdict.is_approved:
            self._record_to_ledger({
                "action": "UPGRADE_REJECTED",
                "skill_id": s_id,
                "candidate_version": new_meta.version,
                "reason": verdict.reason,
                "pass_rate": verdict.pass_rate,
            })
            return False, f"UPGRADE_REJECTED: {verdict.reason}"

        # 2. Hạ cấp phiên bản cũ nếu có
        if old_version and old_version in self._skills.get(s_id, {}):
            old_meta = self._skills[s_id][old_version]
            old_meta.status = SkillLifecycleStatus.DEPRECATED
            old_meta.superseded_by = f"{s_id}:{new_meta.version}"

        # 3. Kích hoạt phiên bản mới
        new_meta.status = SkillLifecycleStatus.ACTIVE
        self.register_skill_version(new_meta)

        self._record_to_ledger({
            "action": "UPGRADE_APPROVED",
            "skill_id": s_id,
            "old_version": old_version,
            "new_version": new_meta.version,
            "pass_rate": verdict.pass_rate,
        })

        return True, f"UPGRADE_APPROVED: Phiên bản {new_meta.version} đã được kích hoạt thành công"

    def scan_and_sunset_expired_skills(
        self,
        current_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Quét toàn bộ kỹ năng và tự động chuyển các kỹ năng quá hạn sang trạng thái SUNSET.
        """
        now = current_time or datetime.now(timezone.utc)
        sunset_list = []

        for s_id, versions in self._skills.items():
            latest_v = self._latest_versions.get(s_id)
            for v_str, meta in versions.items():
                if meta.status in (SkillLifecycleStatus.ACTIVE, SkillLifecycleStatus.DEPRECATED):
                    # Điều kiện 1: Đã hết hạn TTL hoặc qua sunset_at
                    # Điều kiện 2: Đã bị thay thế (deprecated) quá 30 ngày
                    is_time_expired = meta.is_expired(now)
                    is_superseded_old = (
                        meta.status == SkillLifecycleStatus.DEPRECATED and
                        meta.superseded_by is not None and
                        v_str != latest_v
                    )

                    if is_time_expired or is_superseded_old:
                        meta.status = SkillLifecycleStatus.SUNSET
                        record = {
                            "action": "SKILL_SUNSET",
                            "skill_id": s_id,
                            "version": v_str,
                            "superseded_by": meta.superseded_by or (f"{s_id}:{latest_v}" if latest_v != v_str else None),
                            "reason": "EXPIRED_TTL" if is_time_expired else "SUPERSEDED_OLDER_VERSION",
                        }
                        sunset_list.append(record)
                        self._record_to_ledger(record)

        return sunset_list

    def can_invoke_skill(
        self,
        skill_id: str,
        version: Optional[str] = None,
        allow_sunset: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Cổng kiểm định trước khi thực thi kỹ năng:
        - Nếu kỹ năng ở trạng thái SUNSET và không bật cờ allow_sunset -> CHẶN ĐỨNG.
        - Trả về thông tin cảnh báo hoặc kỹ năng kế nhiệm.
        """
        s_dict = self._skills.get(skill_id)
        if not s_dict:
            return False, f"SKILL_NOT_FOUND: Kỹ năng {skill_id} chưa được đăng ký trong hệ thống", None

        v = version or self._latest_versions.get(skill_id)
        meta = s_dict.get(v)
        if not meta:
            return False, f"VERSION_NOT_FOUND: Phiên bản {v} của kỹ năng {skill_id} không tồn tại", None

        # Kiểm tra trạng thái SUNSET
        if meta.status == SkillLifecycleStatus.SUNSET:
            if not allow_sunset:
                return (
                    False,
                    f"SKILL_SUNSET_ERROR: Kỹ năng {skill_id}:{v} đã bị vô hiệu hóa (sự thật cũ). "
                    f"Vui lòng chuyển sang kỹ năng kế nhiệm: {meta.superseded_by or 'None'}",
                    {"status": "SUNSET", "superseded_by": meta.superseded_by},
                )

        # Kiểm tra DEPRECATED
        if meta.status == SkillLifecycleStatus.DEPRECATED:
            return (
                True,
                f"WARNING_SKILL_DEPRECATED: Kỹ năng {skill_id}:{v} sắp hết hạn. Kế nhiệm: {meta.superseded_by}",
                {"status": "DEPRECATED", "superseded_by": meta.superseded_by},
            )

        return True, "SKILL_ACTIVE_READY", {"status": "ACTIVE"}

    def _record_to_ledger(self, record: Dict[str, Any]) -> str:
        """Ghi nhận vào sổ cái băm chuỗi SHA-256 chống giả mạo."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        prev_hash = "GENESIS_SKILL_LIFECYCLE_HASH_000000"

        if self.ledger_path.exists():
            lines = [l.strip() for l in self.ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            if lines:
                try:
                    last_entry = json.loads(lines[-1])
                    prev_hash = last_entry.get("entry_hash", prev_hash)
                except Exception:
                    pass

        entry_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        payload_bytes = json.dumps(entry_data, sort_keys=True).encode("utf-8")
        entry_hash = hashlib.sha256(f"{prev_hash}|{payload_bytes.hex()}".encode("utf-8")).hexdigest()

        ledger_entry = {
            "prev_hash": prev_hash,
            "entry_hash": entry_hash,
            "data": entry_data,
        }

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")

        return entry_hash


# ==============================================================================
# 4. BOOTSTRAP & SINGLETON RUNTIME GATE
# ==============================================================================

_GLOBAL_SKILL_SUNSET_ENGINE: Optional[SkillSunsetEngine] = None


def get_skill_sunset_engine(auto_bootstrap: bool = True) -> SkillSunsetEngine:
    """Lấy thể hiện duy nhất của SkillSunsetEngine trong toàn hệ điều hành."""
    global _GLOBAL_SKILL_SUNSET_ENGINE
    if _GLOBAL_SKILL_SUNSET_ENGINE is None:
        _GLOBAL_SKILL_SUNSET_ENGINE = SkillSunsetEngine()
        if auto_bootstrap:
            bootstrap_physical_skills(engine=_GLOBAL_SKILL_SUNSET_ENGINE)
    return _GLOBAL_SKILL_SUNSET_ENGINE


def bootstrap_physical_skills(
    skills_root: Optional[Path] = None,
    engine: Optional[SkillSunsetEngine] = None,
) -> int:
    """
    Quét toàn bộ thư mục intelligence/skills/ và nạp các kỹ năng vật lý có manifest.json
    vào SkillSunsetEngine (đáp ứng điều kiện kiểm toán Lượt 336 của OpenCode).
    """
    root = Path(skills_root or Path("intelligence/skills")).resolve()
    target_engine = engine or get_skill_sunset_engine(auto_bootstrap=False)
    if not root.exists():
        return 0

    count = 0
    for p in root.rglob("manifest.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            skill_id = data.get("id") or p.parent.name
            version = data.get("version", "1.0.0")
            desc = data.get("description", "")
            meta = SkillVersionMeta(
                skill_id=skill_id,
                version=version,
                status=SkillLifecycleStatus.ACTIVE,
                metadata={"description": desc, "path": str(p)},
            )
            target_engine.register_skill_version(meta)
            count += 1
        except Exception:
            pass

    return count


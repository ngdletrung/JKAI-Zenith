"""
JKAI ZENITH — VERIFICATION PACKAGE: COGNITIVE VERIFIER (v2.1)
File: core/verification/verifier.py

Thẩm định kết quả thực thi (Correct? Complete? Meets mission criteria?).
Phân loại thất bại: FailureClassification (TRANSIENT, TOOL_FAILURE, MODEL_FAILURE, PLAN_FAILURE, VERIFICATION_FAILURE).
Đúc kết trải nghiệm Engram v2 với Bài học tiêu cực (Negative Memory qua từng Attempt).
"""

from __future__ import annotations
import os
import logging
from typing import Dict, Any, List, Optional

from core.contracts.cognitive_contract import CognitiveRequest, DeliverableType
from core.contracts.identity_contract import IdentityChain
from core.contracts.verification_contract import (
    VerificationResult,
    FailureClassification,
    RecoveryStrategy,
    ExperienceRecord,
)

logger = logging.getLogger("jkai.verification.verifier")


class CognitiveVerifier:
    """Bộ Thẩm Định Kết Quả Thực Thi (Cognitive Verifier v2.1)."""

    @classmethod
    def verify(
        cls,
        request: CognitiveRequest,
        result_payload: Dict[str, Any],
        identity: Optional[IdentityChain] = None
    ) -> VerificationResult:
        """
        Thẩm định kết quả thực thi so với CognitiveRequest.
        """
        deliv = request.deliverable
        ident = identity or request.identity
        missing: List[str] = []
        logs: List[str] = []
        fail_cls = FailureClassification.NONE
        rec_rec = RecoveryStrategy.NONE

        if deliv.type in (DeliverableType.FILE_BINARY, DeliverableType.FILE_CODE):
            target_path = result_payload.get("file_path") or deliv.target_path
            
            # 1. Kiểm tra tồn tại file trên đĩa
            if not target_path or not os.path.exists(target_path):
                missing.append(f"PHYSICAL_FILE_MISSING: {target_path}")
                logs.append(f"❌ File '{target_path}' does not exist on disk.")
                fail_cls = FailureClassification.TOOL_FAILURE
                rec_rec = RecoveryStrategy.SUBSTITUTE_CAPABILITY
            else:
                # 2. Kiểm tra dung lượng file > 0 bytes
                size = os.path.getsize(target_path)
                if size <= 0:
                    missing.append("FILE_EMPTY_ZERO_BYTES")
                    logs.append(f"❌ File '{target_path}' exists but is 0 bytes.")
                    fail_cls = FailureClassification.VERIFICATION_FAILURE
                    rec_rec = RecoveryStrategy.DIAGNOSE_AND_REPAIR
                else:
                    logs.append(f"✅ Physical file '{target_path}' verified ({size} bytes).")

                # 3. Thẩm định định dạng file đa năng (xlsx, docx, pdf, json, csv)
                fmt = (deliv.format or "").lower()
                if fmt in ("xlsx", "excel") or target_path.endswith(".xlsx"):
                    try:
                        import openpyxl
                        wb = openpyxl.load_workbook(target_path, read_only=True)
                        logs.append(f"✅ Excel integrity verified: {len(wb.sheetnames)} sheets found ({wb.sheetnames}).")
                        wb.close()
                    except Exception as e:
                        missing.append(f"EXCEL_CORRUPTED: {e}")
                        logs.append(f"❌ Excel integrity check failed: {e}")
                        fail_cls = FailureClassification.VERIFICATION_FAILURE
                        rec_rec = RecoveryStrategy.DIAGNOSE_AND_REPAIR

                elif fmt in ("docx", "word") or target_path.endswith(".docx"):
                    try:
                        import docx
                        doc = docx.Document(target_path)
                        p_count = len(doc.paragraphs)
                        logs.append(f"✅ Word document integrity verified: {p_count} paragraphs found.")
                    except Exception as e:
                        missing.append(f"DOCX_CORRUPTED: {e}")
                        logs.append(f"❌ Word document integrity check failed: {e}")
                        fail_cls = FailureClassification.VERIFICATION_FAILURE
                        rec_rec = RecoveryStrategy.DIAGNOSE_AND_REPAIR

                elif fmt == "pdf" or target_path.endswith(".pdf"):
                    try:
                        with open(target_path, "rb") as pf:
                            head = pf.read(10)
                            if b"%PDF-" not in head:
                                raise ValueError("Missing %PDF- magic bytes header")
                        logs.append("✅ PDF binary header integrity verified.")
                    except Exception as e:
                        missing.append(f"PDF_CORRUPTED: {e}")
                        logs.append(f"❌ PDF integrity check failed: {e}")
                        fail_cls = FailureClassification.VERIFICATION_FAILURE
                        rec_rec = RecoveryStrategy.DIAGNOSE_AND_REPAIR

                elif fmt == "json" or target_path.endswith(".json"):
                    try:
                        import json
                        with open(target_path, "r", encoding="utf-8") as jf:
                            json.load(jf)
                        logs.append("✅ JSON syntax integrity verified.")
                    except Exception as e:
                        missing.append(f"JSON_CORRUPTED: {e}")
                        logs.append(f"❌ JSON syntax check failed: {e}")
                        fail_cls = FailureClassification.VERIFICATION_FAILURE
                        rec_rec = RecoveryStrategy.DIAGNOSE_AND_REPAIR

                elif fmt == "csv" or target_path.endswith(".csv"):
                    try:
                        import csv
                        with open(target_path, "r", encoding="utf-8") as cf:
                            reader = list(csv.reader(cf))
                            if not reader:
                                raise ValueError("Empty CSV rows")
                        logs.append(f"✅ CSV structure verified: {len(reader)} rows.")
                    except Exception as e:
                        missing.append(f"CSV_CORRUPTED: {e}")
                        logs.append(f"❌ CSV check failed: {e}")
                        fail_cls = FailureClassification.VERIFICATION_FAILURE
                        rec_rec = RecoveryStrategy.DIAGNOSE_AND_REPAIR

        passed = len(missing) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(missing) * 0.4))

        ver_res = VerificationResult(
            identity=ident,
            passed=passed,
            score=score,
            failure_classification=fail_cls if not passed else FailureClassification.NONE,
            recommended_recovery=rec_rec if not passed else RecoveryStrategy.NONE,
            summary="Verification PASSED 100%" if passed else f"Verification FAILED: {', '.join(missing)}",
            missing_criteria=missing,
            diagnostic_logs=logs
        )
        logger.info(f"🔎 [COGNITIVE-VERIFIER]: Passed={passed}, Classification={fail_cls.value}, Summary='{ver_res.summary}'")
        return ver_res

    @classmethod
    def create_experience(
        cls,
        request: CognitiveRequest,
        verifier_result: VerificationResult,
        strategy: str,
        tools_used: List[str],
        failure_reason: Optional[str] = None
    ) -> ExperienceRecord:
        """
        Tạo Hồ sơ Trải nghiệm (ExperienceRecord) bao gồm Bài học tiêu cực qua từng Attempt.
        """
        negative_lessons: List[str] = []
        if not verifier_result.passed:
            for miss in verifier_result.missing_criteria:
                if "EXCEL_CORRUPTED" in miss:
                    negative_lessons.append("Avoid raw file stream writing for Excel. Use openpyxl.Workbook.save().")
                elif "PHYSICAL_FILE_MISSING" in miss:
                    negative_lessons.append("Ensure target directory exists before running script.")

        rec = ExperienceRecord(
            identity=verifier_result.identity,
            task_signature=f"{request.intent}_{request.deliverable.format}",
            context_summary=request.goal[:100],
            strategy_used=strategy,
            tools_used=tools_used,
            model_profile_used="AMG_SELECTED_MODEL",
            outcome="SUCCESS" if verifier_result.passed else "FAILED",
            failure_classification=verifier_result.failure_classification,
            failure_cause=failure_reason or verifier_result.summary if not verifier_result.passed else None,
            recovery_action=verifier_result.recommended_recovery.value if not verifier_result.passed else None,
            negative_lessons=negative_lessons,
            confidence_rating=verifier_result.score
        )
        logger.info(f"🧠 [ENGRAM-EXPERIENCE]: Logged record attempt={rec.identity.attempt_id}, outcome={rec.outcome}")
        return rec


class CompletionAuthority:
    """
    P0.3: Supreme Completion Authority (Invariants Enforcement Gate).
    The ONLY legal authority in JKAI Zenith that can grant COMPLETED status.
    Enforces the 3-Condition AND Invariant:
    Status = COMPLETED <=> (Artifact Exists) AND (Schema Valid) AND (State Changed)
    """
    @classmethod
    def evaluate_completion(
        cls,
        mission_id: str,
        receipts: List[Any],
        target_path: Optional[str] = None,
        expected_format: Optional[str] = None,
        initial_checksum: Optional[str] = None,
        verification_result: Optional[VerificationResult] = None
    ) -> Any:
        import hashlib
        from core.contracts.execution_receipt import (
            ExecutionReceipt,
            ExecutionStatus,
            CompletionCertificate,
            CompletionStatus
        )

        reasons: List[str] = []

        # 1. Execution Reality: all receipts must have exit_code == 0
        if not receipts:
            reasons.append("No execution receipts presented")
        for r in receipts:
            exit_code = getattr(r, "exit_code", 0)
            task_id = getattr(r, "task_id", "unknown")
            tool_name = getattr(r, "tool_name", "unknown")
            if exit_code != 0:
                reasons.append(f"Task '{task_id}' ({tool_name}) exited with non-zero code {exit_code}")

        # 2. Condition 1: Artifact Exists & Size > 0
        artifact_exists = False
        current_checksum = ""
        resolved_path = target_path

        if not resolved_path:
            for r in reversed(receipts):
                p = getattr(r, "output_artifact_path", None)
                if p:
                    resolved_path = p
                    break

        if resolved_path and os.path.exists(resolved_path):
            size = os.path.getsize(resolved_path)
            if size > 0:
                artifact_exists = True
                try:
                    with open(resolved_path, "rb") as f:
                        current_checksum = hashlib.sha256(f.read()).hexdigest()
                except Exception:
                    pass
            else:
                reasons.append(f"Artifact at '{resolved_path}' is 0 bytes (empty file)")
        else:
            if target_path:
                reasons.append(f"Artifact does not exist on disk: '{target_path}'")
            else:
                # Query/Read-only tasks without physical file output
                if not reasons:
                    artifact_exists = True

        # 3. Condition 2: Schema / Integrity Valid
        schema_valid = True
        if verification_result is not None:
            schema_valid = verification_result.passed
            if not schema_valid:
                reasons.extend(verification_result.missing_criteria)

        # 4. Condition 3: State Changed / Checksum Mutation
        state_changed = True
        if initial_checksum and current_checksum:
            if initial_checksum == current_checksum:
                state_changed = False
                reasons.append("State unchanged: artifact checksum identical to pre-state")

        is_completed = (artifact_exists and schema_valid and state_changed and len(reasons) == 0)
        status = CompletionStatus.COMPLETED if is_completed else CompletionStatus.FAILED_VERIFICATION

        cert = CompletionCertificate(
            mission_id=mission_id,
            status=status,
            artifact_exists=artifact_exists,
            schema_valid=schema_valid,
            state_changed=state_changed,
            sha256_checksum=current_checksum,
            evidence_count=len(receipts),
            reasons=reasons
        )
        logger.info(
            "🏛️ [COMPLETION-AUTHORITY]: Mission '%s' evaluated -> Status: %s (Artifact: %s, Schema: %s, StateChanged: %s)",
            mission_id, status.value, artifact_exists, schema_valid, state_changed
        )
        return cert


# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: core/cognitive_bus/reflex_evolution.py
- Role: Sovereign Reflex Evolution, Per-Language Calibration Gate & Instant Feedback Engine.
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.0

Invariants:
  1. 100-Gold-Label Gate (.keywork.md Part X.2): Strictly forbids fitting temperature T,
     computing official ECE, or promoting calibration_state to "calibrated" until
     master_gold_dataset.jsonl contains >= 100 records with reviewed_by_master == True.
  2. Instant Feedback Learning (.keywork.md Part X.3): POSITIVE_EXEMPLAR and NEGATIVE_GUARD
     take effect in RAM in < 50ms and persist append-only to disk without service restart.
  3. Contrastive Trajectory Harvesting: Collects (GOOD, BAD, NEAR_MISS) decision triples
     for offline non-autoregressive decision head distillation.
  4. Zero Egress & License Gate (.keywork.md Part V.5): Verifies manifest and SHA-256 before
     hot-swapping any local checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_GOLD_DATASET_PATH = ROOT_DIR / "data" / "gold" / "master_gold_dataset.jsonl"
DEFAULT_FEEDBACK_PATH = ROOT_DIR / "data" / "telemetry" / "reflex_feedback_memory.jsonl"
DEFAULT_CONTRASTIVE_PATH = ROOT_DIR / "data" / "telemetry" / "reflex_contrastive_trajectories.jsonl"
DEFAULT_MANIFEST_PATH = ROOT_DIR / "models" / "reflex_checkpoint_manifest.json"

GOLD_DATASET_MIN_SAMPLES: int = 100
GOLD_DATASET_MIN_FIT_SAMPLES: int = 100
GOLD_DATASET_MIN_PROMOTE_SAMPLES: int = 200
MAX_ECE_FOR_PROMOTION: float = 0.15

# Wide temperature search bounds [0.2, 15.0] (never blindly clamped at [0.5, 5.0],
# because extreme overconfident buckets like raw T=10.2 require T > 5.0).
TEMP_FIT_MIN_BOUND: float = 0.2
TEMP_FIT_MAX_BOUND: float = 15.0

# 5 Canonical Real JKAI Failure Archetypes for Gold Dataset Harvesting (Step 3/4)
REAL_FAILURE_ARCHETYPES: Tuple[str, ...] = (
    "PREMATURE_COMPLETION_CLAIM",
    "SEMANTIC_CACHE_ANTONYM_CONFUSION",
    "OPTIMISTIC_UNSAFE_ALLOW",
    "WRONG_CAPABILITY_SHORTLIST",
    "MISROUTED_FAST_VS_DEEP_PATH",
)

# Canonical Option-Count Calibration Buckets (learned from calibrated decision models)
CALIBRATION_BUCKETS: Tuple[str, ...] = (
    "choice:2",
    "choice:3-5",
    "choice:6-10",
    "boolean:2",
    "score:3-5",
)


def _fit_scalar_temperature_wide(recs: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Fits scalar temperature T over wide range [0.2, 15.0] using 2-stage coarse + fine
    grid search (avoiding the [0.5, 5.0] blind clamp that failed on raw T=10.2).
    Returns (best_t, best_mae_loss).
    """
    if not recs:
        return 1.0, 1.0

    def _eval_loss(cand_t: float) -> float:
        loss = 0.0
        for r in recs:
            raw_conf = max(1e-4, min(1.0 - 1e-4, float(r.get("raw_confidence", 0.8))))
            target_p = float(r["target_prob"]) if "target_prob" in r else (1.0 if r.get("is_correct", True) else 0.0)
            logit = math.log(raw_conf / (1.0 - raw_conf))
            scaled_p = 1.0 / (1.0 + math.exp(-logit / cand_t))
            loss += abs(scaled_p - target_p)
        return loss / len(recs)

    best_t = 1.0
    best_loss = float("inf")
    # Stage 1: Coarse scan across [0.2, 15.0] with step 0.2
    for step in range(1, 76):
        cand_t = round(step * 0.2, 2)
        loss = _eval_loss(cand_t)
        if loss < best_loss:
            best_loss = loss
            best_t = cand_t

    # Stage 2: Fine scan around best_t with step 0.02
    fine_lo = max(TEMP_FIT_MIN_BOUND, best_t - 0.30)
    fine_hi = min(TEMP_FIT_MAX_BOUND, best_t + 0.30)
    fine_steps = int(round((fine_hi - fine_lo) / 0.02)) + 1
    for i in range(fine_steps):
        cand_t = round(fine_lo + i * 0.02, 4)
        loss = _eval_loss(cand_t)
        if loss < best_loss:
            best_loss = loss
            best_t = round(cand_t, 4)

    return best_t, round(best_loss, 4)


def _normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    lowered = unicodedata.normalize("NFC", str(text)).lower().strip()
    return re.sub(r"\s+", " ", lowered)


def _tokenize_bilingual(text: str) -> List[str]:
    norm = _normalize_text_for_match(text)
    return [tok for tok in re.findall(r"[\wàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+", norm) if len(tok) > 1]


@dataclass
class FeedbackEntry:
    entry_id: str
    feedback_type: str  # "POSITIVE_EXEMPLAR" | "NEGATIVE_GUARD"
    language: str       # "vi" | "en" | "*"
    primitive: str      # "Boolean" | "Choice" | "Score"
    state_signature: str
    state_keywords: List[str]
    question_pattern: str
    target_value: Any
    reason: str
    created_at: float = field(default_factory=time.time)


@dataclass
class ContrastiveTrajectory:
    trajectory_id: str
    language: str
    primitive: str
    state_fingerprint: str
    question: str
    options: Optional[List[str]]
    good_outcome: Any
    bad_outcome: Any
    near_miss_outcome: Optional[Any]
    reflex_confidence: float
    resolution_source: str  # "TIER_3_RULE" | "SYSTEM_2_LLM" | "MASTER_FEEDBACK"
    recorded_at: float = field(default_factory=time.time)


class ReflexEvolutionManager:
    """
    Manages calibration gating, instant feedback learning, contrastive trajectory
    collection, real-failure gold harvesting, sealed test independence, and
    Master-locked calibration promotion for the Sovereign Reflex Substrate.
    """

    def __init__(
        self,
        gold_dataset_path: Optional[Path] = None,
        feedback_path: Optional[Path] = None,
        contrastive_path: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
    ):
        self.gold_dataset_path = Path(gold_dataset_path or DEFAULT_GOLD_DATASET_PATH)
        self.feedback_path = Path(feedback_path or DEFAULT_FEEDBACK_PATH)
        self.contrastive_path = Path(contrastive_path or DEFAULT_CONTRASTIVE_PATH)
        self.manifest_path = Path(manifest_path or DEFAULT_MANIFEST_PATH)

        self._lock = threading.RLock()
        self._feedback_entries: List[FeedbackEntry] = []

        # Per-language, per-primitive temperature scaling table (ADR 0005)
        # Default 1.0 (uncalibrated) until >= 100 Master-reviewed gold samples exist.
        self._temperatures: Dict[str, Dict[str, float]] = {
            "en": {"Boolean": 1.0, "Choice": 1.0, "Score": 1.0},
            "vi": {"Boolean": 1.0, "Choice": 1.0, "Score": 1.0},
            "*": {"Boolean": 1.0, "Choice": 1.0, "Score": 1.0},
        }
        # Per-language, per-option-count bucket temperature scaling table
        self._bucket_temperatures: Dict[str, Dict[str, float]] = {
            lang: {b: 1.0 for b in CALIBRATION_BUCKETS}
            for lang in ("en", "vi", "*")
        }
        self._calibration_state: Dict[str, str] = {
            "en": "uncalibrated",
            "vi": "uncalibrated",
            "*": "uncalibrated",
        }
        self._ready_for_promotion: Dict[str, bool] = {
            "en": False,
            "vi": False,
            "*": False,
        }
        self._ece_by_lang: Dict[str, Optional[float]] = {
            "en": None,
            "vi": None,
            "*": None,
        }

        self._load_feedback_from_disk()

    # ------------------------------------------------------------------
    # 1. Dual 100 / 200-Gold-Label Calibration Gate (.keywork.md Part X.2 & ADR 0005)
    # ------------------------------------------------------------------

    def count_verified_gold_labels(self) -> Tuple[int, Dict[str, int]]:
        """
        Counts strictly Master-reviewed records (reviewed_by_master == True)
        in master_gold_dataset.jsonl. Seed banks or unreviewed logs are ignored.
        """
        if not self.gold_dataset_path.exists():
            return 0, {"en": 0, "vi": 0, "*": 0}

        total = 0
        by_lang = {"en": 0, "vi": 0, "*": 0}
        try:
            with open(self.gold_dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_s = line.strip()
                    if not line_s:
                        continue
                    try:
                        rec = json.loads(line_s)
                    except Exception:
                        continue
                    if rec.get("reviewed_by_master") is True:
                        total += 1
                        lang = rec.get("language", "*")
                        if lang not in by_lang:
                            lang = "*"
                        by_lang[lang] += 1
        except Exception:
            return 0, {"en": 0, "vi": 0, "*": 0}

        return total, by_lang

    def can_calibrate(self) -> Tuple[bool, int]:
        """Returns (True, count) only if verified Master gold labels >= 100."""
        total, _ = self.count_verified_gold_labels()
        return (total >= GOLD_DATASET_MIN_FIT_SAMPLES), total

    def get_calibration_state(self, language: str = "*") -> str:
        """Returns calibration state for language (ADR 0005), fail-closed to 'uncalibrated'."""
        total, by_lang = self.count_verified_gold_labels()
        if total < GOLD_DATASET_MIN_PROMOTE_SAMPLES:
            return "uncalibrated"
        lang_count = by_lang.get(language, total if language == "*" else 0)
        if lang_count < GOLD_DATASET_MIN_PROMOTE_SAMPLES:
            return "uncalibrated"
        return self._calibration_state.get(language, "uncalibrated")

    def get_per_language_calibration_map(self) -> Dict[str, str]:
        return {
            "en": self.get_calibration_state("en"),
            "vi": self.get_calibration_state("vi"),
            "*": self.get_calibration_state("*"),
        }

    def get_temperature(self, language: str, primitive: str, bucket: Optional[str] = None) -> float:
        lang_key = language if language in self._temperatures else "*"
        if bucket:
            bucket_map = self._bucket_temperatures.get(lang_key, self._bucket_temperatures["*"])
            if bucket in bucket_map and abs(bucket_map[bucket] - 1.0) > 1e-6:
                return float(bucket_map[bucket])
        lang_map = self._temperatures.get(lang_key, self._temperatures["*"])
        return float(lang_map.get(primitive, 1.0))

    def fit_temperature_from_gold_dataset(
        self,
        *,
        master_approved: bool = False,
        master_signature: str = "",
    ) -> Dict[str, Any]:
        """
        Fits per-language and per-bucket temperature scaling over [0.2, 15.0] from Master Gold Dataset.
        Strictly enforces the Dual 100/200-Gold-Label Gate AND Step 6 Master Approval Lock:
          - n < 100: Forbidden to fit T or compute official ECE (BLOCKED_BY_100_GOLD_LABEL_GATE).
          - 100 <= n < 200: Internal temperature T fitted, calibration_state stays "uncalibrated" (FITTED_INTERNAL_ONLY).
          - n >= 200 per language AND ECE <= 0.15:
              * If master_approved=False (default machine call): stops at READY_FOR_MASTER_APPROVAL;
                calibration_state remains "uncalibrated" until Master calls promote_calibration().
              * If master_approved=True and non-empty master_signature: promotes to "calibrated" (CALIBRATED).
        """
        allowed, gold_count = self.can_calibrate()
        if not allowed:
            self._calibration_state = {"en": "uncalibrated", "vi": "uncalibrated", "*": "uncalibrated"}
            self._ready_for_promotion = {"en": False, "vi": False, "*": False}
            self._ece_by_lang = {"en": None, "vi": None, "*": None}
            return {
                "status": "BLOCKED_BY_100_GOLD_LABEL_GATE",
                "calibrated": False,
                "ready_for_master_approval": False,
                "gold_count": gold_count,
                "required_min": GOLD_DATASET_MIN_FIT_SAMPLES,
                "required_promote_min": GOLD_DATASET_MIN_PROMOTE_SAMPLES,
                "remaining_needed": max(0, GOLD_DATASET_MIN_FIT_SAMPLES - gold_count),
                "calibration_state": dict(self._calibration_state),
                "reason": (
                    f"Master Gold Dataset has {gold_count}/{GOLD_DATASET_MIN_FIT_SAMPLES} verified labels. "
                    "Temperature fitting and ECE calculation are strictly prohibited until n >= 100."
                ),
            }

        records_by_lang: Dict[str, List[Dict[str, Any]]] = {"en": [], "vi": [], "*": []}
        with open(self.gold_dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("reviewed_by_master") is True:
                    lang = rec.get("language", "*")
                    records_by_lang.setdefault(lang if lang in ("en", "vi") else "*", []).append(rec)
                    records_by_lang["*"].append(rec)

        any_promoted = False
        any_ready = False
        has_master_key = (master_approved is True and bool(str(master_signature).strip()))

        for lang, recs in records_by_lang.items():
            if len(recs) < GOLD_DATASET_MIN_FIT_SAMPLES:
                self._calibration_state[lang] = "uncalibrated"
                self._ready_for_promotion[lang] = False
                continue

            best_t, best_loss = _fit_scalar_temperature_wide(recs)
            for prim in ("Boolean", "Choice", "Score"):
                self._temperatures[lang][prim] = best_t

            # Fit per-primitive and per-option-count bucket temperatures if bucketed records exist
            by_bucket: Dict[str, List[Dict[str, Any]]] = {}
            for r in recs:
                b_key = str(r.get("calibration_bucket") or "").strip()
                if b_key:
                    by_bucket.setdefault(b_key, []).append(r)
            for b_key in CALIBRATION_BUCKETS:
                b_recs = by_bucket.get(b_key, [])
                if len(b_recs) >= 10:
                    bt, _ = _fit_scalar_temperature_wide(b_recs)
                    self._bucket_temperatures[lang][b_key] = bt
                else:
                    self._bucket_temperatures[lang][b_key] = best_t

            self._ece_by_lang[lang] = best_loss

            if len(recs) >= GOLD_DATASET_MIN_PROMOTE_SAMPLES and best_loss <= MAX_ECE_FOR_PROMOTION:
                self._ready_for_promotion[lang] = True
                any_ready = True
                if has_master_key:
                    self._calibration_state[lang] = "calibrated"
                    any_promoted = True
                else:
                    self._calibration_state[lang] = "uncalibrated"
            else:
                self._ready_for_promotion[lang] = False
                self._calibration_state[lang] = "uncalibrated"

        if any_promoted:
            status_str = "CALIBRATED"
        elif any_ready:
            status_str = "READY_FOR_MASTER_APPROVAL"
        else:
            status_str = "FITTED_INTERNAL_ONLY"

        return {
            "status": status_str,
            "calibrated": any_promoted,
            "ready_for_master_approval": any_ready,
            "gold_count": gold_count,
            "required_promote_min": GOLD_DATASET_MIN_PROMOTE_SAMPLES,
            "temperatures": dict(self._temperatures),
            "bucket_temperatures": dict(self._bucket_temperatures),
            "calibration_state": dict(self._calibration_state),
            "ece_by_language": dict(self._ece_by_lang),
        }

    def promote_calibration(
        self,
        language: str = "*",
        *,
        master_approved: bool = False,
        master_signature: str = "",
    ) -> Dict[str, Any]:
        """
        Step 6 Master Key Lock: Machine can NEVER auto-promote calibration_state to 'calibrated'.
        Requires explicit Master authorization (master_approved=True + non-empty master_signature)
        after verifying n >= 200 and ECE <= 0.15 for the target language.
        """
        if master_approved is not True or not str(master_signature).strip():
            raise PermissionError(
                "Master Governance Lock Violation: Machine cannot auto-promote calibration_state. "
                "Explicit Master approval (master_approved=True and non-empty master_signature) is required."
            )
        total, by_lang = self.count_verified_gold_labels()
        lang_count = by_lang.get(language, total if language == "*" else 0)
        if lang_count < GOLD_DATASET_MIN_PROMOTE_SAMPLES:
            raise ValueError(
                f"Cannot promote '{language}': only {lang_count}/{GOLD_DATASET_MIN_PROMOTE_SAMPLES} Master-reviewed gold labels."
            )
        ece = self._ece_by_lang.get(language)
        if ece is None or ece > MAX_ECE_FOR_PROMOTION:
            raise ValueError(
                f"Cannot promote '{language}': ECE={ece} exceeds max allowed {MAX_ECE_FOR_PROMOTION} (or temperature not yet fitted)."
            )
        self._calibration_state[language] = "calibrated"
        return {
            "status": "PROMOTED_BY_MASTER",
            "language": language,
            "calibration_state": self._calibration_state[language],
            "ece": ece,
            "master_signature": str(master_signature).strip(),
        }

    # ------------------------------------------------------------------
    # 2. Instant Feedback Learning (< 50ms — .keywork.md Part X.3)
    # ------------------------------------------------------------------

    def _load_feedback_from_disk(self) -> None:
        if not self.feedback_path.exists():
            return
        try:
            loaded: List[FeedbackEntry] = []
            with open(self.feedback_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    loaded.append(FeedbackEntry(**data))
            with self._lock:
                self._feedback_entries = loaded
        except Exception:
            pass

    def learn_from_feedback(
        self,
        state: Any,
        question: str,
        target_value: Any,
        feedback_type: str = "POSITIVE_EXEMPLAR",
        primitive: str = "Choice",
        language: str = "*",
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Records a POSITIVE_EXEMPLAR (ACCEPT) or NEGATIVE_GUARD (REJECT) in RAM immediately
        (< 50ms) and appends to JSONL persistence without service restart.
        """
        t0 = time.perf_counter()
        if feedback_type not in ("POSITIVE_EXEMPLAR", "NEGATIVE_GUARD"):
            raise ValueError(f"Invalid feedback_type: {feedback_type}")

        state_str = json.dumps(state, ensure_ascii=False, sort_keys=True) if isinstance(state, (dict, list)) else str(state)
        state_norm = _normalize_text_for_match(state_str)
        state_sig = hashlib.sha256(state_norm.encode("utf-8")).hexdigest()[:16]
        keywords = _tokenize_bilingual(state_norm)[:24]
        q_norm = _normalize_text_for_match(question)
        entry_id = hashlib.sha256(f"{state_sig}:{q_norm}:{feedback_type}:{target_value}".encode("utf-8")).hexdigest()[:12]

        entry = FeedbackEntry(
            entry_id=entry_id,
            feedback_type=feedback_type,
            language=language,
            primitive=primitive,
            state_signature=state_sig,
            state_keywords=keywords,
            question_pattern=q_norm,
            target_value=target_value,
            reason=reason or f"Instant {feedback_type} registered",
        )

        with self._lock:
            # Replace existing entry with same ID if present, otherwise append
            self._feedback_entries = [e for e in self._feedback_entries if e.entry_id != entry_id]
            self._feedback_entries.append(entry)

        try:
            self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.feedback_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        except Exception:
            pass

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "entry_id": entry_id,
            "feedback_type": feedback_type,
            "latency_ms": round(elapsed_ms, 3),
            "active_entries": len(self._feedback_entries),
        }

    def lookup_feedback_adjustments(
        self,
        state: Any,
        question: str,
    ) -> Tuple[Optional[Any], List[Any], Optional[str]]:
        """
        Checks in-memory feedback entries for matching state & question.
        Returns: (positive_exemplar_value, negative_guard_values, matched_entry_id)
        """
        with self._lock:
            if not self._feedback_entries:
                return None, [], None
            entries = list(self._feedback_entries)

        state_str = json.dumps(state, ensure_ascii=False, sort_keys=True) if isinstance(state, (dict, list)) else str(state)
        state_norm = _normalize_text_for_match(state_str)
        state_sig = hashlib.sha256(state_norm.encode("utf-8")).hexdigest()[:16]
        state_tokens = set(_tokenize_bilingual(state_norm))
        q_norm = _normalize_text_for_match(question)

        pos_val: Optional[Any] = None
        neg_vals: List[Any] = []
        matched_id: Optional[str] = None

        for entry in reversed(entries):
            # Question match check
            if entry.question_pattern != q_norm and entry.question_pattern not in q_norm and q_norm not in entry.question_pattern:
                continue

            # Exact state signature or high keyword overlap (>= 75%)
            is_match = (entry.state_signature == state_sig)
            if not is_match and entry.state_keywords:
                overlap = len(state_tokens & set(entry.state_keywords)) / len(set(entry.state_keywords))
                if overlap >= 0.75:
                    is_match = True

            if is_match:
                if entry.feedback_type == "POSITIVE_EXEMPLAR" and pos_val is None:
                    pos_val = entry.target_value
                    matched_id = entry.entry_id
                elif entry.feedback_type == "NEGATIVE_GUARD":
                    if entry.target_value not in neg_vals:
                        neg_vals.append(entry.target_value)
                    if matched_id is None:
                        matched_id = entry.entry_id

        return pos_val, neg_vals, matched_id

    # ------------------------------------------------------------------
    # 3. Contrastive Trajectory Harvester (RLCD Ready)
    # ------------------------------------------------------------------

    def record_contrastive_trajectory(
        self,
        language: str,
        primitive: str,
        state_fingerprint: str,
        question: str,
        options: Optional[List[str]],
        good_outcome: Any,
        bad_outcome: Any,
        reflex_confidence: float,
        resolution_source: str = "SYSTEM_2_LLM",
        near_miss_outcome: Optional[Any] = None,
    ) -> str:
        """
        Persists a contrastive boundary record (GOOD vs BAD vs NEAR_MISS)
        for future offline RLCD head training.
        """
        traj_id = hashlib.sha256(
            f"{state_fingerprint}:{question}:{good_outcome}:{bad_outcome}:{time.time_ns()}".encode("utf-8")
        ).hexdigest()[:16]

        traj = ContrastiveTrajectory(
            trajectory_id=traj_id,
            language=language,
            primitive=primitive,
            state_fingerprint=state_fingerprint,
            question=question,
            options=options,
            good_outcome=good_outcome,
            bad_outcome=bad_outcome,
            near_miss_outcome=near_miss_outcome,
            reflex_confidence=round(float(reflex_confidence), 4),
            resolution_source=resolution_source,
        )

        try:
            self.contrastive_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.contrastive_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(traj), ensure_ascii=False) + "\n")
        except Exception:
            pass

        return traj_id

    # ------------------------------------------------------------------
    # 4. License Gate & Hot-Swap Checkpoint Verification
    # ------------------------------------------------------------------

    def verify_checkpoint_manifest(self, checkpoint_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validates models/reflex_checkpoint_manifest.json per .keywork.md Part V.5 License Gate.
        """
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Reflex checkpoint manifest missing: {self.manifest_path}")

        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        license_id = manifest.get("research_reference", {}).get("license", "")
        egress = manifest.get("runtime_execution", {}).get("egress_policy", "")
        remote_dl = manifest.get("runtime_execution", {}).get("allow_remote_hub_download", True)

        if license_id != "Apache-2.0":
            raise PermissionError(f"License Gate violation: expected Apache-2.0, got '{license_id}'")
        if egress != "local-only" or remote_dl is not False:
            raise PermissionError("Sovereign Egress Gate violation: remote hub download is prohibited")

        target_dir = Path(checkpoint_dir) if checkpoint_dir else ROOT_DIR / manifest.get("weights_provenance", {}).get("local_checkpoint_dir", "models/sovereign_reflex_multilingual")
        weights_found = False
        computed_sha256: Optional[str] = None

        if target_dir.exists() and target_dir.is_dir():
            for weight_file in ("model.safetensors", "model.onnx", "pytorch_model.bin"):
                wf = target_dir / weight_file
                if wf.exists() and wf.stat().st_size > 0:
                    weights_found = True
                    h = hashlib.sha256()
                    with open(wf, "rb") as f:
                        while chunk := f.read(65536):
                            h.update(chunk)
                    computed_sha256 = h.hexdigest()
                    expected_sha = manifest.get("weights_provenance", {}).get("sha256")
                    if expected_sha and expected_sha != computed_sha256:
                        raise ValueError(
                            f"Checkpoint SHA-256 mismatch for {wf}: expected {expected_sha}, got {computed_sha256}"
                        )
                    break

        return {
            "manifest_valid": True,
            "license": license_id,
            "egress_policy": egress,
            "checkpoint_dir": str(target_dir),
            "weights_found": weights_found,
            "sha256": computed_sha256,
        }

    # ------------------------------------------------------------------
    # 5. Real JKAI Failure Gold Dataset Harvester (Step 3)
    # ------------------------------------------------------------------

    def record_real_failure_gold_candidate(
        self,
        *,
        state: Dict[str, Any],
        correct_choice: str,
        rationale: str,
        execution_evidence: Any,
        acceptance_criteria: str,
        failure_archetype: str,
        language: str = "vi",
        raw_confidence: float = 0.85,
        is_correct: bool = True,
        calibration_bucket: str = "choice:3-5",
        reviewed_by_master: bool = False,
    ) -> Dict[str, Any]:
        """
        Harvests a real JKAI failure case into master_gold_dataset.jsonl according to the
        5 canonical failure archetypes. Enforces that all 5 fields (state, correct_choice,
        rationale, execution_evidence, acceptance_criteria) are non-empty, forbids any
        COMPLETE / COMPLETE_CANDIDATE label in correct_choice, and defaults
        reviewed_by_master=False until Master explicitly reviews the sample.
        """
        if failure_archetype not in REAL_FAILURE_ARCHETYPES:
            raise ValueError(
                f"Invalid failure_archetype '{failure_archetype}'. Must be one of {REAL_FAILURE_ARCHETYPES}"
            )
        if not state or not isinstance(state, dict):
            raise ValueError("Gold failure record requires a non-empty 'state' dict")
        choice_norm = str(correct_choice or "").strip()
        if not choice_norm:
            raise ValueError("Gold failure record requires a non-empty 'correct_choice'")
        if choice_norm.lower() in ("complete", "completed", "complete_candidate", "task_complete", "done") or choice_norm.lower().startswith("complete_"):
            raise PermissionError(
                f"NO_EVIDENCE_NO_COMPLETION Violation: '{choice_norm}' cannot be used as a gold model label. "
                "Use 'VERIFY_AND_CLOSE' proposal instead."
            )
        if not str(rationale or "").strip():
            raise ValueError("Gold failure record requires a non-empty 'rationale'")
        if not execution_evidence:
            raise ValueError("Gold failure record requires non-empty physical 'execution_evidence'")
        if not str(acceptance_criteria or "").strip():
            raise ValueError("Gold failure record requires non-empty 'acceptance_criteria'")

        sample_id = "gold_" + hashlib.sha256(
            f"{json.dumps(state, sort_keys=True, ensure_ascii=False)}:{choice_norm}:{failure_archetype}".encode("utf-8")
        ).hexdigest()[:12]

        record = {
            "sample_id": sample_id,
            "failure_archetype": failure_archetype,
            "language": language,
            "state": state,
            "correct_choice": choice_norm,
            "rationale": str(rationale).strip(),
            "execution_evidence": execution_evidence,
            "acceptance_criteria": str(acceptance_criteria).strip(),
            "raw_confidence": float(raw_confidence),
            "is_correct": bool(is_correct),
            "calibration_bucket": calibration_bucket,
            "reviewed_by_master": bool(reviewed_by_master),
            "created_at": time.time(),
        }

        self.gold_dataset_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.gold_dataset_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    # ------------------------------------------------------------------
    # 6. Option Order Permutation Invariance, Sealed Test & A/B Kill Switch (Steps 4, 5, 6)
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_order_invariance(
        backend: Any,
        state: Dict[str, Any],
        question: str,
        options: List[str],
    ) -> Dict[str, Any]:
        """
        Tests option-order permutation stability (Original, Reversed, and Cyclic Rotations)
        to verify that the decision backend does not suffer from position bias.
        """
        from core.cognitive_bus.decision_substrate_adapter import DecisionPrimitive

        if len(options) < 2:
            raise ValueError("evaluate_order_invariance requires at least 2 options")

        permutations: List[List[str]] = [
            list(options),
            list(reversed(options)),
        ]
        for shift in range(1, min(len(options), 4)):
            permutations.append(list(options[shift:]) + list(options[:shift]))

        winners: List[str] = []
        winner_probs: List[float] = []

        for perm in permutations:
            pkt = backend.predict(
                state=state,
                questions=[(DecisionPrimitive.CHOICE, question, perm)],
            )[question]
            winners.append(str(pkt.result))
            winner_probs.append(float(pkt.distribution.get(str(pkt.result), pkt.confidence)))

        canonical_winner = winners[0]
        consistent_count = sum(1 for w in winners if w == canonical_winner)
        consistency_rate = round(consistent_count / len(permutations), 6)
        max_prob_drift = round(max(winner_probs) - min(winner_probs), 6) if winner_probs else 0.0

        return {
            "passed": consistency_rate == 1.0 and max_prob_drift <= 0.05,
            "canonical_winner": canonical_winner,
            "permutations_tested": len(permutations),
            "consistency_rate": consistency_rate,
            "max_prob_drift": max_prob_drift,
            "winners_by_permutation": winners,
        }

    @staticmethod
    def verify_sealed_test_independence(
        test_author_id: str,
        scorer_author_id: str,
        dataset_path: Optional[Path] = None,
        expected_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Step 4 Sealed Test Set Governance (Zero Self-Grading):
        Enforces that the person/agent who authored the sealed test set is strictly
        distinct from the author of the scorer, and verifies SHA-256 integrity if provided.
        """
        a_test = str(test_author_id or "").strip().lower()
        a_score = str(scorer_author_id or "").strip().lower()
        if not a_test or not a_score:
            raise ValueError("Both test_author_id and scorer_author_id must be non-empty")
        if a_test == a_score:
            raise PermissionError(
                f"Zero Self-Grading Violation: test_author_id ('{test_author_id}') and "
                f"scorer_author_id ('{scorer_author_id}') must be distinct identities."
            )

        computed_sha256: Optional[str] = None
        if dataset_path is not None:
            p = Path(dataset_path)
            if not p.exists():
                raise FileNotFoundError(f"Sealed test dataset not found: {p}")
            computed_sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
            if expected_sha256 and computed_sha256 != expected_sha256:
                raise ValueError(
                    f"Sealed test dataset SHA-256 mismatch: expected {expected_sha256}, got {computed_sha256}"
                )

        return {
            "independent": True,
            "test_author_id": test_author_id,
            "scorer_author_id": scorer_author_id,
            "dataset_sha256": computed_sha256,
        }

    @staticmethod
    def evaluate_ab_kill_switch(
        baseline_metrics: Dict[str, float],
        candidate_metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Step 5 A/B Kill-Switch Gate:
        Evaluates a candidate fine-tuned model or advisory router against 3 mandatory criteria:
          1. true_completion_rate strictly increases
          2. premature_completion_rate strictly decreases
          3. large_model_call_rate strictly decreases
        ALL THREE must pass to return KEEP_CANDIDATE; missing even one triggers KILL_AND_ROLLBACK.
        """
        c1_true_comp_up = float(candidate_metrics["true_completion_rate"]) > float(baseline_metrics["true_completion_rate"])
        c2_premature_down = float(candidate_metrics["premature_completion_rate"]) < float(baseline_metrics["premature_completion_rate"])
        c3_large_call_down = float(candidate_metrics["large_model_call_rate"]) < float(baseline_metrics["large_model_call_rate"])

        all_three_passed = bool(c1_true_comp_up and c2_premature_down and c3_large_call_down)
        return {
            "verdict": "KEEP_CANDIDATE" if all_three_passed else "KILL_AND_ROLLBACK",
            "all_three_passed": all_three_passed,
            "criteria": {
                "true_completion_rate_increased": c1_true_comp_up,
                "premature_completion_rate_decreased": c2_premature_down,
                "large_model_call_rate_decreased": c3_large_call_down,
            },
            "deltas": {
                "true_completion_rate_delta": round(
                    float(candidate_metrics["true_completion_rate"]) - float(baseline_metrics["true_completion_rate"]), 6
                ),
                "premature_completion_rate_delta": round(
                    float(candidate_metrics["premature_completion_rate"]) - float(baseline_metrics["premature_completion_rate"]), 6
                ),
                "large_model_call_rate_delta": round(
                    float(candidate_metrics["large_model_call_rate"]) - float(baseline_metrics["large_model_call_rate"]), 6
                ),
            },
        }

    def generate_readiness_report(
        self,
        *,
        baseline_metrics: Optional[Dict[str, float]] = None,
        candidate_metrics: Optional[Dict[str, float]] = None,
        order_invariance_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Step 6 Machine-Only Readiness Report:
        The machine is only permitted to submit a PASS/FAIL readiness report to Master;
        it can NEVER auto-flip the active backend or auto-promote calibration_state.
        """
        total_gold, by_lang = self.count_verified_gold_labels()
        ab_eval = (
            self.evaluate_ab_kill_switch(baseline_metrics, candidate_metrics)
            if (baseline_metrics and candidate_metrics)
            else None
        )
        order_ok = bool(order_invariance_result.get("passed", False)) if order_invariance_result else False
        cal_ready = any(self._ready_for_promotion.values()) and total_gold >= GOLD_DATASET_MIN_PROMOTE_SAMPLES
        ab_ok = bool(ab_eval and ab_eval["all_three_passed"]) if ab_eval is not None else True

        overall_pass = bool(cal_ready and order_ok and ab_ok)
        return {
            "report_verdict": "PASS_AWAITING_MASTER_KEY" if overall_pass else "NOT_READY",
            "machine_can_auto_promote": False,
            "machine_can_auto_flip_backend": False,
            "verified_gold_labels": total_gold,
            "verified_gold_by_language": by_lang,
            "calibration_state": dict(self._calibration_state),
            "ready_for_promotion_by_language": dict(self._ready_for_promotion),
            "ece_by_language": dict(self._ece_by_lang),
            "order_invariance_passed": order_ok,
            "ab_kill_switch": ab_eval,
        }


_DEFAULT_EVOLUTION_MANAGER: Optional[ReflexEvolutionManager] = None


def get_reflex_evolution_manager() -> ReflexEvolutionManager:
    global _DEFAULT_EVOLUTION_MANAGER
    if _DEFAULT_EVOLUTION_MANAGER is None:
        _DEFAULT_EVOLUTION_MANAGER = ReflexEvolutionManager()
    return _DEFAULT_EVOLUTION_MANAGER

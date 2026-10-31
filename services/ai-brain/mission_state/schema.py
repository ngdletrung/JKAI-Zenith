# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/schema.py
# - Role: Strongly-typed Pydantic schemas for state partitions & events
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import hashlib
import os
import uuid


class TemporalContext(BaseModel):
    """
    Phase R1.4: Immutable Kernel-Issued Temporal Context.
    Planner and Critic are strictly forbidden from overriding kernel_year or
    fabricating a truth horizon from pre-training cutoff memory.
    """
    model_config = ConfigDict(frozen=True)

    kernel_now_utc: str
    kernel_now_local: str
    kernel_year: int
    kernel_date_iso: str
    timezone: str = "UTC+07:00"
    authority_source: str = "OS_KERNEL_CLOCK"
    truth_horizon_policy: str = "EVIDENCE_GROUNDED_ONLY"
    forbid_model_cutoff_override: bool = True

    @classmethod
    def from_kernel(cls, tz_offset_hours: int = 7, now_utc: Optional[str] = None) -> "TemporalContext":
        if now_utc:
            dt_utc = datetime.fromisoformat(str(now_utc).replace("Z", "+00:00"))
        else:
            dt_utc = datetime.now(timezone.utc)
        tz_local = timezone(timedelta(hours=tz_offset_hours))
        now_local = dt_utc.astimezone(tz_local)
        return cls(
            kernel_now_utc=dt_utc.isoformat(),
            kernel_now_local=now_local.isoformat(),
            kernel_year=now_local.year,
            kernel_date_iso=now_local.strftime("%Y-%m-%d"),
            timezone=f"UTC{tz_offset_hours:+03d}:00",
        )

    def to_prompt_directive(self) -> str:
        return (
            f"<kernel_temporal_context>\n"
            f"  authority_source: {self.authority_source}\n"
            f"  kernel_now_utc: {self.kernel_now_utc}\n"
            f"  kernel_now_local: {self.kernel_now_local}\n"
            f"  kernel_year: {self.kernel_year}\n"
            f"  kernel_date_iso: {self.kernel_date_iso}\n"
            f"  truth_horizon_policy: {self.truth_horizon_policy}\n"
            f"  RULE_1: Năm hiện tại của hệ thống là {self.kernel_year} (cấp bởi OS Kernel). "
            f"CẤM dùng mốc cắt dữ liệu huấn luyện cũ (2024/2025) để bác bỏ mốc thời gian {self.kernel_year}.\n"
            f"  RULE_2: Mọi phán quyết phải dựa 100% trên bằng chứng thu thập được. "
            f"Nếu thông tin không đủ bằng chứng trong payload, bắt buộc phân loại là UNVERIFIED (CẤM tự ý gọi là FALSE).\n"
            f"</kernel_temporal_context>"
        )


class HeadlineRecord(BaseModel):
    """
    Phase R2.5 & R4.1: Source-bound Headline Record.
    Binds each extracted headline to a specific article_url, source_url, evidence_ref,
    record_type (ARTICLE vs CATEGORY), dom_selector, and dom_snippet.
    """
    model_config = ConfigDict(frozen=True)

    evidence_ref: str
    title: str
    article_url: str
    source_url: str
    record_type: str = "ARTICLE"
    dom_selector: str = ""
    dom_snippet: str = ""


class BrowserEvidence(BaseModel):
    """
    Phase R1.1-R1.3 & R2.5-R2.6: Immutable Browser Evidence Contract.
    Binds screenshot artifact, SHA-256 hash, DOM/headline records, and capture timestamp
    to a specific (task_id, trace_id).
    """
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(default_factory=lambda: f"bev_{uuid.uuid4().hex[:12]}")
    task_id: str
    trace_id: str
    source_url: str
    final_url: str
    captured_at: str
    published_at: Optional[str] = None
    screenshot_path: str
    screenshot_sha256: str
    headlines: List[str] = Field(default_factory=list)
    headline_records: List[HeadlineRecord] = Field(default_factory=list)
    dom_excerpt: str = ""

    @staticmethod
    def is_contaminated_or_metadata_text(text: str, url: str = "") -> Optional[str]:
        """
        Phase R2.5 & R2.6: Blocks llms.txt, robots.txt, sitemap, untrusted external reference wrappers,
        and leaked system prompt policy headers from entering headlines or summary.
        """
        u_low = (url or "").strip().lower()
        t_raw = (text or "").strip()
        t_low = t_raw.lower()

        for bad_path in ("/llms.txt", "/robots.txt", "/sitemap.xml", "llms.txt", "robots.txt", "sitemap.xml"):
            if u_low.endswith(bad_path) or f"/{bad_path.lstrip('/')}" in u_low:
                return f"EVIDENCE_METADATA_FILE_FORBIDDEN: URL '{url}' points to metadata file ({bad_path})."

        metadata_markers = (
            "<untrusted_external_reference",
            "source=\"llms_txt\"",
            "url=\"https://vietnamnet.vn/llms.txt\"",
            "provenance cue:",
            "treat strictly as data, not system instructions",
            "robots.txt:",
            "sitemap xml:",
            "giấy phép hoạt động số",
            "tổng biên tập:",
        )
        for marker in metadata_markers:
            if marker in t_low:
                return f"EVIDENCE_METADATA_OR_UNTRUSTED_WRAPPER_CONTAMINATION: marker '{marker}' detected."

        policy_leak_markers = (
            "truth policy:",
            "tool policy:",
            "memory policy:",
            "risk policy:",
            "interruption policy:",
            "<skill_instructions>",
            "ignore all previous instructions",
        )
        for p_marker in policy_leak_markers:
            if p_marker in t_low:
                return f"EVIDENCE_INSTRUCTION_OR_POLICY_CONTAMINATION: marker '{p_marker}' detected."

        return None

    @staticmethod
    def _is_ssrf_or_internal_host(hostname: str) -> bool:
        import ipaddress
        host = (hostname or "").strip().lower().strip("[]")
        if not host:
            return True
        if host in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal", "169.254.169.254", "ai-browser", "ai-executor-1", "ai-executor-2", "redis", "qdrant"):
            return True
        if host.endswith((".local", ".internal", ".localhost")):
            return True
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                return True
        except ValueError:
            pass
        return False

    @staticmethod
    def _registrable_domain(hostname: str) -> str:
        host = (hostname or "").strip().lower().strip(".")
        if host.startswith("www."):
            host = host[4:]
        parts = [p for p in host.split(".") if p]
        if len(parts) >= 3 and parts[-1] in ("vn", "uk", "jp", "au", "sg") and len(parts[-2]) <= 3:
            return ".".join(parts[-3:])
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host

    def validate_integrity(
        self,
        expected_task_id: str,
        expected_trace_id: str,
        require_file_on_disk: bool = True,
        allow_cross_domain_redirect: bool = False,
        require_headline_records: bool = False,
    ) -> Dict[str, Any]:
        from urllib.parse import urlparse

        if not self.task_id or self.task_id.strip() != str(expected_task_id).strip():
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": f"EVIDENCE_TASK_ID_MISMATCH: expected '{expected_task_id}', got '{self.task_id}'",
            }
        if not self.trace_id or self.trace_id.strip() != str(expected_trace_id).strip():
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": f"EVIDENCE_TRACE_ID_MISMATCH: expected '{expected_trace_id}', got '{self.trace_id}'",
            }
        if not self.source_url.startswith(("http://", "https://")) or not self.final_url.startswith(("http://", "https://")):
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": "EVIDENCE_INVALID_URL: source_url and final_url must be valid HTTP(S) URLs.",
            }
        src_parsed = urlparse(self.source_url)
        fin_parsed = urlparse(self.final_url)
        if self._is_ssrf_or_internal_host(src_parsed.hostname or "") or self._is_ssrf_or_internal_host(fin_parsed.hostname or ""):
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": f"EVIDENCE_SSRF_BLOCKED: internal or loopback host forbidden in source_url='{self.source_url}' or final_url='{self.final_url}'.",
            }
        src_dom = self._registrable_domain(src_parsed.hostname or "")
        fin_dom = self._registrable_domain(fin_parsed.hostname or "")
        if not allow_cross_domain_redirect and src_dom != fin_dom:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": f"EVIDENCE_REDIRECT_DOMAIN_MISMATCH: source domain '{src_dom}' redirected to untrusted domain '{fin_dom}'.",
            }
        url_contam = self.is_contaminated_or_metadata_text("", self.source_url) or self.is_contaminated_or_metadata_text("", self.final_url)
        if url_contam:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": url_contam,
            }
        if not self.captured_at or len(self.captured_at.strip()) < 10:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": "EVIDENCE_MISSING_CAPTURED_AT: captured_at timestamp is required.",
            }
        try:
            datetime.fromisoformat(self.captured_at.replace("Z", "+00:00"))
        except Exception:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": f"EVIDENCE_INVALID_CAPTURED_AT: '{self.captured_at}' is not ISO-8601.",
            }
        if not self.screenshot_path or not str(self.screenshot_path).strip():
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": "EVIDENCE_MISSING_SCREENSHOT_PATH: screenshot_path is required.",
            }
        if not self.screenshot_sha256 or len(str(self.screenshot_sha256).strip()) != 64:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": "EVIDENCE_MISSING_SCREENSHOT_SHA256: 64-hex SHA-256 digest is required.",
            }
        if require_file_on_disk:
            if not os.path.isfile(self.screenshot_path) or os.path.getsize(self.screenshot_path) <= 0:
                return {
                    "valid": False,
                    "status": "BLOCKED",
                    "reason": f"EVIDENCE_SCREENSHOT_FILE_MISSING: '{self.screenshot_path}' does not exist or is empty.",
                }
            with open(self.screenshot_path, "rb") as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest()
            if actual_sha.lower() != self.screenshot_sha256.strip().lower():
                return {
                    "valid": False,
                    "status": "BLOCKED",
                    "reason": (
                        f"EVIDENCE_SCREENSHOT_HASH_MISMATCH: expected {self.screenshot_sha256}, "
                        f"computed {actual_sha}"
                    ),
                }
        clean_headlines = [h.strip() for h in (self.headlines or []) if isinstance(h, str) and len(h.strip()) >= 5]
        if not clean_headlines and not self.headline_records and len((self.dom_excerpt or "").strip()) < 20:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": "EVIDENCE_MISSING_HEADLINES_OR_DOM: BrowserEvidence requires non-empty headlines or DOM records.",
            }

        # R2.5 & R2.6: Check headlines and dom_excerpt for metadata/llms.txt/policy contamination
        dom_contam = self.is_contaminated_or_metadata_text(self.dom_excerpt or "")
        if dom_contam:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": dom_contam,
            }
        for h_str in clean_headlines:
            h_contam = self.is_contaminated_or_metadata_text(h_str)
            if h_contam:
                return {
                    "valid": False,
                    "status": "BLOCKED",
                    "reason": h_contam,
                }

        if require_headline_records and not self.headline_records:
            return {
                "valid": False,
                "status": "BLOCKED",
                "reason": "EVIDENCE_MISSING_STRUCTURED_HEADLINE_RECORDS: headline_records with (title, article_url, source_url, evidence_ref) are required.",
            }

        for rec in (self.headline_records or []):
            if not rec.evidence_ref or not rec.title or len(rec.title.strip()) < 5 or not rec.article_url or not rec.source_url:
                return {
                    "valid": False,
                    "status": "BLOCKED",
                    "reason": f"EVIDENCE_INVALID_HEADLINE_RECORD: incomplete fields in {rec}",
                }
            rec_contam = self.is_contaminated_or_metadata_text(rec.title, rec.article_url)
            if rec_contam:
                return {
                    "valid": False,
                    "status": "BLOCKED",
                    "reason": rec_contam,
                }
            art_parsed = urlparse(rec.article_url)
            if art_parsed.scheme.lower() not in ("http", "https") or self._is_ssrf_or_internal_host(art_parsed.hostname or ""):
                return {
                    "valid": False,
                    "status": "BLOCKED",
                    "reason": f"EVIDENCE_HEADLINE_ARTICLE_SSRF_OR_INVALID_URL: '{rec.article_url}'",
                }
            art_dom = self._registrable_domain(art_parsed.hostname or "")
            if art_dom != fin_dom and art_dom != src_dom:
                return {
                    "valid": False,
                    "status": "BLOCKED",
                    "reason": (
                        f"EVIDENCE_HEADLINE_ARTICLE_DOMAIN_MISMATCH: article domain '{art_dom}' "
                        f"does not match source domain '{src_dom}'"
                    ),
                }

        return {
            "valid": True,
            "status": "VERIFIED",
            "reason": "BrowserEvidence verified.",
            "evidence_id": self.evidence_id,
            "screenshot_sha256": self.screenshot_sha256,
            "headline_records_count": len(self.headline_records or []),
        }

    @classmethod
    def validate_summary_grounding(cls, summary_text: str, evidence_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase R2.5, R2.6 & R4.1: Validates that the synthesized summary:
        1. Contains no leaked system policy instructions or untrusted wrapper tags.
        2. Cites at least one valid evidence_ref (e.g. [hl_01]) when headline_records are present.
        3. All cited evidence_refs MUST be of type 'ARTICLE' (rejecting 'CATEGORY'/'NAV' citations).
        """
        text = (summary_text or "").strip()
        if not text:
            return {"valid": False, "reason": "SUMMARY_EMPTY"}

        contam = cls.is_contaminated_or_metadata_text(text)
        if contam:
            return {"valid": False, "reason": f"SUMMARY_CONTAMINATED: {contam}"}

        records = (evidence_payload or {}).get("headline_records") or []
        if records:
            ref_type_map = {}
            for r in records:
                ref = str((r.get("evidence_ref") if isinstance(r, dict) else getattr(r, "evidence_ref", "")) or "").strip()
                raw_type = (r.get("record_type") if isinstance(r, dict) else getattr(r, "record_type", None))
                rtype = str(raw_type or "ARTICLE").strip()
                if ref:
                    ref_type_map[ref] = rtype

            valid_refs = list(ref_type_map.keys())
            cited_refs = [r for r in valid_refs if f"[{r}]" in text or f"hl_{r.split('_')[-1]}" in text or r in text]
            if not cited_refs:
                return {
                    "valid": False,
                    "reason": f"SUMMARY_MISSING_EVIDENCE_REF_CITATION: summary must cite at least one evidence_ref from {valid_refs[:5]}",
                }

            # Phase R4.1: Reject citations of CATEGORY/NAVIGATION records
            category_citations = [r for r in cited_refs if ref_type_map.get(r, "ARTICLE") in ("CATEGORY", "NAVIGATION")]
            if category_citations:
                return {
                    "valid": False,
                    "reason": (
                        f"SUMMARY_USES_NON_ARTICLE_RECORD: cited ref(s) {category_citations} "
                        f"have record_type='CATEGORY'/'NAVIGATION'; summary must only cite ARTICLE records."
                    ),
                }

            article_citations = [r for r in cited_refs if ref_type_map.get(r, "ARTICLE") == "ARTICLE"]
            if not article_citations:
                return {
                    "valid": False,
                    "reason": "SUMMARY_NO_ARTICLE_CITATIONS: none of the cited evidence_refs are of type ARTICLE.",
                }

            return {"valid": True, "cited_evidence_refs": article_citations}

        return {"valid": True, "cited_evidence_refs": []}


class ArtifactReceipt(BaseModel):
    """
    Phase R2.3: Immutable Cryptographic Trace Receipt for every produced artifact & summary.
    Binds (task_id, trace_id, artifact_path, artifact_sha256, evidence_id, evidence_sha256) with HMAC-SHA256.
    """
    model_config = ConfigDict(frozen=True)

    receipt_id: str = Field(default_factory=lambda: f"rcpt_{uuid.uuid4().hex[:12]}")
    task_id: str
    trace_id: str
    artifact_type: str = "FILE_ARTIFACT"
    artifact_path: str = ""
    artifact_sha256: str = ""
    size_bytes: int = 0
    evidence_id: str = ""
    evidence_sha256: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hmac_signature: str = ""

    @staticmethod
    def _compute_hmac(
        task_id: str,
        trace_id: str,
        artifact_type: str,
        artifact_path: str,
        artifact_sha256: str,
        size_bytes: int,
        evidence_id: str,
        evidence_sha256: str,
    ) -> str:
        import hmac as _hmac
        secret = (os.getenv("JKAI_RECEIPT_HMAC_KEY") or "jkai_zenith_sovereign_receipt_key_v1").encode("utf-8")
        payload = f"{task_id}|{trace_id}|{artifact_type}|{artifact_path}|{artifact_sha256}|{size_bytes}|{evidence_id}|{evidence_sha256}".encode("utf-8")
        return _hmac.new(secret, payload, hashlib.sha256).hexdigest()

    @classmethod
    def issue(
        cls,
        task_id: str,
        trace_id: str,
        artifact_type: str = "FILE_ARTIFACT",
        artifact_path: str = "",
        artifact_sha256: str = "",
        size_bytes: int = 0,
        evidence_id: str = "",
        evidence_sha256: str = "",
    ) -> "ArtifactReceipt":
        if not task_id or str(task_id).strip() in ("", "None", "null"):
            raise ValueError("TASK_ID_REQUIRED_FOR_RECEIPT")
        if not trace_id or str(trace_id).strip() in ("", "None", "null"):
            raise ValueError("TRACE_ID_REQUIRED_FOR_RECEIPT")
        if artifact_path and os.path.isfile(artifact_path) and not artifact_sha256:
            with open(artifact_path, "rb") as f:
                data = f.read()
            artifact_sha256 = hashlib.sha256(data).hexdigest()
            size_bytes = len(data)
        sig = cls._compute_hmac(
            task_id=str(task_id).strip(),
            trace_id=str(trace_id).strip(),
            artifact_type=artifact_type,
            artifact_path=str(artifact_path),
            artifact_sha256=str(artifact_sha256),
            size_bytes=int(size_bytes),
            evidence_id=str(evidence_id),
            evidence_sha256=str(evidence_sha256),
        )
        return cls(
            task_id=str(task_id).strip(),
            trace_id=str(trace_id).strip(),
            artifact_type=artifact_type,
            artifact_path=str(artifact_path),
            artifact_sha256=str(artifact_sha256),
            size_bytes=int(size_bytes),
            evidence_id=str(evidence_id),
            evidence_sha256=str(evidence_sha256),
            hmac_signature=sig,
        )

    def verify(self, expected_task_id: Optional[str] = None, expected_trace_id: Optional[str] = None) -> bool:
        import hmac as _hmac
        if expected_task_id and self.task_id != str(expected_task_id).strip():
            return False
        if expected_trace_id and self.trace_id != str(expected_trace_id).strip():
            return False
        if not self.artifact_sha256 or len(self.artifact_sha256) != 64:
            return False
        expected_sig = self._compute_hmac(
            task_id=self.task_id,
            trace_id=self.trace_id,
            artifact_type=self.artifact_type,
            artifact_path=self.artifact_path,
            artifact_sha256=self.artifact_sha256,
            size_bytes=self.size_bytes,
            evidence_id=self.evidence_id,
            evidence_sha256=self.evidence_sha256,
        )
        return _hmac.compare_digest(self.hmac_signature, expected_sig)


class MissionMetadata(BaseModel):
    """Immutable Mission metadata set at initialization."""
    mission_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_goal: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    initial_constraints: List[str] = Field(default_factory=list)
    model_profile: str = "default"

class FactItem(BaseModel):
    content: str
    dependencies: List[str] = Field(default_factory=list) # IDs of other facts it relies on
    confidence: float = 1.0
    valid: bool = True
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MissionFacts(BaseModel):
    """Mutable fact storage supporting Truth Maintenance System."""
    facts_db: Dict[str, FactItem] = Field(default_factory=dict)

class MissionPlanner(BaseModel):
    """State tracking for planning steps."""
    current_plan: List[str] = Field(default_factory=list)
    completed_steps: List[str] = Field(default_factory=list)
    blocked_by: Optional[str] = None
    step_confidence: Dict[str, float] = Field(default_factory=dict)

class MissionBudget(BaseModel):
    """Budget and usage constraints to prevent infinite loops."""
    max_cost_usd: float = 5.0
    current_cost_usd: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    api_calls_count: int = 0
    search_calls_count: int = 0
    tool_calls_count: int = 0

class ScopedMemory(BaseModel):
    """Memory subdivided into scopes."""
    global_memory: Dict[str, Any] = Field(default_factory=dict)
    mission_memory: Dict[str, Any] = Field(default_factory=dict)
    agent_memory: Dict[str, Dict[str, Any]] = Field(default_factory=dict) # agent_name -> memory dict
    tool_memory: Dict[str, Any] = Field(default_factory=dict)

class CitationItem(BaseModel):
    source_path: str
    line_range: Optional[str] = None
    checksum: Optional[str] = None
    confidence: float = 1.0

class MissionReferences(BaseModel):
    """Source-of-truth grounding references and dependency graph."""
    citations: Dict[str, CitationItem] = Field(default_factory=dict) # ref_id -> citation
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict) # file -> list of downstream files impacted

class MissionState(BaseModel):
    """The complete Zeniths Unified Mission State (Composite)."""
    metadata: MissionMetadata
    facts: MissionFacts
    planner: MissionPlanner
    budget: MissionBudget
    memory: ScopedMemory
    references: MissionReferences
    lifecycle: str = "READY" # READY, RUNNING, WAITING, BLOCKED, SUCCESS, FAILED
    active_entity_stack: List[Dict[str, Any]] = Field(default_factory=list)

class MissionEvent(BaseModel):
    """Event schema for Event Sourcing."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str
    payload: Dict[str, Any]

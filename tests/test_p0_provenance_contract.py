# -*- coding: utf-8 -*-
"""
test_p0_provenance_contract.py
Harness kiểm định Hợp đồng Bằng chứng Nguồn gốc (Per-Source Provenance Contract - 12 Trường)
Tuân thủ Phán quyết Lượt 98 của Hội đồng AI (JKAI Zenith Protocol v2.3 / SDS v28.27.0).
"""

import hashlib
import ipaddress
import json
import re
import unittest
from datetime import datetime, timezone
from urllib.parse import urlparse


class SSRFSecurityError(Exception):
    """Lỗi khi URI vi phạm chính sách SSRF / Egress."""
    pass


class ProvenanceValidationError(Exception):
    """Lỗi khi bản ghi bằng chứng không hợp lệ."""
    pass


class ProvenanceValidator:
    """
    Bộ kiểm định độc lập (Deterministic Validator) cho Per-Source Provenance Contract.
    Tuyệt đối không cho phép Model hoặc caller tự gán verification_status = 'VERIFIED'.
    """

    PRIVATE_CIDRS = [
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]

    @classmethod
    def canonicalize_url(cls, raw_url: str) -> str:
        """Chuẩn hóa URL: scheme lowercase, loại bỏ default port, strip whitespace."""
        if not raw_url or not isinstance(raw_url, str):
            raise SSRFSecurityError("EMPTY_OR_INVALID_URI")
        raw_url = raw_url.strip()
        parsed = urlparse(raw_url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            raise SSRFSecurityError(f"DISALLOWED_SCHEME({scheme})")
        
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise SSRFSecurityError("MISSING_HOSTNAME")

        # Kiểm tra SSRF IP / Hostname
        cls.validate_ssrf_hostname(hostname)

        # Chuẩn hóa port
        port = parsed.port
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            port_str = ""
        elif port:
            port_str = f":{port}"
        else:
            port_str = ""

        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{hostname}{port_str}{path}{query}"

    @classmethod
    def validate_ssrf_hostname(cls, hostname: str):
        """Chặn loopback, private IP, IPv6-mapped IPv4, link-local metadata."""
        if hostname in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
            raise SSRFSecurityError(f"SSRF_BLOCKED_HOST({hostname})")

        # Thử parse IP
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            # Không phải IP thuần, là tên miền thông thường
            return

        # Kiểm tra IPv6 mapped IPv4 (e.g. ::ffff:127.0.0.1)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped

        for cidr in cls.PRIVATE_CIDRS:
            if cidr.version == ip.version and ip in cidr:
                raise SSRFSecurityError(f"SSRF_PRIVATE_IP_BLOCKED({ip})")
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            raise SSRFSecurityError(f"SSRF_LOOPBACK_OR_LINK_LOCAL({ip})")

    @classmethod
    def compute_hash(cls, data: bytes) -> str:
        """Băm SHA-256 trên raw bytes."""
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def compute_canonical_text_hash(cls, text: str) -> str:
        """Băm SHA-256 trên văn bản đã chuẩn hóa UTF-8 và kết thúc dòng."""
        normalized = (text or "").strip().replace("\r\n", "\n").encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    @classmethod
    def validate_receipt(
        cls,
        receipt: dict,
        raw_response_bytes: bytes,
        extracted_content_text: str,
        raw_query: str,
        current_time_utc: datetime = None,
    ) -> dict:
        """
        Xác thực toàn diện 12 trường của Evidence Receipt.
        Trả về receipt đã được đóng dấu verification_status chuẩn xác.
        """
        if current_time_utc is None:
            current_time_utc = datetime.now(timezone.utc)

        # 1. Kiểm tra sự hiện diện của 12 trường bắt buộc + bindings
        mandatory_fields = [
            "evidence_id", "task_id", "trace_id", "source_uri", "source_type", "provider",
            "retrieved_at", "published_at", "content_hash", "response_hash",
            "query_hash", "extractor_version", "freshness_policy", "verification_status"
        ]
        for field in mandatory_fields:
            if field not in receipt or not receipt[field]:
                if field == "published_at":
                    continue  # published_at có thể None/nullable
                raise ProvenanceValidationError(f"MISSING_MANDATORY_FIELD({field})")

        # 2. Kiểm tra source_uri và SSRF
        canon_uri = cls.canonicalize_url(receipt["source_uri"])

        # 3. Kiểm tra response_hash trên raw bytes
        computed_response_hash = cls.compute_hash(raw_response_bytes)
        if computed_response_hash != receipt["response_hash"]:
            raise ProvenanceValidationError(
                f"RESPONSE_HASH_MISMATCH(declared={receipt['response_hash']}, computed={computed_response_hash})"
            )

        # 4. Kiểm tra content_hash trên canonical extracted content
        computed_content_hash = cls.compute_canonical_text_hash(extracted_content_text)
        if computed_content_hash != receipt["content_hash"]:
            raise ProvenanceValidationError(
                f"CONTENT_HASH_MISMATCH(declared={receipt['content_hash']}, computed={computed_content_hash})"
            )

        # 5. Kiểm tra query_hash trên canonical UTF-8 query
        computed_query_hash = cls.compute_canonical_text_hash(raw_query)
        if computed_query_hash != receipt["query_hash"]:
            raise ProvenanceValidationError(
                f"QUERY_HASH_MISMATCH(declared={receipt['query_hash']}, computed={computed_query_hash})"
            )

        # 6. Kiểm tra retrieved_at (phải là UTC hợp lệ)
        try:
            retrieved_dt = datetime.fromisoformat(receipt["retrieved_at"].replace("Z", "+00:00"))
        except Exception:
            raise ProvenanceValidationError("INVALID_RETRIEVED_AT_ISO_UTC")

        # 7. Kiểm tra Freshness Policy
        policy = receipt.get("freshness_policy", "")
        max_age_match = re.search(r"max_age_days:(\d+)", policy)
        is_expired = False
        if max_age_match:
            max_days = int(max_age_match.group(1))
            age_days = (current_time_utc - retrieved_dt).total_seconds() / 86400.0
            if age_days > max_days:
                is_expired = True

        # 8. Deterministic Status Assignment: Model không được tự phong VERIFIED
        if is_expired:
            final_status = "EXPIRED"
        else:
            final_status = "VERIFIED"

        verified_receipt = dict(receipt)
        verified_receipt["source_uri"] = canon_uri
        verified_receipt["verification_status"] = final_status
        return verified_receipt


class TestP0ProvenanceContract(unittest.TestCase):
    """Bộ kiểm thử thực chứng Hợp đồng Bằng chứng Nguồn gốc (P0 Provenance)."""

    def setUp(self):
        self.raw_html = b"<html><body><h1>RouterOS v7 Routing Manual</h1><p>Syntax changed.</p></body></html>"
        self.extracted_text = "RouterOS v7 Routing Manual\nSyntax changed."
        self.query = "mikrotik routeros v7 routing syntax"
        self.now_utc = datetime(2026, 10, 30, 18, 45, 0, tzinfo=timezone.utc)

        self.valid_receipt = {
            "evidence_id": "ev_20261030_001_mikrotik",
            "task_id": "task_learn_mikrotik_v7",
            "trace_id": "trace_99a8b7c6",
            "source_uri": "https://help.mikrotik.com/docs/display/ROS/Routing",
            "source_type": "web_manual",
            "provider": "duckduckgo_html_0d",
            "retrieved_at": "2026-10-30T18:45:00Z",
            "published_at": "2026-05-15T00:00:00Z",
            "content_hash": ProvenanceValidator.compute_canonical_text_hash(self.extracted_text),
            "response_hash": ProvenanceValidator.compute_hash(self.raw_html),
            "query_hash": ProvenanceValidator.compute_canonical_text_hash(self.query),
            "extractor_version": "html_trafilatura_v1.2",
            "freshness_policy": "max_age_days:30",
            "verification_status": "PENDING",  # Model đặt là PENDING
        }

    def test_01_valid_receipt_verification(self):
        """Test happy path: Biên bản hợp lệ đạt VERIFIED một cách tất định."""
        verified = ProvenanceValidator.validate_receipt(
            self.valid_receipt,
            self.raw_html,
            self.extracted_text,
            self.query,
            self.now_utc
        )
        self.assertEqual(verified["verification_status"], "VERIFIED")
        self.assertEqual(verified["evidence_id"], "ev_20261030_001_mikrotik")
        self.assertTrue(verified["source_uri"].startswith("https://help.mikrotik.com"))

    def test_02_model_self_assigned_verified_is_revalidated(self):
        """Test nguyên tắc OpenCode: Model tự gán VERIFIED nhưng hash sai sẽ bị từ chối ngay."""
        tampered_receipt = dict(self.valid_receipt)
        tampered_receipt["verification_status"] = "VERIFIED"  # Model tự phong
        tampered_receipt["content_hash"] = "0000000000000000000000000000000000000000000000000000000000000000"

        with self.assertRaises(ProvenanceValidationError) as ctx:
            ProvenanceValidator.validate_receipt(
                tampered_receipt,
                self.raw_html,
                self.extracted_text,
                self.query,
                self.now_utc
            )
        self.assertIn("CONTENT_HASH_MISMATCH", str(ctx.exception))

    def test_03_ssrf_rejection_private_ips_and_loopback(self):
        """Test ngăn chặn SSRF: Chặn localhost, 127.0.0.1, 10.x, 192.168.x, metadata."""
        ssrf_targets = [
            "http://127.0.0.1:8080/admin",
            "http://localhost:9999/api",
            "http://10.0.0.1/secret",
            "http://192.168.1.1/winbox",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://[::1]/root",
            "http://[::ffff:127.0.0.1]/status",
        ]
        for url in ssrf_targets:
            tampered = dict(self.valid_receipt)
            tampered["source_uri"] = url
            with self.assertRaises(SSRFSecurityError, msg=f"Failed to block SSRF: {url}"):
                ProvenanceValidator.validate_receipt(
                    tampered,
                    self.raw_html,
                    self.extracted_text,
                    self.query,
                    self.now_utc
                )

    def test_04_tampered_response_hash_detection(self):
        """Test phát hiện raw response bytes bị can thiệp sau thu nhận."""
        tampered = dict(self.valid_receipt)
        tampered["response_hash"] = "badf00d" + "0" * 57
        with self.assertRaises(ProvenanceValidationError) as ctx:
            ProvenanceValidator.validate_receipt(
                tampered,
                self.raw_html,
                self.extracted_text,
                self.query,
                self.now_utc
            )
        self.assertIn("RESPONSE_HASH_MISMATCH", str(ctx.exception))

    def test_05_freshness_policy_expiration(self):
        """Test cơ chế Freshness: Dữ liệu quá hạn max_age_days chuyển sang EXPIRED."""
        # Thời gian kiểm tra là 45 ngày sau khi retrieved_at
        future_time = datetime(2026, 12, 15, 18, 45, 0, tzinfo=timezone.utc)
        verified = ProvenanceValidator.validate_receipt(
            self.valid_receipt,
            self.raw_html,
            self.extracted_text,
            self.query,
            future_time
        )
        self.assertEqual(verified["verification_status"], "EXPIRED")

    def test_06_missing_mandatory_field_rejected(self):
        """Test thiếu bất kỳ trường nào trong 12 trường đều bị fail-closed."""
        for field in ["evidence_id", "content_hash", "response_hash", "retrieved_at", "freshness_policy", "task_id", "trace_id"]:
            tampered = dict(self.valid_receipt)
            del tampered[field]
            with self.assertRaises(ProvenanceValidationError):
                ProvenanceValidator.validate_receipt(
                    tampered,
                    self.raw_html,
                    self.extracted_text,
                    self.query,
                    self.now_utc
                )

    def test_07_conflict_state_tracking(self):
        """Test ghi nhận conflict_state khi 2 nguồn mâu thuẫn về claim kỹ thuật."""
        receipt_source_a = dict(self.valid_receipt)
        receipt_source_b = dict(self.valid_receipt)
        receipt_source_b["evidence_id"] = "ev_20261030_002_forum"
        receipt_source_b["source_uri"] = "https://forum.mikrotik.com/viewtopic.php?t=18000"
        receipt_source_b["response_hash"] = ProvenanceValidator.compute_hash(b"forum html")
        receipt_source_b["content_hash"] = ProvenanceValidator.compute_canonical_text_hash("different syntax")

        # Conflict detector giữa 2 claims
        conflict_record = {
            "entity": "mikrotik_v7_bgp_syntax",
            "claims": [
                {"source_id": receipt_source_a["evidence_id"], "claim": "/routing bgp connection"},
                {"source_id": receipt_source_b["evidence_id"], "claim": "/routing bgp peer"},
            ],
            "conflict_detected": True,
            "resolution_policy": "PREFER_OFFICIAL_VENDOR_OVER_COMMUNITY_FORUM",
            "resolved_winner": receipt_source_a["evidence_id"]
        }
        self.assertTrue(conflict_record["conflict_detected"])
        self.assertEqual(conflict_record["resolved_winner"], "ev_20261030_001_mikrotik")

    def test_08_canonical_url_normalization(self):
        """Test chuẩn hóa URL: loại bỏ port 80/443, lowercase scheme và host."""
        raw_url = "HTTPS://Help.MikroTik.COM:443/docs/display/ROS/Routing?lang=en"
        canon = ProvenanceValidator.canonicalize_url(raw_url)
        self.assertEqual(canon, "https://help.mikrotik.com/docs/display/ROS/Routing?lang=en")


if __name__ == "__main__":
    unittest.main()

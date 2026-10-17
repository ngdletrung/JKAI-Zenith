# -*- coding: utf-8 -*-
"""
core/security/ssrf_resolve_pin_guard.py
=======================================
Phase A7.1: SSRF Resolve-and-Pin & Per-Hop Redirect Revalidation Guard.
- Blocks embedded userinfo (`user:pass@host`), non-HTTP(S) schemes, loopback, RFC1918 private,
  link-local / cloud metadata (`169.254.0.0/16`, `fe80::/10`), CGNAT (`100.64.0.0/10`),
  multicast, reserved, unspecified, and IPv4-mapped IPv6 addresses (`::ffff:127.0.0.1`, `::ffff:169.254.169.254`).
- Resolves DNS once via `socket.getaddrinfo` (or injectable `resolver_fn`), validates ALL resolved IPs,
  and pins the validated IP in audit metadata.
- Provides a single unified HTTP fetch pipeline (`fetch_with_revalidation`) with `follow_redirects=False`
  that re-validates every redirect hop (`301, 302, 303, 307, 308`) through the exact same guard.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse

CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


def is_ip_forbidden(ip_str: str) -> Tuple[bool, str]:
    """
    Checks whether a literal IPv4 or IPv6 address (including IPv4-mapped IPv6 `::ffff:x.x.x.x`)
    belongs to any forbidden internal, loopback, link-local, metadata, or CGNAT range.
    """
    clean_ip = str(ip_str or "").strip().strip("[]")
    if "%" in clean_ip:
        clean_ip = clean_ip.split("%", 1)[0]
    try:
        ip_obj = ipaddress.ip_address(clean_ip)
    except ValueError:
        return True, f"INVALID_IP_LITERAL:{clean_ip}"

    # Unwrap IPv4-mapped IPv6 (e.g., ::ffff:127.0.0.1 or ::ffff:169.254.169.254)
    candidates = [ip_obj]
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped is not None:
        candidates.append(ip_obj.ipv4_mapped)

    for cand in candidates:
        if cand.is_loopback:
            return True, f"LOOPBACK_IP:{cand}"
        if cand.is_private:
            return True, f"PRIVATE_IP:{cand}"
        if cand.is_link_local:
            return True, f"LINK_LOCAL_OR_METADATA_IP:{cand}"
        if cand.is_multicast:
            return True, f"MULTICAST_IP:{cand}"
        if cand.is_reserved:
            return True, f"RESERVED_IP:{cand}"
        if cand.is_unspecified:
            return True, f"UNSPECIFIED_IP:{cand}"
        if isinstance(cand, ipaddress.IPv4Address) and cand in CGNAT_NETWORK:
            return True, f"CGNAT_SHARED_IP:{cand}"

    return False, ""


class SSRFResolveAndPinGuard:
    """
    Provably strict SSRF guard implementing Resolve-and-Pin and Per-Hop Redirect Revalidation.
    """

    @staticmethod
    def default_dns_resolver(host: str, port: int) -> List[str]:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        ips: List[str] = []
        for item in infos:
            sockaddr = item[4]
            if sockaddr and len(sockaddr) >= 1:
                ip_val = str(sockaddr[0])
                if ip_val not in ips:
                    ips.append(ip_val)
        return ips

    @classmethod
    def validate_and_resolve(
        cls,
        url: str,
        allowed_domains: Optional[Sequence[str]] = None,
        resolve_dns: bool = True,
        resolver_fn: Optional[Callable[[str, int], Sequence[str]]] = None,
    ) -> Dict[str, Any]:
        raw_url = str(url or "").strip()
        parsed = urlparse(raw_url)
        scheme = (parsed.scheme or "").lower()
        host = (parsed.hostname or "").strip().lower()

        if scheme not in ("http", "https") or not host:
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "SSRF_INVALID_SCHEME_OR_HOST",
                "url": raw_url,
                "host": host,
                "pinned_ip": None,
                "resolved_ips": [],
                "msg": f"[EGRESS-REFUSED] Giao thức hoặc địa chỉ không hợp lệ: '{raw_url}'.",
            }

        # Block embedded userinfo (https://user:pass@host)
        if parsed.username is not None or parsed.password is not None or "@" in (parsed.netloc or ""):
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "SSRF_EMBEDDED_USERINFO_FORBIDDEN",
                "url": raw_url,
                "host": host,
                "pinned_ip": None,
                "resolved_ips": [],
                "msg": f"[SSRF-BLOCKED] Từ chối URL chứa thông tin xác thực nhúng (userinfo): '{raw_url}'.",
            }

        if (
            host in ("localhost", "0.0.0.0", "::1", "[::1]")
            or host.endswith(".internal")
            or host.endswith(".local")
            or host.endswith(".localhost")
        ):
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "SSRF_BLOCKED_PRIVATE_OR_LOOPBACK",
                "url": raw_url,
                "host": host,
                "pinned_ip": None,
                "resolved_ips": [],
                "msg": f"[SSRF-BLOCKED] Từ chối kết nối tới máy chủ nội bộ/loopback: '{host}'.",
            }

        # Check literal IP (including IPv4-mapped IPv6 ::ffff:127.0.0.1)
        clean_host = host.strip("[]")
        is_literal_ip = False
        try:
            ipaddress.ip_address(clean_host)
            is_literal_ip = True
        except ValueError:
            is_literal_ip = False

        if is_literal_ip:
            forbidden, reason = is_ip_forbidden(clean_host)
            if forbidden:
                return {
                    "status": "refused",
                    "allowed": False,
                    "error_code": "SSRF_BLOCKED_PRIVATE_OR_LOOPBACK",
                    "url": raw_url,
                    "host": host,
                    "pinned_ip": None,
                    "resolved_ips": [clean_host],
                    "msg": f"[SSRF-BLOCKED] Từ chối kết nối tới địa chỉ IP nội bộ/metadata ({reason}): '{host}'.",
                }

        # Check domain allowlist if configured
        env_wl = os.getenv("JKAI_WEB_EGRESS_ALLOWLIST", "").strip()
        effective_wl: List[str] = []
        if allowed_domains is not None:
            effective_wl = [str(d).strip().lower() for d in allowed_domains if str(d).strip()]
        elif env_wl:
            effective_wl = [d.strip().lower() for d in env_wl.split(",") if d.strip()]

        if effective_wl:
            matched = any(host == dom or host.endswith(f".{dom}") for dom in effective_wl)
            if not matched:
                return {
                    "status": "refused",
                    "allowed": False,
                    "error_code": "EGRESS_DOMAIN_NOT_IN_ALLOWLIST",
                    "url": raw_url,
                    "host": host,
                    "allowed_domains": effective_wl,
                    "pinned_ip": None,
                    "resolved_ips": [],
                    "msg": (
                        f"[EGRESS-REFUSED] Tên miền '{host}' không nằm trong danh sách trắng cho phép "
                        f"(allowed_domains={effective_wl})."
                    ),
                }

        # Resolve DNS and validate ALL returned IPs (defeats DNS rebinding)
        resolved_ips: List[str] = [clean_host] if is_literal_ip else []
        if not is_literal_ip and (resolve_dns or resolver_fn is not None):
            port = parsed.port or (443 if scheme == "https" else 80)
            active_resolver = resolver_fn or cls.default_dns_resolver
            try:
                resolved_ips = list(active_resolver(host, port))
            except Exception as exc:
                return {
                    "status": "refused",
                    "allowed": False,
                    "error_code": "SSRF_DNS_RESOLUTION_FAILED",
                    "url": raw_url,
                    "host": host,
                    "pinned_ip": None,
                    "resolved_ips": [],
                    "msg": f"[SSRF-BLOCKED] Không thể phân giải DNS an toàn cho '{host}': {exc}",
                }

            if not resolved_ips:
                return {
                    "status": "refused",
                    "allowed": False,
                    "error_code": "SSRF_DNS_EMPTY_RESPONSE",
                    "url": raw_url,
                    "host": host,
                    "pinned_ip": None,
                    "resolved_ips": [],
                    "msg": f"[SSRF-BLOCKED] Phân giải DNS trả về rỗng cho '{host}'.",
                }

            for rip in resolved_ips:
                forbidden, reason = is_ip_forbidden(rip)
                if forbidden:
                    return {
                        "status": "refused",
                        "allowed": False,
                        "error_code": "SSRF_DNS_RESOLVED_INTERNAL_IP",
                        "url": raw_url,
                        "host": host,
                        "pinned_ip": None,
                        "resolved_ips": resolved_ips,
                        "msg": (
                            f"[SSRF-BLOCKED] Phát hiện DNS Rebinding / IP nội bộ '{rip}' ({reason}) "
                            f"khi phân giải tên miền '{host}'."
                        ),
                    }

        pinned_ip = resolved_ips[0] if resolved_ips else None
        return {
            "status": "allowed",
            "allowed": True,
            "error_code": None,
            "url": raw_url,
            "host": host,
            "pinned_ip": pinned_ip,
            "resolved_ips": resolved_ips,
        }

    @classmethod
    def fetch_with_revalidation(
        cls,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
        max_redirects: int = 3,
        max_bytes: int = 500_000,
        allowed_domains: Optional[Sequence[str]] = None,
        resolve_dns: bool = True,
        resolver_fn: Optional[Callable[[str, int], Sequence[str]]] = None,
        http_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Single unified outbound HTTP fetch pipeline for JKAI:
        - Explicitly disables automatic redirect following (`follow_redirects=False`).
        - Validates initial URL and EVERY redirect hop through `validate_and_resolve`.
        - Records `redirect_chain` and `pinned_ips` for deterministic auditability.
        """
        import httpx

        current_url = str(url or "").strip()
        current_method = str(method or "GET").upper()
        current_data = data
        redirect_chain: List[str] = [current_url]
        pinned_ips: List[str] = []

        def _do_single_request(client_obj: Any, target_url: str, req_method: str, req_data: Any) -> Any:
            if req_method == "POST":
                return client_obj.post(target_url, headers=headers, data=req_data)
            return client_obj.get(target_url, headers=headers)

        owns_client = http_client is None
        client = http_client or httpx.Client(timeout=timeout, follow_redirects=False)
        try:
            for hop in range(max_redirects + 1):
                verdict = cls.validate_and_resolve(
                    current_url,
                    allowed_domains=allowed_domains,
                    resolve_dns=resolve_dns,
                    resolver_fn=resolver_fn,
                )
                if not verdict.get("allowed", False):
                    err_code = verdict.get("error_code") or "SSRF_BLOCKED"
                    if hop > 0:
                        err_code = "SSRF_REDIRECT_HOP_BLOCKED"
                    return {
                        "status": "blocked",
                        "ok": False,
                        "error_code": err_code,
                        "url": current_url,
                        "hop": hop,
                        "redirect_chain": redirect_chain,
                        "pinned_ips": pinned_ips,
                        "status_code": None,
                        "text": "",
                        "error": verdict.get("msg", "SSRF blocked"),
                    }

                if verdict.get("pinned_ip"):
                    pinned_ips.append(str(verdict["pinned_ip"]))

                resp = _do_single_request(client, current_url, current_method, current_data)
                status_code = int(getattr(resp, "status_code", 0))

                if status_code in REDIRECT_STATUS_CODES:
                    if hop >= max_redirects:
                        return {
                            "status": "error",
                            "ok": False,
                            "error_code": "MAX_REDIRECTS_EXCEEDED",
                            "url": current_url,
                            "hop": hop,
                            "redirect_chain": redirect_chain,
                            "pinned_ips": pinned_ips,
                            "status_code": status_code,
                            "text": "",
                            "error": f"Exceeded max_redirects={max_redirects}",
                        }
                    resp_headers = getattr(resp, "headers", {}) or {}
                    loc = resp_headers.get("location") or resp_headers.get("Location") or ""
                    if not loc:
                        return {
                            "status": "error",
                            "ok": False,
                            "error_code": "REDIRECT_MISSING_LOCATION",
                            "url": current_url,
                            "hop": hop,
                            "redirect_chain": redirect_chain,
                            "pinned_ips": pinned_ips,
                            "status_code": status_code,
                            "text": "",
                            "error": f"Redirect HTTP {status_code} missing Location header",
                        }
                    next_url = urljoin(current_url, str(loc).strip())
                    redirect_chain.append(next_url)
                    current_url = next_url
                    if status_code in (301, 302, 303):
                        current_method = "GET"
                        current_data = None
                    continue

                raw_text = str(getattr(resp, "text", "") or "")
                capped_text = raw_text[:max_bytes]
                return {
                    "status": "success" if status_code == 200 and capped_text else "error",
                    "ok": status_code == 200 and bool(capped_text),
                    "error_code": None if (status_code == 200 and capped_text) else f"http_{status_code}",
                    "url": current_url,
                    "hop": hop,
                    "redirect_chain": redirect_chain,
                    "pinned_ips": pinned_ips,
                    "status_code": status_code,
                    "text": capped_text,
                    "error": None if (status_code == 200 and capped_text) else f"http_{status_code}",
                }
        except Exception as exc:
            return {
                "status": "error",
                "ok": False,
                "error_code": "FETCH_EXCEPTION",
                "url": current_url,
                "hop": len(redirect_chain) - 1,
                "redirect_chain": redirect_chain,
                "pinned_ips": pinned_ips,
                "status_code": None,
                "text": "",
                "error": str(exc)[:200],
            }
        finally:
            if owns_client and hasattr(client, "close"):
                client.close()

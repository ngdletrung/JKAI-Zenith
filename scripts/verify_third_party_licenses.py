# -*- coding: utf-8 -*-
"""
scripts/verify_third_party_licenses.py
[LICENSE GOVERNANCE GATE - FAIL CLOSED]

Validates `config/security/third_party_manifest.json` against the repository:

  1. Every entry declares an SPDX license that the policy knows about, and an
     approved entry never carries a forbidden (copyleft/network/non-commercial)
     license.
  2. Approved entries have no remote egress, declare where they are used, and
     (when redistributed) point at an existing full license text in LICENSES/.
  3. Approved entries that must be attributed are present in NOTICE.md; the
     entries flagged `credits_required` are also present in CREDITS.md.
  4. Deferred/rejected entries carry a written reason, and a rejected Python
     package may not appear in requirements.txt.
  5. Required runtime packages that are declared must exist in requirements.txt;
     host-only packages must say why they are not declared there.

Run:
    python scripts/verify_third_party_licenses.py
    python scripts/verify_third_party_licenses.py --json
Exit codes: 0 = PASS, 1 = violations, 2 = manifest unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "config" / "security" / "third_party_manifest.json"
SCHEMA = "jkai.third_party_manifest.v1"
STATUSES = {"approved", "deferred", "rejected"}
DEPENDENCY_KINDS = {
    "python-package",
    "system-binary",
    "data",
    "reference",
    "vendored",
}
EGRESS_VALUES = {"none", "localhost", "remote"}
REQUIRED_ENTRY_KEYS = (
    "id",
    "display_name",
    "upstream_url",
    "version_pin",
    "license",
    "redistributed",
    "dependency_kind",
    "required",
    "egress",
    "modifications",
    "used_in",
    "status",
)
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")


def _violation(code: str, detail: str, entry: str = "") -> Dict[str, str]:
    payload = {"code": code, "detail": detail}
    if entry:
        payload["entry"] = entry
    return payload


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _mentions(text: str, needle: str) -> bool:
    return bool(needle) and needle.casefold() in text.casefold()


def _requirements_has(requirements: str, package: str) -> bool:
    if not package:
        return False
    pattern = re.compile(rf"(?im)^\s*{re.escape(package)}\s*(?:[<>=!~\[;]|$)")
    return bool(pattern.search(requirements))


def validate_manifest(manifest: Dict[str, Any], root: Path) -> List[Dict[str, str]]:
    """Return every governance violation; empty list means PASS."""
    violations: List[Dict[str, str]] = []

    if not isinstance(manifest, dict):
        return [_violation("MANIFEST_NOT_OBJECT", "manifest must be a JSON object")]
    if manifest.get("schema") != SCHEMA:
        violations.append(_violation("SCHEMA_INVALID", f"expected {SCHEMA!r}"))
    if not str(manifest.get("updated_at", "")).strip():
        violations.append(_violation("UPDATED_AT_MISSING", "updated_at is required"))

    policy = manifest.get("policy")
    if not isinstance(policy, dict):
        return violations + [_violation("POLICY_MISSING", "policy object is required")]

    allowed = policy.get("allowed_licenses")
    forbidden = policy.get("forbidden_licenses")
    allowed_egress = policy.get("allowed_egress", [])
    if not isinstance(allowed, list) or not allowed:
        violations.append(_violation("ALLOWED_LICENSES_INVALID", "non-empty list required"))
        allowed = []
    if not isinstance(forbidden, list):
        violations.append(_violation("FORBIDDEN_LICENSES_INVALID", "list required"))
        forbidden = []
    if not isinstance(allowed_egress, list):
        violations.append(_violation("ALLOWED_EGRESS_INVALID", "list required"))
        allowed_egress = []

    overlap = {str(x) for x in allowed} & {str(x) for x in forbidden}
    if overlap:
        violations.append(
            _violation("LICENSE_POLICY_CONFLICT", f"licenses both allowed and forbidden: {sorted(overlap)}")
        )

    required_egress = [e for e in allowed_egress if e not in EGRESS_VALUES]
    if required_egress:
        violations.append(
            _violation("EGRESS_POLICY_INVALID", f"unknown egress values: {required_egress}")
        )

    notice_text = _read_text(root / "NOTICE.md")
    credits_text = _read_text(root / "CREDITS.md")
    requirements_text = _read_text(root / "requirements.txt")

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        return violations + [_violation("ENTRIES_INVALID", "non-empty entries list required")]

    seen_ids = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            violations.append(_violation("ENTRY_NOT_OBJECT", f"entries[{index}] must be an object"))
            continue
        entry_id = str(entry.get("id", "")).strip()
        label = entry_id or f"entries[{index}]"
        missing = [k for k in REQUIRED_ENTRY_KEYS if k not in entry]
        if missing:
            violations.append(_violation("ENTRY_FIELDS_MISSING", f"missing {missing}", label))
            continue
        if not _ID_RE.match(entry_id):
            violations.append(_violation("ENTRY_ID_INVALID", f"{entry_id!r} is not kebab-case", label))
        if entry_id in seen_ids:
            violations.append(_violation("ENTRY_ID_DUPLICATE", entry_id, label))
        seen_ids.add(entry_id)

        status = entry.get("status")
        license_id = str(entry.get("license", ""))
        kind = entry.get("dependency_kind")
        if status not in STATUSES:
            violations.append(_violation("ENTRY_STATUS_INVALID", str(status), label))
        if kind not in DEPENDENCY_KINDS:
            violations.append(_violation("ENTRY_KIND_INVALID", str(kind), label))
        if license_id not in allowed and license_id not in forbidden:
            violations.append(
                _violation(
                    "ENTRY_LICENSE_UNDECLARED",
                    f"{license_id!r} is neither in allowed_licenses nor forbidden_licenses",
                    label,
                )
            )

        text_file = entry.get("license_text_file")
        if text_file:
            if not (root / str(text_file)).is_file():
                violations.append(
                    _violation("LICENSE_TEXT_MISSING", str(text_file), label)
                )
        elif entry.get("redistributed"):
            violations.append(
                _violation("LICENSE_TEXT_REQUIRED", "redistributed code needs a license_text_file", label)
            )

        used_in = entry.get("used_in")
        if not isinstance(used_in, list):
            violations.append(_violation("ENTRY_USED_IN_INVALID", "used_in must be a list", label))
            used_in = []

        if status == "approved":
            if license_id in forbidden:
                violations.append(
                    _violation("FORBIDDEN_LICENSE_APPROVED", license_id, label)
                )
            if entry.get("egress") not in allowed_egress:
                violations.append(
                    _violation(
                        "EGRESS_NOT_ALLOWED",
                        f"{entry.get('egress')!r} not in {allowed_egress}",
                        label,
                    )
                )
            if not used_in:
                violations.append(_violation("ENTRY_USED_IN_EMPTY", "approved entries must list used_in", label))
            if entry.get("redistributed") and not text_file:
                violations.append(
                    _violation("LICENSE_TEXT_REQUIRED", "redistributed code needs a license_text_file", label)
                )
            if entry.get("notice_required", True) and not _mentions(notice_text, str(entry.get("display_name", ""))):
                violations.append(
                    _violation(
                        "NOTICE_ATTRIBUTION_MISSING",
                        f"{entry.get('display_name')!r} absent from NOTICE.md",
                        label,
                    )
                )
            if entry.get("credits_required") and not _mentions(credits_text, str(entry.get("display_name", ""))):
                violations.append(
                    _violation(
                        "CREDITS_ATTRIBUTION_MISSING",
                        f"{entry.get('display_name')!r} absent from CREDITS.md",
                        label,
                    )
                )
            if entry.get("required") and not entry.get("requirements_declared") and not str(entry.get("notes", "")).strip():
                violations.append(
                    _violation(
                        "HOST_ONLY_REASON_MISSING",
                        "required package not in requirements.txt must explain why in notes",
                        label,
                    )
                )
            if (
                kind == "python-package"
                and entry.get("requirements_declared")
                and not _requirements_has(requirements_text, str(entry.get("package", "")))
            ):
                violations.append(
                    _violation(
                        "REQUIREMENTS_ENTRY_MISSING",
                        f"{entry.get('package')!r} declared but absent from requirements.txt",
                        label,
                    )
                )
        else:
            if len(str(entry.get("reason", "")).strip()) < 10:
                violations.append(
                    _violation("ENTRY_REASON_MISSING", "deferred/rejected entries need a written reason", label)
                )
            if status == "rejected" and kind == "python-package":
                if _requirements_has(requirements_text, str(entry.get("package", ""))):
                    violations.append(
                        _violation(
                            "REJECTED_PACKAGE_IN_REQUIREMENTS",
                            f"{entry.get('package')!r} is rejected but listed in requirements.txt",
                            label,
                        )
                    )

    return violations


def build_report(manifest: Dict[str, Any], violations: List[Dict[str, str]], manifest_path: Path) -> Dict[str, Any]:
    entries = manifest.get("entries", []) if isinstance(manifest, dict) else []
    counts = {"approved": 0, "deferred": 0, "rejected": 0}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("status") in counts:
            counts[entry["status"]] += 1
    return {
        "schema": "jkai.third_party_gate.v1",
        "status": "PASS" if not violations else "FAIL",
        "manifest": str(manifest_path),
        "counts": {**counts, "total": len(entries) if isinstance(entries, list) else 0},
        "violations": violations,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate JKAI third-party license governance.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    root = Path(args.root)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"THIRD_PARTY_LICENSE_GATE: ERROR manifest unreadable: {exc}", file=sys.stderr)
        return 2

    violations = validate_manifest(manifest, root)
    report = build_report(manifest, violations, manifest_path)

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif not args.quiet:
        counts = report["counts"]
        print(
            f"THIRD_PARTY_LICENSE_GATE: {report['status']} "
            f"({counts['total']} entries: {counts['approved']} approved, "
            f"{counts['deferred']} deferred, {counts['rejected']} rejected)"
        )
        for item in violations:
            entry = f"[{item['entry']}] " if item.get("entry") else ""
            print(f"  - {item['code']}: {entry}{item['detail']}")

    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

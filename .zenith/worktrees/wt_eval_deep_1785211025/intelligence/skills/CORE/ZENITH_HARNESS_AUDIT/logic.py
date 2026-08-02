# [SDS-HEADER]
# File: logic.py
# Role: Audit Logic Engine
# Version: v1.0 | Project: JKAI Zenith
# [SDS-END]

import os
import json
import subprocess
from pathlib import Path

class ZenithAuditor:
    def __init__(self, root_dir):
        self.root = Path(root_dir)
        self.report = {
            "score": 0,
            "categories": {},
            "findings": []
        }

    def audit_dna(self):
        """Kiểm tra 12 Trụ cột DNA"""
        dna_path = self.root / "intelligence" / "identity"
        dna_files = [
            "ZENITH_IDENTITY.md", "ZENITH_MANIFESTO.md", "ZENITH_SOVEREIGN_RULES.md",
            "ZENITH_AGENT_PROFILES.md", "ZENITH_KNOWLEDGE_SPEC.md", "ZENITH_PROMPT_ISA.md",
            "ZENITH_SOVEREIGN_OPERATIONS.md", "ZENITH_VAULT.md", "GLOBAL_SYSTEM_CONTEXT.md",
            "ZENITH_INFRASTRUCTURE_SPEC.md", "SUPREME_TRINITY.md"
        ]
        
        passed = 0
        for f in dna_files:
            if (dna_path / f).exists():
                passed += 1
            else:
                self.report["findings"].append(f"[DNA] Missing: {f}")
        
        self.report["categories"]["DNA"] = {
            "score": int((passed / len(dna_files)) * 100),
            "status": "PASS" if passed == len(dna_files) else "WARNING"
        }

    def audit_services(self):
        """Kiểm tra Docker Services (Giả lập cho Logic)"""
        try:
            result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
            services = result.stdout.splitlines()
            count = len(services)
            # Giả định hệ thống cần ít nhất 15 dịch vụ để đạt 100%
            score = min(100, int((count / 15) * 100))
            self.report["categories"]["Services"] = {
                "score": score,
                "count": count,
                "status": "PASS" if count >= 15 else "CRITICAL"
            }
        except Exception:
            self.report["categories"]["Services"] = {"score": 0, "status": "ERROR"}

    def generate_report(self):
        self.audit_dna()
        self.audit_services()
        
        # Tính điểm tổng
        total_score = sum(c["score"] for c in self.report["categories"].values())
        self.report["score"] = int(total_score / len(self.report["categories"]))
        return self.report

if __name__ == "__main__":
    auditor = ZenithAuditor("D:/Docker/JKAI")
    print(json.dumps(auditor.generate_report(), indent=2))

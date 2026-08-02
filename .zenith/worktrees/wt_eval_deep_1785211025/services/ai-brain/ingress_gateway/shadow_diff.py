# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/ingress_gateway/shadow_diff.py
# - Role: Structured Decision Diff Engine for Shadow Mode
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Trien khai chuan hoa intent (canonicalization) va so sanh bam thong minh.
# - Dam bao chi OBSERVE, khong duoc MUTATE STATE duoi moi hinh thuc!

import hashlib
import re

class DecisionDiffEngine:
    """
    May So Khop Quyet Dinh (Structured Diff Score cho Shadow Mode)
    Khong dung Binary Diff (Chi True/False). Dung trong so (Weighted Score).
    Tuyet doi CHI OBSERVE, KHONG MUTATE STATE!
    """
    def __init__(self):
        self.stopwords = {
            "hay", "lam", "cho", "toi", "de", "voi", "va", "cua", "la", "trong", "tren", "duoi", "duoc", "bi", "ra", "vao",
            "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for"
        }

    def canonicalize_intent(self, intent: str) -> str:
        """
        Chuan hoa intent thanh mot chuoi dai dien duy nhat (Canonical Form).
        Chuyen sang chu thuong, loai bo ky tu dac biet, stop words, va sap xep cac tu de chong lech thu tu.
        """
        if not intent:
            return ""
        
        cleaned = re.sub(r"[^\w\s]", " ", intent.lower())
        words = cleaned.split()
        
        # Loc stopwords va tu rong
        filtered_words = [w for w in words if w not in self.stopwords]
        
        # Sap xep cac tu theo thu tu alphabet de giu tinh bat bien ve trat tu tu
        filtered_words.sort()
        
        return " ".join(filtered_words)

    def calculate_intent_hash(self, intent: str) -> str:
        """Tao ma hash SHA-256 tu intent da duoc chuan hoa."""
        canonical_str = self.canonicalize_intent(intent)
        if not canonical_str:
            return "EMPTY_INTENT_HASH"
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def calculate_divergence(self, legacy_manifest: dict, shadow_manifest: dict) -> float:
        """
        Tra ve Divergence Score tu 0.0 (Giong het) den 1.0 (Sai lech hoan toan).
        Weights: Intent(40%), Risk(25%), Capability(20%), Toolset(15%)
        """
        score = 0.0
        
        # 1. Diff Intent (40%) - Chuan hoa va so khop bam
        legacy_intent = legacy_manifest.get("intent", "")
        shadow_intent = shadow_manifest.get("intent", "")
        
        legacy_hash = self.calculate_intent_hash(legacy_intent)
        shadow_hash = self.calculate_intent_hash(shadow_intent)
        
        if legacy_hash != shadow_hash:
            set_legacy = set(self.canonicalize_intent(legacy_intent).split())
            set_shadow = set(self.canonicalize_intent(shadow_intent).split())
            
            if set_legacy or set_shadow:
                intersection = set_legacy.intersection(set_shadow)
                union = set_legacy.union(set_shadow)
                jaccard_similarity = len(intersection) / len(union) if union else 0.0
                jaccard_distance = 1.0 - jaccard_similarity
                score += 0.40 * jaccard_distance
            else:
                score += 0.40
            
        # 2. Diff Risk (25%)
        legacy_risk = legacy_manifest.get("risk", "UNKNOWN").upper()
        shadow_risk = shadow_manifest.get("risk", "UNKNOWN").upper()
        if legacy_risk != shadow_risk:
            risk_mapping = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4, "UNKNOWN": 0}
            r_legacy = risk_mapping.get(legacy_risk, 0)
            r_shadow = risk_mapping.get(shadow_risk, 0)
            
            if r_legacy != r_shadow:
                diff_steps = abs(r_legacy - r_shadow)
                score += min(0.25, 0.10 * diff_steps)
            
        # 3. Diff Capability (20%)
        legacy_caps = set(legacy_manifest.get("capabilities", []))
        shadow_caps = set(shadow_manifest.get("capabilities", []))
        if legacy_caps != shadow_caps:
            union_caps = legacy_caps.union(shadow_caps)
            intersection_caps = legacy_caps.intersection(shadow_caps)
            if union_caps:
                cap_distance = 1.0 - (len(intersection_caps) / len(union_caps))
                score += 0.20 * cap_distance
            else:
                score += 0.20
            
        # 4. Diff Toolset (15%)
        legacy_tools = set(legacy_manifest.get("tools", []))
        shadow_tools = set(shadow_manifest.get("tools", []))
        if legacy_tools != shadow_tools:
            union_tools = legacy_tools.union(shadow_tools)
            intersection_tools = legacy_tools.intersection(shadow_tools)
            if union_tools:
                tool_distance = 1.0 - (len(intersection_tools) / len(union_tools))
                score += 0.15 * tool_distance
            else:
                score += 0.15
            
        return min(1.0, score)

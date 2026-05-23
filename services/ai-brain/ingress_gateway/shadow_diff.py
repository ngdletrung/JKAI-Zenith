class DecisionDiffEngine:
    """
    🕵️ Máy So Khớp Quyết Định (Structured Diff Score cho Shadow Mode)
    Không dùng Binary Diff (Chỉ True/False). Dùng trọng số (Weighted Score).
    Tuyệt đối CHỈ OBSERVE, KHÔNG MUTATE STATE!
    """
    def __init__(self):
        pass

    def calculate_divergence(self, legacy_manifest: dict, shadow_manifest: dict) -> float:
        """
        Trả về Divergence Score từ 0.0 (Giống hệt) đến 1.0 (Sai lệch hoàn toàn).
        Weights: Intent(40%), Risk(25%), Capability(20%), Toolset(15%)
        """
        score = 0.0
        
        # 1. Diff Intent (40%)
        # TODO: Giả sử canonicalize intent và so sánh hash
        if legacy_manifest.get("intent") != shadow_manifest.get("intent"):
            score += 0.40
            
        # 2. Diff Risk (25%)
        # Ví dụ: Legacy=LOW, Shadow=HIGH -> Bất đồng nghiêm trọng
        if legacy_manifest.get("risk") != shadow_manifest.get("risk"):
            score += 0.25
            
        # 3. Diff Capability (20%)
        if set(legacy_manifest.get("capabilities", [])) != set(shadow_manifest.get("capabilities", [])):
            score += 0.20
            
        # 4. Diff Toolset (15%)
        if set(legacy_manifest.get("tools", [])) != set(shadow_manifest.get("tools", [])):
            score += 0.15
            
        return score

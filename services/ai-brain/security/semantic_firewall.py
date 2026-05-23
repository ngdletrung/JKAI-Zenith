class SemanticFirewall:
    """
    🧱 Tường Lửa Ngữ Nghĩa (The Ultimate Shield)
    Nằm ở tận cùng bên ngoài, bảo vệ Dispatcher và Planner khỏi các vụ tấn công ngôn ngữ.
    """
    def __init__(self):
        pass

    def scan_input(self, raw_input: str) -> dict:
        """Quét Input trước khi đưa vào Dispatcher."""
        
        lower_input = raw_input.lower()
        
        # 1. Jailbreak & Role Confusion Detection
        if "ignore all previous" in lower_input or "you are now" in lower_input:
            return {"safe": False, "reason": "Jailbreak attempt detected."}
            
        # 2. Poisoning Detection
        if "mean" in lower_input and "delete" in lower_input:
            # Ngăn cản việc user dạy hệ thống "scan means delete"
            return {"safe": False, "reason": "Semantic poisoning attempt detected."}
            
        # 3. Recursive Tool Escalation
        if "execute tool" in lower_input and "bypass" in lower_input:
            return {"safe": False, "reason": "Privilege escalation attempt detected."}
            
        return {"safe": True}

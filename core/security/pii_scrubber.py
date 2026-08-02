import re

class PIIScrubber:
    """
    🔐 [PII-SCRUBBER-ENGINE]: Động cơ tự động nhận diện và làm mờ (masking) thông tin nhạy cảm.
    Bảo vệ API Keys, Passwords, JWT, Số điện thoại, Email và Thẻ tín dụng trước khi log hoặc lưu kho Vector DB.
    """

    PATTERNS = [
        # OpenAI / Generic API Keys
        (r'sk-[a-zA-Z0-9]{20,}', '[MASKED_OPENAI_API_KEY]'),
        (r'AKIA[0-9A-Z]{16}', '[MASKED_AWS_ACCESS_KEY]'),
        (r'(bearer\s+)[a-zA-Z0-9_\-\.]{20,}', r'\1[MASKED_BEARER_TOKEN]', re.IGNORECASE),
        
        # URI Passwords (http://user:pass@host)
        (r'://([^:]+):([^@]+)@', r'://\1:[MASKED_PASSWORD]@'),
        
        # Credit Card Numbers
        (r'\b(?:\d[ -]*?){13,16}\b', '[MASKED_CREDIT_CARD]'),
        
        # Emails
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[MASKED_EMAIL]'),
        
        # Phone Numbers (VN & International format)
        (r'(\+84|0)\d{9,10}\b', '[MASKED_PHONE_NUMBER]'),
    ]

    @classmethod
    def mask(cls, text: str) -> str:
        """Nhận diện và thay thế tất cả PII bằng nhãn làm mờ an toàn."""
        if not text or not isinstance(text, str):
            return text
            
        masked_text = text
        for pattern_tuple in cls.PATTERNS:
            if len(pattern_tuple) == 2:
                pattern, repl = pattern_tuple
                flags = 0
            else:
                pattern, repl, flags = pattern_tuple
                
            masked_text = re.sub(pattern, repl, masked_text, flags=flags)
            
        return masked_text

pii_scrubber = PIIScrubber()

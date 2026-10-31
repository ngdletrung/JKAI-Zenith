import re

class PIIScrubber:
    """
    🔐 [PII-SCRUBBER-ENGINE]: Động cơ tự động nhận diện và làm mờ (masking) thông tin nhạy cảm.
    Bảo vệ API Keys, Passwords, JWT, Số điện thoại, Email và Thẻ tín dụng trước khi log hoặc lưu kho Vector DB.
    """

    PATTERNS = [
        # Local Filesystem Paths (Windows & Unix)
        (r'\b[a-zA-Z]:[/\\](?:[^<>:"|?*\n\r\s]+[/\\])*[^<>:"|?*\n\r\s]*', '[LOCAL_PATH]'),
        (r'/(?:home|var|etc|usr|opt|root|tmp)/[^\s]+', '[LOCAL_PATH]'),

        # Internal IPs & Localhost
        (r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|127\.0\.0\.1|localhost)\b', '[INTERNAL_HOST]'),

        # Cloud Provider API Keys
        (r'\beyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\b', '[MASKED_JWT]'),
        (r'sk-[a-zA-Z0-9_\-]{20,}', '[MASKED_OPENAI_API_KEY]'),
        (r'tvly-[a-zA-Z0-9_\-]{16,}', '[MASKED_TAVILY_KEY]'),
        (r'xai-[a-zA-Z0-9_\-]{16,}', '[MASKED_XAI_KEY]'),
        (r'AIzaSy[a-zA-Z0-9_\-]{30,}', '[MASKED_GEMINI_KEY]'),
        (r'AKIA[0-9A-Z]{16}', '[MASKED_AWS_ACCESS_KEY]'),
        (r'(bearer\s+)[a-zA-Z0-9_\-\.]{20,}', r'\1[MASKED_BEARER_TOKEN]', re.IGNORECASE),
        
        # URI Passwords (http://user:pass@host)
        (r'://([^:]+):([^@]+)@', r'://\1:[MASKED_PASSWORD]@'),
        
        # Vietnamese Citizen ID (CCCD: 12 digits, CMND: 9 digits)
        (r'\b\d{12}\b', '[REDACTED_CITIZEN_ID]'),

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

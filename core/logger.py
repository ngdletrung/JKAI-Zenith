import logging
import re

class PIIMaskingFormatter(logging.Formatter):
    PII_PATTERNS = [
        (re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'), '[EMAIL_MASKED]'),
        (re.compile(r'\b\d{4}[-.]?\d{3}[-.]?\d{3}\b'), '[PHONE_MASKED]'),
    ]

    def format(self, record):
        original_msg = super().format(record)
        masked_msg = original_msg
        for pattern, replacement in self.PII_PATTERNS:
            masked_msg = pattern.sub(replacement, masked_msg)
        return masked_msg

def setup_logger(name="aijk_logger", trace_id=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = PIIMaskingFormatter('%(asctime)s - %(name)s - [%(levelname)s] - TraceID: %(trace_id)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    extra = {'trace_id': trace_id or 'NO_TRACE'}
    return logging.LoggerAdapter(logger, extra)
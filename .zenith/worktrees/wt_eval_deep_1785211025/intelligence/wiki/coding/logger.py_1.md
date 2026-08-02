---
type: python_file
file: logger.py
tags: []
---

# logger

import logging
import re

class PIIMaskingFormatter(logging.Formatter):
    PII_PATTERNS = [
        (re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'), '[EMAIL_MASKED]'),
        (re.compile(r'\b\d{4}[-.]?\d{3}[-.]?\d{3}\b'), '[PHONE_MASKED]'),
    ]

    def format(self, record):
     

## Links to
- [[logging]]
- [[re]]

## Linked by
- [[__init__.py]]

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from core.security.pii_scrubber import pii_scrubber

class TestPIIScrubber(unittest.TestCase):
    def test_pii_masking_openai_key(self):
        raw = "Key sk-1234567890123456789012345 is private"
        masked = pii_scrubber.mask(raw)
        self.assertNotIn("sk-1234567890123456789012345", masked)
        self.assertIn("[MASKED_OPENAI_API_KEY]", masked)

    def test_pii_masking_email(self):
        raw = "Contact info: admin@example.com for support"
        masked = pii_scrubber.mask(raw)
        self.assertNotIn("admin@example.com", masked)
        self.assertIn("[MASKED_EMAIL]", masked)

    def test_pii_masking_uri_pass(self):
        raw = "Connect redis://admin:secretpass123@redis:6379"
        masked = pii_scrubber.mask(raw)
        self.assertNotIn("secretpass123", masked)
        self.assertIn("[MASKED_PASSWORD]", masked)

if __name__ == "__main__":
    unittest.main()

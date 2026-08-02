import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from core.utils.otlp_tracer import generate_trace_parent, parse_trace_parent

class TestOTLPTracer(unittest.TestCase):
    def test_generate_and_parse_trace_parent(self):
        header = generate_trace_parent()
        self.assertTrue(header.startswith("00-"))
        self.assertEqual(len(header.split("-")), 4)

        trace_id, span_id = parse_trace_parent(header)
        self.assertEqual(len(trace_id), 32)
        self.assertEqual(len(span_id), 16)

if __name__ == "__main__":
    unittest.main()

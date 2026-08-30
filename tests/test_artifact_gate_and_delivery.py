# -*- coding: utf-8 -*-
"""
🧪 TEST SUITE: ARTIFACT GATE & NATIVE DELIVERY RECEIPT
File: tests/test_artifact_gate_and_delivery.py
"""

import os
import tempfile
import unittest
from core.kernel.artifact_gate import verify_artifact_on_disk, format_delivery_receipt, _format_bytes


class TestArtifactGateAndDelivery(unittest.TestCase):

    def test_format_bytes(self):
        self.assertEqual(_format_bytes(500), "500 B")
        self.assertEqual(_format_bytes(1024), "1.0 KB")
        self.assertEqual(_format_bytes(int(1024 * 1024 * 2.5)), "2.50 MB")

    def test_verify_artifact_on_disk_valid(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
            f.write(b"SAMPLE EXCEL DATA CONTENT 1234567890")
            tmp_path = f.name

        try:
            res = verify_artifact_on_disk(tmp_path)
            self.assertTrue(res["verified"])
            self.assertGreater(res["size_bytes"], 0)
            self.assertGreater(len(res["checksum"]), 0)
            self.assertTrue(res["filename"].endswith(".xlsx"))

            receipt = format_delivery_receipt(res)
            self.assertIn("Biên Lai Bàn Giao Tệp", receipt)
            self.assertIn(res["filename"], receipt)
            self.assertIn(res["size_formatted"], receipt)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_verify_artifact_on_disk_empty(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            tmp_path = f.name  # 0 bytes

        try:
            res = verify_artifact_on_disk(tmp_path)
            self.assertFalse(res["verified"])
            self.assertIn("rỗng", res["reason"])
            receipt = format_delivery_receipt(res)
            self.assertEqual(receipt, "")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_verify_artifact_on_disk_nonexistent(self):
        fake_path = os.path.join(tempfile.gettempdir(), "non_existent_file_99999.pdf")
        if os.path.exists(fake_path):
            os.remove(fake_path)

        res = verify_artifact_on_disk(fake_path)
        self.assertFalse(res["verified"])
        self.assertIn("không tồn tại", res["reason"])


if __name__ == "__main__":
    unittest.main()

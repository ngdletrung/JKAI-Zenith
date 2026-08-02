import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from pathlib import Path
from core.kernel.saga_atomic_healer import saga_atomic_healer

class TestSagaAtomicHealer(unittest.TestCase):
    def setUp(self):
        self.test_file = Path("D:\\Docker\\JKAI\\brain\\scratch\\test_saga_target.txt")
        self.test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("ORIGINAL_CONTENT_V1")

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()

    def test_begin_and_commit_transaction(self):
        task_id = "tx_commit_001"
        saga_atomic_healer.begin_transaction(task_id, [str(self.test_file)])
        
        bak_file = self.test_file.with_suffix(".txt.bak")
        self.assertTrue(bak_file.exists())
        
        # Sửa nội dung
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("MODIFIED_CONTENT_V2")
            
        saga_atomic_healer.commit_transaction(task_id)
        self.assertFalse(bak_file.exists()) # .bak file removed after commit
        
        with open(self.test_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "MODIFIED_CONTENT_V2")

    def test_begin_and_rollback_transaction(self):
        task_id = "tx_rollback_002"
        saga_atomic_healer.begin_transaction(task_id, [str(self.test_file)])
        
        # Sửa làm hỏng file
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("BROKEN_CONTENT_CORRUPTED")
            
        # Kích hoạt Rollback
        res = saga_atomic_healer.rollback_transaction(task_id, error_detail="Syntax Error in file edit")
        self.assertTrue(res)
        
        # Kiểm tra file đã được khôi phục về ORIGINAL_CONTENT_V1
        with open(self.test_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "ORIGINAL_CONTENT_V1")

if __name__ == "__main__":
    unittest.main()

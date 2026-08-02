import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_test_db = os.path.join(tempfile.gettempdir(), f".ks_test_metadata_{os.getpid()}.db")
os.environ["KS_METADATA_DB"] = _test_db

from core.knowledge_sources.metadata import MetadataDB


class TestMetadataDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(_test_db):
            os.remove(_test_db)
        cls.db = MetadataDB()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        if os.path.exists(_test_db):
            os.remove(_test_db)

    def setUp(self):
        conn = self.db._get_conn()
        conn.execute("DELETE FROM files")
        conn.execute("DELETE FROM sources")
        conn.commit()

    def test_register_source(self):
        self.db.register_source("test_1", "Test Source", "local_folder", {"path": "/tmp"})
        src = self.db.get_source("test_1")
        self.assertIsNotNone(src)
        self.assertEqual(src["name"], "Test Source")
        self.assertEqual(src["type"], "local_folder")

    def test_remove_source(self):
        self.db.register_source("test_2", "To Delete", "local_folder")
        self.db.remove_source("test_2")
        self.assertIsNone(self.db.get_source("test_2"))

    def test_upsert_file(self):
        self.db.register_source("test_3", "File Source", "local_folder")
        self.db.upsert_file("test_3", "docs/file.md", "/abs/path/file.md", ".md", "abc123", 100, 1000.0)
        f = self.db.get_file("test_3", "docs/file.md")
        self.assertIsNotNone(f)
        self.assertEqual(f["checksum"], "abc123")
        self.assertEqual(f["status"], "pending")

    def test_upsert_file_status_stays_pending_on_same_checksum(self):
        """Upsert cùng checksum không được đổi status thưa Master."""
        self.db.register_source("test_4", "Change Test", "local_folder")
        self.db.upsert_file("test_4", "test.md", "/abs/test.md", ".md", "same_hash", 100, 1000.0)
        # upsert lại cùng checksum
        self.db.upsert_file("test_4", "test.md", "/abs/test.md", ".md", "same_hash", 100, 1000.0)
        f = self.db.get_file("test_4", "test.md")
        self.assertEqual(f["checksum"], "same_hash")

    def test_mark_indexed(self):
        self.db.register_source("test_5", "Indexed", "local_folder")
        self.db.upsert_file("test_5", "indexed.md", "/abs/indexed.md", ".md", "aaa", 100, 1000.0)
        self.db.mark_indexed("test_5", "indexed.md", checksum="aaa")
        f = self.db.get_file("test_5", "indexed.md")
        self.assertEqual(f["status"], "indexed")

    def test_mark_failed(self):
        self.db.register_source("test_6", "Failed", "local_folder")
        self.db.upsert_file("test_6", "fail.md", "/abs/fail.md", ".md", "xxx", 100, 1000.0)
        self.db.mark_failed("test_6", "fail.md", "Some error")
        f = self.db.get_file("test_6", "fail.md")
        self.assertEqual(f["status"], "failed")
        self.assertIn("Some error", f["error_msg"])

    def test_get_stale_files_with_future_cutoff(self):
        """Dùng cutoff trong tương lai để lấy tất cả file thưa Master."""
        self.db.register_source("test_8", "Stale", "local_folder")
        self.db.upsert_file("test_8", "old.md", "/abs/old.md", ".md", "old", 100, 1000.0)
        self.db.upsert_file("test_8", "current.md", "/abs/current.md", ".md", "cur", 100, 1000.0)
        # Mark current.md indexed
        self.db.mark_indexed("test_8", "current.md")
        # Stale với cutoff trong tương lai xa -> trả về file chưa indexed
        stale = self.db.get_stale_files("test_8", cutoff=time.time() + 9999)
        paths = [f["rel_path"] for f in stale]
        self.assertIn("old.md", paths, "old.md chưa indexed phải là stale thưa Master")

    def test_get_all_indexed_files(self):
        self.db.register_source("test_9", "Indexed All", "local_folder")
        self.db.upsert_file("test_9", "a.md", "/abs/a.md", ".md", "a", 100, 1000.0)
        self.db.upsert_file("test_9", "b.md", "/abs/b.md", ".md", "b", 100, 1000.0)
        self.db.mark_indexed("test_9", "a.md")
        indexed = self.db.get_all_indexed_files("test_9")
        self.assertEqual(len(indexed), 1)
        self.assertEqual(indexed[0]["rel_path"], "a.md")

    def test_list_sources(self):
        self.db.register_source("src_a", "A", "web_url")
        self.db.register_source("src_b", "B", "local_folder")
        sources = self.db.list_sources()
        self.assertGreaterEqual(len(sources), 2)

    def test_hot_query_tracking(self):
        self.db.record_hot_query("what is JKAI?")
        self.db.record_hot_query("what is JKAI?")
        top = self.db.get_top_hot_queries(limit=5)
        queries = [q["query_text"] for q in top]
        self.assertIn("what is JKAI?", queries)


if __name__ == "__main__":
    unittest.main()

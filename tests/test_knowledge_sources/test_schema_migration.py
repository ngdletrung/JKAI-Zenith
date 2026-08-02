"""
Unit Tests: Schema Migration System
Test bảo đảm hệ thống migration database hoạt động đúng
khi nâng cấp phiên bản schema thưa Master.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Dùng DB riêng biệt cho test này
_test_db = os.path.join(tempfile.gettempdir(), f".ks_test_migration_{os.getpid()}.db")
os.environ["KS_METADATA_DB"] = _test_db


class TestSchemaMigration(unittest.TestCase):
    """Kiểm thử hệ thống migration schema database thưa Master."""

    def setUp(self):
        """Xóa DB cũ trước mỗi test để đảm bảo môi trường sạch."""
        if os.path.exists(_test_db):
            os.remove(_test_db)
        # Xóa module cache để MetadataDB được tái khởi tạo hoàn toàn
        mods = [k for k in sys.modules if "metadata" in k]
        for m in mods:
            del sys.modules[m]

    def tearDown(self):
        if os.path.exists(_test_db):
            os.remove(_test_db)

    def _get_fresh_db(self):
        from core.knowledge_sources.metadata import MetadataDB
        return MetadataDB()

    def test_initial_migration_creates_schema_version_table(self):
        """DB mới phải có bảng schema_version thưa Master."""
        db = self._get_fresh_db()
        conn = db._get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        self.assertIsNotNone(row, "Bảng schema_version phải tồn tại sau khi khởi tạo DB")
        db.close()

    def test_schema_version_is_1_after_first_init(self):
        """Sau lần init đầu tiên, phiên bản schema phải là 1 thưa Master."""
        db = self._get_fresh_db()
        conn = db._get_conn()
        row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1, "Phiên bản schema phải là 1 sau lần init đầu")
        db.close()

    def test_migration_is_idempotent(self):
        """Khởi tạo DB lần 2 không được làm hỏng dữ liệu hay thay đổi version thưa Master."""
        db1 = self._get_fresh_db()
        db1.register_source("s1", "Test", "local_folder")
        db1.close()

        # Xóa module cache và tái import để mô phỏng khởi động lại container
        mods = [k for k in sys.modules if "metadata" in k]
        for m in mods:
            del sys.modules[m]

        from core.knowledge_sources.metadata import MetadataDB
        db2 = MetadataDB()
        conn = db2._get_conn()
        row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        self.assertEqual(row[0], 1, "Version không được thay đổi khi chạy lại migration")
        src = db2.get_source("s1")
        self.assertIsNotNone(src, "Dữ liệu cũ phải còn nguyên sau khi restart")
        db2.close()

    def test_all_required_tables_exist(self):
        """Tất cả các bảng cốt lõi phải tồn tại sau khi init thưa Master."""
        required_tables = {"sources", "files", "hot_queries", "schema_version"}
        db = self._get_fresh_db()
        conn = db._get_conn()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        actual = {r[0] for r in rows}
        for t in required_tables:
            self.assertIn(t, actual, f"Bảng '{t}' phải tồn tại thưa Master")
        db.close()

    def test_indexes_are_created(self):
        """Các index cần thiết phải được tạo đúng để tối ưu truy vấn thưa Master."""
        db = self._get_fresh_db()
        conn = db._get_conn()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        idx_names = {r[0] for r in rows}
        self.assertIn("idx_files_source", idx_names, "idx_files_source phải tồn tại")
        self.assertIn("idx_files_status", idx_names, "idx_files_status phải tồn tại")
        db.close()


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.knowledge_sources.sources.source import Source, SourceType, FileRecord


class TestSourceModels(unittest.TestCase):
    def test_source_creation(self):
        src = Source(id="test_1", name="My Folder", type=SourceType.LOCAL_FOLDER, config={"path": "/tmp"})
        self.assertEqual(src.id, "test_1")
        self.assertEqual(src.type.value, "local_folder")
        self.assertEqual(src.target_collection, "jkai_external")
        self.assertTrue(src.enabled)

    def test_source_types(self):
        self.assertEqual(SourceType.LOCAL_FOLDER.value, "local_folder")
        self.assertEqual(SourceType.WEB_URL.value, "web_url")
        self.assertEqual(SourceType.ONEDRIVE.value, "onedrive")
        self.assertEqual(SourceType.GOOGLE_DRIVE.value, "gdrive")
        self.assertEqual(SourceType.SHAREPOINT.value, "sharepoint")
        self.assertEqual(SourceType.CUSTOM_PLUGIN.value, "custom_plugin")

    def test_source_equality(self):
        src1 = Source(id="s1", name="S1", type=SourceType.INTELLIGENCE_DIR)
        src2 = Source(id="s1", name="S2", type=SourceType.LOCAL_FOLDER)
        self.assertEqual(src1.id, src2.id)

    def test_file_record_defaults(self):
        rec = FileRecord(source_id="src1", rel_path="docs/file.md")
        self.assertEqual(rec.status, "pending")
        self.assertEqual(rec.file_size, 0)
        self.assertEqual(rec.mtime, 0.0)
        self.assertIsNone(rec.checksum)
        self.assertIsNone(rec.abs_path)

    def test_file_record_full(self):
        rec = FileRecord(
            source_id="src1",
            rel_path="docs/file.md",
            abs_path="/abs/docs/file.md",
            file_type=".md",
            checksum="abc123",
            file_size=1024,
            mtime=1000.0,
            status="indexed",
        )
        self.assertEqual(rec.checksum, "abc123")
        self.assertEqual(rec.status, "indexed")
        self.assertEqual(rec.file_size, 1024)


if __name__ == "__main__":
    unittest.main()

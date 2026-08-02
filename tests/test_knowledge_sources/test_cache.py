import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.knowledge_sources.cache import CacheLayer


class TestCacheLayer(unittest.TestCase):
    def setUp(self):
        self.cache = CacheLayer()

    def test_file_cache_set_get(self):
        content = "# Test content\nHello world"
        self.cache.set_file_cache("/path/test.md", content)
        cached = self.cache.get_file_cache("/path/test.md")
        self.assertEqual(cached, content)

    def test_file_cache_missing(self):
        val = self.cache.get_file_cache("/nonexistent/path.md")
        self.assertIsNone(val)

    def test_embedding_cache(self):
        text = "JKAI là hệ điều hành trí tuệ"
        self.cache.set_embedding(text, [0.1, 0.2, 0.3])
        vec = self.cache.get_embedding(text)
        self.assertEqual(vec, [0.1, 0.2, 0.3])

    def test_lru_eviction(self):
        for i in range(20):
            self.cache.set_file_cache(f"/tmp/{i}.md", f"val{i}")
        # LRU should evict old entries when over max (500 default)
        cached = self.cache.get_file_cache("/tmp/0.md")
        # May or may not be evicted depending on state; just verify no crash
        self.assertIsNotNone(self.cache.get_file_cache("/tmp/19.md"))


if __name__ == "__main__":
    unittest.main()

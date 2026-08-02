import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.knowledge_sources.retriever import RetrievalResult


class TestRetrievalResult(unittest.TestCase):
    def test_create_empty_result(self):
        """RetrievalResult phải tạo được với các trường cơ bản thưa Master."""
        r = RetrievalResult(results=[], sources=[], elapsed=0.0)
        self.assertEqual(r.results, [])
        self.assertEqual(r.sources, [])
        self.assertAlmostEqual(r.elapsed, 0.0)

    def test_create_with_data(self):
        """RetrievalResult phải lưu đúng dữ liệu đầu vào thưa Master."""
        items = [{"score": 0.9, "payload": {"text": "hello"}}]
        r = RetrievalResult(results=items, sources=["jkai_knowledge"], elapsed=0.12)
        self.assertEqual(len(r.results), 1)
        self.assertEqual(r.results[0]["score"], 0.9)
        self.assertIn("jkai_knowledge", r.sources)
        self.assertAlmostEqual(r.elapsed, 0.12, places=2)

    def test_collections_constants_defined(self):
        """Các hằng số collection phải được định nghĩa thưa Master."""
        from core.knowledge_sources.retriever import (
            COLLECTION_KNOWLEDGE,
            COLLECTION_MEMORY,
            COLLECTION_REASONING,
            COLLECTION_EXTERNAL,
        )
        self.assertEqual(COLLECTION_KNOWLEDGE, "jkai_knowledge")
        self.assertEqual(COLLECTION_MEMORY, "jkai_memory")
        self.assertEqual(COLLECTION_REASONING, "jkai_reasoning_bank")
        self.assertEqual(COLLECTION_EXTERNAL, "jkai_external")

    def test_retriever_singleton(self):
        """UnifiedRetriever phải la Singleton thưa Master."""
        from core.knowledge_sources.retriever import UnifiedRetriever
        r1 = UnifiedRetriever()
        r2 = UnifiedRetriever()
        self.assertIs(r1, r2, "UnifiedRetriever phai tra ve cung mot instance")


if __name__ == "__main__":
    unittest.main()

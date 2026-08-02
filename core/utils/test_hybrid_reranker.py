import sys
import os

# Add workspace directory to path
sys.path.append(os.getcwd())

from core.utils.hybrid_reranker import HybridReranker, BM25Calculator

def test_bm25_calculator():
    print("[TEST]: Testing BM25 Calculator...")
    corpus = [
        "Python is a great programming language for AI and machine learning",
        "Machine learning and deep learning are subfields of AI",
        "We are learning Python programming today in the class",
        "Docker is used to containerize applications"
    ]
    
    bm25 = BM25Calculator(corpus)
    
    # Test tokenization
    tokens = bm25._tokenize("Python, programming! language.")
    assert "python" in tokens
    assert "programming" in tokens
    assert "language" in tokens
    assert len(tokens) == 3
    
    # Test scoring: doc containing search terms should score higher than doc that doesn't
    # Query "Python programming"
    q_terms = ["python", "programming"]
    score_doc0 = bm25.get_score(0, q_terms)
    score_doc2 = bm25.get_score(2, q_terms)
    score_doc3 = bm25.get_score(3, q_terms)
    
    print(f"Score Doc 0: {score_doc0:.4f}")
    print(f"Score Doc 2: {score_doc2:.4f}")
    print(f"Score Doc 3: {score_doc3:.4f}")
    
    assert score_doc0 > 0.0
    assert score_doc2 > 0.0
    assert score_doc3 == 0.0
    print("[SUCCESS]: BM25 Calculator behaves correctly.")

def test_freshness_decay():
    print("\n[TEST]: Testing Freshness Decay...")
    reranker = HybridReranker()
    
    # Current date is 2026-07-01
    current_date = reranker._parse_date("2026-07-01")
    
    # Test cases:
    # 1. Same day
    date_same = reranker._parse_date("2026-07-01")
    score_same = reranker._calculate_freshness_score(date_same, current_date)
    assert score_same == 1.0
    
    # 2. 6 months ago (approx 180 days)
    date_6m = reranker._parse_date("2026-01-01")
    score_6m = reranker._calculate_freshness_score(date_6m, current_date)
    # inside 12 months should be linear decay between 0.5 and 1.0
    assert 0.5 < score_6m < 1.0
    
    # 3. 1 year ago (approx 365 days)
    date_1y = reranker._parse_date("2025-07-01")
    score_1y = reranker._calculate_freshness_score(date_1y, current_date)
    assert abs(score_1y - 0.5) < 0.01
    
    # 4. 3 years ago (more than 1 year)
    date_3y = reranker._parse_date("2023-07-01")
    score_3y = reranker._calculate_freshness_score(date_3y, current_date)
    assert score_3y < 0.5
    
    # 5. Missing / Invalid date
    score_missing = reranker._calculate_freshness_score(None, current_date)
    assert score_missing == 0.0
    
    print(f"Score Same Day: {score_same}")
    print(f"Score 6 Months Ago: {score_6m:.4f}")
    print(f"Score 1 Year Ago: {score_1y:.4f}")
    print(f"Score 3 Years Ago: {score_3y:.4f}")
    print(f"Score Missing: {score_missing}")
    print("[SUCCESS]: Freshness decay behaves correctly.")

def test_hybrid_reranker():
    print("\n[TEST]: Testing Hybrid Reranker rerank function...")
    reranker = HybridReranker()
    
    documents = [
        {
            "id": 1,
            "text": "Introduction to Python programming. Ideal for AI.",
            "cosine_score": 0.85,
            "metadata": {"date": "2026-06-01"} # Very fresh (1 month ago)
        },
        {
            "id": 2,
            "text": "Docker containerization guide for web apps.",
            "cosine_score": 0.90,
            "metadata": {"date": "2025-01-01"} # Old (1.5 years ago)
        },
        {
            "id": 3,
            "text": "Advanced AI techniques and Python architectures.",
            "cosine_score": 0.70,
            "metadata": {"date": "2026-06-25"} # Extremely fresh (1 week ago)
        }
    ]
    
    # Query: "Python AI"
    # Document 1 and 3 should have high BM25, Doc 2 should have 0 BM25.
    # We set current date as 2026-07-01
    reranked = reranker.rerank(documents, "Python AI", current_date_str="2026-07-01")
    
    print("\nReranked documents:")
    for doc in reranked:
        print(f"ID: {doc['id']} | Cosine: {doc['cosine_score']:.3f} | BM25: {doc['bm25_score']:.3f} | Freshness: {doc['freshness_score']:.3f} | Hybrid: {doc['hybrid_score']:.4f} | Text: {doc['text']}")
    
    # Assertions
    # Since Doc 2 has BM25 of 0 and old freshness, Doc 1 or 3 should rank higher than Doc 2.
    assert reranked[0]["id"] in [1, 3]
    assert "hybrid_score" in reranked[0]
    assert reranked[0]["hybrid_score"] >= reranked[1]["hybrid_score"]
    
    print("[SUCCESS]: Hybrid Reranker correctly reranked and computed scores.")

if __name__ == "__main__":
    test_bm25_calculator()
    test_freshness_decay()
    test_hybrid_reranker()

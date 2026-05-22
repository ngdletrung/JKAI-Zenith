import os

def web_search_definition(query: str):
    """Định nghĩa công cụ tìm kiếm web cho JKAI."""
    print(f"🔍 [JKAI-SEARCH-DEF] Searching for: {query}")
    # Thực tế sẽ gọi tới module tìm kiếm thực
    return {"status": "routing", "target": "ai-executor.web_search"}

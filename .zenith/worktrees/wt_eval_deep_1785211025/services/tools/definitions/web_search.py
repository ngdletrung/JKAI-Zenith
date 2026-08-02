import os
import logging

logger = logging.getLogger("jkai.tools.search")

def web_search_definition(query: str):
    """Định nghĩa công cụ tìm kiếm web cho JKAI."""
    logger.info("[JKAI-SEARCH-DEF] Searching for: %s", query)
    # Thực tế sẽ gọi tới module tìm kiếm thực
    return {"status": "routing", "target": "ai-executor.web_search"}

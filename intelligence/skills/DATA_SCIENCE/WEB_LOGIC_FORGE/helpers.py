"""
🏛️ JKAI ZENITH: NEURAL EYE HELPERS v1.0
---------------------------------------
ĐỊNH LUẬT SẮT: JKAI có quyền tự viết code vào tệp này sau khi được Master phê duyệt.
Tệp này chứa các hàm bổ trợ giúp việc duyệt web trở nên thông minh và tự trị hơn.
"""

import asyncio
import logging

logger = logging.getLogger("neural_eye.helpers")

async def wait_for_selector_smart(page, selector, timeout=10000):
    """
    Kỹ năng chờ thông minh: Tự động cuộn trang và kiểm tra sự hiện diện.
    """
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception as e:
        logger.warning("[SMART-WAIT]: Không tìm thấy %s. Đang thử cuộn trang...", selector)
        await page.evaluate("window.scrollBy(0, 500)")
        try:
            await page.wait_for_selector(selector, timeout=timeout/2)
            return True
        except Exception:
            return False

# --- [AI LEARNED HELPERS WILL BE APPENDED BELOW] ---

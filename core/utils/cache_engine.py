import hashlib
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("CacheEngine")


class CacheEngine:
    def __init__(self):
        self._intel_file_cache = {}

    def get_intel_file(self, filename, intel_dir, redis_conn=None):
        base_paths = [
            '/intelligence', '/intelligence/identity', '/intelligence/context',
            '/intelligence/agents', '/intelligence/rules', '/intelligence/skills',
            intel_dir, os.path.join(intel_dir, 'identity'),
            os.path.join(intel_dir, 'context')
        ]
        clean_name = filename[2:] if filename.startswith('./') else filename
        for bp in base_paths:
            full_path = os.path.join(bp, clean_name)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    mtime = os.path.getmtime(full_path)
                    if full_path in self._intel_file_cache:
                        cached_mtime, cached_content = self._intel_file_cache[full_path]
                        if cached_mtime == mtime:
                            return cached_content
                    redis_key = f"intel_cache:{hashlib.md5(full_path.encode('utf-8')).hexdigest()}"
                    if redis_conn:
                        try:
                            shared_data = redis_conn.get(redis_key)
                            if shared_data:
                                parsed = json.loads(shared_data)
                                if parsed.get("mtime") == mtime:
                                    content = parsed.get("content")
                                    self._intel_file_cache[full_path] = (mtime, content)
                                    return content
                        except Exception:
                            pass
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._intel_file_cache[full_path] = (mtime, content)
                    if redis_conn:
                        try:
                            redis_conn.setex(redis_key, 86400,
                                             json.dumps({"mtime": mtime, "content": content},
                                                        ensure_ascii=False))
                        except Exception:
                            pass
                    return content
                except Exception:
                    pass
        return None

    def invalidate(self, filename, intel_dir):
        for bp in [intel_dir, os.path.join(intel_dir, 'identity')]:
            full_path = os.path.join(bp, filename)
            self._intel_file_cache.pop(full_path, None)


cache_engine = CacheEngine()

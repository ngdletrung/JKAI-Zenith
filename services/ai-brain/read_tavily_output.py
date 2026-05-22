import sys
import os
import json

sys.path.append(r"/app")
sys.path.append(r"/shared")

from core.utils.redis_client import get_redis

r = get_redis()

print("Searching keys with trace signature 97e8cf4c...")
keys = r.keys("*97e8cf4c*")
for k in keys:
    print(f"Key: {k}")
    try:
        t = r.type(k)
        if t == "hash":
            print(f"  Hash: {r.hgetall(k)}")
        else:
            print(f"  String (trimmed): {r.get(k)[:1000]}")
    except Exception as e:
        print(f"  Error: {e}")

print("Searching all keys with n8n or active tasks...")
all_keys = r.keys("*")
for k in all_keys[:100]:
    k_str = k.decode() if isinstance(k, bytes) else str(k)
    if any(x in k_str.lower() for x in ["task", "mission", "exec", "result"]):
        print(f"Key: {k_str} (Type: {r.type(k)})")

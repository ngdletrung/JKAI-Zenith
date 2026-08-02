import time
import json
import os
import hashlib
from core.redis_client import redis_safe

DEFAULT_HOT_FILES = [
    "/workspace/intelligence/identity/ZENITH_IDENTITY.md",
    "/workspace/intelligence/rules_software.md",
    "/workspace/intelligence/rule_hardware.md",
    "/workspace/intelligence/SKILL_PROTOCOL.md",
    "/workspace/intelligence/registry_Map_skills.json",
]


def start_warmup_sequence(socketio):
    print(" [JKAI] Warmup Sequence Starting...")
    time.sleep(2)

    try:
        _warmup_skill_registry()
    except Exception:
        pass

    try:
        _warmup_hot_knowledge()
    except Exception:
        pass

    try:
        _warmup_hot_embeddings()
    except Exception:
        pass

    import_path = "/intelligence/vault/00_Import"
    has_intel = False
    try:
        if os.path.exists(import_path):
            files = [f for f in os.listdir(import_path) if os.path.isfile(os.path.join(import_path, f))]
            if len(files) > 0:
                has_intel = True
    except Exception:
        pass

    messages = [
        {"tag": "JKAI", "msg": "Đã hồi phục toàn bộ Tri thức. Hệ thống ổn định ở chế độ Active.", "ts": time.time()},
    ]

    if has_intel:
        messages.append({"tag": "SYSTEM", "msg": "Phát hiện tín hiệu dữ liệu mới trong khu vực Import.", "ts": time.time() + 0.3})
        messages.append({
            "tag": "PROPOSAL",
            "msg": "Phát hiện các tài liệu tri thức mới trong thư mục Import. Master có muốn nâng cấp Ma trận Tri thức ngay bây giờ không?",
            "ts": time.time() + 0.6,
            "action": "import_intel"
        })
    else:
        messages.append({"tag": "SYSTEM", "msg": "Ma trận Tri thức đã đạt trạng thái Zenith. Không phát hiện dữ liệu ngoại lai.", "ts": time.time() + 0.3})

    for msg in messages:
        payload = json.dumps(msg, ensure_ascii=False)
        redis_safe(lambda r: r.publish("monitor:log_channel", payload))
        redis_safe(lambda r: r.lpush("monitor:log_history", payload))
        time.sleep(0.4)

    print(" [JKAI] Warmup complete.")


def _warmup_skill_registry():
    registry_path = "/intelligence/registry_Map_skills.json"
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            skills = data.get("skills", {})
            redis_safe(lambda r: r.setex("ks_cache:file:" + registry_path, 3600, json.dumps(skills, ensure_ascii=False)))
            print(f" [WARMUP] Loaded {len(skills)} skills into cache.")


def _warmup_hot_knowledge():
    try:
        r = redis_safe(lambda r: r.zrevrange("ks_cache:hit_count", 0, 9), [])
        hot_paths = DEFAULT_HOT_FILES
        if r:
            hot_paths = [p.decode("utf-8") if isinstance(p, bytes) else p for p in r]

        for path in hot_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                key = "ks_cache:file:" + hashlib.md5(path.encode()).hexdigest()
                redis_safe(lambda r: r.setex(key, 3600, json.dumps({"text": content[:2000]}, ensure_ascii=False)))
        print(f" [WARMUP] Pre-cached {len(hot_paths)} hot files.")
    except Exception:
        pass


def _warmup_hot_embeddings():
    try:
        import requests as req
        OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        embed_model = os.getenv("EMBED_MODEL", "nomic-embed-text")

        hot_paths = DEFAULT_HOT_FILES
        for path in hot_paths:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()[:2000]

            embed_key = "ks_cache:embed:" + hashlib.md5(content.encode()).hexdigest()
            already_cached = redis_safe(lambda r: r.exists(embed_key), False)
            if already_cached:
                continue

            try:
                resp = req.post(
                    f"{OLLAMA_HOST}/api/embed",
                    json={"model": embed_model, "input": content},
                    timeout=30,
                )
                if resp.status_code == 200:
                    vector = resp.json().get("embeddings", [])
                    if vector:
                        redis_safe(
                            lambda r, k=embed_key, v=json.dumps(vector):
                            r.setex(k, 604800, v)
                        )
                        print(f" [WARMUP] Pre-embedded: {os.path.basename(path)}")
            except Exception:
                pass
        print(" [WARMUP] Hot embedding preload complete.")
    except Exception:
        pass

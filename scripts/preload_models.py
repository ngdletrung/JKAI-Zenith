import os
import re
import sys
import time
import json
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def preload_active_models():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rule_file = os.path.join(root_dir, "intelligence", "rule_hardware.md")
    
    if not os.path.exists(rule_file):
        print(f"⚠️ [PRELOADER]: rule_hardware.md not found at {rule_file}")
        return

    with open(rule_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse Section 3 table lines
    pattern = r'^\|\s*([A-Z_]+)\s*\|\s*([^\|]+)\|\s*\*\*([^\*]+)\*\*'
    matches = re.findall(pattern, content, re.MULTILINE)

    model_map = {}
    for role, model_raw, hw_raw in matches:
        model = model_raw.strip()
        hw = hw_raw.strip()
        if model in ("auto", "Active Model") or "SDXL" in model or "whisper" in model:
            continue
        host = "http://127.0.0.1:11435" if "CPU" in hw else "http://127.0.0.1:11434"
        if model not in model_map:
            model_map[model] = {"model": model, "roles": [role], "host": host, "hw": hw}
        else:
            model_map[model]["roles"].append(role)

    unique_models = list(model_map.values())
    print(f"📦 [PRELOADER]: Found {len(unique_models)} active model(s) in rule_hardware.md to preload.")

    for idx, item in enumerate(unique_models, 1):
        model = item["model"]
        roles_str = ", ".join(item["roles"])
        host = item["host"]
        hw_label = "CPU RAM (11435)" if "CPU" in item["hw"] else "GPU VRAM (11434)"
        
        print(f"⏳ [{idx}/{len(unique_models)}] Preloading '{model}' [{roles_str}] into {hw_label}...")
        t0 = time.time()
        try:
            if "embed" in model.lower():
                url = f"{host}/api/embeddings"
                payload = {"model": model, "prompt": "warmup", "keep_alive": -1}
            else:
                url = f"{host}/api/generate"
                payload = {"model": model, "prompt": "", "keep_alive": -1, "stream": False}

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp.read()
            elapsed = time.time() - t0
            print(f"✅ [{idx}/{len(unique_models)}] Successfully preloaded '{model}' into {hw_label} ({elapsed:.1f}s).")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"⚠️ [{idx}/{len(unique_models)}] Preload trigger for '{model}': {e} ({elapsed:.1f}s)")

if __name__ == "__main__":
    preload_active_models()

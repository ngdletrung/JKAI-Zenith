import urllib.request, json

def check_ollama(port, label):
    print(f"\n=== {label} (port {port}) ===")
    
    # HOT models (running)
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/api/ps", timeout=5)
        data = json.loads(r.read())
        models = data.get("models", [])
        print(f"  HOT (running): {len(models)} model(s)")
        for m in models:
            vram_mb = m.get("size_vram", 0) // 1024 // 1024
            print(f"    - {m['name']} | VRAM={vram_mb}MB")
    except Exception as e:
        print(f"  HOT check ERROR: {e}")
    
    # AVAILABLE models (library)
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=5)
        data = json.loads(r.read())
        names = [m["name"] for m in data.get("models", [])]
        print(f"  AVAILABLE library: {len(names)} model(s)")
        for n in names:
            print(f"    - {n}")
    except Exception as e:
        print(f"  LIBRARY check ERROR: {e}")

check_ollama(11434, "GPU Ollama")
check_ollama(11435, "CPU Ollama")

# Cross-reference with rule_hardware.md config
print("\n\n=== CROSS-REFERENCE: rule_hardware.md vs Ollama Reality ===")
config_roles = [
    ("EMBEDDER",        "nomic-embed-text:latest",                       "GPU/VRAM", 11434),
    ("RECEPTIONIST",    "tomng/nanbeige4.1:3b-q4_K_M",                   "CPU/RAM",  11435),
    ("CHAT",            "tomng/nanbeige4.1:3b-q4_K_M",                   "CPU/RAM",  11435),
    ("SUMMARIZER",      "deepseek-r1:latest",                            "GPU/VRAM", 11434),
    ("DISPATCHER",      "tomng/nanbeige4.1:3b-q4_K_M",                   "CPU/RAM",  11435),
    ("CRITIC",          "tomng/nanbeige4.1:3b-q4_K_M",                   "CPU/RAM",  11435),
    ("PLANNER",         "deepseek-r1:latest",                            "GPU/VRAM", 11434),
    ("CRITIC_ALPHA",    "deepseek-r1:latest",                            "GPU/VRAM", 11434),
    ("CRITIC_BETA",     "tomng/nanbeige4.1:3b-q4_K_M",                   "CPU/RAM",  11435),
    ("DATA_SCOUT",      "tomng/nanbeige4.1:3b-q4_K_M",                   "CPU/RAM",  11435),
    ("EXECUTOR_ALPHA",  "deepseek-r1:latest",                            "GPU/VRAM", 11434),
    ("EXECUTOR_BETA",   "fauxpaslife/nanbeige4.1-python-deepthink:3b",   "CPU/RAM",  11435),
    ("EXECUTOR",        "fauxpaslife/nanbeige4.1-python-deepthink:3b",   "CPU/RAM",  11435),
    ("RESERVE_AGENT",   "tomng/nanbeige4.1:3b-q4_K_M",                   "CPU/RAM",  11435),
    ("COMPRESSOR",      "qwen3:0.6b",                                    "GPU/VRAM", 11434),
    ("VISION",          "moondream:latest",                              "CPU/RAM",  11435),
    ("TRANSLATOR",      "qwen3.5:latest",                                "CPU/RAM",  11435),
]

# Build available sets per port
avail = {}
for port in [11434, 11435]:
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=5)
        data = json.loads(r.read())
        avail[port] = set(m["name"].lower() for m in data.get("models", []))
        # Also add name without tag
        for m in data.get("models", []):
            avail[port].add(m["name"].split(":")[0].lower())
    except:
        avail[port] = set()

print(f"\n{'Role':<16} {'Hardware':<10} {'Port':<6} {'Model':<55} {'Status'}")
print("-" * 110)
for role, model, hw, port in config_roles:
    model_lower = model.lower()
    model_base = model_lower.split(":")[0]
    in_lib = model_lower in avail.get(port, set()) or model_base in avail.get(port, set())
    status = "OK" if in_lib else "MISSING in correct host!"
    print(f"{role:<16} {hw:<10} {port:<6} {model:<55} {status}")

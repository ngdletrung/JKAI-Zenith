#!/usr/bin/env python3
"""Check ollama models on both GPU and CPU ports."""
import urllib.request, json

for port, label in [(11434, "GPU"), (11435, "CPU")]:
    try:
        # Check available models
        resp = urllib.request.urlopen(f'http://localhost:{port}/api/tags', timeout=5)
        data = json.load(resp)
        print(f"=== {label} Ollama ({port}) ===")
        for m in data.get('models', []):
            sz = m.get('size', 0) / 1e9
            print(f"  {m['name']}: {sz:.1f}GB")
        
        # Check loaded models
        resp2 = urllib.request.urlopen(f'http://localhost:{port}/api/ps', timeout=5)
        data2 = json.load(resp2)
        print(f"  Loaded: {[m['name'] for m in data2.get('models', [])]}")
    except Exception as e:
        print(f"=== {label} Ollama ({port}): {e} ===")

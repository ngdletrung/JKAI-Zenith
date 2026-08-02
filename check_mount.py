#!/usr/bin/env python3
import subprocess, json

result = subprocess.run(
    ["docker", "inspect", "ai-brain", "--format", "{{json .Mounts}}"],
    capture_output=True, text=True
)
mounts = json.loads(result.stdout.strip())
for m in mounts:
    print(f'{m.get("Source", "?")} -> {m.get("Destination", "?")} ({m.get("Type", "?")})')

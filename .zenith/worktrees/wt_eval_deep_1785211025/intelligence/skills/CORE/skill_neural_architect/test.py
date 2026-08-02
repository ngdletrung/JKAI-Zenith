import asyncio
import os
import sys

# [PATH-ALIGNMENT]
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from intelligence.skills.skill_neural_architect.logic import run_skill

async def test_mapping():
    print("[TEST]: Starting Neural Architect verification...")
    try:
        # Simulate mapping JKAI system
        result = await run_skill("Map JKAI", task_id="test_arch")
        print(f"[RESULT]: {result}")
        
        # Check if topology file was created
        topology_path = os.path.join(project_root, "ZENITH_TOPOLOGY.md")
        if os.path.exists(topology_path):
            print("[SUCCESS]: ZENITH_TOPOLOGY.md has been generated.")
        else:
            print("[FAILURE]: ZENITH_TOPOLOGY.md not found.")
            
    except Exception as e:
        print(f"[ERROR]: Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mapping())

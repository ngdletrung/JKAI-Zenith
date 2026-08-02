import asyncio
import sys
import os

brain_path = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(brain_path, "..", ".."))

if brain_path not in sys.path:
    sys.path.append(brain_path)
if project_root not in sys.path:
    sys.path.append(project_root)

from receptionist import Receptionist

async def main():
    print("========================================")
    print("🧪 STARTING HYBRID REACT LOOP TEST")
    print("========================================")
    
    rec = Receptionist()
    
    test_question = "thời tiết hôm nay thế nào?"
    print(f"\n[USER INPUT]: {test_question}\n")
    
    response = await rec.handle_task(test_question, "TEST-REACT-100")
    
    print("\n========================================")
    print("✅ TEST COMPLETE")
    print("========================================")
    print(f"FINAL RESPONSE:\n{response}")

if __name__ == "__main__":
    asyncio.run(main())

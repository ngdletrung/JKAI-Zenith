import asyncio
import os
import sys
import inspect
import importlib.util

# Add /shared to python path just in case
sys.path.append("/shared")

async def test():
    from tool_router import ToolRouter
    from core.utils.knowledge_manager import knowledge_orchestrator

    router = ToolRouter()
    tool_name = "read_url_content"
    
    all_skills = await knowledge_orchestrator.get_all_skills_dict()
    resolved_tool_name = "SEARCH_WEB_GLOBAL"
    skill_info = all_skills.get(resolved_tool_name)
    
    print("--- skill_info ---")
    print(skill_info)
    
    rel_path = skill_info.get("rel_path", "")
    print(f"rel_path (raw): {repr(rel_path)}")
    
    rel_path = rel_path.replace("\\", "/")
    print(f"rel_path (norm): {repr(rel_path)}")
    
    skill_dir = os.path.dirname(rel_path)
    print(f"skill_dir: {repr(skill_dir)}")
    
    skill_folder = os.path.basename(skill_dir)
    print(f"skill_folder: {repr(skill_folder)}")
    
    logic_file = os.path.join(router.base_dir if hasattr(router, 'base_dir') else router.skills_root, skill_dir, "logic.py")
    print(f"logic_file: {repr(logic_file)}")
    
    exists = os.path.exists(logic_file)
    print(f"exists: {exists}")
    
    if not exists:
        print("File does not exist, checking alternative path...")
        logic_file = os.path.join(router.skills_root, skill_folder, "logic.py")
        print(f"alt logic_file: {repr(logic_file)}")
        print(f"alt exists: {os.path.exists(logic_file)}")

    print("\n--- Spec Loading ---")
    spec = importlib.util.spec_from_file_location(f"{skill_folder}.logic", logic_file)
    print("spec:", spec)
    
    module = importlib.util.module_from_spec(spec)
    print("module:", module)
    
    # 🧬 Register in sys.modules to prevent dataclass AttributeError
    sys.modules[module.__name__] = module
    
    spec.loader.exec_module(module)
    print("module execution: SUCCESS")

if __name__ == "__main__":
    asyncio.run(test())

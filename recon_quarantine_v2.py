import os
import re
import json

# Paths
BASE_DIR = r"d:\Docker\JKAI"
INTELLIGENCE_DIR = os.path.join(BASE_DIR, "intelligence")
QUARANTINE_DIR = os.path.join(INTELLIGENCE_DIR, "archive", "quarantine")
SKILLS_DIR = os.path.join(INTELLIGENCE_DIR, "skills")
AGENTS_DIR = os.path.join(INTELLIGENCE_DIR, "agents")
PROMPTS_DIR = os.path.join(INTELLIGENCE_DIR, "prompts")

def get_skill_id(skill_md_path):
    if not os.path.exists(skill_md_path):
        return None
    try:
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Try to match id: ... in yaml block
            match = re.search(r'^id:\s*"?([\w_-]+)"?', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    except Exception:
        pass
    return None

def scan_active_entities():
    active_names = set()
    active_ids = {} # id -> path
    
    # 1. Scan Skills (Nested domains)
    if os.path.exists(SKILLS_DIR):
        for domain in os.listdir(SKILLS_DIR):
            domain_path = os.path.join(SKILLS_DIR, domain)
            if os.path.isdir(domain_path):
                for skill in os.listdir(domain_path):
                    skill_path = os.path.join(domain_path, skill)
                    if os.path.isdir(skill_path):
                        active_names.add(skill)
                        sid = get_skill_id(os.path.join(skill_path, "SKILL.md"))
                        if sid:
                            active_ids[sid] = skill_path
                            
    # 2. Scan Agents (Files and directories)
    if os.path.exists(AGENTS_DIR):
        for item in os.listdir(AGENTS_DIR):
            name = os.path.splitext(item)[0]
            if name.startswith("agent_"):
                name = name[6:]
            active_names.add(name)
            active_names.add(item)
            
    # 3. Scan Prompts (Files)
    if os.path.exists(PROMPTS_DIR):
        for item in os.listdir(PROMPTS_DIR):
            name = os.path.splitext(item)[0]
            active_names.add(name)
            active_names.add(item)
            
    return active_names, active_ids

def run_recon():
    active_names, active_ids = scan_active_entities()
    
    results = {
        "ĐỘC BẢN": [],
        "XUNG ĐỘT": [],
        "RÁC": []
    }
    
    if not os.path.exists(QUARANTINE_DIR):
        print(f"Error: Quarantine dir {QUARANTINE_DIR} not found.")
        return

    quarantine_items = os.listdir(QUARANTINE_DIR)
    
    for item in quarantine_items:
        item_path = os.path.join(QUARANTINE_DIR, item)
        
        # Classification
        classification = "ĐỘC BẢN"
        reason = ""
        
        if not os.path.isdir(item_path):
            results["RÁC"].append(f"{item} (Not a directory)")
            continue
            
        # Check if empty
        has_files = False
        for root, dirs, files in os.walk(item_path):
            if files:
                has_files = True
                break
        
        if not has_files:
            results["RÁC"].append(f"{item} (Empty directory)")
            continue
            
        # Check Garbage names
        if item.endswith(".bak") or "_old" in item.lower() or "temp" in item.lower() or item == "__pycache__":
            results["RÁC"].append(f"{item} (Garbage/Temp pattern)")
            continue

        # Check Name Conflict
        clean_item = item
        if item.startswith("agent-"): clean_item = item[6:].replace("-", "_")
        if item.startswith("skill_"): clean_item = item[6:]
        
        is_conflict = False
        if item in active_names or clean_item in active_names:
            is_conflict = True
            reason = "Name conflict"
            
        # Check ID Conflict
        skill_md = os.path.join(item_path, "SKILL.md")
        sid = get_skill_id(skill_md)
        if sid and sid in active_ids:
            is_conflict = True
            reason += (" & " if reason else "") + f"ID conflict ({sid})"
            
        if is_conflict:
            results["XUNG ĐỘT"].append(f"{item} [{reason}]")
        else:
            results["ĐỘC BẢN"].append(item)

    # Special priority: skill_tucaitien
    print("\n=== [SPECIAL ANALYSIS: skill_tucaitien] ===")
    tucaitien_path = os.path.join(QUARANTINE_DIR, "skill_tucaitien")
    if os.path.exists(tucaitien_path):
        print(f"Found skill_tucaitien in quarantine.")
        sid = get_skill_id(os.path.join(tucaitien_path, "SKILL.md"))
        print(f"ID: {sid}")
        # Find active self-improvement
        active_si = [k for k in active_ids if "self" in k.lower() or "tucaitien" in k.lower() or "improve" in k.lower()]
        print(f"Potential active duplicates: {active_si}")
    else:
        print("skill_tucaitien NOT found in quarantine.")

    # Sort results
    for key in results:
        results[key].sort()

    # Write results to file
    report_path = os.path.join(BASE_DIR, "recon_report_v2.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nScan complete. Found {len(results['ĐỘC BẢN'])} UNIQUE, {len(results['XUNG ĐỘT'])} CONFLICT, {len(results['RÁC'])} TRASH.")
    print(f"Detailed report saved to: {report_path}")
    
    # Print UNIQUE items for report
    print("\n=== [TINH HOA] (UNIQUE ENTITIES) ===")
    for item in results["ĐỘC BẢN"]:
        print(f" - {item}")

if __name__ == "__main__":
    run_recon()

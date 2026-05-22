"""
Script tu dong cap nhat MAP_SKILLS.md voi 134 ky nang Ruflo.
Doc tu registry.json, phan loai va ghi vao MAP_SKILLS.md thua Master.
"""
import json
import re
from pathlib import Path

REGISTRY_PATH = Path(r"d:\Docker\N8N\intelligence\registry.json")
MAP_SKILLS_PATH = Path(r"d:\Docker\N8N\intelligence\MAP_SKILLS.md")

# Tim so thu tu lon nhat hien tai trong MAP_SKILLS.md
def get_last_skill_number(content: str) -> int:
    matches = re.findall(r"#(\d+)\.", content)
    if not matches:
        return 124
    return max(int(m) for m in matches)

def run():
    print("[UPDATE-MAP-SKILLS]: Dang doc registry.json...")

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    with open(MAP_SKILLS_PATH, "r", encoding="utf-8") as f:
        current_content = f.read()

    # Lay so thu tu cuoi cung
    last_num = get_last_skill_number(current_content)
    print(f"[INFO]: So thu tu ky nang hien tai lon nhat: #{last_num}")

    # Chi lay cac ky nang Ruflo (chua co trong MAP_SKILLS)
    ruflo_skills = {
        k: v for k, v in registry["skills"].items()
        if v.get("type") == "assimilated"
        and f"skill_{k}" not in current_content
        and k not in current_content
    }
    print(f"[INFO]: Tim thay {len(ruflo_skills)} ky nang Ruflo chua dang ky vao MAP_SKILLS.")

    if not ruflo_skills:
        print("[DONE]: Tat ca ky nang Ruflo da co trong MAP_SKILLS roi thua Master.")
        return

    # Xay dung section moi
    lines = [
        "\n---\n",
        f"## 🌌 TANG VIII: DI SAN RUFLO ELITE (ASSIMILATED SWARM SKILLS - v35.0)\n",
        "> 134 tuyet ky dong hoa tu Ruflo v3: Swarm Orchestration, CRDT, Neural Training, Consensus, Memory Management...\n",
        "\n"
    ]

    current_num = last_num + 1
    for skill_id, skill_data in sorted(ruflo_skills.items()):
        name = skill_data.get("name", skill_id)
        desc = skill_data.get("description", "Elite skill assimilated from Ruflo.")
        # Cat gon description neu qua dai
        if len(desc) > 100:
            desc = desc[:100] + "..."
        lines.append(f"- **#{current_num}. {skill_id}** [ASSIMILATED]: {desc}\n")
        current_num += 1

    lines.append("\n---\n")
    lines.append("*Sovereign Property of Tong Giam Doc LeeTrung. v35.0 Sovereign Swarm Intelligence.*\n")

    # Xoa footer cu va them vao
    footer_marker = "---\n*Sovereign Property of Master LeeTrung"
    if footer_marker in current_content:
        new_content = current_content[:current_content.rfind("---\n*Sovereign Property of Master LeeTrung")]
    else:
        new_content = current_content.rstrip() + "\n"

    new_content += "".join(lines)

    with open(MAP_SKILLS_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[SUCCESS]: Da ghi danh {len(ruflo_skills)} ky nang Ruflo vao MAP_SKILLS.md thua Master!")
    print(f"[INFO]: So thu tu ky nang moi tu #{last_num + 1} den #{current_num - 1}")

if __name__ == "__main__":
    run()

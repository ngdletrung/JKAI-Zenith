# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

"""
[JKAI SKILL WRAPPER FIX]
Tu dong quet tat ca logic.py trong skills va them module-level wrappers
te ToolRouter co the nhan dien cac ham qua hasattr(module, tool_name).
"""
import os
import re
import sys

SKILLS_ROOT = r"D:\Docker\N8N\intelligence\skills"

def fix_logic_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Kiểm tra xem đã có wrapper chưa
    if "# 🚀 GIAO THỨC NHẤT THỂ HÓA" in content:
        # Xóa các wrapper cũ nếu có để tạo lại cái mới (với **kwargs)
        content = content.split("# 🚀 GIAO THỨC NHẤT THỂ HÓA")[0].strip()

    # Tìm tất cả các method trong class (không phải __init__)
    # Pattern: "    async def func_name(self" hoặc "    def func_name(self"
    methods = re.findall(r'^\s+(?:async )?def ([a-zA-Z_][a-zA-Z0-9_]*)\s*\(self', content, re.MULTILINE)
    methods = [m for m in methods if not m.startswith('_')]

    if not methods:
        return False

    # Tìm tên biến instance (thường là dòng cuối: logic = ClassName())
    instance_match = re.search(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\w+\(\)', content, re.MULTILINE)
    instance_name = instance_match.group(1) if instance_match else None

    # Xây dựng wrapper
    wrappers = ["\n\n# 🚀 GIAO THỨC NHẤT THỂ HÓA: Wrapper cấp module để ToolRouter nhận diện"]

    # Tìm class name
    class_match = re.search(r'^class (\w+)', content, re.MULTILINE)
    class_name = class_match.group(1) if class_match else None

    # Xóa dòng instance cũ nếu có để thay bằng _instance
    if instance_name and instance_name != "_instance":
        # Thay dòng 'logic = ClassName()' bằng '_instance = ClassName()'
        content = re.sub(
            rf'^{re.escape(instance_name)}\s*=\s*(\w+\(\))',
            r'_instance = \1',
            content,
            flags=re.MULTILINE
        )
        wrappers.append(f"# (Đã đổi '{instance_name}' thành '_instance' để tránh xung đột tên)")
    elif not instance_name and class_name:
        content = content.rstrip() + f"\n\n_instance = {class_name}()"

    for method in methods:
        # Kiểm tra xem method là async hay không
        is_async = bool(re.search(rf'async def {re.escape(method)}\s*\(self', content))
        if is_async:
            wrappers.append(f"\nasync def {method}(**kwargs):\n    return await _instance.{method}(**kwargs)")
        else:
            wrappers.append(f"\ndef {method}(**kwargs):\n    return _instance.{method}(**kwargs)")

    new_content = content.rstrip() + "\n" + "\n".join(wrappers) + "\n"

    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write(new_content)

    return True

fixed = 0
skipped = 0
errors = 0

for skill_folder in os.listdir(SKILLS_ROOT):
    skill_path = os.path.join(SKILLS_ROOT, skill_folder)
    if not os.path.isdir(skill_path):
        continue
    logic_file = os.path.join(skill_path, "logic.py")
    if not os.path.exists(logic_file):
        continue
    try:
        result = fix_logic_file(logic_file)
        if result:
            print(f"[FIXED] {logic_file}")
            fixed += 1
        else:
            print(f"[SKIP] {skill_folder} (đã có wrapper hoặc không có method)")
            skipped += 1
    except Exception as e:
        print(f"[ERR] {logic_file}: {e}")
        errors += 1

print(f"\nDone: Fixed={fixed}, Skipped={skipped}, Errors={errors}")

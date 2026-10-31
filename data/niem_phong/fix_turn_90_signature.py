# -*- coding: utf-8 -*-
disc_path = "d:/Docker/JKAI/Thao luan AI/Noi dung thao luan.md"
with open(disc_path, "r", encoding="utf-8") as f:
    text = f.read()

target = """<!-- TURN_END
turn_id: 90
speaker: Opencode"""

sig_replacement = """— Ký tên: Opencode | 29/10/2026 13:09:40 (GMT+7)

<!-- TURN_END
turn_id: 90
speaker: Opencode"""

if target in text and "— Ký tên: Opencode" not in text[text.rfind("turn_id: 90") - 100:]:
    text = text.replace(target, sig_replacement, 1)
    with open(disc_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Inserted signature for Turn 90 successfully!")
else:
    print("Already inserted or target not found!")

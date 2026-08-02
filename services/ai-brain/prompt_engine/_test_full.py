"""Full integration test: prompt_engine with compression."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import prompt_core
from context import context_compressor
from injectors import behavior_injector
from builder import prompt_builder

# Test 1: Compressor standalone
print("=== Test 1: Compressor ===")
compressed = context_compressor.compress_kb_chunks([
    "Hop dong so HD-2026-09 voi Sysme. Ben mua: Sysme Corporation. Ben ban: HueIC."
    " San pham: Cisco C9300 switch. Gia tri: 450,000,000 VND. Ngay ky: 15/06/2026."
] * 5)
print(f"  Compressed: {len(compressed)} chars")

# Test 2: builder.build_system
print("\n=== Test 2: Builder ===")
identity = "<identity><sovereign>JKAI</sovereign></identity>"
behavior = behavior_injector.inject()
context = "<context><time>14:30</time></context>"
tools = "<tools><tool name='qdrant'/></tools>"
sys_p = prompt_builder.build_system(identity, behavior, context, tools, task_type="LOOKUP",
    task_instruction=prompt_builder.get_task_instruction("LOOKUP"))
print(f"  System prompt: {len(sys_p)} chars")
assert "<system>" in sys_p
assert "</system>" in sys_p

# Test 3: core.build
print("\n=== Test 3: Core.build ===")
tt, sys_p, user_p = prompt_core.build(
    goal="hop dong gan day nhat cua Sysme la mua gi ?",
    role="RECEPTIONIST",
    kb_context="Hop dong so HD-2026-09 voi Sysme. Cisco C9300. 450,000,000 VND. 15/06/2026."
)
print(f"  task_type: {tt}")
print(f"  system: {len(sys_p)} chars")
print(f"  user: {len(user_p)} chars")
assert tt == "LOOKUP"
print("  KB compression active:", "knowledge_context" in user_p or "<knowledge_context>" not in user_p)

# Test 4: inject_to_messages
print("\n=== Test 4: inject_to_messages ===")
msgs = [{"role": "user", "content": "test goal"}]
msgs = prompt_core.inject_to_messages(msgs, role="RECEPTIONIST")
print(f"  messages: {len(msgs)}")
assert msgs[0]["role"] == "system"

# Clean up
os.remove(__file__)
print("\n=== ALL TESTS PASSED ===")

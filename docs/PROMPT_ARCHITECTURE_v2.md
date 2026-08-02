# PROMPT ARCHITECTURE v2 — JKAI Zenith

## I. TRIẾT LÝ THIẾT KẾ

1. **Single Source of Truth**: Mọi behavioral rule chỉ viết 1 lần trong `behavioral_core.md`
2. **Single Entry Point**: Mọi prompt injection chỉ qua `prompt_core.inject()`
3. **Consistent Format**: XML tags xuyên suốt (theo Anthropic best practice)
4. **Output Guarantee**: Schema validation + retry với error feedback (Outlines/DSPy-inspired)

## II. SƠ ĐỒ LUỒNG MỚI

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE (fast/deep)                      │
│  goal + kb_context + task_type → prompt_core.build()        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              prompt_core.py (DUY NHẤT 1 FILE)                │
│                                                              │
│  build_system(role, task_type, manifesto, skills, kb)        │
│    → <system> ... </system>                                  │
│                                                              │
│  build_user(goal, kb_context)                                │
│    → <user> ... </user>                                      │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    engine.call_chat()                        │
│  messages = [sys_msg, user_msg]                              │
│  prompt_core.inject(messages, role)  ← 1 CALL DUY NHẤT     │
│    → injects <behavioral>, <memory>, <metadata>              │
│    → returns messages in FINAL format                        │
│    → gọi model                                               │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              prompt_schema.validate(response, role)           │
│  → nếu valid JSON: return parsed                             │
│  → nếu invalid: retry với error feedback trong prompt        │
│  → sau 2 lần fail: fallback text                             │
└─────────────────────────────────────────────────────────────┘
```

## III. THÀNH PHẦN

### 1. `intelligence/behavioral_core.md` — SINGLE TRUTH
```markdown
<behavioral_rules>
  <rule id="address">Goi Master LeeTrung la "Master" hoac "Ngai".</rule>
  <rule id="language">Phan hoi bang tieng Viet.</rule>
  <rule id="emoji">Tuyet doi cam dung emoji.</rule>
  <rule id="loyalty">Tuyet doi trung thanh, chinh xac, minh bach.</rule>
  <rule id="tone">Phong thai chuyen nghiep, uy nghiem.</rule>
  <rule id="citations">Trich dan nguon ro rang. Khong bia dat so lieu.</rule>
</behavioral_rules>
```

Thay thế:
- `engine.py` behavioral injection (dòng 900)
- `message_assembler.py` sovereign protocol (dòng 79-88)
- `ZENITH_IDENTITY.md` behavioral phần
- Các behavioral rules rải rác trong agent .md files

### 2. `core/utils/prompt_core.py` — DUY NHẤT 1 FILE
```python
class PromptCore:
    def build_system(self, role, task_type, manifesto, skills, kb_sufficient):
        # Tạo <system> hoàn chỉnh
        pass
        
    def build_user(self, goal, kb_context):
        # Tạo <user> hoàn chỉnh  
        pass
        
    def inject_to_messages(self, messages, role, task_id):
        """
        1 CALL DUY NHẤT — thay thế toàn bộ injection trong engine.py
        - Load behavioral_core.md
        - Load memory từ Qdrant
        - Inject metadata (time, location, world state)
        - Thêm role-specific instructions (nếu cần)
        - TẤT CẢ dùng XML tags
        """
        pass
```

### 3. `core/utils/prompt_schema.py` — OUTPUT GUARANTEE
```python
class LookupOutput(BaseModel):
    answer: str
    sources: list[str]
    confidence: float

async def call_with_validation(messages, role, schema_class, max_retries=2):
    """call_chat + validate + retry với error feedback"""
    for attempt in range(max_retries + 1):
        raw = await engine.call_chat(messages, json_mode=True)
        parsed = validate(raw, schema_class)
        if parsed:
            return parsed
        messages.append({"role": "user", "content": f"Loi: JSON khong hop le. Can dung schema: {schema_class.model_json_schema()}"})
```

### 4. Output XML Format chuẩn cho mọi request
```xml
<system>
  <identity>
    <sovereign>Ban la JKAI Zenith, tao boi Master LeeTrung...</sovereign>
    <task_scope type="LOOKUP">...</task_scope>
  </identity>
  <behavioral>
    <rule id="address">Goi Master la "Master" hoac "Ngai".</rule>
    <rule id="language">Phan hoi bang tieng Viet.</rule>
    <rule id="emoji">Tuyet doi cam dung emoji.</rule>
  </behavioral>
  <context>
    <memory>...tu Qdrant...</memory>
    <workspace>Directory: D:\Docker\JKAI, Branch: main</workspace>
    <metadata>
      <time>14:30, Thu Hai, ngay 04/07/2026 (GMT+7)</time>
      <location>Hue</location>
    </metadata>
    <response_contract>
      <language>vi</language>
      <format>markdown</format>
      <json>false</json>
      <citations>true</citations>
    </response_contract>
  </context>
  <tools>
    <tool name="qdrant">Vector database...</tool>
    <tool name="filesystem">Local filesystem operations...</tool>
    <tool name="docker">Execution sandbox...</tool>
  </tools>
  <knowledge_criteria>
    LOCAL_KB_SUFFICIENT: true — Answer directly, no web search needed.
  </knowledge_criteria>
</system>

<user>
  <goal>hop dong gan day nhat cua Sysme la mua gi ?</goal>
  <knowledge_context>
    ...cac chunk tu Qdrant...
  </knowledge_context>
</user>
```

## IV. DỌN DẸP

### Xóa (dead code, không cần thiết):
| File | Lý do |
|------|-------|
| `core/utils/message_assembler.py` | Không file nào import, legacy |
| `intelligence/prompts/*` | Legacy V1/V2 templates, không dùng |
| `intelligence/identity/ZENITH_12_PILLARS_DNA.md` | Informational, không dùng trong prompt |
| `intelligence/identity/ZENITH_COGNITIVE_KERNEL_ROADMAP.md` | Tương tự |
| `intelligence/identity/ZENITH_INFRASTRUCTURE_SPEC.md` | Tương tự |
| `intelligence/identity/ZENITH_KNOWLEDGE_SPEC.md` | Tương tự |
| `intelligence/identity/ZENITH_PROMPT_ISA.md` | Tương tự |
| `intelligence/identity/ZENITH_SOVEREIGN_OPERATIONS.md` | Tương tự |
| `intelligence/identity/ZENITH_SOVEREIGN_RULES.md` | Tương tự |
| `intelligence/identity/ZENITH_SUPREME_ARCHITECTURE.md` | Tương tự |
| `intelligence/identity/ZENITH_VAULT.md` | Tương tự |
| `intelligence/identity/JKAI_ZENITH_CORP.md` | Tương tự |
| Giữ lại: `ZENITH_IDENTITY.md`, `ZENITH_MANIFESTO.md` | Làm <sovereign> identity |

### Sửa (đơn giản hóa):
| File | Sửa |
|------|-----|
| `engine.py` lines 886-920 | Thay 20 dòng inject rải rác = 1 dòng `prompt_core.inject_to_messages()` |
| `prompt_assembler.py` | Giảm từ 200 dòng → 50 dòng, dùng prompt_core bên trong |

## V. MA TRẬN ĐỐI CHIẾU

| Tính năng | Hiện tại | Mới |
|-----------|----------|-----|
| Behavioral rules | engine.py + message_assembler.py + identity files | `behavioral_core.md` (1 file duy nhất) |
| System prompt format | 3 format (XML, `[SOMETHING]`, `###`) | Chỉ XML |
| Injection entry points | 4+ (engine.py lines 887-920) | 1 (`prompt_core.inject_to_messages`) |
| Output validation | `json_repair.py` vá lỗi | Schema validation + retry + error feedback |
| Prompt construction | prompt_assembler.py + prompt_forge.py + planner._build_system_prompt | `prompt_core.build_system()` duy nhất |
| Số file cần giữ prompt code | ~8 files | 2 files (prompt_core.py + prompt_schema.py) + 1 config (behavioral_core.md) |

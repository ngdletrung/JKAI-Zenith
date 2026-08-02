import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain"))

import unittest

from prompt_engine.injectors import (
    identity_injector, context_injector, tool_injector,
    IdentityInjector, ContextInjector, ToolInjector,
)
from prompt_engine.injected_reminders import inject_reminder, get_reminder, REMINDERS
from prompt_engine.builder import prompt_builder


class TestIdentityInjector(unittest.TestCase):
    def test_inject(self):
        result = identity_injector.inject()
        self.assertIn("JKAI Zenith", result)
        self.assertIn("Master LeeTrung", result)

    def test_inject_compress(self):
        result = identity_injector.inject(compress=True)
        self.assertIn("JKAI Zenith", result)
        self.assertEqual(result, identity_injector.inject(compress=False))

    def test_fresh_instance(self):
        inj = IdentityInjector()
        result = inj.inject()
        self.assertIn("JKAI Zenith", result)


class TestContextInjector(unittest.TestCase):
    def test_inject_contains_time_and_workspace(self):
        result = context_injector.inject()
        self.assertIn("Context", result)
        self.assertIn("Time", result)
        self.assertIn("Location", result)
        self.assertIn("Workspace", result)

    def test_inject_with_extra(self):
        result = context_injector.inject({"lang": "en", "json_mode": True})
        self.assertIn("Context", result)

    def test_response_contract(self):
        result = context_injector.inject_response_contract({"lang": "en", "json_mode": True})
        self.assertIn("Response Contract", result)
        self.assertIn("Language: en", result)
        self.assertIn("Format: Markdown", result)

    def test_response_contract_defaults(self):
        result = context_injector.inject_response_contract()
        self.assertIn("Language: vi", result)
        self.assertIn("JSON mode: False", result)

    def test_custom_geo(self):
        inj = ContextInjector(root_dir="/custom", geo_location="Saigon")
        result = inj.inject()
        self.assertIn("Saigon", result)
        self.assertIn("/custom", result)


class TestToolInjector(unittest.TestCase):
    def test_inject_empty(self):
        result = tool_injector.inject()
        self.assertEqual(result, "")

    def test_inject_with_skills_dna(self):
        result = tool_injector.inject(skills_dna="skill_foo: test skill")
        self.assertIn("Active Skills", result)
        self.assertIn("skill_foo", result)

    def test_inject_with_extra_tools(self):
        result = tool_injector.inject(extra_tools=[
            {"name": "web_search", "description": "Search the web"},
            {"name": "read_file", "description": "Read a file"},
        ])
        self.assertIn("web_search", result)
        self.assertIn("read_file", result)

    def test_inject_both(self):
        result = tool_injector.inject(
            skills_dna="skill_bar: bar skill",
            extra_tools=[{"name": "tool_baz", "description": "baz"}],
        )
        self.assertIn("Active Skills", result)
        self.assertIn("skill_bar", result)
        self.assertIn("tool_baz", result)


class TestInjectedReminders(unittest.TestCase):
    def test_get_reminder_known_keys(self):
        for key in REMINDERS:
            r = get_reminder(key)
            self.assertNotEqual(r, "")
            self.assertGreater(len(r), 10)

    def test_get_reminder_unknown(self):
        self.assertEqual(get_reminder("nonexistent_key"), "")

    def test_inject_reminder(self):
        base = "## System Prompt\nBe helpful."
        result = inject_reminder(base, "brief_mode")
        self.assertIn(base, result)
        self.assertIn("[BRIEF MODE]", result)

    def test_inject_reminder_unknown(self):
        base = "Hello"
        result = inject_reminder(base, "unknown_key")
        self.assertEqual(result, base)

    def test_reminders_dict_completeness(self):
        expected_keys = {"brief_mode", "model_switched", "container_restart", "non_interactive"}
        self.assertEqual(set(REMINDERS.keys()), expected_keys)


class TestPromptBuilder(unittest.TestCase):
    def test_get_task_instruction_lookup(self):
        instr = prompt_builder.get_task_instruction("LOOKUP")
        self.assertIn("knowledge retriever", instr.lower())

    def test_get_task_instruction_coding(self):
        instr = prompt_builder.get_task_instruction("CODING")
        self.assertIn("software engineer", instr.lower())
        self.assertIn("no placeholders", instr.lower())

    def test_get_task_instruction_analysis(self):
        instr = prompt_builder.get_task_instruction("ANALYSIS")
        self.assertIn("systems analyst", instr.lower())

    def test_get_task_instruction_default(self):
        instr = prompt_builder.get_task_instruction("UNKNOWN_TYPE")
        self.assertIn("JKAI Zenith", instr)

    def test_get_critic_instruction_lookup(self):
        crit = prompt_builder.get_critic_instruction("LOOKUP")
        self.assertIn("Critic Rules", crit)
        self.assertIn("hallucinations", crit.lower())

    def test_get_critic_instruction_coding(self):
        crit = prompt_builder.get_critic_instruction("CODING")
        self.assertIn("Critic Rules", crit)
        self.assertIn("security flaws", crit.lower())

    def test_get_critic_instruction_analysis(self):
        crit = prompt_builder.get_critic_instruction("ANALYSIS")
        self.assertIn("Critic Rules", crit)

    def test_get_critic_instruction_default(self):
        crit = prompt_builder.get_critic_instruction("UNKNOWN")
        self.assertIn("Critic Rules", crit)

    def test_build_user_simple(self):
        result = prompt_builder.build_user("Test goal")
        self.assertIn("## Goal", result)
        self.assertIn("Test goal", result)

    def test_build_user_with_kb(self):
        result = prompt_builder.build_user("Goal", kb_context="Some knowledge base content here")
        self.assertIn("## Goal", result)
        self.assertIn("## Knowledge Context", result)
        self.assertIn("Some knowledge base", result)

    def test_build_user_kb_truncation(self):
        long_kb = "A" * 5000
        result = prompt_builder.build_user("Goal", kb_context=long_kb, max_kb_chars=100)
        self.assertLess(len(result), 200)


if __name__ == "__main__":
    unittest.main()

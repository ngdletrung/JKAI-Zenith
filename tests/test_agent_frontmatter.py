import os
import sys
import unittest
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "intelligence", "agents")
REQUIRED_FIELDS = ["name", "type", "description", "capabilities", "priority"]


def parse_frontmatter(content: str):
    if not content.startswith("---\r\n") and not content.startswith("---\n"):
        return None, content
    delimiter = "---\r\n" if content.startswith("---\r\n") else "---\n"
    parts = content.split(delimiter, 2)
    if len(parts) < 3:
        return None, content
    yaml_text = parts[1]
    body = parts[2]
    try:
        meta = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        meta = None
    return meta, body


class TestAgentFrontmatter(unittest.TestCase):
    def test_all_agent_files_have_frontmatter(self):
        agent_files = glob.glob(os.path.join(AGENTS_DIR, "agent_*.md"))
        self.assertTrue(agent_files, "No agent files found")
        missing = []
        for f in agent_files:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            meta, _ = parse_frontmatter(content)
            if meta is None:
                missing.append(os.path.basename(f))
        self.assertEqual(missing, [], f"Files missing YAML frontmatter: {missing}")

    def test_required_fields_present(self):
        agent_files = glob.glob(os.path.join(AGENTS_DIR, "agent_*.md"))
        bad = []
        for f in agent_files:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            meta, _ = parse_frontmatter(content)
            if meta is None:
                bad.append(f"{os.path.basename(f)}: no frontmatter")
                continue
            for field in REQUIRED_FIELDS:
                if field not in meta:
                    bad.append(f"{os.path.basename(f)}: missing '{field}'")
        self.assertEqual(bad, [], "Invalid frontmatter:\n" + "\n".join(bad))

    def test_capabilities_is_list(self):
        agent_files = glob.glob(os.path.join(AGENTS_DIR, "agent_*.md"))
        bad = []
        for f in agent_files:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            meta, _ = parse_frontmatter(content)
            if meta is None:
                continue
            caps = meta.get("capabilities", [])
            if not isinstance(caps, list) or not caps:
                bad.append(f"{os.path.basename(f)}: capabilities not a non-empty list")
        self.assertEqual(bad, [], "Invalid capabilities:\n" + "\n".join(bad))

    def test_agent_count(self):
        agent_files = glob.glob(os.path.join(AGENTS_DIR, "agent_*.md"))
        self.assertGreaterEqual(len(agent_files), 18)


if __name__ == "__main__":
    unittest.main()

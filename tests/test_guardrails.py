import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
import tempfile
import json

from core.guardrails.terminal_enforcer import check_command, check_directory


class TestCheckCommand(unittest.TestCase):
    def test_allowed_command_passes(self):
        allowed, reason = check_command("npm install")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_allowed_dir_passes(self):
        allowed, reason = check_command("dir")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_blocked_command_fails(self):
        allowed, reason = check_command("sudo rm -rf /")
        self.assertFalse(allowed)
        self.assertIn("blocked", reason.lower())

    def test_shutdown_blocked(self):
        allowed, reason = check_command("shutdown -s -t 0")
        self.assertFalse(allowed)
        self.assertIn("blocked", reason.lower())

    def test_git_allowed(self):
        allowed, reason = check_command("git status")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_chmod_777_blocked(self):
        allowed, reason = check_command("chmod 777 /etc/passwd")
        self.assertFalse(allowed)
        self.assertIn("blocked", reason.lower())


class TestCheckDirectory(unittest.TestCase):
    def test_allowed_src_path(self):
        allowed, reason = check_directory("./src/main.py")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_allowed_tests_path(self):
        allowed, reason = check_directory("./tests/test_main.py")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_allowed_core_util_path(self):
        allowed, reason = check_directory("./core/utils/engine.py")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_absolute_allowed_path(self):
        allowed, reason = check_directory("D:\\Docker\\JKAI\\src\\main.py")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_blocked_dotenv_path(self):
        allowed, reason = check_directory("./config/.env.production")
        self.assertFalse(allowed)
        self.assertIn("blocked", reason.lower())

    def test_blocked_pem_path(self):
        allowed, reason = check_directory("./keys/private.pem")
        self.assertFalse(allowed)
        self.assertIn("blocked", reason.lower())

    def test_blocked_secrets_path(self):
        allowed, reason = check_directory("./config/secrets/credentials.json")
        self.assertFalse(allowed)
        self.assertIn("blocked", reason.lower())


class TestCheckCommandNoGuardrails(unittest.TestCase):
    def setUp(self):
        from core.guardrails.rules_loader import invalidate_cache
        invalidate_cache()

    def tearDown(self):
        from core.guardrails.rules_loader import invalidate_cache
        invalidate_cache()

    def test_empty_guardrails_allows_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_rules = os.path.join(tmpdir, ".jkairules.json")
            with open(fake_rules, "w") as f:
                json.dump({"infrastructure_guardrails": {}}, f)
            from core.guardrails.rules_loader import invalidate_cache, load_rules
            invalidate_cache()
            load_rules(fake_rules)
            allowed, reason = check_command("any_command_at_all")
            self.assertTrue(allowed)
            self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()

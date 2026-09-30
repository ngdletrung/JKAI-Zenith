# -*- coding: utf-8 -*-
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.kernel.dynamic_skill_creator import DynamicSkillCreator, dynamic_skill_creator


class TestDynamicSkillCreator(unittest.TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix="jkai_skill_gov_")
        self.skills_dir = os.path.join(self.tmp_root, "skills")
        self.cands_dir = os.path.join(self.tmp_root, "candidates")
        self.ckpts_dir = os.path.join(self.tmp_root, "checkpoints")
        self.creator = DynamicSkillCreator(
            skills_root=self.skills_dir,
            candidates_dir=self.cands_dir,
            checkpoints_dir=self.ckpts_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_create_dynamic_skill(self):
        sample_code = (
            "# Dynamic Skill Logic\n"
            "def run_custom_audit(data=None):\n"
            "    return {'status': 'success', 'audit': 'Passed dynamic code audit'}\n"
        )
        res = self.creator.create_skill(
            skill_name="test_dynamic_audit",
            description="Thao tác kiểm toán động",
            python_code=sample_code,
            category="TEST",
            approved=True,
            approver_id="master_admin",
            require_hot_reload=False,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["skill_name"], "test_dynamic_audit")
        self.assertTrue(os.path.exists(res["skill_dir"]))
        self.assertIn("receipt", res)
        self.assertTrue(res["receipt"]["receipt_id"].startswith("rcpt_"))

    def test_proposal_only_does_not_write_production_logic_py(self):
        code = "def calc_metric(x):\n    return x * 2\n"
        res = self.creator.create_skill(
            skill_name="staged_metric",
            description="Chỉ tạo đề xuất ứng viên",
            python_code=code,
            category="CUSTOM",
            proposal_only=True,
        )
        self.assertEqual(res["status"], "proposed")
        self.assertTrue(os.path.exists(res["candidate_file"]))
        target_logic = os.path.join(self.skills_dir, "CUSTOM", "staged_metric", "logic.py")
        self.assertFalse(os.path.exists(target_logic))

    def test_blocks_path_traversal_in_name_and_category(self):
        code = "def safe_fn():\n    return 1\n"
        res1 = self.creator.create_skill(
            skill_name="../../etc/passwd",
            description="Traversal attempt",
            python_code=code,
            category="CUSTOM",
            approved=True,
        )
        self.assertEqual(res1["status"], "rejected")
        self.assertEqual(res1["stage"], "PATH_VALIDATION")

        res2 = self.creator.create_skill(
            skill_name="normal_skill",
            description="Traversal category",
            python_code=code,
            category="../OUTSIDE",
            approved=True,
        )
        self.assertEqual(res2["status"], "rejected")
        self.assertEqual(res2["stage"], "PATH_VALIDATION")

    def test_blocks_dangerous_ast_imports_and_calls(self):
        dangerous_samples = [
            "import subprocess\ndef bad():\n    subprocess.run(['ls'])\n",
            "import os\ndef bad():\n    os.system('rm -rf /')\n",
            "def bad(x):\n    return eval(x)\n",
            "def bad(x):\n    exec(x)\n",
            "import shutil\ndef bad():\n    shutil.rmtree('/tmp/a')\n",
        ]
        for sample in dangerous_samples:
            res = self.creator.create_skill(
                skill_name="malicious_skill",
                description="Test AST block",
                python_code=sample,
                category="SECURITY",
                approved=True,
            )
            self.assertEqual(res["status"], "rejected")
            self.assertEqual(res["stage"], "AST_ALLOWLIST")

    def test_blocks_secrets_and_prompt_injection_via_state_sanitizer(self):
        leaked_code = (
            "def leak_fn():\n"
            "    key = 'sk-" + "1234567890abcdefghijklmnopqrstuvwx'\n"
            "    return key\n"
        )
        res = self.creator.create_skill(
            skill_name="secret_leak_skill",
            description="Contains OpenAI key",
            python_code=leaked_code,
            category="CUSTOM",
            approved=True,
        )
        self.assertEqual(res["status"], "rejected")
        self.assertEqual(res["stage"], "STATE_SANITIZER")

    def test_blocks_failed_regression_100_gate(self):
        code = "def compute(a):\n    return a - 1\n"
        res = self.creator.create_skill(
            skill_name="reg_fail_skill",
            description="Regression fails",
            python_code=code,
            category="CUSTOM",
            approved=True,
            regression_validator=lambda src: False,
        )
        self.assertEqual(res["status"], "rejected")
        self.assertEqual(res["stage"], "REGRESSION_100")

    def test_production_requires_explicit_approval_and_blocks_llm_self_approval(self):
        code = "def prod_fn():\n    return 'ok'\n"
        old_env = os.environ.get("JKAI_ENV")
        old_sec = os.environ.get("JKAI_GOVERNANCE_SECRET")
        try:
            os.environ["JKAI_ENV"] = "production"
            os.environ["JKAI_GOVERNANCE_SECRET"] = "prod_test_secret_key_2026_sovereign"
            # Missing regression_validator in production -> rejected at REGRESSION_100
            res_no_reg = self.creator.create_skill(
                skill_name="prod_skill",
                description="Missing regression validator in prod",
                python_code=code,
                category="CUSTOM",
                approved=True,
                approver_id="master_admin",
            )
            self.assertEqual(res_no_reg["status"], "rejected")
            self.assertEqual(res_no_reg["stage"], "REGRESSION_100")

            # Missing approval in production -> rejected at APPROVAL_GATE
            res_unapproved = self.creator.create_skill(
                skill_name="prod_skill",
                description="Unapproved in prod",
                python_code=code,
                category="CUSTOM",
                regression_validator=lambda src: True,
            )
            self.assertEqual(res_unapproved["status"], "rejected")
            self.assertEqual(res_unapproved["stage"], "APPROVAL_GATE")

            # LLM self-approval -> rejected
            res_llm = self.creator.create_skill(
                skill_name="prod_skill",
                description="LLM self-approved",
                python_code=code,
                category="CUSTOM",
                approved=True,
                approver_id="llm",
                regression_validator=lambda src: True,
            )
            self.assertEqual(res_llm["status"], "rejected")
            self.assertEqual(res_llm["stage"], "APPROVAL_GATE")
        finally:
            if old_env is None:
                os.environ.pop("JKAI_ENV", None)
            else:
                os.environ["JKAI_ENV"] = old_env
            if old_sec is None:
                os.environ.pop("JKAI_GOVERNANCE_SECRET", None)
            else:
                os.environ["JKAI_GOVERNANCE_SECRET"] = old_sec

    def test_restore_drill_checkpoint_partial_crash_rollback_and_sha256_verify(self):
        # 1. Publish v1.0.0 baseline skill
        v1_code = "def execute_v1():\n    return 'version_1_stable'\n"
        res_v1 = self.creator.create_skill(
            skill_name="critical_router_skill",
            description="Baseline v1 skill",
            python_code=v1_code,
            category="CORE",
            version="1.0.0",
            approved=True,
            approver_id="master_admin",
            require_hot_reload=False,
        )
        self.assertEqual(res_v1["status"], "success")
        logic_path = os.path.join(res_v1["skill_dir"], "logic.py")
        v1_sha256 = hashlib.sha256(open(logic_path, "rb").read()).hexdigest()
        self.assertEqual(v1_sha256, res_v1["code_sha256"])

        # 2. Attempt v2.0.0 upgrade with simulated partial publish crash
        v2_code = "def execute_v2():\n    return 'version_2_broken_mid_write'\n"
        res_v2 = self.creator.create_skill(
            skill_name="critical_router_skill",
            description="Mutated v2 skill",
            python_code=v2_code,
            category="CORE",
            version="2.0.0",
            approved=True,
            approver_id="master_admin",
            require_hot_reload=False,
            _simulate_partial_publish_crash=True,
        )
        self.assertEqual(res_v2["status"], "rolled_back_on_error")
        self.assertEqual(res_v2["stage"], "ATOMIC_PUBLISH")
        rb = res_v2["rollback"]
        self.assertEqual(rb["status"], "rolled_back")
        self.assertEqual(rb["restored_logic_sha256"], v1_sha256)
        self.assertEqual(rb["expected_logic_sha256"], v1_sha256)
        self.assertIn("hmac_signature", rb["receipt"])

        # 3. Verify file on disk has exact v1 SHA-256 and SKILL.md is also restored to v1.0.0
        disk_sha256 = hashlib.sha256(open(logic_path, "rb").read()).hexdigest()
        self.assertEqual(disk_sha256, v1_sha256)
        md_text = open(os.path.join(res_v1["skill_dir"], "SKILL.md"), "r", encoding="utf-8").read()
        self.assertIn("version: 1.0.0", md_text)

    def test_hot_reload_failure_triggers_rollback_when_strict(self):
        v1_code = "def stable_fn():\n    return 'v1'\n"
        old_url = os.environ.get("EXECUTOR_URL")
        try:
            os.environ["EXECUTOR_URL"] = "http://127.0.0.1:59999"
            res = self.creator.create_skill(
                skill_name="strict_reload_skill",
                description="Requires hot reload",
                python_code=v1_code,
                category="CUSTOM",
                approved=True,
                approver_id="master_admin",
                require_hot_reload=True,
            )
            self.assertEqual(res["status"], "rolled_back_on_error")
            self.assertEqual(res["stage"], "HOT_RELOAD")
            logic_path = os.path.join(self.skills_dir, "CUSTOM", "strict_reload_skill", "logic.py")
            self.assertFalse(os.path.exists(logic_path))
        finally:
            if old_url is None:
                os.environ.pop("EXECUTOR_URL", None)
            else:
                os.environ["EXECUTOR_URL"] = old_url

    def test_other_callers_cannot_bypass_skill_governance(self):
        import asyncio
        from pathlib import Path
        from core.kernel.autonomous_repair_loop import autonomous_repair_loop
        from core.utils.sandbox_deploy_gate import promote_candidate_to_production

        # 1. AutonomousRepairLoop must block direct LLM self-healing of intelligence/skills/.../logic.py
        fake_skill_dir = Path(self.tmp_root) / "intelligence" / "skills" / "CUSTOM" / "protected_skill"
        fake_skill_dir.mkdir(parents=True, exist_ok=True)
        fake_logic = fake_skill_dir / "logic.py"
        fake_logic.write_text("def broken():\n    return 1/0\n", encoding="utf-8")

        res_repair = asyncio.run(autonomous_repair_loop.execute_and_self_heal(str(fake_logic), task_id="t_bypass"))
        self.assertEqual(res_repair["status"], "error")
        self.assertIn("GOVERNANCE_BLOCKED", res_repair["msg"])

        # 2. promote_candidate_to_production must block dangerous AST or unapproved promotion
        cand_file = Path(self.tmp_root) / "logic_candidate.py"
        prod_file = Path(self.tmp_root) / "logic_prod.py"
        cand_file.write_text("import subprocess\ndef evil():\n    subprocess.run(['whoami'])\n", encoding="utf-8")
        ok_ast, msg_ast = promote_candidate_to_production(cand_file, prod_file, invalidate_cache=False, approved=True)
        self.assertFalse(ok_ast)
        self.assertIn("GOVERNANCE_AST_REJECTED", msg_ast)

        cand_file.write_text("def clean_fn():\n    return 42\n", encoding="utf-8")
        ok_unapp, msg_unapp = promote_candidate_to_production(
            cand_file, prod_file, invalidate_cache=False, approved=False
        )
        self.assertFalse(ok_unapp)
        self.assertIn("GOVERNANCE_APPROVAL_REQUIRED", msg_unapp)

    def test_sandbox_capability_blocks_network_and_spawn_and_fs_escape(self):
        # 1. Network access attempt
        net_code = "import socket\ndef try_net():\n    s = socket.socket()\n    return 'connected'\n"
        ok_net, rep_net = DynamicSkillCreator.verify_skill_in_sandbox(net_code)
        self.assertFalse(ok_net)
        self.assertIn("SANDBOX_SECURITY_VIOLATION", rep_net["reason"])
        self.assertIn("Network access is forbidden", rep_net["reason"])

        # 2. Process spawn attempt
        spawn_code = "import subprocess\ndef try_spawn():\n    p = subprocess.Popen(['echo', 'hi'])\n    return 'spawned'\n"
        ok_spawn, rep_spawn = DynamicSkillCreator.verify_skill_in_sandbox(spawn_code)
        self.assertFalse(ok_spawn)
        self.assertIn("SANDBOX_SECURITY_VIOLATION", rep_spawn["reason"])
        self.assertIn("Process spawning is forbidden", rep_spawn["reason"])

        # 3. External write attempt
        fs_code = "def try_leak():\n    with open('../escape_leak.txt', 'w') as f:\n        f.write('pwned')\n    return 'leaked'\n"
        ok_fs, rep_fs = DynamicSkillCreator.verify_skill_in_sandbox(fs_code)
        self.assertFalse(ok_fs)
        self.assertIn("SANDBOX_SECURITY_VIOLATION", rep_fs["reason"])
        self.assertIn("Write outside sandbox", rep_fs["reason"])

    def test_rollback_hmac_tampering_and_symlink_defense(self):
        # Create a skill and its checkpoint
        v1_code = "def prod_v1():\n    return 100\n"
        res_v1 = self.creator.create_skill(
            skill_name="tamper_defense_skill",
            description="Test tamper rollback",
            python_code=v1_code,
            category="CUSTOM",
            approved=True,
            approver_id="master_admin",
            require_hot_reload=False,
        )
        self.assertEqual(res_v1["status"], "success")

        # Create checkpoint
        skill_dir = res_v1["skill_dir"]
        ckpt = self.creator.create_checkpoint("tamper_defense_skill", "CUSTOM", skill_dir)
        ckpt_file = ckpt["checkpoint_file"]
        self.assertTrue(os.path.exists(ckpt_file))

        # Tamper the checkpoint content
        with open(ckpt_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["logic_py_content"] = "def evil_injected():\n    return 666\n"
        with open(ckpt_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Rollback must be rejected due to tampered HMAC
        res_tampered = self.creator.rollback_skill(ckpt_file)
        self.assertEqual(res_tampered["status"], "error")
        self.assertIn("CORRUPT_OR_TAMPERED_CHECKPOINT_HMAC", res_tampered["reason"])


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""
tests/test_action_confirmation_runtime_gate.py
==============================================
Kiểm thử chuyên sâu Cổng Phê Duyệt An Toàn (Action Confirmation Gate)
được nối trực tiếp tại Execution Boundary của SemanticBrowserActuator.
Chứng minh các cơ chế:
1. Mutation không approval => DENIED (Fail-Closed, sinh Confirmation Card).
2. Approval hợp lệ => SUCCESS.
3. Replay token lần hai => DENIED (One-Time Token Enforcement).
4. Stale snapshot version mismatch => DENIED (TOCTOU Version Gate).
5. TOCTOU State Drift (DOM thay đổi trước khi click) => DENIED.
"""

import os
import sys
import asyncio
import pytest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "services" / "ai-browser"))

from semantic_actuator import SemanticBrowserActuator, ActRequest
from visual_aci_gateway import VisualACIGateway


@pytest.fixture(autouse=True)
def setup_env():
    # Đảm bảo gate luôn bật (không cho phép unsafe mutation)
    os.environ["JKAI_ALLOW_UNSAFE_MUTATION"] = "0"
    os.environ["JKAI_BROWSER_HEADLESS"] = "true"
    VisualACIGateway.reset_consumed_tokens()
    yield
    VisualACIGateway.reset_consumed_tokens()


@pytest.mark.asyncio
async def test_01_mutation_without_approval_is_denied():
    """Mutation action (click on button) without approval token MUST be rejected and return Confirmation Card."""
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        # Load fixture có nút mutation
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)

        # Tìm nút có rủi ro (click trên button)
        mutate_btn = next((e for e in obs.elements if "mutate" in e.name.lower() or "button" in e.tag), None)
        assert mutate_btn is not None, "Button must exist in fixture"

        # Gửi hành động KHÔNG có token
        req = ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            expected_snapshot_version=obs.snapshot_version
        )
        res = await actuator.act(page, req)

        # Bắt buộc bị từ chối và sinh thẻ xác nhận
        assert res.status == "rejected"
        assert res.healing_tier_used == "MUTATION_GATE_BLOCKED"
        assert res.confirmation_card is not None
        assert "action_id" in res.confirmation_card
        assert "approval_token" in res.confirmation_card
        assert res.confirmation_card["approval_status"] == "PENDING_USER_APPROVAL"
    finally:
        await actuator.close_session()


@pytest.mark.asyncio
async def test_02_mutation_with_valid_approval_token_succeeds():
    """Mutation action with valid approval token must pass the gate and execute."""
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)
        mutate_btn = next((e for e in obs.elements if "mutate" in e.name.lower() or "button" in e.tag), None)
        assert mutate_btn is not None

        # Bước 1: Gửi yêu cầu để nhận confirmation card
        req1 = ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            expected_snapshot_version=obs.snapshot_version
        )
        res1 = await actuator.act(page, req1)
        assert res1.status == "rejected"
        card = res1.confirmation_card

        # Bước 2: Gửi lại hành động với approval_token và action_id hợp lệ
        req2 = ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            action_id=card["action_id"],
            approval_token=card["approval_token"],
            expected_snapshot_version=obs.snapshot_version
        )
        res2 = await actuator.act(page, req2)
        assert res2.status == "success"
        assert res2.healing_tier_used == "TIER_0_DIRECT"
    finally:
        await actuator.close_session()


@pytest.mark.asyncio
async def test_03_replay_attack_with_same_token_is_denied():
    """Using the same approval token a second time MUST be rejected as an ALREADY_CONSUMED replay attack."""
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)
        mutate_btn = next((e for e in obs.elements if "mutate" in e.name.lower() or "button" in e.tag), None)

        # Lần 1: Nhận card
        res1 = await actuator.act(page, ActRequest(action="click", target=mutate_btn.ref_id, expected_snapshot_version=obs.snapshot_version))
        card = res1.confirmation_card

        # Lần 2: Sử dụng token hợp lệ -> PASS
        res2 = await actuator.act(page, ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            action_id=card["action_id"],
            approval_token=card["approval_token"],
            expected_snapshot_version=obs.snapshot_version
        ))
        assert res2.status == "success"

        # Lần 3: REPLAY ATTACK (Dùng lại chính token đó) -> BẮT BUỘC BỊ TỪ CHỐI
        res3 = await actuator.act(page, ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            action_id=card["action_id"],
            approval_token=card["approval_token"],
            expected_snapshot_version=obs.snapshot_version
        ))
        assert res3.status == "rejected"
        assert res3.healing_tier_used == "MUTATION_GATE_REJECTED"
        assert "APPROVAL_TOKEN_ALREADY_CONSUMED" in res3.msg
    finally:
        await actuator.close_session()


@pytest.mark.asyncio
async def test_04_stale_snapshot_version_mismatch_is_rejected():
    """Requesting an action with an outdated snapshot version MUST fail-closed."""
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)
        mutate_btn = next((e for e in obs.elements if "mutate" in e.name.lower() or "button" in e.tag), None)

        # Gửi phiên bản snapshot cũ (v999 thay vì obs.snapshot_version)
        req = ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            expected_snapshot_version=999
        )
        res = await actuator.act(page, req)
        assert res.status == "rejected"
        assert res.healing_tier_used == "STALE_SNAPSHOT_GUARD"
        assert "STALE_SNAPSHOT_REJECTED" in res.msg
    finally:
        await actuator.close_session()


@pytest.mark.asyncio
async def test_05_toctou_state_drift_is_rejected():
    """If the DOM content changes after card generation, execution MUST be blocked by TOCTOU state drift guard."""
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)
        mutate_btn = next((e for e in obs.elements if "mutate" in e.name.lower() or "button" in e.tag), None)

        # Tạo card
        res1 = await actuator.act(page, ActRequest(action="click", target=mutate_btn.ref_id, expected_snapshot_version=obs.snapshot_version))
        card = res1.confirmation_card

        # Làm trôi DOM nhân tạo (thay đổi nội dung body trước khi click)
        await page.evaluate("document.body.innerHTML += '<div>DRIFTED_CONTENT_INJECTED</div>';")

        # Gửi phê duyệt với token cũ nhưng DOM đã bị drift
        res2 = await actuator.act(page, ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            action_id=card["action_id"],
            approval_token=card["approval_token"],
            expected_snapshot_version=obs.snapshot_version
        ))
        assert res2.status == "rejected"
        assert res2.healing_tier_used == "MUTATION_GATE_REJECTED"
        assert "TOCTOU_STATE_DRIFT" in res2.msg
    finally:
        await actuator.close_session()


@pytest.mark.asyncio
async def test_06_unauthorized_skip_mutation_gate_is_rejected():
    """When JKAI_ALLOW_UNSAFE_MUTATION=0, attempting skip_mutation_gate=True MUST be rejected (P0 Bypass Fix)."""
    os.environ["JKAI_ALLOW_UNSAFE_MUTATION"] = "0"
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)
        mutate_btn = next((e for e in obs.elements if "mutate" in e.name.lower() or "button" in e.tag), None)

        req = ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            skip_mutation_gate=True,  # Cố tình bypass
            expected_snapshot_version=obs.snapshot_version
        )
        res = await actuator.act(page, req)
        assert res.status == "rejected"
        assert res.healing_tier_used == "MUTATION_GATE_BLOCKED"
        assert "POLICY_VIOLATION_GATE_BYPASS_REJECTED" in res.msg
    finally:
        await actuator.close_session()


@pytest.mark.asyncio
async def test_07_unknown_action_id_is_rejected():
    """Passing an un-registered / fabricated action_id MUST be rejected (P1 Provenance Fix)."""
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)
        mutate_btn = next((e for e in obs.elements if "mutate" in e.name.lower() or "button" in e.tag), None)

        req = ActRequest(
            action="click",
            target=mutate_btn.ref_id,
            action_id="act_fabricated_fake_id_12345",
            approval_token="fake_token_hex_value",
            expected_snapshot_version=obs.snapshot_version
        )
        res = await actuator.act(page, req)
        assert res.status == "rejected"
        assert res.healing_tier_used == "MUTATION_GATE_REJECTED"
        assert "UNKNOWN_ACTION_ID" in res.msg
    finally:
        await actuator.close_session()


@pytest.mark.asyncio
async def test_08_cross_action_token_binding_mismatch_is_rejected():
    """Using card A's token for request B (different target/action) MUST be rejected by Request-Card Binding Guard."""
    actuator = SemanticBrowserActuator()
    page = await actuator.get_or_create_page()
    try:
        fixture_path = WORKSPACE_ROOT / "tests" / "sandbox" / "fixture.html"
        await page.goto(fixture_path.as_uri(), wait_until="domcontentloaded")
        obs = await actuator.observe(page)
        buttons = [e for e in obs.elements if "button" in e.tag or "button" in e.role]
        assert len(buttons) >= 2, "At least 2 buttons needed for cross-action binding test"
        btn_a, btn_b = buttons[0], buttons[1]

        # 1. Phát hành Card A cho btn_a
        req_a = ActRequest(action="click", target=btn_a.ref_id, expected_snapshot_version=obs.snapshot_version)
        res_a = await actuator.act(page, req_a)
        assert res_a.status == "rejected"
        card_a = res_a.confirmation_card

        # 2. CONFUSED DEPUTY ATTACK: Dùng card_a (action_id & token của btn_a) để gọi lệnh trên btn_b!
        req_b = ActRequest(
            action="click",
            target=btn_b.ref_id,  # Target khác với card_a!
            action_id=card_a["action_id"],
            approval_token=card_a["approval_token"],
            expected_snapshot_version=obs.snapshot_version
        )
        res_b = await actuator.act(page, req_b)

        # BẮT BUỘC BỊ TỪ CHỐI BỞI REQUEST-CARD BINDING
        assert res_b.status == "rejected"
        assert res_b.healing_tier_used == "MUTATION_GATE_REJECTED"
        assert "CARD_TARGET_REF_MISMATCH" in res_b.msg or "CARD_TARGET_MISMATCH" in res_b.msg

        # 3. Chứng minh token của Card A KHÔNG bị consume oan bởi request B sai ngữ cảnh!
        # Dùng lại token card_a đúng ngữ cảnh cho btn_a -> PHẢI THÀNH CÔNG!
        req_a_valid = ActRequest(
            action="click",
            target=btn_a.ref_id,  # Đúng target của card_a
            action_id=card_a["action_id"],
            approval_token=card_a["approval_token"],
            expected_snapshot_version=obs.snapshot_version
        )
        res_a_valid = await actuator.act(page, req_a_valid)
        assert res_a_valid.status == "success"
    finally:
        await actuator.close_session()



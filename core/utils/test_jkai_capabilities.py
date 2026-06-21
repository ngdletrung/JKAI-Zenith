from core.os.intent_taxonomy import OSIntent, classify_os_intent
from core.utils.jkai_capabilities import goal_is_capabilities_inquiry, build_capabilities_report
from core.utils.project_workspace import workspace_task_mode


def test_capabilities_inquiry_detected():
    g = "Hãy liệt kê các tính năng của chính mình xem ?"
    assert goal_is_capabilities_inquiry(g)
    assert classify_os_intent(g, {}) == OSIntent.CAPABILITIES


def test_xem_at_end_not_audit_mode():
    g = "Hãy liệt kê các tính năng của chính mình xem ?"
    assert workspace_task_mode(g) == "audit"
    assert classify_os_intent(g, {}) != OSIntent.AUDIT


def test_report_has_sections():
    text = build_capabilities_report()
    assert "AI OS" in text
    assert "DEEP" in text
    assert "/help" in text

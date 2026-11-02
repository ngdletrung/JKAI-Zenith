# -*- coding: utf-8 -*-
"""
services/ai_desktop/__init__.py
JKAI Zenith Desktop OS Actuator (M5) Package.
"""
from .threat_model import DesktopSecurityGate, DesktopSecurityViolation
from .app_policy import AppRule, DesktopActionPolicy, DesktopPolicyError, get_policy
from .mouse_engine import SmoothMouseEngine, MockDesktopMouseAdapter, NativeWindowsMouseAdapter, DesktopMouseAdapterProtocol
from .window_inspector import WindowElementRef, MockWindowInspector, NativeWindowInspector, WindowInspectorProtocol
from .watchdog import DesktopWatchdog, DesktopEmergencyStop
from .desktop_actuator import DesktopOSActuator, DesktopActRequest, DesktopActResponse
from .sandbox_fixture import NotepadSandboxSession
from .window_message_adapter import WindowMessageAdapter, WindowMessageReceipt
from .uia_tree_inspector import UIATreeInspector, UIAElementNode, UIATreeSnapshot
from .gateway_verifier import GatewayObservationVerifier
from .isolated_desktop import IsolatedDesktopSandbox
from .visual_engine import VisualWindowCaptureEngine, WindowVisualSnapshot

__all__ = [
    "DesktopSecurityGate",
    "DesktopSecurityViolation",
    "AppRule",
    "DesktopActionPolicy",
    "DesktopPolicyError",
    "get_policy",
    "SmoothMouseEngine",
    "MockDesktopMouseAdapter",
    "NativeWindowsMouseAdapter",
    "DesktopMouseAdapterProtocol",
    "WindowElementRef",
    "MockWindowInspector",
    "NativeWindowInspector",
    "WindowInspectorProtocol",
    "DesktopWatchdog",
    "DesktopEmergencyStop",
    "DesktopOSActuator",
    "DesktopActRequest",
    "DesktopActResponse",
    "NotepadSandboxSession",
    "WindowMessageAdapter",
    "WindowMessageReceipt",
    "UIATreeInspector",
    "UIAElementNode",
    "UIATreeSnapshot",
    "GatewayObservationVerifier",
    "IsolatedDesktopSandbox",
    "VisualWindowCaptureEngine",
    "WindowVisualSnapshot",
]

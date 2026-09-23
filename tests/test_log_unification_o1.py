# -*- coding: utf-8 -*-
"""
tests/test_log_unification_o1.py
Unit tests verifying P2-O1 (Log System Unification).

Verifies that:
1. ObservabilityEngine TelemetrySpan completion directly triggers StructuredLogger JSON emission.
2. log_engine.publish_mission_log emits structured JSON events for audit/critical tags.
3. No redundant 4th log system is introduced; all logs converge on StructuredLogger schema.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from core.telemetry.observability_engine import RealTimeObservabilityEngine
from core.utils.log_engine import LogEngine



class TestLogUnificationO1:

    def test_observability_span_bridges_to_structured_logger(self):
        """Khi TelemetrySpan hoàn tất, sự kiện phải được phát sang StructuredLogger."""
        engine = RealTimeObservabilityEngine()
        span = engine.start_span(
            name="test_tool_execution",
            trace_id="tr_test_12345",
            attributes={"tool_name": "write_to_file", "authority_decision": "ALLOW"}
        )

        with patch("core.observability.structured_logger.log_structured_event") as mock_log:
            span.finish(status="OK")
            engine.record_span(span)

            assert mock_log.called
            call_kwargs = mock_log.call_args.kwargs
            assert "test_tool_execution" in call_kwargs["message"]
            assert call_kwargs["tool_name"] == "write_to_file"
            assert call_kwargs["trace_id"] == "tr_test_12345"
            assert call_kwargs["authority_decision"] == "ALLOW"
            assert call_kwargs["extra"]["span_status"] == "OK"

    def test_critical_mission_log_bridges_to_structured_logger(self):
        """Khi publish_mission_log với tag CRITICAL/SECURITY, phải phát sang StructuredLogger."""
        log_engine = LogEngine()
        mock_redis = MagicMock()

        with patch("core.observability.structured_logger.log_structured_event") as mock_log:
            log_engine.publish_mission_log(
                tag="SECURITY",
                msg="Master Credentials check failed for dangerous command",
                task_id="task_sec_999",
                trace_id="tr_sec_999",
                redis_conn=mock_redis
            )

            assert mock_log.called
            call_kwargs = mock_log.call_args.kwargs
            assert "Master Credentials check failed" in call_kwargs["message"]
            assert call_kwargs["tool_name"] == "security"
            assert call_kwargs["authority_decision"] == "DENY"
            assert call_kwargs["trace_id"] == "tr_sec_999"

    def test_routine_mission_log_does_not_flood_structured_logger(self):
        """Các log thông thường (INFO, UI) chỉ đi qua Redis pubsub, không gây nghẽn structured logger."""
        log_engine = LogEngine()
        mock_redis = MagicMock()


        with patch("core.observability.structured_logger.log_structured_event") as mock_log:
            log_engine.publish_mission_log(
                tag="INFO",
                msg="Regular UI status update",
                task_id="task_ui_1",
                redis_conn=mock_redis
            )

            assert not mock_log.called

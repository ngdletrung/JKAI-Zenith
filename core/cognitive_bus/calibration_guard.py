"""
JKAI Zenith - Cognitive Bus: Calibration Guard & ECE Drift Telemetry (v2.1)
Architecture: T8 Learning & Telemetry Plane / Atomic Decision Engine
Protocol: Protocol v2.0 - Two-Agent Cooperative Execution Protocol
Consensus Sign-Off: Antigravity & OpenCode (Phiên 21)

Tracks Expected Calibration Error (ECE) and enforces 3-Tier Drift Defense:
- ECE <= 0.08: OPTIMAL
- 0.08 < ECE <= 0.15: ALERT_DEGRADED (reduce confidence weight by 0.1)
- 0.15 < ECE <= 0.25: AUTONOMOUS_DISABLED (force human review)
- ECE > 0.25: SHUTDOWN_REVERT (revert to LLM-only verification)
- Rollback Trigger: false_positive_rate > baseline * 1.2 -> REVERT
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


class CalibrationHealth(str, Enum):
    OPTIMAL = "OPTIMAL"
    ALERT_DEGRADED = "ALERT_DEGRADED"
    AUTONOMOUS_DISABLED = "AUTONOMOUS_DISABLED"
    SHUTDOWN_REVERT = "SHUTDOWN_REVERT"


@dataclass
class CalibrationTelemetryReport:
    ece: float
    brier_score: float
    sample_count: int
    health: CalibrationHealth
    confidence_weight_modifier: float
    autonomous_enabled: bool
    rollback_triggered: bool
    recommended_action: str


class CalibrationGuard:
    """
    Monitors and guards model calibration against statistical drift.
    """

    ECE_ALERT_THRESHOLD = 0.08
    ECE_DISABLE_THRESHOLD = 0.15
    ECE_SHUTDOWN_THRESHOLD = 0.25
    ROLLBACK_FPR_RATIO = 1.20

    def __init__(self, baseline_fpr: float = 0.05):
        self.baseline_fpr = baseline_fpr
        self.samples: List[Tuple[float, int]] = []  # (predicted_prob, actual_binary_outcome)
        self.false_positives = 0
        self.total_negatives = 0

    def record_outcome(self, predicted_prob: float, actual_outcome: int):
        """Records a single prediction-vs-reality ground truth pair."""
        self.samples.append((predicted_prob, 1 if actual_outcome else 0))
        if not actual_outcome:
            self.total_negatives += 1
            if predicted_prob >= 0.50:
                self.false_positives += 1

    def compute_ece(self, num_bins: int = 10) -> float:
        """Computes Expected Calibration Error across equal-width probability bins."""
        if not self.samples:
            return 0.0

        n = len(self.samples)
        ece = 0.0

        for i in range(num_bins):
            bin_lower = i / num_bins
            bin_upper = (i + 1) / num_bins
            bin_samples = [s for s in self.samples if bin_lower <= s[0] < bin_upper or (i == num_bins - 1 and s[0] == 1.0)]
            
            if not bin_samples:
                continue

            bin_size = len(bin_samples)
            avg_confidence = sum(s[0] for s in bin_samples) / bin_size
            avg_accuracy = sum(s[1] for s in bin_samples) / bin_size
            ece += (bin_size / n) * abs(avg_accuracy - avg_confidence)

        return round(ece, 4)

    def compute_brier_score(self) -> float:
        if not self.samples:
            return 0.0
        return round(sum((prob - actual) ** 2 for prob, actual in self.samples) / len(self.samples), 4)

    def evaluate_health(self) -> CalibrationTelemetryReport:
        ece = self.compute_ece()
        brier = self.compute_brier_score()
        current_fpr = (self.false_positives / max(1, self.total_negatives))

        # Check Rollback Trigger
        rollback_triggered = current_fpr > (self.baseline_fpr * self.ROLLBACK_FPR_RATIO) and self.total_negatives >= 10

        # Evaluate 3-tier health
        if ece > self.ECE_SHUTDOWN_THRESHOLD or rollback_triggered:
            health = CalibrationHealth.SHUTDOWN_REVERT
            conf_mod = 0.0
            auto_enabled = False
            action = "SHUTDOWN_REVERT: Revert immediately to baseline LLM verification."
        elif ece > self.ECE_DISABLE_THRESHOLD:
            health = CalibrationHealth.AUTONOMOUS_DISABLED
            conf_mod = -0.2
            auto_enabled = False
            action = "AUTONOMOUS_DISABLED: High drift detected. Require manual Human Review for all decisions."
        elif ece > self.ECE_ALERT_THRESHOLD:
            health = CalibrationHealth.ALERT_DEGRADED
            conf_mod = -0.1
            auto_enabled = True
            action = "ALERT_DEGRADED: Calibration degraded. Applying -0.1 confidence modifier."
        else:
            health = CalibrationHealth.OPTIMAL
            conf_mod = 0.0
            auto_enabled = True
            action = "OPTIMAL: Calibration within healthy parameters."

        return CalibrationTelemetryReport(
            ece=ece,
            brier_score=brier,
            sample_count=len(self.samples),
            health=health,
            confidence_weight_modifier=conf_mod,
            autonomous_enabled=auto_enabled,
            rollback_triggered=rollback_triggered,
            recommended_action=action
        )

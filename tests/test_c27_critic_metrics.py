# -*- coding: utf-8 -*-
"""
C27 — Critic decisions must be counted, and system counters need one owner.

The critic is the quality gate of every audited answer: it approves, enforces a
corrected answer, sends the goal back for one retry, overrides a rejection with
deterministic evidence, or blocks the answer outright. None of those outcomes
was counted, so nobody could answer "how often is the gate fighting us?".

C26 also left each subsystem with its own Redis/fail-fast code. This contract
pins the shared owner so the pattern cannot be re-implemented per module.

Contract:
1. SystemCounters (core/telemetry, shared by every service) keeps local counters
   and publishes to Redis `jkai:counters:<name>`.
2. A downed Redis costs one failed attempt per 30s window, not one per event.
3. read() prefers Redis and falls back to local.
4. CognitiveMetrics only accepts known critic outcomes and exports them.
5. ai-brain records all five outcomes and exposes GET /critic/stats.
6. The firewall delegates to the shared counter instead of its own Redis code.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "services" / "ai-brain"
METRICS = BRAIN / "telemetry" / "metrics.py"
COUNTERS = ROOT / "core" / "telemetry" / "system_counters.py"
FIREWALL = BRAIN / "security" / "semantic_firewall.py"
MAIN = BRAIN / "main.py"

if str(BRAIN) not in sys.path:
    sys.path.append(str(BRAIN))


class FakeRedis:
    def __init__(self, data=None, as_bytes=False):
        self.data = dict(data or {})
        self.as_bytes = as_bytes

    def hincrby(self, key, field, amount):
        self.data[field] = self.data.get(field, 0) + amount

    def hgetall(self, key):
        if self.as_bytes:
            return {str(k).encode(): str(v).encode() for k, v in self.data.items()}
        return dict(self.data)


class DownRedis:
    def __init__(self):
        self.calls = 0

    def hincrby(self, *args, **kwargs):
        self.calls += 1
        raise RuntimeError("redis down")


def load_counters():
    spec = importlib.util.spec_from_file_location("c27_system_counters", COUNTERS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_metrics():
    spec = importlib.util.spec_from_file_location("c27_metrics", METRICS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bump_accumulates_locally_and_publishes_to_redis(monkeypatch):
    module = load_counters()
    counters = module.SystemCounters()
    redis = FakeRedis()
    monkeypatch.setattr(counters, "_get_redis", lambda: redis)

    counters.bump("critic", "retry")
    counters.bump("critic", "retry")
    counters.bump("critic", "approve", amount=3)

    assert counters.local("critic") == {"retry": 2, "approve": 3}
    assert redis.data == {"retry": 2, "approve": 3}


def test_downed_redis_costs_one_attempt_per_window(monkeypatch):
    module = load_counters()
    counters = module.SystemCounters()
    boom = DownRedis()
    monkeypatch.setattr(counters, "_get_redis", lambda: boom)

    for _ in range(5):
        counters.bump("firewall", "total_scanned")

    assert boom.calls == 1, "fail-fast must stop retrying a dead Redis on every request"
    assert counters.local("firewall") == {"total_scanned": 5}


def test_read_prefers_redis_and_falls_back_to_local(monkeypatch):
    module = load_counters()
    counters = module.SystemCounters()

    monkeypatch.setattr(counters, "_get_redis", lambda: None)
    counters.bump("critic", "approve")
    local_report = counters.read("critic")
    assert local_report["source"] == "local"
    assert local_report["counters"] == {"approve": 1}

    shared = FakeRedis({"approve": 40, "retry": 4}, as_bytes=True)
    monkeypatch.setattr(counters, "_get_redis", lambda: shared)
    redis_report = counters.read("critic")
    assert redis_report["source"] == "redis"
    assert redis_report["counters"] == {"approve": 40, "retry": 4}

    monkeypatch.setattr(counters, "_get_redis", lambda: FakeRedis())
    assert counters.read("critic")["source"] == "local", "empty Redis must not look like zero traffic"


def test_critic_metrics_count_known_outcomes_only():
    module = load_metrics()
    metrics = module.CognitiveMetrics()

    for outcome in module.CRITIC_OUTCOMES:
        metrics.record_critic_decision(outcome)
    metrics.record_critic_decision("not-a-real-outcome")

    assert metrics.snapshot()["critic_decisions"] == {outcome: 1 for outcome in module.CRITIC_OUTCOMES}

    if module.PROMETHEUS_AVAILABLE:
        decoded = metrics.get_prometheus_bytes()[0]
    else:
        decoded = metrics.get_prometheus_bytes()[0].decode()
    for outcome in module.CRITIC_OUTCOMES:
        assert f'jkai_critic_decision_total{{outcome="{outcome}"}} 1' in decoded


def test_ai_brain_records_every_outcome_and_exposes_stats():
    main_src = MAIN.read_text(encoding="utf-8")
    for outcome in ("approve", "enforce", "retry", "deterministic_override", "double_reject"):
        assert f'_record_critic_decision("{outcome}")' in main_src, f"{outcome} has no producer"
    assert "'/critic/stats'" in main_src
    assert 'system_counters.read("critic")' in main_src


def test_firewall_uses_the_shared_counter_owner():
    firewall_src = FIREWALL.read_text(encoding="utf-8")
    assert 'system_counters.bump("firewall"' in firewall_src
    assert 'system_counters.read("firewall")' in firewall_src
    assert "hincrby" not in firewall_src, "each subsystem must not keep its own Redis counter code"

"""Mission 1 v2 (Calibration) — Bo kiem chuan nghiem thu vat ly.

Agent DAT khi: 4/4 test PASS (exit code 0), chi sua mission2_shipping.py,
khong sua file test nay.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mission2_shipping import shipping_fee


def test_below_threshold():
    assert shipping_fee(100000) == 30000


def test_exact_threshold_free():
    assert shipping_fee(500000) == 0


def test_above_threshold_free():
    assert shipping_fee(800000) == 0


def test_express_below_threshold():
    assert shipping_fee(100000, express=True) == 60000

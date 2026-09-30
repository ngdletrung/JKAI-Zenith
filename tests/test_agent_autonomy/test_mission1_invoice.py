"""Mission 1 (Calibration) — Bo kiem chuan nghiem thu vat ly.

Agent DAT khi: 4/4 test PASS (exit code 0), chi sua mission1_invoice.py,
khong sua file test nay.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mission1_invoice import calc_subtotal, calc_total


def test_subtotal_basic():
    assert calc_subtotal([(10000, 2), (5000, 1)]) == 25000


def test_subtotal_empty():
    assert calc_subtotal([]) == 0


def test_total_no_discount():
    # 25000 + VAT 10% = 27500
    assert calc_total([(10000, 2), (5000, 1)], 0) == 27500


def test_total_with_discount():
    # subtotal 200000, giam 10% -> 180000, + VAT 10% -> 198000
    assert calc_total([(50000, 4)], 10) == 198000

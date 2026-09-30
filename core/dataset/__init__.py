# -*- coding: utf-8 -*-
"""
JKAI Dataset & Active Learning Package
"""
try:
    from .dataset_manager import dataset_manager, LabeledRecord, CATEGORIES
except ImportError:
    from dataset_manager import dataset_manager, LabeledRecord, CATEGORIES

__all__ = ["dataset_manager", "LabeledRecord", "CATEGORIES"]

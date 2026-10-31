import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "services" / "ai-brain"))
_spec = importlib.util.spec_from_file_location("deep_pipeline", Path(__file__).parents[1] / "services" / "ai-brain" / "deep_pipeline.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
DeepPipeline = _module.DeepPipeline


def test_future_year_blocks_unlabelled_evidence():
    result = DeepPipeline.check_temporal_consistency("Tin cập nhật năm 2099")
    assert result["ok"] is False


def test_labelled_future_year_allowed_for_review():
    result = DeepPipeline.check_temporal_consistency("[future] Tin năm 2099")
    assert result["ok"] is True


def test_mixed_years_block_without_freshness_label():
    result = DeepPipeline.check_temporal_consistency("Tin năm 2024 và 2025")
    assert result["ok"] is False

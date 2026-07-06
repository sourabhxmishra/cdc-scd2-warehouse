"""Watermark store tests."""
from src.watermark import Watermark


def test_default_watermark_is_zero(tmp_path):
    assert Watermark(str(tmp_path / "wm.json")).get() == 0


def test_advance_persists_across_instances(tmp_path):
    path = str(tmp_path / "wm.json")
    Watermark(path).advance(42)
    assert Watermark(path).get() == 42

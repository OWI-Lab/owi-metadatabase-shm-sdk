from __future__ import annotations

import json
from pathlib import Path

import pytest

from owi.metadatabase.shm import (
    LegacySignalIdentifier,
    load_json_data,
    parse_legacy_signal_id,
)


def test_parse_legacy_signal_id_returns_typed_model() -> None:
    parsed = parse_legacy_signal_id("NRT_WTG_TP_STRAIN_LAT02_DEG270_Y")

    assert parsed == LegacySignalIdentifier(
        raw="NRT_WTG_TP_STRAIN_LAT02_DEG270_Y",
        parts=("NRT", "WTG", "TP", "STRAIN", "LAT02", "DEG270", "Y"),
        subassembly="TP",
        signal_type="STRAIN",
        lateral_position=2,
        angular_position=270,
        orientation="Y",
    )


def test_parse_legacy_signal_id_returns_none_for_short_value() -> None:
    assert parse_legacy_signal_id("NRT_TP") is None


def test_parse_legacy_signal_id_defaults_unknown_orientation_to_zero() -> None:
    parsed = parse_legacy_signal_id("NRT_WTG_TP_STRAIN_LAT02_DEG270_AZIMUTH")

    assert parsed is not None
    assert parsed.orientation == "0"


def test_parse_legacy_signal_id_raises_for_non_numeric_latitude() -> None:
    with pytest.raises(ValueError, match=r"Found None for LAT"):
        parse_legacy_signal_id("NRT_WTG_TP_STRAIN_LAT_DEG270_Y")


def test_load_json_data_reads_json_document(tmp_path: Path) -> None:
    path = tmp_path / "sensor-types.json"
    path.write_text(json.dumps([{"name": "strain"}]), encoding="utf-8")

    assert load_json_data(None) is None
    assert load_json_data(path) == [{"name": "strain"}]

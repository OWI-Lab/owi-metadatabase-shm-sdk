from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from owi.metadatabase.shm import (
    ConfiguredSignalConfigProcessor,
    DelimitedSignalKeyParser,
    JsonStemConfigDiscovery,
    LevelBasedDerivedSignalStrategy,
    SignalProcessorSpec,
    load_signal_processor_spec,
)


def _packaged_processor_spec_path() -> Path:
    return Path(__file__).resolve().parents[2] / "src/owi/metadatabase/shm/config/default_signal_processor.yaml"


def _packaged_processor_spec() -> SignalProcessorSpec:
    return load_signal_processor_spec(_packaged_processor_spec_path())


def test_configured_processor_matches_archive_shape_for_sample_config(tmp_path) -> None:
    config_path = tmp_path / "T01.json"
    config_path.write_text(json.dumps(_sample_signal_config()), encoding="utf-8")

    new_processor = ConfiguredSignalConfigProcessor(
        path_configs=tmp_path,
        processor_spec=_packaged_processor_spec(),
    )
    signals, derived_signals = new_processor.signal_preprocess_data(config_path)

    assert signals == {
        "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y": {
            "heading": "north",
            "temperature_compensation": {"TCSensor": "TC-1"},
            "status": [
                {
                    "time": "01/01/1972 00:00",
                    "name": "X",
                    "status": "ok",
                },
                {"time": "02/01/1972 00:00", "status": "maintenance"},
            ],
            "offset": [
                {
                    "time": "01/01/1972 00:00",
                    "offset": 1.2,
                    "TCSensor": "TC-1",
                },
                {
                    "time": "02/01/1972 00:00",
                    "offset": 1.5,
                    "TCSensor": "TC-1",
                },
            ],
            "cwl": [{"time": "01/01/1972 00:00", "cwl": 3.4}],
        },
        "X": {},
    }
    assert derived_signals["NRT_WTG_TP_ACC_LAT01_DEG000_FA"] == {
        "data": {"name": "acceleration/yaw_transformation"},
        "calibration": [
            {"time": "01/01/1972 00:00", "yaw_parameter": 1.0, "yaw_offset": 2.0},
            {"time": "02/01/1972 00:00", "yaw_parameter": 1.0, "yaw_offset": 3.0},
        ],
        "parent_signals": ["SIG_A", "SIG_B"],
    }
    assert derived_signals["NRT_WTG_TP_VSG_LAT02_DEG270_DEG090_0"] == {
        "data": {"name": "strain/bending_moment"},
        "calibration": [
            {
                "time": "01/01/1972 00:00",
                "yaw_parameter": 1.5,
                "yaw_offset": 0.5,
                "measurement_location": "flange",
            },
            {
                "time": "02/01/1972 00:00",
                "yaw_parameter": 1.5,
                "yaw_offset": 0.75,
                "measurement_location": "flange",
            },
        ],
        "parent_signals": ["SIG_C", "SIG_D"],
    }


def test_json_stem_config_discovery_warns_for_missing_turbines(tmp_path) -> None:
    (tmp_path / "T01.json").write_text("[]", encoding="utf-8")
    discovery = JsonStemConfigDiscovery()

    with pytest.warns(UserWarning, match="Some turbines"):
        config_paths = discovery.discover(tmp_path, turbines=["T01", "T02"])

    assert config_paths == {"T01": tmp_path / "T01.json"}


def test_configured_processor_carries_forward_previous_timestamp() -> None:
    processor = ConfiguredSignalConfigProcessor(
        path_configs=".",
        processor_spec=_packaged_processor_spec(),
    )

    result = processor.process_events(
        [
            {
                "time": "02/01/1972 00:00",
                "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/status": "ok",
            },
            {"NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/offset": 1.5},
        ]
    )

    signals, _ = result.to_legacy_data()

    assert signals == {
        "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y": {
            "status": [{"time": "02/01/1972 00:00", "status": "ok"}],
            "offset": [{"time": "02/01/1972 00:00", "offset": 1.5}],
        }
    }


def test_signals_process_data_limits_results_to_requested_turbines(tmp_path) -> None:
    (tmp_path / "T01.json").write_text(
        json.dumps(_sample_signal_config()),
        encoding="utf-8",
    )
    (tmp_path / "T02.json").write_text(
        json.dumps(_sample_signal_config()),
        encoding="utf-8",
    )

    processor = ConfiguredSignalConfigProcessor(
        path_configs=tmp_path,
        turbines=["T02"],
        processor_spec=_packaged_processor_spec(),
    )

    processor.signals_process_data()

    assert processor.turbines == ["T02"]
    assert list(processor.signals_data) == ["T02"]
    assert list(processor.signals_derived_data) == ["T02"]
    assert "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y" in processor.signals_data["T02"]


def test_signals_process_data_discovers_single_config_file_from_public_src_surface(tmp_path) -> None:
    config_path = tmp_path / "T03.json"
    config_path.write_text(json.dumps(_sample_signal_config()), encoding="utf-8")

    processor = ConfiguredSignalConfigProcessor(
        path_configs=config_path,
        processor_spec=_packaged_processor_spec(),
    )

    processor.signals_process_data()

    assert processor.turbines == ["T03"]
    assert list(processor.signals_data) == ["T03"]
    assert processor.signals_data["T03"]["NRT_WTG_TP_STRAIN_LAT01_DEG000_Y"]["heading"] == "north"
    assert "NRT_WTG_TP_ACC_LAT01_DEG000_FA" in processor.signals_derived_data["T03"]


def test_configured_processor_accepts_custom_farm_rules() -> None:
    def build_signal_name(level: str, suffix: str) -> str:
        return f"{level}__{suffix}"

    def build_parent_signals(payload: dict[str, object], level: str) -> tuple[str, ...]:
        return tuple(payload[level])

    def build_calibration(payload: dict[str, object], level: str) -> dict[str, object]:
        return {"gain": payload["gain"], "level": level}

    processor = ConfiguredSignalConfigProcessor(
        path_configs=".",
        processor_spec=SignalProcessorSpec(
            farm_name="Custom Farm",
            signal_key_parser=DelimitedSignalKeyParser(signal_prefixes=("WF_",)),
            derived_signal_strategies={
                "custom/summary": LevelBasedDerivedSignalStrategy(
                    suffixes=("AVG",),
                    signal_name_builder=build_signal_name,
                    parent_signals_builder=build_parent_signals,
                    calibration_fields_builder=build_calibration,
                )
            },
        ),
    )

    result = processor.process_events(
        [
            {
                "WF_SIG/status": "ok",
                "custom/summary": {
                    "levels": ["WF_SIG"],
                    "gain": 4,
                    "WF_SIG": ["PARENT_A", "PARENT_B"],
                },
            }
        ]
    )

    signals, derived_signals = result.to_legacy_data()

    assert signals == {"WF_SIG": {"status": [{"time": "01/01/1972 00:00", "status": "ok"}]}}
    assert derived_signals == {
        "WF_SIG__AVG": {
            "data": {"name": "custom/summary"},
            "calibration": [
                {
                    "time": "01/01/1972 00:00",
                    "gain": 4,
                    "level": "WF_SIG",
                }
            ],
            "parent_signals": ["PARENT_A", "PARENT_B"],
        }
    }


def test_configured_processor_loads_yaml_spec(tmp_path) -> None:
    spec_path = tmp_path / "farm.yaml"
    spec_path.write_text(
        textwrap.dedent(
            """
            farm_name: Demo Farm
            signal_key_parser:
              kind: delimited
              signal_prefixes:
                - WF_
            derived_signal_strategies:
              custom/summary:
                kind: level_based
                suffixes:
                  - AVG
                parent_signals_builder: parent_signals_from_level
                calibration_fields_builder: yaw_calibration_fields
            postprocessors: []
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    processor = ConfiguredSignalConfigProcessor.from_yaml_spec(
        path_configs=".",
        processor_spec_path=spec_path,
    )

    result = processor.process_events(
        [
            {
                "WF_SIG/status": "ok",
                "custom/summary": {
                    "levels": ["WF_SIG"],
                    "yaw_parameter": 4.0,
                    "yaw_offset": 2.5,
                    "WF_SIG": ["PARENT_A", "PARENT_B"],
                },
            }
        ]
    )

    signals, derived_signals = result.to_legacy_data()

    assert signals == {
        "WF_SIG": {
            "status": [{"time": "01/01/1972 00:00", "status": "ok"}]
        }
    }
    assert derived_signals == {
        "WF_SIG_AVG": {
            "data": {"name": "custom/summary"},
            "calibration": [
                {
                    "time": "01/01/1972 00:00",
                    "yaw_parameter": 4.0,
                    "yaw_offset": 2.5,
                }
            ],
            "parent_signals": ["PARENT_A", "PARENT_B"],
        }
    }


def test_load_packaged_processor_spec_uses_packaged_yaml() -> None:
    path = _packaged_processor_spec_path()
    spec = load_signal_processor_spec(path)

    assert isinstance(path, Path)
    assert path.name == "default_signal_processor.yaml"
    assert path.is_file()
    assert spec.farm_name == "Default Wind Farm"
    assert tuple(spec.derived_signal_strategies) == (
        "acceleration/yaw_transformation",
        "strain/bending_moment",
    )


def test_load_signal_processor_spec_rejects_unknown_builder(tmp_path) -> None:
    spec_path = tmp_path / "invalid.yaml"
    spec_path.write_text(
        textwrap.dedent(
            """
            farm_name: Broken Farm
            signal_key_parser:
              kind: delimited
              signal_prefixes:
                - WF_
            derived_signal_strategies:
              custom/summary:
                kind: level_based
                suffixes:
                  - AVG
                parent_signals_builder: missing_builder
                calibration_fields_builder: yaw_calibration_fields
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing_builder"):
        load_signal_processor_spec(spec_path)


def _sample_signal_config() -> list[dict[str, object]]:
    return [
        {
            "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/status": "ok",
            "X/name": "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y",
            "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/offset": 1.2,
            "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/cwl": 3.4,
            "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/heading": "north",
            "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/temperature_compensation": {"TCSensor": "TC-1"},
            "acceleration/yaw_transformation": {
                "levels": ["NRT_WTG_TP_ACC_LAT01_DEG000"],
                "yaw_parameter": 1.0,
                "yaw_offset": 2.0,
                "NRT_WTG_TP_ACC_LAT01_DEG000": ["SIG_A", "SIG_B"],
            },
            "strain/bending_moment": {
                "levels": ["NRT_WTG_TP_SG_LAT02_DEG270"],
                "yaw_parameter": 1.5,
                "yaw_offset": 0.5,
                "NRT_WTG_TP_SG_LAT02_DEG270": {
                    "measurement_location": "flange",
                    "sensors": ["SIG_C", "SIG_D"],
                },
            },
        },
        {
            "time": "02/01/1972 00:00",
            "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/status": "maintenance",
            "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/offset": 1.5,
            "acceleration/yaw_transformation": {
                "levels": ["NRT_WTG_TP_ACC_LAT01_DEG000"],
                "yaw_parameter": 1.0,
                "yaw_offset": 3.0,
                "NRT_WTG_TP_ACC_LAT01_DEG000": ["SIG_A", "SIG_B"],
            },
            "strain/bending_moment": {
                "levels": ["NRT_WTG_TP_SG_LAT02_DEG270"],
                "yaw_parameter": 1.5,
                "yaw_offset": 0.75,
                "NRT_WTG_TP_SG_LAT02_DEG270": {
                    "measurement_location": "flange",
                    "sensors": ["SIG_C", "SIG_D"],
                },
            },
        },
    ]

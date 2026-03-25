import json
from datetime import date
from pathlib import Path

import pytest

from owi.metadatabase.shm.signal_ids import parse_legacy_signal_id
from owi.metadatabase.shm.upload.payloads import (
    SensorCalibrationPayload,
    build_derived_signal_calibration_payloads,
    build_derived_signal_main_payload,
    build_derived_signal_parent_patch,
    build_derived_signal_status_payload,
    build_sensor_calibration_payloads,
    build_sensor_payloads,
    build_sensor_type_payloads,
    build_signal_calibration_payloads,
    build_signal_main_payload,
    build_signal_status_payloads,
)
from owi.metadatabase.shm.upload_context import SignalUploadContext


def _upload_context() -> SignalUploadContext:
    return SignalUploadContext(
        site_id=10,
        asset_location_id=20,
        model_definition_id=30,
        permission_group_ids=[7, 11],
        subassembly_ids_by_type={"TP": 40, "TW": 41, "MP": 42},
    )


def test_build_signal_main_payload_serializes_archive_misc_fields() -> None:
    signal = parse_legacy_signal_id("NRT_WTG_TP_STRAIN_LAT02_DEG270_Y")
    assert signal is not None

    payload = build_signal_main_payload(
        signal,
        {
            "heading": "N",
            "level": 2,
            "orientation": "Y",
            "stats": "mean",
            "custom_factor": 1.5,
            "calculation": {"window": "10m"},
        },
        _upload_context(),
    )

    assert payload == {
        "site": 10,
        "model_definition": 30,
        "asset_location": 20,
        "signal_type": "STRAIN",
        "heading": "N",
        "level": 2,
        "orientation": "Y",
        "signal_id": "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y",
        "stats": "mean",
        "visibility": "usergroup",
        "visibility_groups": [7, 11],
        "sub_assembly": 40,
        "data_additional": json.dumps(
            {
                "custom_factor": 1.5,
                "calculation": {"window": "10m"},
            }
        ),
    }


def test_build_signal_status_payloads_only_mark_latest_entry() -> None:
    payloads = build_signal_status_payloads(
        77,
        {
            "status": [
                {"time": "24/03/2026 08:00:00", "status": "ok"},
                {"time": "24/03/2026 09:30:00", "status": "maintenance", "name": "LEG-002"},
            ]
        },
        sensor_serial_number=88,
    )

    assert payloads == [
        {
            "signal_id": 77,
            "activity_start_timestamp": "2026-03-24T08:00:00",
            "is_latest_status": False,
            "status": "ok",
            "sensor_serial_number": 88,
            "status_approval": "yes",
        },
        {
            "signal_id": 77,
            "activity_start_timestamp": "2026-03-24T09:30:00",
            "is_latest_status": True,
            "status": "maintenance",
            "sensor_serial_number": 88,
            "status_approval": "yes",
            "legacy_signal_id": "LEG-002",
        },
    ]


def test_build_signal_calibration_payloads_preserve_archive_json_shapes() -> None:
    payloads = build_signal_calibration_payloads(
        77,
        {
            "temperature_compensation": True,
            "offset": [
                {
                    "time": "24/03/2026 08:15:00",
                    "offset": 1.25,
                    "TCSensor": "TC-001",
                    "Coefficients": [1.0, 2.0],
                    "t_ref": 21.5,
                    "gauge_correction": 0.2,
                    "lead_correction": {"t_ref": 25.0, "coef": 0.5},
                }
            ],
            "cwl": [{"time": "24/03/2026 08:30:00", "cwl": 13.4}],
        },
        tempcomp_signal_ids={"TC-001": 101},
    )

    assert payloads == [
        {
            "signal_id": 77,
            "calibration_date": "2026-03-24T08:15:00",
            "data": json.dumps(
                {
                    "offset": 1.25,
                    "Coefficients": [1.0, 2.0],
                    "t_ref": 21.5,
                    "gauge_correction": 0.2,
                    "lead_correction": {"t_ref": 25.0, "coef": 0.5},
                }
            ),
            "tempcomp_signal_id": 101,
            "status_approval": "yes",
        },
        {
            "signal_id": 77,
            "calibration_date": "2026-03-24T08:30:00",
            "data": json.dumps({"cwl": 13.4}),
            "tempcomp_signal_id": None,
            "status_approval": "yes",
        },
    ]


def test_build_derived_signal_payloads_keep_archive_contract() -> None:
    signal = parse_legacy_signal_id("NRT_WTG_TP_YAW_LAT01_DEG000_Y")
    assert signal is not None
    signal_data = {
        "heading": "N",
        "level": 1,
        "orientation": "Y",
        "stats": "last",
        "data": {"window": "10m", "formula": "yaw_a - yaw_b"},
        "calibration": [
            {
                "time": "24/03/2026 07:45:00",
                "yaw_parameter": "offset",
                "yaw_offset": 4.5,
                "measurement_location": "nacelle",
            }
        ],
    }

    main_payload = build_derived_signal_main_payload(signal, signal_data, _upload_context())
    status_payload = build_derived_signal_status_payload(501, signal_data)
    calibration_payloads = build_derived_signal_calibration_payloads(501, signal_data)
    parent_patch = build_derived_signal_parent_patch((77, 78))

    assert main_payload == {
        "site": 10,
        "model_definition": 30,
        "asset_location": 20,
        "signal_type": "YAW",
        "heading": "N",
        "level": 1,
        "orientation": "Y",
        "derived_signal_id": "NRT_WTG_TP_YAW_LAT01_DEG000_Y",
        "stats": "last",
        "visibility": "usergroup",
        "visibility_groups": [7, 11],
        "sub_assembly": 40,
        "data_additional": json.dumps({"window": "10m", "formula": "yaw_a - yaw_b"}),
    }
    assert status_payload == {
        "activity_start_timestamp": "2026-03-24T07:45:00",
        "is_latest_status": True,
        "status": "ok",
        "derived_signal_id": 501,
        "status_approval": "yes",
    }
    assert calibration_payloads == [
        {
            "calibration_date": "2026-03-24T07:45:00",
            "data": json.dumps(
                {
                    "yaw_parameter": "offset",
                    "yaw_offset": 4.5,
                    "measurement_location": "nacelle",
                }
            ),
            "derived_signal_id": 501,
            "status_approval": "yes",
        }
    ]
    assert parent_patch == {"parent_signals": [77, 78]}


def test_build_sensor_type_payloads_resolves_image_paths(tmp_path: Path) -> None:
    payloads = build_sensor_type_payloads(
        [
            {
                "name": "393B04",
                "type": "ACC",
                "type_extended": "Acceleration",
                "hardware_supplier": "PCB",
                "file": "sensor.png",
            }
        ],
        visibility_groups=[1, 2],
        path_to_images=tmp_path,
    )

    assert len(payloads) == 1
    assert payloads[0].to_payload()["visibility_groups"] == [1, 2]
    assert payloads[0].file == tmp_path / "sensor.png"


def test_build_sensor_payloads_raises_on_mismatched_columns() -> None:
    with pytest.raises(ValueError, match="same length"):
        build_sensor_payloads(1, ["A", "B"], ["CAB1"], visibility_groups=None)


def test_sensor_calibration_payload_normalizes_dates() -> None:
    payload = SensorCalibrationPayload(
        sensor_serial_number=42,
        calibration_date=date(2024, 1, 1),
        file="calibration.pdf",
    )

    assert payload.to_payload()["calibration_date"] == "2024-01-01T00:00:00"


def test_build_sensor_calibration_payloads_skips_unknown_signals(tmp_path: Path) -> None:
    payloads = build_sensor_calibration_payloads(
        {"SIG_A": 42},
        {
            "SIG_A": {"date": "28-02-2019", "filename": "cal.pdf"},
            "SIG_B": {"date": "01-01-2020", "filename": "missing.pdf"},
        },
        path_to_datasheets=tmp_path,
    )

    assert len(payloads) == 1
    assert payloads[0].sensor_serial_number == 42
    assert str(payloads[0].file).endswith("cal.pdf")

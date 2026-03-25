"""Tests for the ShmSensorUploader orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owi.metadatabase.shm import ShmSensorUploader
from owi.metadatabase.shm.upload.errors import ShmUploadError


def _mock_api() -> MagicMock:
    api = MagicMock()
    api.get_sensor_type.return_value = {"exists": True, "id": 100}
    api.get_sensor.return_value = {"exists": True, "id": 200}
    api.create_sensor_type.return_value = {"exists": True, "id": 10}
    api.create_sensor.return_value = {"exists": True, "id": 20}
    api.create_sensor_calibration.return_value = {"exists": True, "id": 30}
    return api


def test_upload_sensor_types_delegates_to_create_sensor_type() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    raw_types = [
        {"name": "ACC", "type": "ACC", "type_extended": "Acceleration", "hardware_supplier": "PCB"},
        {"name": "TC", "type": "TC", "type_extended": "Thermocouple", "hardware_supplier": "S1"},
    ]
    results = uploader.upload_sensor_types(raw_types, permission_group_ids=[1])

    assert len(results) == 2
    assert api.create_sensor_type.call_count == 2
    first_call_payload = api.create_sensor_type.call_args_list[0][0][0]
    assert first_call_payload["name"] == "ACC"
    assert first_call_payload["visibility_groups"] == [1]


def test_upload_sensors_collects_serial_numbers_and_cabinets() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    sensors_data = {
        "T01": {
            "accelerometers": {
                "serial_numbers": [111, 222],
                "cabinets": ["CAB1", "CAB2"],
            }
        },
        "T02": {
            "accelerometers": {
                "serial_numbers": [333],
                "cabinets": ["CAB3"],
            }
        },
    }
    results = uploader.upload_sensors(
        sensor_type_name="accelerometers",
        sensor_type_params={"name": "393B04"},
        sensors_data=sensors_data,
        permission_group_ids=[1],
    )

    assert len(results) == 3
    api.get_sensor_type.assert_called_once_with(name="393B04")
    assert api.create_sensor.call_count == 3


def test_upload_sensors_respects_turbine_filter() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    sensors_data = {
        "T01": {"acc": {"serial_numbers": [1], "cabinets": ["C1"]}},
        "T02": {"acc": {"serial_numbers": [2], "cabinets": ["C2"]}},
    }
    results = uploader.upload_sensors(
        sensor_type_name="acc",
        sensor_type_params={"name": "ACC"},
        sensors_data=sensors_data,
        permission_group_ids=None,
        turbines=["T01"],
    )

    assert len(results) == 1


def test_upload_sensors_handles_null_serial_numbers() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    sensors_data = {
        "T01": {
            "thermocouples": {
                "serial_numbers": None,
                "cabinets": ["C1", "C2", "C3"],
            }
        }
    }
    results = uploader.upload_sensors(
        sensor_type_name="thermocouples",
        sensor_type_params={"name": "TC"},
        sensors_data=sensors_data,
        permission_group_ids=None,
    )

    assert len(results) == 3
    for c in api.create_sensor.call_args_list:
        assert c[0][0]["serial_number"] is None


def test_upload_sensors_handles_null_cabinets() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    sensors_data = {
        "T01": {
            "sg": {
                "serial_numbers": ["SN1", "SN2"],
                "cabinets": None,
            }
        }
    }
    results = uploader.upload_sensors(
        sensor_type_name="sg",
        sensor_type_params={"name": "SG"},
        sensors_data=sensors_data,
        permission_group_ids=None,
    )

    assert len(results) == 2
    for c in api.create_sensor.call_args_list:
        assert c[0][0]["cabinet"] is None


def test_upload_sensors_skips_null_category() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    sensors_data = {"T01": {"FBG": None}}
    results = uploader.upload_sensors(
        sensor_type_name="FBG",
        sensor_type_params={"name": "FBG"},
        sensors_data=sensors_data,
        permission_group_ids=None,
    )

    assert results == []
    api.create_sensor.assert_not_called()


def test_upload_sensors_raises_on_length_mismatch() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    sensors_data = {
        "T01": {
            "acc": {"serial_numbers": [1, 2], "cabinets": ["C1"]},
        }
    }
    with pytest.raises(ShmUploadError, match="do not match"):
        uploader.upload_sensors(
            sensor_type_name="acc",
            sensor_type_params={"name": "ACC"},
            sensors_data=sensors_data,
            permission_group_ids=None,
        )


def test_upload_sensor_calibrations_resolves_sensors_and_creates_calibrations(tmp_path: Path) -> None:
    api = _mock_api()

    # Create a fake PDF file
    fake_pdf = tmp_path / "cal.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")

    uploader = ShmSensorUploader(shm_api=api)

    signal_sensor_map = {
        "T01": {
            "SIG_A": {"sensor_type_id": {"name": "ACC"}, "serial_number": "111"},
        }
    }
    signal_calibration_map = {
        "T01": {
            "SIG_A": {"date": "28-02-2019", "filename": "cal.pdf"},
        }
    }

    results = uploader.upload_sensor_calibrations(
        signal_sensor_map_data=signal_sensor_map,
        signal_calibration_map_data=signal_calibration_map,
        path_to_datasheets=str(tmp_path),
    )

    assert len(results) == 1
    api.get_sensor_type.assert_called_once_with(name="ACC")
    api.get_sensor.assert_called_once()
    api.create_sensor_calibration.assert_called_once()
    # Should have files since PDF exists
    call_kwargs = api.create_sensor_calibration.call_args
    assert call_kwargs[1].get("files") is not None


def test_upload_sensor_calibrations_skips_missing_turbine() -> None:
    api = _mock_api()
    uploader = ShmSensorUploader(shm_api=api)

    results = uploader.upload_sensor_calibrations(
        signal_sensor_map_data={},
        signal_calibration_map_data={"T01": {"SIG_A": {"date": "01-01-2020", "filename": "x.pdf"}}},
        path_to_datasheets="/tmp",
        turbines=["T01"],
    )

    assert results == []
    api.create_sensor_calibration.assert_not_called()

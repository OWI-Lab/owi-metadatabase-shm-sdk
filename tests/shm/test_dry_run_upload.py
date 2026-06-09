from __future__ import annotations

from unittest.mock import Mock

import pytest

from owi.metadatabase.shm import (
    AssetSignalUploadRequest,
    DryRunSensorUploadClient,
    DryRunSignalUploadClient,
    ShmSensorUploader,
    ShmSignalUploader,
)
from owi.metadatabase.shm.upload_context import SignalUploadContext


def _upload_context() -> SignalUploadContext:
    return SignalUploadContext(
        site_id=10,
        asset_location_id=20,
        model_definition_id="MD-01",
        permission_group_ids=[7],
        subassembly_ids_by_type={"TP": 40},
    )


def test_dry_run_clients_expose_seeded_operation_log_structure() -> None:
    sensor_api = DryRunSensorUploadClient(
        sensor_types=[{"id": 10, "name": "ACC"}],
        sensors=[{"id": 20, "serial_number": "S-001"}],
    )
    signal_api = DryRunSignalUploadClient(signals=[{"id": 30, "signal_id": "EXISTING"}])

    assert sensor_api.operations == ()
    assert sensor_api.sensor_types == ({"id": 10, "name": "ACC"},)
    assert sensor_api.sensors == ({"id": 20, "serial_number": "S-001"},)
    assert signal_api.operations == ()
    assert signal_api.signals == ({"id": 30, "signal_id": "EXISTING"},)


def test_sensor_dry_run_records_upload_operations() -> None:
    dry_api = DryRunSensorUploadClient(sensor_types=[{"id": 100, "name": "ACC"}])
    uploader = ShmSensorUploader(shm_api=dry_api)

    results = uploader.upload_sensors(
        sensor_type_name="accelerometers",
        sensor_type_params={"name": "ACC"},
        sensors_data={
            "T01": {
                "accelerometers": {
                    "serial_numbers": ["S-001"],
                    "cabinets": ["CAB-01"],
                }
            }
        },
        permission_group_ids=[7],
    )

    assert len(results) == 1
    assert [(op.action, op.resource) for op in dry_api.operations] == [
        ("lookup", "sensor_type"),
        ("create", "sensor"),
    ]
    assert dry_api.operations[-1].payload == {
        "sensor_type_id": 100,
        "serial_number": "S-001",
        "cabinet": "CAB-01",
        "visibility": "usergroup",
        "visibility_groups": [7],
    }


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Signal dry-run recording is implemented in a follow-up PR.",
    strict=True,
)
def test_signal_dry_run_records_upload_operations() -> None:
    dry_api = DryRunSignalUploadClient(starting_id=100)
    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=dry_api, lookup_service=lookup_service)

    result = uploader.upload_asset(
        AssetSignalUploadRequest(
            projectsite="Project A",
            assetlocation="T01",
            signals={
                "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": {
                    "heading": "N",
                    "level": 2,
                    "orientation": "Y",
                    "stats": "mean",
                    "status": [{"time": "24/03/2026 08:00:00", "status": "ok"}],
                }
            },
            derived_signals={
                "NRT_WTG_TP_YAW_LAT01_DEG000_Y": {
                    "data": {"window": "10m"},
                    "parent_signals": ["NRT_WTG_TP_STRAIN_LAT02_DEG270_Y"],
                    "calibration": [
                        {
                            "time": "24/03/2026 07:45:00",
                            "yaw_parameter": "offset",
                            "yaw_offset": 4.5,
                        }
                    ],
                }
            },
            permission_group_ids=[7],
        )
    )

    assert result.signal_ids_by_name == {"NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": 100}
    assert result.derived_signal_ids_by_name == {"NRT_WTG_TP_YAW_LAT01_DEG000_Y": 102}
    assert [(op.action, op.resource) for op in dry_api.operations] == [
        ("create", "signal"),
        ("create", "signal_history"),
        ("create", "derived_signal"),
        ("create", "derived_signal_history"),
        ("patch", "derived_signal_history"),
        ("create", "derived_signal_calibration"),
    ]

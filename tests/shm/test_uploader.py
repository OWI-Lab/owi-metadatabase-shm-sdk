from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import Mock, call

import pandas as pd
import pytest

from owi.metadatabase.shm import (
    AssetSignalUploadRequest,
    ConfiguredSignalConfigProcessor,
    ParentSignalLookupError,
    ShmSignalUploader,
    SignalConfigUploadSource,
    SignalProcessorSpec,
    UploadResultError,
    load_signal_processor_spec,
)
from owi.metadatabase.shm.upload_context import SignalUploadContext


def _upload_context() -> SignalUploadContext:
    return SignalUploadContext(
        site_id=10,
        asset_location_id=20,
        model_definition_id="MD-01",
        permission_group_ids=[7, 11],
        subassembly_ids_by_type={"TP": 40, "TW": 41, "MP": 42},
    )


def _packaged_processor_spec() -> SignalProcessorSpec:
    path = Path(__file__).resolve().parents[2] / "src/owi/metadatabase/shm/config/default_signal_processor.yaml"
    return load_signal_processor_spec(path)


def test_upload_asset_uses_lookup_context_and_shm_transport_helpers() -> None:
    shm_api = Mock()
    shm_api.create_signal.return_value = {"id": 101, "exists": True}
    shm_api.create_signal_history.return_value = {"id": 201, "exists": True}
    shm_api.create_signal_calibration.side_effect = [
        {"id": 301, "exists": True},
        {"id": 302, "exists": True},
    ]
    shm_api.create_derived_signal.return_value = {"id": 501, "exists": True}
    shm_api.create_derived_signal_history.return_value = {"id": 601, "exists": True}
    shm_api.patch_derived_signal_history.return_value = {"id": 601, "exists": True}
    shm_api.create_derived_signal_calibration.return_value = {"id": 701, "exists": True}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    request = AssetSignalUploadRequest(
        projectsite="Project A",
        assetlocation="Asset-01",
        signals={
            "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": {
                "heading": "N",
                "level": 2,
                "orientation": "Y",
                "stats": "mean",
                "status": [{"time": "24/03/2026 08:00:00", "status": "ok"}],
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
                "custom_factor": 1.5,
            }
        },
        derived_signals={
            "NRT_WTG_TP_YAW_LAT01_DEG000_Y": {
                "heading": "N",
                "level": 1,
                "orientation": "Y",
                "stats": "last",
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
        permission_group_ids=[7, 11],
        sensor_serial_numbers_by_signal={"NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": 88},
        temperature_compensation_signal_ids={"TC-001": 909},
    )

    result = uploader.upload_asset(request)

    lookup_service.get_signal_upload_context.assert_called_once_with(
        projectsite="Project A",
        assetlocation="Asset-01",
        permission_group_ids=[7, 11],
    )
    shm_api.create_signal.assert_called_once()
    assert shm_api.create_signal.call_args.kwargs == {}
    assert shm_api.create_signal.call_args.args[0]["signal_id"] == "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y"
    assert shm_api.create_signal.call_args.args[0]["sub_assembly"] == 40

    shm_api.create_signal_history.assert_called_once_with(
        {
            "signal_id": 101,
            "activity_start_timestamp": "2026-03-24T08:00:00",
            "is_latest_status": True,
            "status": "ok",
            "sensor_serial_number": 88,
            "status_approval": "yes",
        }
    )
    assert shm_api.create_signal_calibration.call_args_list == [
        call(
            {
                "signal_id": 101,
                "calibration_date": "2026-03-24T08:15:00",
                "data": (
                    '{"offset": 1.25, "Coefficients": [1.0, 2.0], '
                    '"t_ref": 21.5, "gauge_correction": 0.2, '
                    '"lead_correction": {"t_ref": 25.0, "coef": 0.5}}'
                ),
                "tempcomp_signal_id": 909,
                "status_approval": "yes",
            }
        ),
        call(
            {
                "signal_id": 101,
                "calibration_date": "2026-03-24T08:30:00",
                "data": '{"cwl": 13.4}',
                "tempcomp_signal_id": None,
                "status_approval": "yes",
            }
        ),
    ]
    shm_api.create_derived_signal.assert_called_once()
    assert shm_api.create_derived_signal.call_args.args[0]["derived_signal_id"] == "NRT_WTG_TP_YAW_LAT01_DEG000_Y"
    shm_api.create_derived_signal_history.assert_called_once_with(
        {
            "activity_start_timestamp": "2026-03-24T07:45:00",
            "is_latest_status": True,
            "status": "ok",
            "derived_signal_id": 501,
            "status_approval": "yes",
        }
    )
    shm_api.patch_derived_signal_history.assert_called_once_with(601, {"parent_signals": [101]})
    shm_api.create_derived_signal_calibration.assert_called_once_with(
        {
            "calibration_date": "2026-03-24T07:45:00",
            "data": '{"yaw_parameter": "offset", "yaw_offset": 4.5}',
            "derived_signal_id": 501,
            "status_approval": "yes",
        }
    )
    assert result.asset_key == "Project A/Asset-01"
    assert result.signal_ids_by_name == {"NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": 101}
    assert result.derived_signal_ids_by_name == {"NRT_WTG_TP_YAW_LAT01_DEG000_Y": 501}


def test_upload_asset_falls_back_to_signal_lookup_for_parent_ids() -> None:
    shm_api = Mock()
    shm_api.create_derived_signal.return_value = {"id": 501, "exists": True}
    shm_api.create_derived_signal_history.return_value = {"id": 601, "exists": True}
    shm_api.patch_derived_signal_history.return_value = {"id": 601, "exists": True}
    shm_api.create_derived_signal_calibration.return_value = {"id": 701, "exists": True}
    shm_api.get_signal.return_value = {
        "id": 77,
        "exists": True,
        "data": pd.DataFrame([{"id": 77, "signal_id": "EXISTING_SIGNAL"}]),
    }

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    result = uploader.upload_asset(
        AssetSignalUploadRequest(
            projectsite="Project A",
            assetlocation="Asset-01",
            signals={},
            derived_signals={
                "NRT_WTG_TP_YAW_LAT01_DEG000_Y": {
                    "data": {"window": "10m"},
                    "parent_signals": ["EXISTING_SIGNAL"],
                    "calibration": [
                        {
                            "time": "24/03/2026 07:45:00",
                            "yaw_parameter": "offset",
                            "yaw_offset": 4.5,
                        }
                    ],
                }
            },
        )
    )

    shm_api.get_signal.assert_called_once_with("EXISTING_SIGNAL")
    shm_api.patch_derived_signal_history.assert_called_once_with(601, {"parent_signals": [77]})
    assert result.derived_signal_ids_by_name == {"NRT_WTG_TP_YAW_LAT01_DEG000_Y": 501}


def test_upload_asset_skips_invalid_or_incomplete_archive_records() -> None:
    shm_api = Mock()

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    result = uploader.upload_asset(
        AssetSignalUploadRequest(
            projectsite="Project A",
            assetlocation="Asset-01",
            signals={
                "INVALID_SIGNAL": {"heading": "N", "stats": "mean"},
                "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": {"heading": "N"},
            },
            derived_signals={
                "INVALID_DERIVED": {
                    "data": {"window": "10m"},
                    "calibration": [{"time": "24/03/2026 07:45:00"}],
                },
                "NRT_WTG_TP_YAW_LAT01_DEG000_Y": {"data": {"window": "10m"}},
            },
        )
    )

    lookup_service.get_signal_upload_context.assert_called_once_with(
        projectsite="Project A",
        assetlocation="Asset-01",
        permission_group_ids=None,
    )
    assert shm_api.mock_calls == []
    assert result.signal_ids_by_name == {}
    assert result.derived_signal_ids_by_name == {}
    assert result.results_main == []
    assert result.results_secondary == []
    assert result.results_derived_main == []
    assert result.results_derived_secondary == []


def test_upload_asset_raises_when_signal_create_result_has_no_id() -> None:
    shm_api = Mock()
    shm_api.create_signal.return_value = {"exists": True}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    with pytest.raises(
        UploadResultError,
        match="Backend response for signal 'NRT_WTG_TP_STRAIN_LAT02_DEG270_Y' did not include an id",
    ):
        uploader.upload_asset(
            AssetSignalUploadRequest(
                projectsite="Project A",
                assetlocation="Asset-01",
                signals={
                    "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": {
                        "heading": "N",
                        "stats": "mean",
                    }
                },
            )
        )


def test_upload_asset_raises_when_derived_history_result_has_no_id() -> None:
    shm_api = Mock()
    shm_api.create_signal.return_value = {"id": 101, "exists": True}
    shm_api.create_derived_signal.return_value = {"id": 501, "exists": True}
    shm_api.create_derived_signal_history.return_value = {"exists": True}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    with pytest.raises(
        UploadResultError,
        match="Backend response for derived signal history for 'NRT_WTG_TP_YAW_LAT01_DEG000_Y' did not include an id",
    ):
        uploader.upload_asset(
            AssetSignalUploadRequest(
                projectsite="Project A",
                assetlocation="Asset-01",
                signals={
                    "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": {
                        "heading": "N",
                        "stats": "mean",
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
            )
        )


def test_upload_asset_raises_for_non_string_parent_signal_identifier() -> None:
    shm_api = Mock()
    shm_api.create_derived_signal.return_value = {"id": 501, "exists": True}
    shm_api.create_derived_signal_history.return_value = {"id": 601, "exists": True}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    with pytest.raises(
        ParentSignalLookupError,
        match="Derived signal parent_signals must be a sequence of signal identifiers",
    ):
        uploader.upload_asset(
            AssetSignalUploadRequest(
                projectsite="Project A",
                assetlocation="Asset-01",
                signals={},
                derived_signals={
                    "NRT_WTG_TP_YAW_LAT01_DEG000_Y": {
                        "data": {"window": "10m"},
                        "parent_signals": [101],
                        "calibration": [
                            {
                                "time": "24/03/2026 07:45:00",
                                "yaw_parameter": "offset",
                                "yaw_offset": 4.5,
                            }
                        ],
                    }
                },
            )
        )


def test_upload_asset_raises_when_parent_signal_lookup_fails() -> None:
    shm_api = Mock()
    shm_api.create_derived_signal.return_value = {"id": 501, "exists": True}
    shm_api.create_derived_signal_history.return_value = {"id": 601, "exists": True}
    shm_api.get_signal.return_value = {"id": None, "exists": False, "data": pd.DataFrame()}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    with pytest.raises(ParentSignalLookupError, match="Could not resolve parent signal 'MISSING_SIGNAL'"):
        uploader.upload_asset(
            AssetSignalUploadRequest(
                projectsite="Project A",
                assetlocation="Asset-01",
                signals={},
                derived_signals={
                    "NRT_WTG_TP_YAW_LAT01_DEG000_Y": {
                        "data": {"window": "10m"},
                        "parent_signals": ["MISSING_SIGNAL"],
                        "calibration": [
                            {
                                "time": "24/03/2026 07:45:00",
                                "yaw_parameter": "offset",
                                "yaw_offset": 4.5,
                            }
                        ],
                    }
                },
            )
        )


def test_upload_turbines_keeps_turbine_keys_and_uses_explicit_assetlocations() -> None:
    shm_api = Mock()
    shm_api.create_signal.return_value = {"id": 101, "exists": True}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    results = uploader.upload_turbines(
        projectsite="Project A",
        signals_by_turbine={
            "T01": {
                "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": {
                    "heading": "N",
                    "level": 2,
                    "orientation": "Y",
                }
            }
        },
        assetlocations_by_turbine={"T01": "WTG-01"},
        permission_group_ids=[7],
    )

    lookup_service.get_signal_upload_context.assert_called_once_with(
        projectsite="Project A",
        assetlocation="WTG-01",
        permission_group_ids=[7],
    )
    assert tuple(results) == ("T01",)
    assert results["T01"].asset_key == "Project A/WTG-01"
    assert results["T01"].signal_ids_by_name == {"NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": 101}


def test_upload_from_processor_processes_configs_then_uploads_turbines() -> None:
    shm_api = Mock()
    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)
    mock_upload_turbines = Mock(return_value={"T01": Mock(asset_key="Project A/WTG-01")})
    object.__setattr__(uploader, "upload_turbines", mock_upload_turbines)

    processor = Mock()
    processor.signals_data = {
        "T01": {
            "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": {
                "heading": "N",
                "level": 2,
                "orientation": "Y",
            }
        }
    }
    processor.signals_derived_data = {"T01": {}}

    result = uploader.upload_from_processor(
        projectsite="Project A",
        processor=cast(SignalConfigUploadSource, processor),
        assetlocations_by_turbine={"T01": "WTG-01"},
        permission_group_ids=[7, 11],
        sensor_serial_numbers_by_turbine={"T01": {"SIG": 88}},
        temperature_compensation_signal_ids_by_turbine={"T01": {"TC-1": 99}},
    )

    processor.signals_process_data.assert_called_once_with()
    mock_upload_turbines.assert_called_once_with(
        projectsite="Project A",
        signals_by_turbine=processor.signals_data,
        derived_signals_by_turbine=processor.signals_derived_data,
        assetlocations_by_turbine={"T01": "WTG-01"},
        permission_group_ids=[7, 11],
        sensor_serial_numbers_by_turbine={"T01": {"SIG": 88}},
        temperature_compensation_signal_ids_by_turbine={"T01": {"TC-1": 99}},
    )
    assert tuple(result) == ("T01",)


def test_upload_from_processor_files_resolves_archive_style_file_maps(
    tmp_path,
) -> None:
    signal_name = "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y"
    signal_sensor_map_path = tmp_path / "signal_sensor_map.json"
    signal_sensor_map_path.write_text(
        json.dumps(
            {
                "T01": {
                    signal_name: {
                        "sensor_type_id": {"description": "Strain sensor"},
                        "serial_number": "SG-01",
                        "cabinet": "CAB-1",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    sensor_tc_map_path = tmp_path / "sensor_tc_map.json"
    sensor_tc_map_path.write_text(
        json.dumps({"T01": ["TC-001"]}),
        encoding="utf-8",
    )

    shm_api = Mock()
    shm_api.get_sensor_type.return_value = {"id": 801, "exists": True}
    shm_api.get_sensor.return_value = {"id": 88, "exists": True}
    shm_api.get_signal.return_value = {"id": 909, "exists": True}
    shm_api.create_signal.return_value = {"id": 101, "exists": True}
    shm_api.create_signal_history.return_value = {"id": 201, "exists": True}
    shm_api.create_signal_calibration.return_value = {"id": 301, "exists": True}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    processor = Mock()
    processor.signals_data = {
        "T01": {
            signal_name: {
                "heading": "N",
                "level": 2,
                "orientation": "Y",
                "status": [{"time": "24/03/2026 08:00:00", "status": "ok"}],
                "offset": [
                    {
                        "time": "24/03/2026 08:15:00",
                        "offset": 1.25,
                        "TCSensor": "TC-001",
                    }
                ],
            }
        }
    }
    processor.signals_derived_data = {"T01": {}}

    results = uploader.upload_from_processor_files(
        projectsite="Project A",
        processor=cast(SignalConfigUploadSource, processor),
        path_signal_sensor_map=signal_sensor_map_path,
        path_sensor_tc_map=sensor_tc_map_path,
        assetlocations_by_turbine={"T01": "WTG-01"},
        permission_group_ids=[7],
    )

    processor.signals_process_data.assert_called_once_with()
    shm_api.get_sensor_type.assert_called_once_with(description="Strain sensor")
    shm_api.get_sensor.assert_called_once_with(
        sensor_type_id=801,
        serial_number="SG-01",
        cabinet="CAB-1",
    )
    shm_api.get_signal.assert_called_once_with("TC-001")
    lookup_service.get_signal_upload_context.assert_called_once_with(
        projectsite="Project A",
        assetlocation="WTG-01",
        permission_group_ids=[7],
    )
    shm_api.create_signal_history.assert_called_once_with(
        {
            "signal_id": 101,
            "activity_start_timestamp": "2026-03-24T08:00:00",
            "is_latest_status": True,
            "status": "ok",
            "sensor_serial_number": 88,
            "status_approval": "yes",
        }
    )
    shm_api.create_signal_calibration.assert_called_once_with(
        {
            "signal_id": 101,
            "calibration_date": "2026-03-24T08:15:00",
            "data": '{"offset": 1.25}',
            "tempcomp_signal_id": 909,
            "status_approval": "yes",
        }
    )
    assert tuple(results) == ("T01",)
    assert results["T01"].asset_key == "Project A/WTG-01"


def test_upload_from_processor_batches_real_config_files_through_public_src_surface(tmp_path) -> None:
    (tmp_path / "T01.json").write_text(
        json.dumps(
            [
                {
                    "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/status": "ok",
                    "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/offset": 1.2,
                    "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/temperature_compensation": {"TCSensor": "TC-1"},
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "T02.json").write_text(
        json.dumps(
            [
                {
                    "time": "24/03/2026 09:00:00",
                    "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y/heading": "south",
                    "NRT_WTG_TP_STRAIN_LAT02_DEG270_Y/status": "maintenance",
                }
            ]
        ),
        encoding="utf-8",
    )

    processor = ConfiguredSignalConfigProcessor(
        path_configs=tmp_path,
        processor_spec=_packaged_processor_spec(),
    )

    shm_api = Mock()
    shm_api.create_signal.side_effect = [
        {"id": 101, "exists": True},
        {"id": 102, "exists": True},
    ]
    shm_api.create_signal_history.side_effect = [
        {"id": 201, "exists": True},
        {"id": 202, "exists": True},
    ]
    shm_api.create_signal_calibration.return_value = {"id": 301, "exists": True}

    lookup_service = Mock()
    lookup_service.get_signal_upload_context.return_value = _upload_context()
    uploader = ShmSignalUploader(shm_api=shm_api, lookup_service=lookup_service)

    results = uploader.upload_from_processor(
        projectsite="Project A",
        processor=cast(SignalConfigUploadSource, processor),
        assetlocations_by_turbine={"T01": "WTG-01"},
        sensor_serial_numbers_by_turbine={"T01": {"NRT_WTG_TP_STRAIN_LAT01_DEG000_Y": 88}},
        temperature_compensation_signal_ids_by_turbine={"T01": {"TC-1": 909}},
    )

    assert tuple(results) == ("T01", "T02")
    assert results["T01"].asset_key == "Project A/WTG-01"
    assert results["T01"].signal_ids_by_name == {"NRT_WTG_TP_STRAIN_LAT01_DEG000_Y": 101}
    assert results["T02"].asset_key == "Project A/T02"
    assert results["T02"].signal_ids_by_name == {"NRT_WTG_TP_STRAIN_LAT02_DEG270_Y": 102}
    assert lookup_service.get_signal_upload_context.call_args_list == [
        call(
            projectsite="Project A",
            assetlocation="WTG-01",
            permission_group_ids=None,
        ),
        call(
            projectsite="Project A",
            assetlocation="T02",
            permission_group_ids=None,
        ),
    ]
    assert shm_api.create_signal_history.call_args_list == [
        call(
            {
                "signal_id": 101,
                "activity_start_timestamp": "1972-01-01T00:00:00",
                "is_latest_status": True,
                "status": "ok",
                "sensor_serial_number": 88,
                "status_approval": "yes",
            }
        ),
        call(
            {
                "signal_id": 102,
                "activity_start_timestamp": "2026-03-24T09:00:00",
                "is_latest_status": True,
                "status": "maintenance",
                "sensor_serial_number": None,
                "status_approval": "yes",
            }
        ),
    ]
    shm_api.create_signal_calibration.assert_called_once_with(
        {
            "signal_id": 101,
            "calibration_date": "1972-01-01T00:00:00",
            "data": '{"offset": 1.2}',
            "tempcomp_signal_id": 909,
            "status_approval": "yes",
        }
    )


def test_request_factory_accepts_generic_processor_output() -> None:
    processor = ConfiguredSignalConfigProcessor(
        path_configs=".",
        processor_spec=_packaged_processor_spec(),
    )
    processing_result = processor.process_events(
        [
            {
                "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/offset": 1.2,
                "NRT_WTG_TP_STRAIN_LAT01_DEG000_Y/temperature_compensation": {"TCSensor": "TC-1"},
                "acceleration/yaw_transformation": {
                    "levels": ["NRT_WTG_TP_ACC_LAT01_DEG000"],
                    "yaw_parameter": 1.0,
                    "yaw_offset": 2.0,
                    "NRT_WTG_TP_ACC_LAT01_DEG000": ["SIG_A", "SIG_B"],
                },
            }
        ]
    )

    request = AssetSignalUploadRequest.from_processing_result(
        projectsite="Project A",
        assetlocation="Asset-01",
        processing_result=processing_result,
        permission_group_ids=[7],
    )

    assert request.result_key == "Project A/Asset-01"
    assert request.permission_group_ids == [7]
    assert request.signals["NRT_WTG_TP_STRAIN_LAT01_DEG000_Y"]["offset"][0] == {
        "time": "01/01/1972 00:00",
        "offset": 1.2,
        "TCSensor": "TC-1",
    }
    assert request.derived_signals == {
        "NRT_WTG_TP_ACC_LAT01_DEG000_FA": {
            "data": {"name": "acceleration/yaw_transformation"},
            "calibration": [{"time": "01/01/1972 00:00", "yaw_parameter": 1.0, "yaw_offset": 2.0}],
            "parent_signals": ["SIG_A", "SIG_B"],
        },
        "NRT_WTG_TP_ACC_LAT01_DEG000_SS": {
            "data": {"name": "acceleration/yaw_transformation"},
            "calibration": [{"time": "01/01/1972 00:00", "yaw_parameter": 1.0, "yaw_offset": 2.0}],
            "parent_signals": ["SIG_A", "SIG_B"],
        },
    }

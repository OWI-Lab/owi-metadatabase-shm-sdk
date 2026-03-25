"""Sensor upload orchestration for SHM assets.

This module provides :class:`ShmSensorUploader` which handles the three-phase
sensor upload workflow that mirrors the archive ``SensorsUploader``:

1. Upload sensor types (with optional image attachments).
2. Upload sensors (per-turbine, per-sensor-category).
3. Upload sensor calibrations (with optional PDF attachments).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from .errors import ShmUploadError
from .payloads import (
    SensorCalibrationPayload,
    SensorTypePayload,
    build_sensor_calibration_payloads,
    build_sensor_payloads,
    build_sensor_type_payloads,
)


class ShmSensorUploadClient(Protocol):
    """Protocol describing the SHM transport methods used by the sensor uploader."""

    def get_sensor_type(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one SHM sensor type record."""
        ...

    def get_sensor(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one SHM sensor record."""
        ...

    def create_sensor_type(
        self, payload: Mapping[str, Any], files: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a sensor type record."""
        ...

    def create_sensor(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a sensor record."""
        ...

    def create_sensor_calibration(
        self, payload: Mapping[str, Any], files: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a sensor calibration record."""
        ...


SensorsDataByTurbine = Mapping[str, Mapping[str, Any] | None]


class ShmSensorUploader:
    """Upload sensor types, sensors, and sensor calibrations for SHM assets.

    Parameters
    ----------
    shm_api
        SHM transport client that satisfies :class:`ShmSensorUploadClient`.
    """

    def __init__(self, shm_api: ShmSensorUploadClient) -> None:
        self.shm_api = shm_api

    def upload_sensor_types(
        self,
        sensor_types_data: Sequence[Mapping[str, Any]],
        permission_group_ids: Sequence[int] | None,
        path_to_images: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Upload sensor type records, optionally with image attachments.

        Parameters
        ----------
        sensor_types_data
            List of sensor type records (e.g. loaded from ``sensor_types.json``).
        permission_group_ids
            Permission groups applied to every sensor type.
        path_to_images
            Optional directory containing sensor type image files.

        Returns
        -------
        list[dict[str, Any]]
            Raw backend responses for each created sensor type.
        """
        payloads = build_sensor_type_payloads(
            sensor_types_data,
            visibility_groups=permission_group_ids,
            path_to_images=path_to_images,
        )
        return [self._upload_sensor_type(payload) for payload in payloads]

    def _upload_sensor_type(self, payload: SensorTypePayload) -> dict[str, Any]:
        files = payload.to_files()
        return self.shm_api.create_sensor_type(payload.to_payload(), files=files)

    def upload_sensors(
        self,
        sensor_type_name: str,
        sensor_type_params: Mapping[str, str],
        sensors_data: SensorsDataByTurbine,
        permission_group_ids: Sequence[int] | None,
        turbines: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Upload sensor records for a single sensor category across turbines.

        Parameters
        ----------
        sensor_type_name
            Key identifying the sensor category within each turbine's data
            (e.g. ``"accelerometers"``).
        sensor_type_params
            Query parameters used to resolve the backend sensor type id
            (e.g. ``{"name": "393B04"}``).
        sensors_data
            Per-turbine sensor data keyed by turbine identifier. Each turbine
            has categories mapping to ``{"serial_numbers": [...], "cabinets": [...]}``.
        permission_group_ids
            Permission groups applied to every sensor.
        turbines
            Optional filter to upload only specific turbines. When *None*,
            all turbines in ``sensors_data`` are processed.

        Returns
        -------
        list[dict[str, Any]]
            Raw backend responses for each created sensor.
        """
        sensor_type_result = self.shm_api.get_sensor_type(**dict(sensor_type_params))
        sensor_type_id = self._require_existing_result_id(
            sensor_type_result,
            label=f"sensor type '{sensor_type_name}'",
        )

        serial_numbers: list[str | None] = []
        cabinets: list[str | int | None] = []
        turbine_keys = turbines if turbines is not None else list(sensors_data.keys())

        for turbine in turbine_keys:
            data_turbine = sensors_data.get(turbine)
            self._collect_sensor_columns(
                data_turbine,
                sensor_type_name,
                serial_numbers,
                cabinets,
                turbine,
            )

        if not serial_numbers and not cabinets:
            return []

        payloads = build_sensor_payloads(
            sensor_type_id=sensor_type_id,
            serial_numbers=serial_numbers,
            cabinets=cabinets,
            visibility_groups=permission_group_ids,
        )
        return [self.shm_api.create_sensor(p.to_payload()) for p in payloads]

    @staticmethod
    def _collect_sensor_columns(
        data_turbine: Mapping[str, Any] | None,
        sensor_type_name: str,
        serial_numbers: list[str | None],
        cabinets: list[str | int | None],
        turbine: str,
    ) -> None:
        """Collect serial numbers and cabinets from one turbine's data."""
        if data_turbine is None:
            return
        data_category = data_turbine.get(sensor_type_name)
        if data_category is None:
            return

        sn = data_category.get("serial_numbers")
        cb = data_category.get("cabinets")

        if sn is not None and cb is not None and len(sn) != len(cb):
            raise ShmUploadError(
                f"Length of serial numbers ({len(sn)}) and cabinets ({len(cb)}) "
                f"do not match for sensor type '{sensor_type_name}' on turbine '{turbine}'."
            )

        if sn is None and cb is not None:
            sn = [None] * len(cb)
        if cb is None and sn is not None:
            cb = [None] * len(sn)

        if sn is not None:
            serial_numbers.extend(sn)
        if cb is not None:
            cabinets.extend(cb)

    def upload_sensor_calibrations(
        self,
        signal_sensor_map_data: Mapping[str, Mapping[str, Mapping[str, Any]]],
        signal_calibration_map_data: Mapping[str, Mapping[str, Mapping[str, str]]],
        path_to_datasheets: str | Path,
        turbines: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Upload sensor calibration records with optional PDF attachments.

        Parameters
        ----------
        signal_sensor_map_data
            Per-turbine signal-to-sensor mapping (keyed by turbine, then signal
            name, with sensor lookup params including ``sensor_type_id``).
        signal_calibration_map_data
            Per-turbine calibration data (keyed by turbine, then signal name,
            with ``date`` and ``filename`` fields).
        path_to_datasheets
            Directory containing calibration PDF files.
        turbines
            Optional turbine filter. When *None*, all turbines are processed.

        Returns
        -------
        list[dict[str, Any]]
            Raw backend responses for each created calibration.
        """
        results: list[dict[str, Any]] = []
        turbine_keys = turbines if turbines is not None else list(signal_sensor_map_data.keys())

        for turbine in turbine_keys:
            turbine_ss_map = signal_sensor_map_data.get(turbine)
            turbine_sc_map = signal_calibration_map_data.get(turbine)
            if turbine_ss_map is None:
                continue

            resolved_sensor_ids = self._resolve_sensor_ids_for_turbine(turbine_ss_map, turbine)

            if turbine_sc_map is not None:
                payloads = build_sensor_calibration_payloads(
                    signal_sensor_map=resolved_sensor_ids,
                    signal_calibration_map=turbine_sc_map,
                    path_to_datasheets=path_to_datasheets,
                )
                for payload in payloads:
                    results.append(self._upload_sensor_calibration(payload))

        return results

    def _resolve_sensor_ids_for_turbine(
        self,
        turbine_ss_map: Mapping[str, Mapping[str, Any]],
        turbine: str,
    ) -> dict[str, int]:
        """Resolve backend sensor ids for all signals in a turbine's sensor map."""
        resolved: dict[str, int] = {}
        for signal_name, sensor_lookup in turbine_ss_map.items():
            params = dict(sensor_lookup)
            sensor_type_lookup = params.get("sensor_type_id")
            if isinstance(sensor_type_lookup, Mapping):
                sensor_type_result = self.shm_api.get_sensor_type(**dict(sensor_type_lookup))
                params["sensor_type_id"] = self._require_existing_result_id(
                    sensor_type_result,
                    label=f"sensor type for signal '{signal_name}' on turbine '{turbine}'",
                )
            sensor_result = self.shm_api.get_sensor(**params)
            resolved[signal_name] = self._require_existing_result_id(
                sensor_result,
                label=f"sensor for signal '{signal_name}' on turbine '{turbine}'",
            )
        return resolved

    def _upload_sensor_calibration(self, payload: SensorCalibrationPayload) -> dict[str, Any]:
        data = payload.to_payload()
        file_path = Path(data.pop("file"))
        if file_path.exists():
            files = {"file": (file_path.name, file_path.open("rb"))}
            return self.shm_api.create_sensor_calibration(data, files=files)
        return self.shm_api.create_sensor_calibration(data)

    def _require_existing_result_id(
        self,
        result: Mapping[str, Any],
        *,
        label: str,
    ) -> int:
        if not result.get("exists", False):
            raise ShmUploadError(f"Could not resolve {label}.")
        record_id = result.get("id")
        if record_id is None:
            raise ShmUploadError(f"Backend response for {label} did not include an id.")
        return int(record_id)

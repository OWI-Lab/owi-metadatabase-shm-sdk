"""Generic backend-facing signal upload orchestration for SHM assets.

This module keeps asset lookup, payload building, and transport on their
existing seams:

- parent SDK lookups are resolved through :class:`ParentSDKLookupService`
- archive-compatible payload shapes come from :mod:`owi.metadatabase.shm.upload.payloads`
- HTTP transport stays on :class:`owi.metadatabase.shm.io.ShmAPI`
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from ..json_utils import load_json_data
from ..lookup import (
    ParentGeometryLookupClient,
    ParentLocationsLookupClient,
    ParentSDKLookupService,
)
from ..signal_ids import parse_legacy_signal_id
from ..upload_context import SignalUploadContext
from .errors import ParentSignalLookupError, ShmUploadError, UploadResultError
from .models import (
    AssetSignalUploadRequest,
    AssetSignalUploadResult,
    SignalConfigMap,
    SignalConfigMapByTurbine,
)
from .payloads import (
    build_derived_signal_calibration_payloads,
    build_derived_signal_main_payload,
    build_derived_signal_parent_patch,
    build_derived_signal_status_payload,
    build_signal_calibration_payloads,
    build_signal_main_payload,
    build_signal_status_payloads,
)
from .protocols import ShmSignalUploadClient, SignalConfigUploadSource


class ShmSignalUploader:
    """Upload archive-compatible SHM signal data for arbitrary wind-farm assets.

    Parameters
    ----------
    shm_api
        SHM transport client, typically :class:`owi.metadatabase.shm.ShmAPI`.
    lookup_service
        Parent SDK lookup service used to resolve site, asset, and
        subassembly ids.
    """

    def __init__(
        self,
        shm_api: ShmSignalUploadClient,
        lookup_service: ParentSDKLookupService,
    ) -> None:
        self.shm_api = shm_api
        self.lookup_service = lookup_service

    @classmethod
    def from_clients(
        cls,
        shm_api: ShmSignalUploadClient,
        locations_client: ParentLocationsLookupClient,
        geometry_client: ParentGeometryLookupClient,
    ) -> ShmSignalUploader:
        """Construct the uploader from SHM and parent SDK clients.

        Parameters
        ----------
        shm_api
            SHM transport client used for backend mutations.
        locations_client
            Parent SDK client that resolves project and asset locations.
        geometry_client
            Parent SDK client that resolves subassemblies and model
            definitions.

        Returns
        -------
        ShmSignalUploader
            Uploader wired to the canonical SHM lookup service.
        """
        return cls(
            shm_api=shm_api,
            lookup_service=ParentSDKLookupService(
                locations_client=locations_client,
                geometry_client=geometry_client,
            ),
        )

    def upload_asset(self, request: AssetSignalUploadRequest) -> AssetSignalUploadResult:
        """Upload main and secondary SHM records for one asset.

        Parameters
        ----------
        request
            Asset-scoped upload request containing the archive-compatible main
            and derived signal mappings.

        Returns
        -------
        AssetSignalUploadResult
            Created backend ids plus raw backend responses grouped by upload
            phase.
        """
        upload_context = self.lookup_service.get_signal_upload_context(
            projectsite=request.projectsite,
            assetlocation=request.assetlocation,
            permission_group_ids=request.permission_group_ids,
        )
        signal_ids_by_name, results_main = self._upload_main_signals(
            request.signals,
            upload_context,
        )
        results_secondary = self._upload_signal_secondary_data(
            request.signals,
            signal_ids_by_name=signal_ids_by_name,
            sensor_serial_numbers_by_signal=request.sensor_serial_numbers_by_signal,
            temperature_compensation_signal_ids=request.temperature_compensation_signal_ids,
        )

        derived_signal_ids_by_name: dict[str, int] = {}
        results_derived_main: list[dict[str, Any]] = []
        results_derived_secondary: list[dict[str, Any]] = []
        if request.derived_signals:
            derived_signal_ids_by_name, results_derived_main = self._upload_main_derived_signals(
                request.derived_signals,
                upload_context,
            )
            results_derived_secondary = self._upload_derived_signal_secondary_data(
                request.derived_signals,
                signal_ids_by_name=signal_ids_by_name,
                derived_signal_ids_by_name=derived_signal_ids_by_name,
            )

        return AssetSignalUploadResult(
            asset_key=request.result_key,
            signal_ids_by_name=signal_ids_by_name,
            derived_signal_ids_by_name=derived_signal_ids_by_name,
            results_main=results_main,
            results_secondary=results_secondary,
            results_derived_main=results_derived_main,
            results_derived_secondary=results_derived_secondary,
        )

    def upload_assets(
        self,
        requests: Sequence[AssetSignalUploadRequest],
    ) -> dict[str, AssetSignalUploadResult]:
        """Upload SHM signal data for multiple assets.

        Parameters
        ----------
        requests
            Asset-scoped upload requests to execute in order.

        Returns
        -------
        dict[str, AssetSignalUploadResult]
            Upload results keyed by each request's stable result key.
        """
        return {request.result_key: self.upload_asset(request) for request in requests}

    def upload_turbines(
        self,
        *,
        projectsite: str,
        signals_by_turbine: SignalConfigMapByTurbine,
        derived_signals_by_turbine: SignalConfigMapByTurbine | None = None,
        assetlocations_by_turbine: Mapping[str, str] | None = None,
        permission_group_ids: Sequence[int] | None = None,
        sensor_serial_numbers_by_turbine: Mapping[str, Mapping[str, int]] | None = None,
        temperature_compensation_signal_ids_by_turbine: Mapping[str, Mapping[str, int]] | None = None,
    ) -> dict[str, AssetSignalUploadResult]:
        """Upload SHM signal data for multiple turbine-scoped config bundles.

        Parameters
        ----------
        projectsite
            Parent SDK project site title shared by the turbine batch.
        signals_by_turbine
            Main signal mappings keyed by turbine identifier.
        derived_signals_by_turbine
            Optional derived signal mappings keyed by turbine identifier.
        assetlocations_by_turbine
            Optional turbine-to-asset-location override mapping.
        permission_group_ids
            Visibility groups applied to created SHM objects.
        sensor_serial_numbers_by_turbine
            Optional per-turbine mapping of signal identifiers to sensor serial
            numbers used for signal history rows.
        temperature_compensation_signal_ids_by_turbine
            Optional per-turbine mapping of temperature-compensation tokens to
            backend SHM signal ids.

        Returns
        -------
        dict[str, AssetSignalUploadResult]
            Upload results keyed by turbine identifier.

        This keeps the response keyed by turbine while parent lookups use the
        corresponding asset-location title.
        """
        results: dict[str, AssetSignalUploadResult] = {}
        for turbine, signals in signals_by_turbine.items():
            assetlocation = turbine
            if assetlocations_by_turbine is not None:
                assetlocation = assetlocations_by_turbine.get(turbine, turbine)

            derived_signals = None
            if derived_signals_by_turbine is not None:
                derived_signals = derived_signals_by_turbine.get(turbine)

            sensor_serial_numbers_by_signal = None
            if sensor_serial_numbers_by_turbine is not None:
                sensor_serial_numbers_by_signal = sensor_serial_numbers_by_turbine.get(turbine)

            temperature_compensation_signal_ids = None
            if temperature_compensation_signal_ids_by_turbine is not None:
                temperature_compensation_signal_ids = temperature_compensation_signal_ids_by_turbine.get(turbine)

            results[turbine] = self.upload_asset(
                AssetSignalUploadRequest(
                    projectsite=projectsite,
                    assetlocation=assetlocation,
                    signals=signals,
                    derived_signals=derived_signals,
                    permission_group_ids=permission_group_ids,
                    sensor_serial_numbers_by_signal=sensor_serial_numbers_by_signal,
                    temperature_compensation_signal_ids=temperature_compensation_signal_ids,
                )
            )
        return results

    def upload_from_processor(
        self,
        *,
        projectsite: str,
        processor: SignalConfigUploadSource,
        assetlocations_by_turbine: Mapping[str, str] | None = None,
        permission_group_ids: Sequence[int] | None = None,
        sensor_serial_numbers_by_turbine: Mapping[str, Mapping[str, int]] | None = None,
        temperature_compensation_signal_ids_by_turbine: Mapping[str, Mapping[str, int]] | None = None,
    ) -> dict[str, AssetSignalUploadResult]:
        """Process turbine configs and upload them through the generic SHM seam.

        Parameters
        ----------
        projectsite
            Parent SDK project site title shared by the processor output.
        processor
            Processor instance that populates ``signals_data`` and
            ``signals_derived_data``.
        assetlocations_by_turbine
            Optional turbine-to-asset-location override mapping.
        permission_group_ids
            Visibility groups applied to created SHM objects.
        sensor_serial_numbers_by_turbine
            Optional per-turbine mapping of signal identifiers to sensor serial
            numbers used for signal history rows.
        temperature_compensation_signal_ids_by_turbine
            Optional per-turbine mapping of temperature-compensation tokens to
            backend SHM signal ids.

        Returns
        -------
        dict[str, AssetSignalUploadResult]
            Upload results keyed by turbine identifier.
        """
        processor.signals_process_data()
        return self.upload_turbines(
            projectsite=projectsite,
            signals_by_turbine=processor.signals_data,
            derived_signals_by_turbine=processor.signals_derived_data,
            assetlocations_by_turbine=assetlocations_by_turbine,
            permission_group_ids=permission_group_ids,
            sensor_serial_numbers_by_turbine=sensor_serial_numbers_by_turbine,
            temperature_compensation_signal_ids_by_turbine=(
                temperature_compensation_signal_ids_by_turbine
            ),
        )

    def upload_from_processor_files(
        self,
        *,
        projectsite: str,
        processor: SignalConfigUploadSource,
        path_signal_sensor_map: str | Path | None = None,
        path_sensor_tc_map: str | Path | None = None,
        assetlocations_by_turbine: Mapping[str, str] | None = None,
        permission_group_ids: Sequence[int] | None = None,
    ) -> dict[str, AssetSignalUploadResult]:
        """Process configs, resolve optional file maps, and upload by turbine.

        Parameters
        ----------
        projectsite
            Parent SDK project site title shared by the batch.
        processor
            Processor that populates turbine-scoped signal mappings.
        path_signal_sensor_map
            Optional JSON file keyed by turbine and signal id with SHM sensor
            lookup parameters. When ``sensor_type_id`` is itself a mapping,
            the uploader resolves it through ``get_sensor_type()`` before the
            final sensor lookup.
        path_sensor_tc_map
            Optional JSON file keyed by turbine with temperature-
            compensation signal identifiers to resolve through
            ``get_signal()``.
        assetlocations_by_turbine
            Optional turbine-to-asset-location override mapping.
        permission_group_ids
            Visibility groups applied to created SHM objects.

        Returns
        -------
        dict[str, AssetSignalUploadResult]
            Upload results keyed by turbine identifier.

        Examples
        --------
        >>> from unittest.mock import Mock
        >>> uploader = ShmSignalUploader(shm_api=Mock(), lookup_service=Mock())
        >>> processor = Mock()
        >>> processor.signals_data = {}
        >>> processor.signals_derived_data = {}
        >>> uploader.upload_from_processor_files(projectsite="Project A", processor=processor)
        {}
        """
        processor.signals_process_data()
        sensor_serial_numbers_by_turbine = self._resolve_sensor_serial_numbers_by_turbine(
            path_signal_sensor_map
        )
        temperature_compensation_signal_ids_by_turbine = (
            self._resolve_temperature_compensation_signal_ids_by_turbine(
                path_sensor_tc_map
            )
        )
        return self.upload_turbines(
            projectsite=projectsite,
            signals_by_turbine=processor.signals_data,
            derived_signals_by_turbine=processor.signals_derived_data,
            assetlocations_by_turbine=assetlocations_by_turbine,
            permission_group_ids=permission_group_ids,
            sensor_serial_numbers_by_turbine=sensor_serial_numbers_by_turbine,
            temperature_compensation_signal_ids_by_turbine=(
                temperature_compensation_signal_ids_by_turbine
            ),
        )

    @staticmethod
    def _load_turbine_file_map(
        path_to_map: str | Path | None,
        *,
        label: str,
    ) -> Mapping[str, Any] | None:
        payload = load_json_data(path_to_map)
        if payload is None:
            return None
        if not isinstance(payload, Mapping):
            raise ShmUploadError(f"{label} must contain an object keyed by turbine.")
        return cast(Mapping[str, Any], payload)

    def _resolve_sensor_serial_numbers_by_turbine(
        self,
        path_signal_sensor_map: str | Path | None,
    ) -> dict[str, dict[str, int]] | None:
        raw_map = self._load_turbine_file_map(
            path_signal_sensor_map,
            label="Signal-sensor map",
        )
        if raw_map is None:
            return None

        resolved: dict[str, dict[str, int]] = {}
        for turbine, turbine_map in raw_map.items():
            if not isinstance(turbine, str):
                raise ShmUploadError("Signal-sensor map keys must be turbine names.")
            if not isinstance(turbine_map, Mapping):
                raise ShmUploadError(
                    f"Signal-sensor map for turbine '{turbine}' must be an object keyed by signal id."
                )

            resolved[turbine] = {}
            for signal_name, sensor_lookup in turbine_map.items():
                if not isinstance(signal_name, str):
                    raise ShmUploadError(
                        f"Signal-sensor map for turbine '{turbine}' must use string signal ids."
                    )
                if not isinstance(sensor_lookup, Mapping):
                    raise ShmUploadError(
                        f"Sensor lookup for signal '{signal_name}' on turbine '{turbine}' must be an object."
                    )

                resolved[turbine][signal_name] = self._resolve_sensor_record_id(
                    sensor_lookup=sensor_lookup,
                    turbine=turbine,
                    signal_name=signal_name,
                )

        return resolved

    def _resolve_sensor_record_id(
        self,
        *,
        sensor_lookup: Mapping[str, Any],
        turbine: str,
        signal_name: str,
    ) -> int:
        resolved_lookup = dict(sensor_lookup)
        sensor_type_lookup = resolved_lookup.get("sensor_type_id")
        if isinstance(sensor_type_lookup, Mapping):
            sensor_type_result = self.shm_api.get_sensor_type(**dict(sensor_type_lookup))
            resolved_lookup["sensor_type_id"] = self._require_existing_result_id(
                sensor_type_result,
                label=f"sensor type for signal '{signal_name}' on turbine '{turbine}'",
            )

        sensor_result = self.shm_api.get_sensor(**resolved_lookup)
        return self._require_existing_result_id(
            sensor_result,
            label=f"sensor for signal '{signal_name}' on turbine '{turbine}'",
        )

    def _resolve_temperature_compensation_signal_ids_by_turbine(
        self,
        path_sensor_tc_map: str | Path | None,
    ) -> dict[str, dict[str, int]] | None:
        raw_map = self._load_turbine_file_map(
            path_sensor_tc_map,
            label="Temperature-compensation map",
        )
        if raw_map is None:
            return None

        resolved: dict[str, dict[str, int]] = {}
        for turbine, signal_names in raw_map.items():
            if not isinstance(turbine, str):
                raise ShmUploadError(
                    "Temperature-compensation map keys must be turbine names."
                )
            if not isinstance(signal_names, Sequence) or isinstance(signal_names, (str, bytes)):
                raise ShmUploadError(
                    f"Temperature-compensation map for turbine '{turbine}' must be a list of signal ids."
                )

            resolved[turbine] = {}
            for signal_name in signal_names:
                if not isinstance(signal_name, str):
                    raise ShmUploadError(
                        f"Temperature-compensation map for turbine '{turbine}' must contain string signal ids."
                    )
                result = self.shm_api.get_signal(signal_name)
                resolved[turbine][signal_name] = self._require_existing_result_id(
                    result,
                    label=(
                        f"temperature-compensation signal '{signal_name}' on turbine "
                        f"'{turbine}'"
                    ),
                )

        return resolved

    def _upload_main_signals(
        self,
        signals: SignalConfigMap,
        upload_context: SignalUploadContext,
    ) -> tuple[dict[str, int], list[dict[str, Any]]]:
        signal_ids_by_name: dict[str, int] = {}
        results: list[dict[str, Any]] = []
        for signal_name, signal_data in signals.items():
            parsed_signal = parse_legacy_signal_id(signal_name)
            if parsed_signal is None:
                continue

            payload = build_signal_main_payload(parsed_signal, signal_data, upload_context)
            if payload is None:
                continue

            result = self.shm_api.create_signal(payload)
            signal_ids_by_name[signal_name] = self._require_result_id(
                result,
                label=f"signal '{signal_name}'",
            )
            results.append(result)
        return signal_ids_by_name, results

    def _upload_signal_secondary_data(
        self,
        signals: SignalConfigMap,
        signal_ids_by_name: Mapping[str, int],
        sensor_serial_numbers_by_signal: Mapping[str, int] | None,
        temperature_compensation_signal_ids: Mapping[str, int] | None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for signal_name, signal_data in signals.items():
            signal_id = signal_ids_by_name.get(signal_name)
            if signal_id is None:
                continue

            sensor_serial_number = None
            if sensor_serial_numbers_by_signal is not None:
                sensor_serial_number = sensor_serial_numbers_by_signal.get(signal_name)

            for payload in build_signal_status_payloads(
                signal_id,
                signal_data,
                sensor_serial_number=sensor_serial_number,
            ):
                results.append(self.shm_api.create_signal_history(payload))

            for payload in build_signal_calibration_payloads(
                signal_id,
                signal_data,
                tempcomp_signal_ids=temperature_compensation_signal_ids,
            ):
                results.append(self.shm_api.create_signal_calibration(payload))

        return results

    def _upload_main_derived_signals(
        self,
        derived_signals: SignalConfigMap,
        upload_context: SignalUploadContext,
    ) -> tuple[dict[str, int], list[dict[str, Any]]]:
        derived_signal_ids_by_name: dict[str, int] = {}
        results: list[dict[str, Any]] = []
        for signal_name, signal_data in derived_signals.items():
            parsed_signal = parse_legacy_signal_id(signal_name)
            if parsed_signal is None:
                continue

            payload = build_derived_signal_main_payload(parsed_signal, signal_data, upload_context)
            if payload is None:
                continue

            result = self.shm_api.create_derived_signal(payload)
            derived_signal_ids_by_name[signal_name] = self._require_result_id(
                result,
                label=f"derived signal '{signal_name}'",
            )
            results.append(result)
        return derived_signal_ids_by_name, results

    def _upload_derived_signal_secondary_data(
        self,
        derived_signals: SignalConfigMap,
        signal_ids_by_name: Mapping[str, int],
        derived_signal_ids_by_name: Mapping[str, int],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for signal_name, signal_data in derived_signals.items():
            derived_signal_id = derived_signal_ids_by_name.get(signal_name)
            if derived_signal_id is None:
                continue

            status_payload = build_derived_signal_status_payload(
                derived_signal_id,
                signal_data,
            )
            status_result = self.shm_api.create_derived_signal_history(status_payload)
            results.append(status_result)

            parent_signal_ids = self._resolve_parent_signal_ids(
                signal_data=signal_data,
                signal_ids_by_name=signal_ids_by_name,
            )
            if parent_signal_ids:
                history_id = self._require_result_id(
                    status_result,
                    label=f"derived signal history for '{signal_name}'",
                )
                patch_payload = build_derived_signal_parent_patch(parent_signal_ids)
                results.append(self.shm_api.patch_derived_signal_history(history_id, patch_payload))

            for payload in build_derived_signal_calibration_payloads(
                derived_signal_id,
                signal_data,
            ):
                results.append(self.shm_api.create_derived_signal_calibration(payload))

        return results

    def _resolve_parent_signal_ids(
        self,
        signal_data: Mapping[str, Any],
        signal_ids_by_name: Mapping[str, int],
    ) -> list[int]:
        parent_signals = signal_data.get("parent_signals")
        if not isinstance(parent_signals, Sequence) or isinstance(parent_signals, (str, bytes)):
            return []

        parent_signal_ids: list[int] = []
        for parent_signal_name in parent_signals:
            if not isinstance(parent_signal_name, str):
                raise ParentSignalLookupError(
                    "Derived signal parent_signals must be a sequence of signal identifiers."
                )

            parent_signal_id = signal_ids_by_name.get(parent_signal_name)
            if parent_signal_id is None:
                result = self.shm_api.get_signal(parent_signal_name)
                if not result.get("exists", False):
                    raise ParentSignalLookupError(
                        f"Could not resolve parent signal '{parent_signal_name}'."
                    )
                parent_signal_id = self._require_result_id(
                    result,
                    label=f"parent signal '{parent_signal_name}'",
                )
            parent_signal_ids.append(parent_signal_id)
        return parent_signal_ids

    def _require_existing_result_id(
        self,
        result: Mapping[str, Any],
        *,
        label: str,
    ) -> int:
        if not result.get("exists", False):
            raise ShmUploadError(f"Could not resolve {label}.")
        return self._require_result_id(result, label=label)

    @staticmethod
    def _require_result_id(result: Mapping[str, Any], label: str) -> int:
        record_id = result.get("id")
        if record_id is None:
            raise UploadResultError(f"Backend response for {label} did not include an id.")
        return int(record_id)

"""High-level services for typed SHM entity operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional, cast

import pandas as pd

from ..io import ShmAPI
from ..models import (
    DerivedSignalCalibrationRecord,
    DerivedSignalHistoryRecord,
    DerivedSignalRecord,
    SensorCalibrationRecord,
    SensorRecord,
    SensorTypeRecord,
    ShmEntityName,
    ShmQuery,
    ShmResourceRecord,
    SignalCalibrationRecord,
    SignalHistoryRecord,
    SignalRecord,
)
from ..protocols import EntityRegistryProtocol, ShmRepositoryProtocol
from ..registry import default_registry


class ApiShmRepository:
    """Repository adapter built on top of :class:`ShmAPI`."""

    def __init__(self, api: ShmAPI | None = None) -> None:
        self.api = api or ShmAPI(token="dummy")
        self._list_methods = {
            ShmEntityName.SENSOR_TYPE: self.api.list_sensor_types,
            ShmEntityName.SENSOR: self.api.list_sensors,
            ShmEntityName.SENSOR_CALIBRATION: self.api.list_sensor_calibrations,
            ShmEntityName.SIGNAL: self.api.list_signals,
            ShmEntityName.SIGNAL_HISTORY: self.api.list_signal_history,
            ShmEntityName.SIGNAL_CALIBRATION: self.api.list_signal_calibrations,
            ShmEntityName.DERIVED_SIGNAL: self.api.list_derived_signals,
            ShmEntityName.DERIVED_SIGNAL_HISTORY: self.api.list_derived_signal_history,
            ShmEntityName.DERIVED_SIGNAL_CALIBRATION: self.api.list_derived_signal_calibrations,
        }
        self._get_methods = {
            ShmEntityName.SENSOR_TYPE: self.api.get_sensor_type,
            ShmEntityName.SENSOR: self.api.get_sensor,
            ShmEntityName.SENSOR_CALIBRATION: self.api.get_sensor_calibration,
            ShmEntityName.SIGNAL: self.api.get_signal,
            ShmEntityName.SIGNAL_HISTORY: self.api.get_signal_history,
            ShmEntityName.SIGNAL_CALIBRATION: self.api.get_signal_calibration,
            ShmEntityName.DERIVED_SIGNAL: self.api.get_derived_signal,
            ShmEntityName.DERIVED_SIGNAL_HISTORY: self.api.get_derived_signal_history,
            ShmEntityName.DERIVED_SIGNAL_CALIBRATION: self.api.get_derived_signal_calibration,
        }
        self._create_methods = {
            ShmEntityName.SENSOR_TYPE: self.api.create_sensor_type,
            ShmEntityName.SENSOR: self.api.create_sensor,
            ShmEntityName.SENSOR_CALIBRATION: self.api.create_sensor_calibration,
            ShmEntityName.SIGNAL: self.api.create_signal,
            ShmEntityName.SIGNAL_HISTORY: self.api.create_signal_history,
            ShmEntityName.SIGNAL_CALIBRATION: self.api.create_signal_calibration,
            ShmEntityName.DERIVED_SIGNAL: self.api.create_derived_signal,
            ShmEntityName.DERIVED_SIGNAL_HISTORY: self.api.create_derived_signal_history,
            ShmEntityName.DERIVED_SIGNAL_CALIBRATION: self.api.create_derived_signal_calibration,
        }

    @staticmethod
    def _resolve_name(entity_name: ShmEntityName | str) -> ShmEntityName:
        return entity_name if isinstance(entity_name, ShmEntityName) else ShmEntityName(entity_name)

    def list_records(self, entity_name: ShmEntityName | str, **filters: Any) -> pd.DataFrame:
        """Return backend rows for a collection query."""
        resolved_name = self._resolve_name(entity_name)
        return cast(pd.DataFrame, self._list_methods[resolved_name](**filters)["data"])

    def get_record(self, entity_name: ShmEntityName | str, **filters: Any) -> Mapping[str, Any]:
        """Return the raw backend response for a single-resource query."""
        resolved_name = self._resolve_name(entity_name)
        if resolved_name is ShmEntityName.SIGNAL and "signal_id" in filters:
            signal_id = str(filters.pop("signal_id"))
            return self.api.get_signal(signal_id, **filters)
        return self._get_methods[resolved_name](**filters)

    def create_record(
        self,
        entity_name: ShmEntityName | str,
        payload: Mapping[str, Any],
        files: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Create a resource through the configured SHM API client."""
        resolved_name = self._resolve_name(entity_name)
        if files is not None:
            if resolved_name is ShmEntityName.SENSOR_TYPE:
                return self.api.create_sensor_type(dict(payload), files=files)
            if resolved_name is ShmEntityName.SENSOR_CALIBRATION:
                return self.api.create_sensor_calibration(dict(payload), files=files)
        create_method = self._create_methods[resolved_name]
        return create_method(dict(payload))


class ShmEntityService:
    """Facade for typed SHM retrieval and creation."""

    def __init__(
        self,
        repository: ShmRepositoryProtocol | None = None,
        registry: EntityRegistryProtocol | None = None,
    ) -> None:
        self.repository = repository or ApiShmRepository()
        self.registry = registry or default_registry

    @staticmethod
    def _resolve_name(entity_name: ShmEntityName | str) -> ShmEntityName:
        return entity_name if isinstance(entity_name, ShmEntityName) else ShmEntityName(entity_name)

    def _coerce_query(
        self,
        entity_name: ShmEntityName | str,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> ShmQuery:
        resolved_name = self._resolve_name(entity_name)
        if isinstance(filters, ShmQuery):
            if filters.entity is not None:
                return filters
            return filters.model_copy(update={"entity": resolved_name})
        return ShmQuery(entity=resolved_name, backend_filters=dict(filters or {}))

    def list_records(
        self,
        entity_name: ShmEntityName | str,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[ShmResourceRecord]:
        """Return typed resources for a collection query."""
        query = self._coerce_query(entity_name, filters)
        definition = self.registry.get(query.entity or self._resolve_name(entity_name))
        frame = self.repository.list_records(definition.name, **query.to_backend_filters())
        return [
            cast(
                ShmResourceRecord,
                definition.serializer.from_mapping(cast(dict[str, Any], row)),
            )
            for row in frame.to_dict(orient="records")
        ]

    def get_record(
        self,
        entity_name: ShmEntityName | str,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> ShmResourceRecord | None:
        """Return a single typed resource when it exists."""
        query = self._coerce_query(entity_name, filters)
        definition = self.registry.get(query.entity or self._resolve_name(entity_name))
        result = self.repository.get_record(definition.name, **query.to_backend_filters())
        frame = result.get("data")
        if not result.get("exists") or not isinstance(frame, pd.DataFrame) or frame.empty:
            return None
        return cast(ShmResourceRecord, definition.serializer.from_mapping(frame.iloc[0].to_dict()))

    def create_record(
        self,
        entity_name: ShmEntityName | str,
        payload: Mapping[str, Any] | ShmResourceRecord,
        files: Mapping[str, Any] | None = None,
    ) -> ShmResourceRecord | None:
        """Create and deserialize one SHM resource."""
        resolved_name = self._resolve_name(entity_name)
        definition = self.registry.get(resolved_name)
        serialized_payload = definition.serializer.to_payload(payload)
        result = self.repository.create_record(resolved_name, serialized_payload, files=files)
        frame = result.get("data")
        if not result.get("exists") or not isinstance(frame, pd.DataFrame) or frame.empty:
            return None
        return cast(ShmResourceRecord, definition.serializer.from_mapping(frame.iloc[0].to_dict()))


class SensorService:
    """Convenience service for sensor-domain SHM entities."""

    def __init__(self, entity_service: ShmEntityService | None = None) -> None:
        self.entity_service = entity_service or ShmEntityService()

    def list_sensor_types(self, filters: ShmQuery | Mapping[str, Any] | None = None) -> list[SensorTypeRecord]:
        return cast(list[SensorTypeRecord], self.entity_service.list_records(ShmEntityName.SENSOR_TYPE, filters))

    def get_sensor_type(self, filters: ShmQuery | Mapping[str, Any] | None = None) -> SensorTypeRecord | None:
        return cast(Optional[SensorTypeRecord], self.entity_service.get_record(ShmEntityName.SENSOR_TYPE, filters))

    def create_sensor_type(
        self,
        payload: Mapping[str, Any] | SensorTypeRecord,
        files: Mapping[str, Any] | None = None,
    ) -> SensorTypeRecord | None:
        return cast(
            Optional[SensorTypeRecord],
            self.entity_service.create_record(ShmEntityName.SENSOR_TYPE, payload, files=files),
        )

    def list_sensors(self, filters: ShmQuery | Mapping[str, Any] | None = None) -> list[SensorRecord]:
        return cast(list[SensorRecord], self.entity_service.list_records(ShmEntityName.SENSOR, filters))

    def get_sensor(self, filters: ShmQuery | Mapping[str, Any] | None = None) -> SensorRecord | None:
        return cast(Optional[SensorRecord], self.entity_service.get_record(ShmEntityName.SENSOR, filters))

    def create_sensor(self, payload: Mapping[str, Any] | SensorRecord) -> SensorRecord | None:
        return cast(Optional[SensorRecord], self.entity_service.create_record(ShmEntityName.SENSOR, payload))

    def list_sensor_calibrations(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[SensorCalibrationRecord]:
        return cast(
            list[SensorCalibrationRecord],
            self.entity_service.list_records(ShmEntityName.SENSOR_CALIBRATION, filters),
        )

    def get_sensor_calibration(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> SensorCalibrationRecord | None:
        return cast(
            Optional[SensorCalibrationRecord],
            self.entity_service.get_record(ShmEntityName.SENSOR_CALIBRATION, filters),
        )

    def create_sensor_calibration(
        self,
        payload: Mapping[str, Any] | SensorCalibrationRecord,
        files: Mapping[str, Any] | None = None,
    ) -> SensorCalibrationRecord | None:
        return cast(
            Optional[SensorCalibrationRecord],
            self.entity_service.create_record(ShmEntityName.SENSOR_CALIBRATION, payload, files=files),
        )


class SignalService:
    """Convenience service for signal-domain SHM entities."""

    def __init__(self, entity_service: ShmEntityService | None = None) -> None:
        self.entity_service = entity_service or ShmEntityService()

    def list_signals(self, filters: ShmQuery | Mapping[str, Any] | None = None) -> list[SignalRecord]:
        return cast(list[SignalRecord], self.entity_service.list_records(ShmEntityName.SIGNAL, filters))

    def get_signal(self, filters: ShmQuery | Mapping[str, Any] | None = None) -> SignalRecord | None:
        return cast(Optional[SignalRecord], self.entity_service.get_record(ShmEntityName.SIGNAL, filters))

    def create_signal(self, payload: Mapping[str, Any] | SignalRecord) -> SignalRecord | None:
        return cast(Optional[SignalRecord], self.entity_service.create_record(ShmEntityName.SIGNAL, payload))

    def list_signal_history(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[SignalHistoryRecord]:
        return cast(list[SignalHistoryRecord], self.entity_service.list_records(ShmEntityName.SIGNAL_HISTORY, filters))

    def get_signal_history(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> SignalHistoryRecord | None:
        return cast(
            Optional[SignalHistoryRecord],
            self.entity_service.get_record(ShmEntityName.SIGNAL_HISTORY, filters),
        )

    def create_signal_history(
        self,
        payload: Mapping[str, Any] | SignalHistoryRecord,
    ) -> SignalHistoryRecord | None:
        return cast(
            Optional[SignalHistoryRecord],
            self.entity_service.create_record(ShmEntityName.SIGNAL_HISTORY, payload),
        )

    def list_signal_calibrations(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[SignalCalibrationRecord]:
        return cast(
            list[SignalCalibrationRecord],
            self.entity_service.list_records(ShmEntityName.SIGNAL_CALIBRATION, filters),
        )

    def get_signal_calibration(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> SignalCalibrationRecord | None:
        return cast(
            Optional[SignalCalibrationRecord],
            self.entity_service.get_record(ShmEntityName.SIGNAL_CALIBRATION, filters),
        )

    def create_signal_calibration(
        self,
        payload: Mapping[str, Any] | SignalCalibrationRecord,
    ) -> SignalCalibrationRecord | None:
        return cast(
            Optional[SignalCalibrationRecord],
            self.entity_service.create_record(ShmEntityName.SIGNAL_CALIBRATION, payload),
        )

    def list_derived_signals(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[DerivedSignalRecord]:
        return cast(
            list[DerivedSignalRecord],
            self.entity_service.list_records(ShmEntityName.DERIVED_SIGNAL, filters),
        )

    def get_derived_signal(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> DerivedSignalRecord | None:
        return cast(
            Optional[DerivedSignalRecord],
            self.entity_service.get_record(ShmEntityName.DERIVED_SIGNAL, filters),
        )

    def create_derived_signal(
        self,
        payload: Mapping[str, Any] | DerivedSignalRecord,
    ) -> DerivedSignalRecord | None:
        return cast(
            Optional[DerivedSignalRecord],
            self.entity_service.create_record(ShmEntityName.DERIVED_SIGNAL, payload),
        )

    def list_derived_signal_history(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[DerivedSignalHistoryRecord]:
        return cast(
            list[DerivedSignalHistoryRecord],
            self.entity_service.list_records(ShmEntityName.DERIVED_SIGNAL_HISTORY, filters),
        )

    def get_derived_signal_history(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> DerivedSignalHistoryRecord | None:
        return cast(
            Optional[DerivedSignalHistoryRecord],
            self.entity_service.get_record(ShmEntityName.DERIVED_SIGNAL_HISTORY, filters),
        )

    def create_derived_signal_history(
        self,
        payload: Mapping[str, Any] | DerivedSignalHistoryRecord,
    ) -> DerivedSignalHistoryRecord | None:
        return cast(
            Optional[DerivedSignalHistoryRecord],
            self.entity_service.create_record(ShmEntityName.DERIVED_SIGNAL_HISTORY, payload),
        )

    def list_derived_signal_calibrations(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[DerivedSignalCalibrationRecord]:
        return cast(
            list[DerivedSignalCalibrationRecord],
            self.entity_service.list_records(ShmEntityName.DERIVED_SIGNAL_CALIBRATION, filters),
        )

    def get_derived_signal_calibration(
        self,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> DerivedSignalCalibrationRecord | None:
        return cast(
            Optional[DerivedSignalCalibrationRecord],
            self.entity_service.get_record(ShmEntityName.DERIVED_SIGNAL_CALIBRATION, filters),
        )

    def create_derived_signal_calibration(
        self,
        payload: Mapping[str, Any] | DerivedSignalCalibrationRecord,
    ) -> DerivedSignalCalibrationRecord | None:
        return cast(
            Optional[DerivedSignalCalibrationRecord],
            self.entity_service.create_record(ShmEntityName.DERIVED_SIGNAL_CALIBRATION, payload),
        )

"""Entity registry for typed SHM resources."""

from __future__ import annotations

from dataclasses import dataclass

from .io import DEFAULT_SHM_ENDPOINTS
from .models import (
    DerivedSignalCalibrationRecord,
    DerivedSignalHistoryRecord,
    DerivedSignalRecord,
    SensorCalibrationRecord,
    SensorRecord,
    SensorTypeRecord,
    ShmEntityName,
    ShmResourceRecord,
    SignalCalibrationRecord,
    SignalHistoryRecord,
    SignalRecord,
)
from .protocols import SerializerProtocol
from .serializers import DEFAULT_SERIALIZERS


@dataclass(frozen=True)
class ShmEntityDefinition:
    """Typed description of one SHM resource."""

    name: ShmEntityName
    endpoint: str
    record_model: type[ShmResourceRecord]
    serializer: SerializerProtocol


class ShmEntityRegistry:
    """Simple in-process registry for SHM entities."""

    def __init__(self) -> None:
        self._registry: dict[ShmEntityName, ShmEntityDefinition] = {}

    def register(self, definition: ShmEntityDefinition) -> ShmEntityDefinition:
        """Register one SHM entity definition."""
        self._registry[definition.name] = definition
        return definition

    def get(self, entity_name: ShmEntityName | str) -> ShmEntityDefinition:
        """Return the configured entity definition."""
        resolved_name = entity_name if isinstance(entity_name, ShmEntityName) else ShmEntityName(entity_name)
        try:
            return self._registry[resolved_name]
        except KeyError as exc:
            raise KeyError(f"Unknown SHM entity: {resolved_name}") from exc

    def names(self) -> list[str]:
        """Return registered entity names."""
        return sorted(name.value for name in self._registry)


def _build_default_registry() -> ShmEntityRegistry:
    registry = ShmEntityRegistry()
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.SENSOR_TYPE,
            endpoint=DEFAULT_SHM_ENDPOINTS.sensor_type,
            record_model=SensorTypeRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.SENSOR_TYPE],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.SENSOR,
            endpoint=DEFAULT_SHM_ENDPOINTS.sensor,
            record_model=SensorRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.SENSOR],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.SENSOR_CALIBRATION,
            endpoint=DEFAULT_SHM_ENDPOINTS.sensor_calibration,
            record_model=SensorCalibrationRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.SENSOR_CALIBRATION],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.SIGNAL,
            endpoint=DEFAULT_SHM_ENDPOINTS.signal,
            record_model=SignalRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.SIGNAL],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.SIGNAL_HISTORY,
            endpoint=DEFAULT_SHM_ENDPOINTS.signal_history,
            record_model=SignalHistoryRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.SIGNAL_HISTORY],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.SIGNAL_CALIBRATION,
            endpoint=DEFAULT_SHM_ENDPOINTS.signal_calibration,
            record_model=SignalCalibrationRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.SIGNAL_CALIBRATION],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.DERIVED_SIGNAL,
            endpoint=DEFAULT_SHM_ENDPOINTS.derived_signal,
            record_model=DerivedSignalRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.DERIVED_SIGNAL],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.DERIVED_SIGNAL_HISTORY,
            endpoint=DEFAULT_SHM_ENDPOINTS.derived_signal_history,
            record_model=DerivedSignalHistoryRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.DERIVED_SIGNAL_HISTORY],
        )
    )
    registry.register(
        ShmEntityDefinition(
            name=ShmEntityName.DERIVED_SIGNAL_CALIBRATION,
            endpoint=DEFAULT_SHM_ENDPOINTS.derived_signal_calibration,
            record_model=DerivedSignalCalibrationRecord,
            serializer=DEFAULT_SERIALIZERS[ShmEntityName.DERIVED_SIGNAL_CALIBRATION],
        )
    )
    return registry


default_registry = _build_default_registry()

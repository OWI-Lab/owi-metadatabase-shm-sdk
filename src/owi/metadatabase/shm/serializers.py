"""Serializers for typed SHM resources."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any, Generic, TypeVar

import pandas as pd
from pydantic import BaseModel

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

TShmRecord = TypeVar("TShmRecord", bound=ShmResourceRecord)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _normalize_mapping(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_mapping(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_mapping(item) for item in value]
    if _is_missing(value):
        return None
    return value


def _normalize_json_field(value: Any) -> dict[str, Any]:
    normalized = _normalize_mapping(value)
    if normalized is None:
        return {}
    if isinstance(normalized, str):
        try:
            decoded = json.loads(normalized)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    if isinstance(normalized, Mapping):
        return dict(normalized)
    return {}


class ShmEntitySerializer(Generic[TShmRecord]):
    """Generic serializer for a single SHM entity type."""

    def __init__(self, record_model: type[TShmRecord], *, json_fields: tuple[str, ...] = ()) -> None:
        self.record_model = record_model
        self.json_fields = json_fields

    def to_payload(self, obj: TShmRecord | BaseModel | Mapping[str, Any]) -> dict[str, Any]:
        """Serialize a resource model or mapping into a backend payload."""
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json", exclude_none=True)
        return {key: value for key, value in _normalize_mapping(dict(obj)).items() if value is not None}

    def from_mapping(self, mapping: Mapping[str, Any]) -> TShmRecord:
        """Deserialize a backend row into a typed resource model."""
        normalized = _normalize_mapping(dict(mapping))
        for field_name in self.json_fields:
            normalized[field_name] = _normalize_json_field(normalized.get(field_name))
        return self.record_model.model_validate(normalized)


SENSOR_SERIALIZER = ShmEntitySerializer(SensorRecord)
SENSOR_TYPE_SERIALIZER = ShmEntitySerializer(SensorTypeRecord)
SENSOR_CALIBRATION_SERIALIZER = ShmEntitySerializer(SensorCalibrationRecord)
SIGNAL_SERIALIZER = ShmEntitySerializer(SignalRecord, json_fields=("data_additional",))
SIGNAL_HISTORY_SERIALIZER = ShmEntitySerializer(SignalHistoryRecord)
SIGNAL_CALIBRATION_SERIALIZER = ShmEntitySerializer(SignalCalibrationRecord, json_fields=("data",))
DERIVED_SIGNAL_SERIALIZER = ShmEntitySerializer(DerivedSignalRecord, json_fields=("data_additional",))
DERIVED_SIGNAL_HISTORY_SERIALIZER = ShmEntitySerializer(DerivedSignalHistoryRecord)
DERIVED_SIGNAL_CALIBRATION_SERIALIZER = ShmEntitySerializer(
    DerivedSignalCalibrationRecord,
    json_fields=("data",),
)

DEFAULT_SERIALIZERS: dict[ShmEntityName, ShmEntitySerializer[Any]] = {
    ShmEntityName.SENSOR_TYPE: SENSOR_TYPE_SERIALIZER,
    ShmEntityName.SENSOR: SENSOR_SERIALIZER,
    ShmEntityName.SENSOR_CALIBRATION: SENSOR_CALIBRATION_SERIALIZER,
    ShmEntityName.SIGNAL: SIGNAL_SERIALIZER,
    ShmEntityName.SIGNAL_HISTORY: SIGNAL_HISTORY_SERIALIZER,
    ShmEntityName.SIGNAL_CALIBRATION: SIGNAL_CALIBRATION_SERIALIZER,
    ShmEntityName.DERIVED_SIGNAL: DERIVED_SIGNAL_SERIALIZER,
    ShmEntityName.DERIVED_SIGNAL_HISTORY: DERIVED_SIGNAL_HISTORY_SERIALIZER,
    ShmEntityName.DERIVED_SIGNAL_CALIBRATION: DERIVED_SIGNAL_CALIBRATION_SERIALIZER,
}

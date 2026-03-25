"""Pydantic models for typed SHM resources."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ShmEntityName(str, Enum):
    """Supported SHM entity names."""

    SENSOR_TYPE = "sensor_type"
    SENSOR = "sensor"
    SENSOR_CALIBRATION = "sensor_calibration"
    SIGNAL = "signal"
    SIGNAL_HISTORY = "signal_history"
    SIGNAL_CALIBRATION = "signal_calibration"
    DERIVED_SIGNAL = "derived_signal"
    DERIVED_SIGNAL_HISTORY = "derived_signal_history"
    DERIVED_SIGNAL_CALIBRATION = "derived_signal_calibration"


class ShmBaseModel(BaseModel):
    """Base Pydantic configuration for SHM models."""

    model_config = ConfigDict(extra="ignore")


class ShmResourceRecord(ShmBaseModel):
    """Base resource model shared by SHM entity records."""

    id: int | None = None


class ShmQuery(BaseModel):
    """Validated wrapper for backend filter payloads."""

    model_config = ConfigDict(extra="forbid")

    entity: ShmEntityName | None = None
    backend_filters: dict[str, Any] = Field(default_factory=dict)

    def to_backend_filters(self) -> dict[str, Any]:
        """Return backend-compatible filter arguments."""
        return dict(self.backend_filters)


class SensorTypeRecord(ShmResourceRecord):
    """Typed SHM sensor-type record."""

    name: str | None = None
    hardware_supplier: str | None = None
    type: str | None = None
    type_extended: str | None = None
    unit: str | None = None
    visibility: str | None = None
    visibility_groups: list[int] | None = None


class SensorRecord(ShmResourceRecord):
    """Typed SHM sensor record."""

    sensor_type_id: int | None = None
    serial_number: str | None = None
    name: str | None = None
    slug: str | None = None
    cabinet: str | int | None = None
    visibility: str | None = None
    visibility_groups: list[int] | None = None


class SensorCalibrationRecord(ShmResourceRecord):
    """Typed SHM sensor calibration record."""

    sensor_id: int | None = None
    sensor_serial_number: int | None = None
    calibration_date: datetime | None = None
    value: float | None = None
    file: str | None = None
    status_approval: str | None = None


class SignalRecord(ShmResourceRecord):
    """Typed SHM signal record."""

    signal_id: str | None = None
    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    signal_type: str | None = None
    status: str | None = None
    site: int | None = None
    asset_location: int | None = None
    asset_location_id: int | None = None
    model_definition: int | None = None
    sub_assembly: int | None = None
    heading: Any = None
    level: Any = None
    orientation: str | None = None
    stats: Any = None
    visibility: str | None = None
    visibility_groups: list[int] | None = None
    data_additional: dict[str, Any] = Field(default_factory=dict)


class SignalHistoryRecord(ShmResourceRecord):
    """Typed SHM signal history record."""

    signal_id: int | None = None
    activity_start_timestamp: datetime | None = None
    timestamp: datetime | None = None
    is_latest_status: bool | None = None
    status: str | None = None
    sensor_serial_number: int | None = None
    legacy_signal_id: str | None = None
    status_approval: str | None = None
    value: float | None = None


class SignalCalibrationRecord(ShmResourceRecord):
    """Typed SHM signal calibration record."""

    signal_id: int | None = None
    calibration_date: datetime | None = None
    tempcomp_signal_id: int | None = None
    status_approval: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class DerivedSignalRecord(ShmResourceRecord):
    """Typed SHM derived-signal record."""

    derived_signal_id: str | None = None
    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    signal_type: str | None = None
    status: str | None = None
    site: int | None = None
    asset_location: int | None = None
    asset_location_id: int | None = None
    model_definition: int | None = None
    visibility: str | None = None
    visibility_groups: list[int] | None = None
    data_additional: dict[str, Any] = Field(default_factory=dict)


class DerivedSignalHistoryRecord(ShmResourceRecord):
    """Typed SHM derived-signal history record."""

    derived_signal_id: int | None = None
    activity_start_timestamp: datetime | None = None
    timestamp: datetime | None = None
    is_latest_status: bool | None = None
    status: str | None = None
    parent_signals: list[int] | None = None
    value: float | None = None


class DerivedSignalCalibrationRecord(ShmResourceRecord):
    """Typed SHM derived-signal calibration record."""

    derived_signal_id: int | None = None
    calibration_date: datetime | None = None
    status_approval: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

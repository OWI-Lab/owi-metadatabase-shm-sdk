"""Non-legacy payload helpers for SHM upload workflows."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Optional, Union, cast

from dateutil.parser import parse

from ..signal_ids import LegacySignalIdentifier
from ..upload_context import SignalUploadContext

TimestampValue = Union[str, date, datetime]
JsonScalar = Optional[Union[str, int, float, bool]]
JsonValue = Union[JsonScalar, list["JsonValue"], dict[str, "JsonValue"]]

_GENERAL_SIGNAL_FIELDS = frozenset(
    {
        "heading",
        "level",
        "orientation",
        "status",
        "offset",
        "cwl",
        "temperature_compensation",
        "stats",
        "Ri",
        "Ro",
    }
)


def _isoformat_timestamp(timestamp: TimestampValue) -> str:
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    if isinstance(timestamp, date):
        return datetime.combine(timestamp, time.min).isoformat()
    return parse(timestamp, dayfirst=True).isoformat()


def _normalize_visibility_groups(permission_group_ids: Sequence[int] | None) -> list[int] | None:
    if permission_group_ids is None:
        return None
    return list(permission_group_ids)


def _serialize_json_data(data: Mapping[str, JsonValue]) -> str:
    return json.dumps(dict(data))


def _legacy_signal_misc_data(signal_data: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {field: value for field, value in signal_data.items() if field not in _GENERAL_SIGNAL_FIELDS}


def _expand_columns(columns: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
    if not columns:
        return []
    expected_length = len(next(iter(columns.values())))
    if any(len(values) != expected_length for values in columns.values()):
        raise ValueError("All column lists must have the same length.")
    rows: list[dict[str, Any]] = []
    for index in range(expected_length):
        rows.append({name: values[index] for name, values in columns.items()})
    return rows


@dataclass(frozen=True)
class SignalPayload:
    """Payload model for signal records."""

    site: int
    model_definition: int | str
    asset_location: int
    signal_type: str
    signal_id: str
    visibility_groups: Sequence[int] | None
    sub_assembly: int | None = None
    heading: JsonScalar = None
    level: JsonScalar = None
    orientation: str | None = None
    stats: JsonValue = None
    data_additional: Mapping[str, JsonValue] | None = None
    visibility: str = "usergroup"

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "site": self.site,
            "model_definition": self.model_definition,
            "asset_location": self.asset_location,
            "signal_type": self.signal_type,
            "heading": self.heading,
            "level": self.level,
            "orientation": self.orientation,
            "signal_id": self.signal_id,
            "stats": self.stats,
            "visibility": self.visibility,
            "visibility_groups": _normalize_visibility_groups(self.visibility_groups),
        }
        if self.sub_assembly is not None:
            payload["sub_assembly"] = self.sub_assembly
        if self.data_additional:
            payload["data_additional"] = _serialize_json_data(self.data_additional)
        return payload


@dataclass(frozen=True)
class SignalHistoryPayload:
    """Payload model for signal history records."""

    signal_id: int
    activity_start_timestamp: TimestampValue
    is_latest_status: bool
    status: str
    sensor_serial_number: int | None = None
    status_approval: str = "yes"
    legacy_signal_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "signal_id": self.signal_id,
            "activity_start_timestamp": _isoformat_timestamp(self.activity_start_timestamp),
            "is_latest_status": self.is_latest_status,
            "status": self.status,
            "sensor_serial_number": self.sensor_serial_number,
            "status_approval": self.status_approval,
        }
        if self.legacy_signal_id is not None:
            payload["legacy_signal_id"] = self.legacy_signal_id
        return payload


@dataclass(frozen=True)
class LeadCorrectionPayload:
    """Nested payload model for signal lead correction data."""

    t_ref: JsonScalar
    coef: JsonValue

    def to_payload(self) -> dict[str, JsonValue]:
        return {"t_ref": self.t_ref, "coef": self.coef}


@dataclass(frozen=True)
class SignalCalibrationData:
    """Nested payload model for signal calibration data."""

    offset: JsonScalar = None
    cwl: JsonScalar = None
    coefficients: JsonValue = None
    t_ref: JsonScalar = None
    gauge_correction: JsonValue = None
    lead_correction: LeadCorrectionPayload | None = None

    def to_payload(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {}
        if self.offset is not None:
            payload["offset"] = self.offset
        if self.cwl is not None:
            payload["cwl"] = self.cwl
        if self.coefficients is not None:
            payload["Coefficients"] = self.coefficients
        if self.t_ref is not None:
            payload["t_ref"] = self.t_ref
        if self.gauge_correction is not None:
            payload["gauge_correction"] = self.gauge_correction
        if self.lead_correction is not None:
            payload["lead_correction"] = self.lead_correction.to_payload()
        if not payload:
            raise ValueError("Signal calibration data cannot be empty.")
        return payload


@dataclass(frozen=True)
class SignalCalibrationPayload:
    """Payload model for signal calibration records."""

    signal_id: int
    calibration_date: TimestampValue
    data: SignalCalibrationData
    tempcomp_signal_id: int | None = None
    status_approval: str = "yes"

    @classmethod
    def from_cwl(
        cls,
        signal_id: int,
        calibration_date: TimestampValue,
        cwl: JsonScalar,
        tempcomp_signal_id: int | None = None,
        status_approval: str = "yes",
    ) -> SignalCalibrationPayload:
        return cls(
            signal_id=signal_id,
            calibration_date=calibration_date,
            data=SignalCalibrationData(cwl=cwl),
            tempcomp_signal_id=tempcomp_signal_id,
            status_approval=status_approval,
        )

    @classmethod
    def from_offset(
        cls,
        signal_id: int,
        calibration_date: TimestampValue,
        offset: JsonScalar,
        tempcomp_signal_id: int | None = None,
        coefficients: JsonValue = None,
        t_ref: JsonScalar = None,
        gauge_correction: JsonValue = None,
        lead_correction: LeadCorrectionPayload | None = None,
        status_approval: str = "yes",
    ) -> SignalCalibrationPayload:
        return cls(
            signal_id=signal_id,
            calibration_date=calibration_date,
            data=SignalCalibrationData(
                offset=offset,
                coefficients=coefficients,
                t_ref=t_ref,
                gauge_correction=gauge_correction,
                lead_correction=lead_correction,
            ),
            tempcomp_signal_id=tempcomp_signal_id,
            status_approval=status_approval,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "calibration_date": _isoformat_timestamp(self.calibration_date),
            "data": _serialize_json_data(self.data.to_payload()),
            "tempcomp_signal_id": self.tempcomp_signal_id,
            "status_approval": self.status_approval,
        }


@dataclass(frozen=True)
class DerivedSignalPayload:
    """Payload model for derived signal records."""

    site: int
    model_definition: int | str
    asset_location: int
    sub_assembly: int
    signal_type: str
    derived_signal_id: str
    visibility_groups: Sequence[int] | None
    heading: JsonScalar = None
    level: JsonScalar = None
    orientation: str | None = None
    stats: JsonValue = None
    data_additional: Mapping[str, JsonValue] | None = None
    visibility: str = "usergroup"

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "site": self.site,
            "model_definition": self.model_definition,
            "asset_location": self.asset_location,
            "sub_assembly": self.sub_assembly,
            "signal_type": self.signal_type,
            "heading": self.heading,
            "level": self.level,
            "orientation": self.orientation,
            "derived_signal_id": self.derived_signal_id,
            "stats": self.stats,
            "visibility": self.visibility,
            "visibility_groups": _normalize_visibility_groups(self.visibility_groups),
        }
        if self.data_additional:
            payload["data_additional"] = _serialize_json_data(self.data_additional)
        return payload


@dataclass(frozen=True)
class DerivedSignalHistoryPayload:
    """Payload model for derived signal history records."""

    derived_signal_id: int
    activity_start_timestamp: TimestampValue
    is_latest_status: bool
    status: str
    status_approval: str = "yes"

    def to_payload(self) -> dict[str, Any]:
        return {
            "activity_start_timestamp": _isoformat_timestamp(self.activity_start_timestamp),
            "is_latest_status": self.is_latest_status,
            "status": self.status,
            "derived_signal_id": self.derived_signal_id,
            "status_approval": self.status_approval,
        }


@dataclass(frozen=True)
class DerivedSignalHistoryParentSignalsPatch:
    """Patch payload for linking parent signals to a derived signal history."""

    parent_signals: Sequence[int]

    def to_payload(self) -> dict[str, list[int]]:
        return {"parent_signals": list(self.parent_signals)}


@dataclass(frozen=True)
class DerivedSignalCalibrationData:
    """Nested payload model for derived signal calibration data."""

    yaw_parameter: JsonScalar
    yaw_offset: JsonScalar
    measurement_location: JsonScalar = None

    def to_payload(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "yaw_parameter": self.yaw_parameter,
            "yaw_offset": self.yaw_offset,
        }
        if self.measurement_location is not None:
            payload["measurement_location"] = self.measurement_location
        return payload


@dataclass(frozen=True)
class DerivedSignalCalibrationPayload:
    """Payload model for derived signal calibration records."""

    derived_signal_id: int
    calibration_date: TimestampValue
    data: DerivedSignalCalibrationData
    status_approval: str = "yes"

    @classmethod
    def from_yaw_offset(
        cls,
        derived_signal_id: int,
        calibration_date: TimestampValue,
        yaw_parameter: JsonScalar,
        yaw_offset: JsonScalar,
        measurement_location: JsonScalar = None,
        status_approval: str = "yes",
    ) -> DerivedSignalCalibrationPayload:
        return cls(
            derived_signal_id=derived_signal_id,
            calibration_date=calibration_date,
            data=DerivedSignalCalibrationData(
                yaw_parameter=yaw_parameter,
                yaw_offset=yaw_offset,
                measurement_location=measurement_location,
            ),
            status_approval=status_approval,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "calibration_date": _isoformat_timestamp(self.calibration_date),
            "data": _serialize_json_data(self.data.to_payload()),
            "derived_signal_id": self.derived_signal_id,
            "status_approval": self.status_approval,
        }


@dataclass(frozen=True)
class SensorTypePayload:
    """Payload model for sensor type records."""

    name: str
    type: str
    type_extended: str
    hardware_supplier: str
    file: str | Path | None = None
    visibility: str = "usergroup"
    visibility_groups: Sequence[int] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "type_extended": self.type_extended,
            "hardware_supplier": self.hardware_supplier,
            "visibility": self.visibility,
            "visibility_groups": _normalize_visibility_groups(self.visibility_groups),
        }

    def to_files(self) -> dict[str, Any] | None:
        if self.file is None:
            return None
        path = Path(self.file)
        return {"file": (path.name, path.open("rb"))}


@dataclass(frozen=True)
class SensorPayload:
    """Payload model for sensor records."""

    sensor_type_id: int
    serial_number: str | None
    cabinet: str | int | None
    visibility: str = "usergroup"
    visibility_groups: Sequence[int] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "sensor_type_id": self.sensor_type_id,
            "serial_number": self.serial_number,
            "cabinet": self.cabinet,
            "visibility": self.visibility,
            "visibility_groups": _normalize_visibility_groups(self.visibility_groups),
        }


@dataclass(frozen=True)
class SensorCalibrationPayload:
    """Payload model for sensor calibration records."""

    sensor_serial_number: int
    calibration_date: TimestampValue
    file: str | Path

    def to_payload(self) -> dict[str, Any]:
        return {
            "sensor_serial_number": self.sensor_serial_number,
            "calibration_date": _isoformat_timestamp(self.calibration_date),
            "file": str(self.file),
        }


def build_sensor_payloads(
    sensor_type_id: int,
    serial_numbers: Sequence[str | None],
    cabinets: Sequence[str | int | None],
    visibility_groups: Sequence[int] | None,
    visibility: str = "usergroup",
) -> list[SensorPayload]:
    """Build sensor payload models from parallel columns."""
    rows = _expand_columns({"serial_number": serial_numbers, "cabinet": cabinets})
    return [
        SensorPayload(
            sensor_type_id=sensor_type_id,
            serial_number=row["serial_number"],
            cabinet=row["cabinet"],
            visibility=visibility,
            visibility_groups=visibility_groups,
        )
        for row in rows
    ]


def build_sensor_type_payloads(
    sensor_types_data: Sequence[Mapping[str, Any]],
    visibility_groups: Sequence[int] | None,
    path_to_images: str | Path | None = None,
    visibility: str = "usergroup",
) -> list[SensorTypePayload]:
    """Build sensor type payload models from raw records."""
    payloads: list[SensorTypePayload] = []
    for entry in sensor_types_data:
        file_path: Path | None = None
        filename = entry.get("file")
        if filename is not None and path_to_images is not None:
            file_path = Path(path_to_images) / str(filename)
        payloads.append(
            SensorTypePayload(
                name=str(entry["name"]),
                type=str(entry["type"]),
                type_extended=str(entry["type_extended"]),
                hardware_supplier=str(entry["hardware_supplier"]),
                file=file_path,
                visibility=visibility,
                visibility_groups=visibility_groups,
            )
        )
    return payloads


def build_sensor_calibration_payloads(
    signal_sensor_map: Mapping[str, int],
    signal_calibration_map: Mapping[str, Mapping[str, str]],
    path_to_datasheets: str | Path,
) -> list[SensorCalibrationPayload]:
    """Build sensor calibration payload models for one turbine."""
    payloads: list[SensorCalibrationPayload] = []
    for signal_name, calibration in signal_calibration_map.items():
        sensor_id = signal_sensor_map.get(signal_name)
        if sensor_id is None:
            continue
        payloads.append(
            SensorCalibrationPayload(
                sensor_serial_number=sensor_id,
                calibration_date=calibration["date"],
                file=Path(path_to_datasheets) / calibration["filename"],
            )
        )
    return payloads


def build_signal_main_payload(
    signal: LegacySignalIdentifier,
    signal_data: Mapping[str, Any],
    context: SignalUploadContext,
) -> dict[str, Any] | None:
    """Build the main signal payload from archive-style signal data."""
    if len(signal_data) <= 1:
        return None

    payload = SignalPayload(
        site=context.site_id,
        model_definition=context.model_definition_id,
        asset_location=context.asset_location_id,
        signal_type=signal.signal_type,
        signal_id=signal.raw,
        sub_assembly=(
            context.subassembly_id_for(signal.subassembly) if signal.subassembly in {"TP", "TW", "MP"} else None
        ),
        heading=signal_data.get("heading"),
        level=signal_data.get("level"),
        orientation=signal_data.get("orientation"),
        stats=signal_data.get("stats"),
        data_additional=_legacy_signal_misc_data(signal_data),
        visibility_groups=context.permission_group_ids,
    )
    return payload.to_payload()


def build_signal_status_payloads(
    signal_id: int,
    signal_data: Mapping[str, Any],
    sensor_serial_number: int | None = None,
) -> list[dict[str, Any]]:
    """Build signal status payloads from archive-style status rows."""
    statuses = signal_data.get("status")
    if not isinstance(statuses, Sequence) or isinstance(statuses, (str, bytes)):
        return []

    payloads: list[dict[str, Any]] = []
    for index, status in enumerate(statuses):
        if not isinstance(status, Mapping):
            continue
        status_row = cast(Mapping[str, Any], status)
        payloads.append(
            SignalHistoryPayload(
                signal_id=signal_id,
                activity_start_timestamp=cast(TimestampValue, status_row["time"]),
                is_latest_status=index == len(statuses) - 1,
                status=cast(str, status_row["status"]),
                sensor_serial_number=sensor_serial_number,
                legacy_signal_id=cast(Optional[str], status_row.get("name")),
            ).to_payload()
        )
    return payloads


def build_signal_calibration_payloads(
    signal_id: int,
    signal_data: Mapping[str, Any],
    tempcomp_signal_ids: Mapping[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Build signal calibration payloads from archive-style offset and CWL data."""
    payloads: list[dict[str, Any]] = []

    offsets = signal_data.get("offset")
    if isinstance(offsets, Sequence) and not isinstance(offsets, (str, bytes)):
        for offset in offsets:
            if not isinstance(offset, Mapping):
                continue
            lead_correction = offset.get("lead_correction")
            tc_sensor = offset.get("TCSensor")
            payloads.append(
                SignalCalibrationPayload.from_offset(
                    signal_id=signal_id,
                    calibration_date=offset["time"],
                    offset=offset["offset"],
                    tempcomp_signal_id=(
                        tempcomp_signal_ids.get(tc_sensor)
                        if tempcomp_signal_ids is not None and isinstance(tc_sensor, str)
                        else None
                    ),
                    coefficients=offset.get("Coefficients"),
                    t_ref=offset.get("t_ref"),
                    gauge_correction=offset.get("gauge_correction"),
                    lead_correction=(
                        LeadCorrectionPayload(
                            t_ref=lead_correction["t_ref"],
                            coef=lead_correction["coef"],
                        )
                        if isinstance(lead_correction, Mapping)
                        else None
                    ),
                ).to_payload()
            )

    cwl_rows = signal_data.get("cwl")
    if isinstance(cwl_rows, Sequence) and not isinstance(cwl_rows, (str, bytes)):
        for cwl in cwl_rows:
            if not isinstance(cwl, Mapping):
                continue
            payloads.append(
                SignalCalibrationPayload.from_cwl(
                    signal_id=signal_id,
                    calibration_date=cwl["time"],
                    cwl=cwl["cwl"],
                ).to_payload()
            )

    return payloads


def build_derived_signal_main_payload(
    signal: LegacySignalIdentifier,
    signal_data: Mapping[str, Any],
    context: SignalUploadContext,
) -> dict[str, Any] | None:
    """Build the main derived-signal payload from archive-style data."""
    if len(signal_data) <= 1:
        return None

    sub_assembly = context.subassembly_id_for(signal.subassembly)
    if sub_assembly is None:
        raise KeyError(f"Missing sub-assembly id for {signal.subassembly!r}")

    return DerivedSignalPayload(
        site=context.site_id,
        model_definition=context.model_definition_id,
        asset_location=context.asset_location_id,
        sub_assembly=sub_assembly,
        signal_type=signal.signal_type,
        derived_signal_id=signal.raw,
        heading=signal_data.get("heading"),
        level=signal_data.get("level"),
        orientation=signal_data.get("orientation"),
        stats=signal_data.get("stats"),
        data_additional=signal_data.get("data"),
        visibility_groups=context.permission_group_ids,
    ).to_payload()


def build_derived_signal_status_payload(
    derived_signal_id: int,
    signal_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the derived-signal status payload used before parent patching."""
    calibrations = signal_data.get("calibration")
    if not isinstance(calibrations, Sequence) or isinstance(calibrations, (str, bytes)) or not calibrations:
        raise ValueError("Derived signal calibration rows are required to build a status payload.")

    first = calibrations[0]
    if not isinstance(first, Mapping):
        raise ValueError("Derived signal calibration rows must be mappings.")

    return DerivedSignalHistoryPayload(
        derived_signal_id=derived_signal_id,
        activity_start_timestamp=first["time"],
        is_latest_status=True,
        status="ok",
    ).to_payload()


def build_derived_signal_parent_patch(parent_signal_ids: Sequence[int]) -> dict[str, list[int]]:
    """Build the parent-signals patch payload for derived signal status rows."""
    return DerivedSignalHistoryParentSignalsPatch(parent_signal_ids).to_payload()


def build_derived_signal_calibration_payloads(
    derived_signal_id: int,
    signal_data: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build derived-signal calibration payloads from archive-style data."""
    calibrations = signal_data.get("calibration")
    if not isinstance(calibrations, Sequence) or isinstance(calibrations, (str, bytes)):
        return []

    payloads: list[dict[str, Any]] = []
    for calibration in calibrations:
        if not isinstance(calibration, Mapping):
            continue
        payloads.append(
            DerivedSignalCalibrationPayload.from_yaw_offset(
                derived_signal_id=derived_signal_id,
                calibration_date=calibration["time"],
                yaw_parameter=calibration["yaw_parameter"],
                yaw_offset=calibration["yaw_offset"],
                measurement_location=calibration.get("measurement_location"),
            ).to_payload()
        )
    return payloads


__all__ = [
    "build_derived_signal_calibration_payloads",
    "build_derived_signal_main_payload",
    "build_derived_signal_parent_patch",
    "build_derived_signal_status_payload",
    "SensorCalibrationPayload",
    "SensorPayload",
    "SensorTypePayload",
    "build_signal_calibration_payloads",
    "build_signal_main_payload",
    "build_signal_status_payloads",
    "build_sensor_calibration_payloads",
    "build_sensor_payloads",
    "build_sensor_type_payloads",
    "DerivedSignalCalibrationData",
    "DerivedSignalCalibrationPayload",
    "DerivedSignalHistoryParentSignalsPatch",
    "DerivedSignalHistoryPayload",
    "DerivedSignalPayload",
    "LeadCorrectionPayload",
    "SignalCalibrationData",
    "SignalCalibrationPayload",
    "SignalHistoryPayload",
    "SignalPayload",
]

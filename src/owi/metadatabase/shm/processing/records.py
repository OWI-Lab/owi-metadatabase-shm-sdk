"""Typed in-memory signal record models and processing results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .parsing import LegacyRecord, LegacySignalMap


@dataclass(slots=True)
class ProcessedSignalRecord:
    """Typed in-memory representation of one processed signal.

    Parameters
    ----------
    scalar_fields
        Arbitrary scalar properties stored on the signal.
    status_rows
        Collected status event rows.
    offset_rows
        Collected offset event rows.
    cwl_rows
        Collected CWL event rows.

    Examples
    --------
    >>> record = ProcessedSignalRecord()
    >>> record.add_status("01/01/1972 00:00", "ok")
    >>> record.to_legacy_dict()["status"][0]["status"]
    'ok'
    """

    scalar_fields: dict[str, Any] = field(default_factory=dict)
    status_rows: list[dict[str, Any]] = field(default_factory=list)
    offset_rows: list[dict[str, Any]] = field(default_factory=list)
    cwl_rows: list[dict[str, Any]] = field(default_factory=list)

    def set_scalar(self, property_name: str, value: Any) -> None:
        """Store a scalar property on the signal.

        Parameters
        ----------
        property_name
            Scalar field name from the raw configuration event.
        value
            Value to persist on the signal record.
        """
        self.scalar_fields[property_name] = value

    def add_status(self, timestamp: str, status: Any) -> None:
        """Append a status row.

        Parameters
        ----------
        timestamp
            Event timestamp associated with the status.
        status
            Status value to store.
        """
        self.status_rows.append({"time": timestamp, "status": status})

    def add_status_alias(self, timestamp: str, alias_name: str) -> None:
        """Append a status row that carries a legacy alias name.

        Parameters
        ----------
        timestamp
            Event timestamp associated with the alias.
        alias_name
            Legacy signal name that points at this record.
        """
        self.status_rows.append({"time": timestamp, "name": alias_name})

    def add_offset(self, timestamp: str, offset: Any) -> None:
        """Append an offset row.

        Parameters
        ----------
        timestamp
            Event timestamp associated with the offset.
        offset
            Offset value to store.
        """
        self.offset_rows.append({"time": timestamp, "offset": offset})

    def add_cwl(self, timestamp: str, cwl: Any) -> None:
        """Append a CWL row.

        Parameters
        ----------
        timestamp
            Event timestamp associated with the CWL value.
        cwl
            CWL value to store.
        """
        self.cwl_rows.append({"time": timestamp, "cwl": cwl})

    def to_legacy_dict(self) -> LegacyRecord:
        """Return the uploader-facing legacy mapping.

        Returns
        -------
        LegacyRecord
            Archive-compatible mapping consumed by uploader payload builders.
        """
        data = dict(self.scalar_fields)
        if self.status_rows:
            data["status"] = [dict(row) for row in self.status_rows]
        if self.offset_rows:
            data["offset"] = [dict(row) for row in self.offset_rows]
        if self.cwl_rows:
            data["cwl"] = [dict(row) for row in self.cwl_rows]
        return data


@dataclass(slots=True)
class ProcessedDerivedSignalRecord:
    """Typed in-memory representation of one processed derived signal.

    Examples
    --------
    >>> record = ProcessedDerivedSignalRecord()
    >>> record.ensure_source_name("strain/bending_moment", {"suffix": "N"})
    >>> record.set_parent_signals(["SIG_A", "SIG_B"])
    >>> record.add_calibration("01/01/1972 00:00", {"yaw_offset": 2.0})
    >>> sorted(record.to_legacy_dict())
    ['calibration', 'data', 'parent_signals']
    """

    data_fields: dict[str, Any] = field(default_factory=dict)
    calibration_rows: list[dict[str, Any]] = field(default_factory=list)
    parent_signals: tuple[str, ...] = ()

    def ensure_source_name(
        self,
        source_name: str,
        extra_fields: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize immutable source metadata for the derived signal.

        Parameters
        ----------
        source_name
            Event key that produced the derived signal.
        extra_fields
            Optional metadata merged into the legacy ``data`` mapping the first
            time the source name is set.
        """
        if not self.data_fields:
            self.data_fields = {"name": source_name}
            if extra_fields:
                self.data_fields.update(extra_fields)

    def set_parent_signals(self, parent_signals: Sequence[str]) -> None:
        """Set parent signals when they are first known.

        Parameters
        ----------
        parent_signals
            Ordered parent signal identifiers for the derived signal.
        """
        if not self.parent_signals:
            self.parent_signals = tuple(parent_signals)

    def add_calibration(self, timestamp: str, calibration_fields: Mapping[str, Any]) -> None:
        """Append a derived-signal calibration row.

        Parameters
        ----------
        timestamp
            Event timestamp associated with the calibration.
        calibration_fields
            Calibration fields emitted by the derived-signal strategy.
        """
        row = {"time": timestamp}
        row.update(calibration_fields)
        self.calibration_rows.append(row)

    def to_legacy_dict(self) -> LegacyRecord:
        """Return the uploader-facing legacy mapping.

        Returns
        -------
        LegacyRecord
            Archive-compatible mapping consumed by uploader payload builders.
        """
        data: LegacyRecord = {}
        if self.data_fields:
            data["data"] = dict(self.data_fields)
        if self.calibration_rows:
            data["calibration"] = [dict(row) for row in self.calibration_rows]
        if self.parent_signals:
            data["parent_signals"] = list(self.parent_signals)
        return data


@dataclass(frozen=True, slots=True)
class SignalProcessingResult:
    """Processed signal and derived-signal records.

    Examples
    --------
    >>> signal = ProcessedSignalRecord()
    >>> signal.add_status("01/01/1972 00:00", "ok")
    >>> result = SignalProcessingResult(signals={"SIG": signal}, derived_signals={})
    >>> result.to_legacy_data()[0]["SIG"]["status"][0]["status"]
    'ok'
    """

    signals: Mapping[str, ProcessedSignalRecord]
    derived_signals: Mapping[str, ProcessedDerivedSignalRecord]

    def to_legacy_data(self) -> tuple[LegacySignalMap, LegacySignalMap]:
        """Return archive-compatible dicts for uploader seams.

        Returns
        -------
        tuple[LegacySignalMap, LegacySignalMap]
            Main-signal and derived-signal mappings in the uploader-facing
            archive shape.
        """
        return (
            {name: record.to_legacy_dict() for name, record in self.signals.items()},
            {
                name: record.to_legacy_dict()
                for name, record in self.derived_signals.items()
            },
        )

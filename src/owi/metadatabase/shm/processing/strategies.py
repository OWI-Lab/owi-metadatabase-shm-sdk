"""Derived signal strategies and callable registries."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from .parsing import JsonValue, _coerce_mapping, _coerce_string, _coerce_string_sequence
from .records import ProcessedSignalRecord

SignalNameBuilder = Callable[[str, str], str]
ParentSignalsBuilder = Callable[[Mapping[str, Any], str], Sequence[str]]
CalibrationFieldsBuilder = Callable[[Mapping[str, Any], str], Mapping[str, JsonValue]]
DerivedDataBuilder = Callable[[Mapping[str, Any], str], Mapping[str, JsonValue]]
SignalPostprocessor = Callable[[MutableMapping[str, ProcessedSignalRecord]], None]

_DEFAULT_STRAIN_VECTOR_SUFFIXES: Final[frozenset[str]] = frozenset({"DEG090_0", "DEG000_0"})


def _default_level_signal_name(level: str, suffix: str) -> str:
    return f"{level}_{suffix}"


def _default_strain_signal_name(
    level: str,
    suffix: str,
    defaults: frozenset[str] = _DEFAULT_STRAIN_VECTOR_SUFFIXES,
) -> str:
    signal_level = level
    if suffix in defaults:
        signal_level = re.sub(r"_SG_", "_VSG_", level)
    return f"{signal_level}_{suffix}"


def _parent_signals_from_level(payload: Mapping[str, Any], level: str) -> tuple[str, ...]:
    return _coerce_string_sequence(payload.get(level), context=f"{level}.parent_signals")


def _parent_signals_from_nested_sensors(
    payload: Mapping[str, Any],
    level: str,
) -> tuple[str, ...]:
    level_data = _coerce_mapping(payload.get(level), context=level)
    return _coerce_string_sequence(level_data.get("sensors"), context=f"{level}.sensors")


def _yaw_calibration_fields(payload: Mapping[str, Any], level: str) -> Mapping[str, JsonValue]:
    del level
    return {
        "yaw_parameter": payload["yaw_parameter"],
        "yaw_offset": payload["yaw_offset"],
    }


def _strain_calibration_fields(payload: Mapping[str, Any], level: str) -> Mapping[str, JsonValue]:
    level_data = _coerce_mapping(payload.get(level), context=level)
    return {
        "yaw_parameter": payload["yaw_parameter"],
        "yaw_offset": payload["yaw_offset"],
        "measurement_location": level_data["measurement_location"],
    }


def _default_signal_postprocessor(
    signals: MutableMapping[str, ProcessedSignalRecord],
) -> None:
    """Apply default wind-farm status and offset normalization rules."""
    for signal_name, record in signals.items():
        if signal_name.startswith("NRT"):
            if record.status_rows:
                indices_to_drop: list[int] = []
                for index, row in enumerate(record.status_rows):
                    if "name" in row and "status" not in row:
                        previous_index = index - 1
                        next_index = index + 1
                        if previous_index >= 0 and "status" in record.status_rows[previous_index]:
                            row["status"] = record.status_rows[previous_index]["status"]
                            indices_to_drop.append(previous_index)
                        elif next_index < len(record.status_rows) and "status" in record.status_rows[next_index]:
                            row["status"] = record.status_rows[next_index]["status"]
                            indices_to_drop.append(next_index)
                record.status_rows = [
                    row for index, row in enumerate(record.status_rows) if index not in indices_to_drop
                ]

            temperature_comp = record.scalar_fields.get("temperature_compensation")
            if isinstance(temperature_comp, Mapping) and record.offset_rows:
                record.offset_rows[0] = {**record.offset_rows[0], **dict(temperature_comp)}
                tc_sensor = temperature_comp.get("TCSensor")
                for row in record.offset_rows[1:]:
                    row["TCSensor"] = tc_sensor


@dataclass(frozen=True)
class DerivedSignalUpdate:
    """One derived-signal contribution emitted from a source event.

    Parameters
    ----------
    signal_name
        Final derived signal identifier emitted for the event.
    parent_signals
        Parent signal identifiers referenced by the derived signal.
    calibration_fields
        Calibration row fields appended at the event timestamp.
    data_fields
        Optional extra metadata stored under the legacy ``data`` payload.
    """

    signal_name: str
    parent_signals: tuple[str, ...]
    calibration_fields: Mapping[str, JsonValue]
    data_fields: Mapping[str, JsonValue] = field(default_factory=dict)


class DerivedSignalStrategy(ABC):
    """Strategy for translating one event into derived-signal updates.

    Implementations keep farm-specific derived-signal semantics outside the
    generic processor loop.
    """

    @abstractmethod
    def emit_updates(
        self,
        event_key: str,
        payload: Mapping[str, Any],
    ) -> list[DerivedSignalUpdate]:
        """Build derived-signal updates for one event payload.

        Parameters
        ----------
        event_key
            Raw event key that selected the strategy.
        payload
            Mapping stored under the raw event key.

        Returns
        -------
        list[DerivedSignalUpdate]
            Derived-signal mutations emitted for the event.
        """


@dataclass(frozen=True)
class LevelBasedDerivedSignalStrategy(DerivedSignalStrategy):
    """Expand a level-based event into derived signals.

    Parameters
    ----------
    suffixes
        Suffixes appended to each level identifier.
    signal_name_builder
        Callback used to derive the final signal name for a level/suffix pair.
    parent_signals_builder
        Callback that returns parent signal identifiers for a level.
    calibration_fields_builder
        Callback that returns calibration data for a level.
    data_builder
        Optional callback for extra metadata stored under ``data``.

    Examples
    --------
    >>> strategy = LevelBasedDerivedSignalStrategy(
    ...     suffixes=("FA",),
    ...     parent_signals_builder=lambda payload, level: tuple(payload[level]),
    ...     calibration_fields_builder=lambda payload, level: {"yaw_offset": payload["yaw_offset"]},
    ... )
    >>> updates = strategy.emit_updates(
    ...     "acceleration/yaw_transformation",
    ...     {"levels": ["SIG_A"], "yaw_offset": 2.0, "SIG_A": ["PARENT_1", "PARENT_2"]},
    ... )
    >>> updates[0].signal_name
    'SIG_A_FA'
    >>> updates[0].parent_signals
    ('PARENT_1', 'PARENT_2')
    """

    suffixes: tuple[str, ...]
    signal_name_builder: SignalNameBuilder = _default_level_signal_name
    parent_signals_builder: ParentSignalsBuilder = _parent_signals_from_level
    calibration_fields_builder: CalibrationFieldsBuilder = _yaw_calibration_fields
    data_builder: DerivedDataBuilder | None = None
    levels_key: str = "levels"

    def emit_updates(
        self,
        event_key: str,
        payload: Mapping[str, Any],
    ) -> list[DerivedSignalUpdate]:
        """Build derived-signal updates for a level-based payload.

        Parameters
        ----------
        event_key
            Raw event key that triggered the strategy. The value is accepted
            for interface parity and is not used directly by the default
            implementation.
        payload
            Mapping that must contain the configured ``levels_key`` plus the
            fields required by the configured callbacks.

        Returns
        -------
        list[DerivedSignalUpdate]
            One update per level and configured suffix.
        """
        del event_key
        levels = _coerce_string_sequence(payload.get(self.levels_key), context=self.levels_key)
        updates: list[DerivedSignalUpdate] = []
        for level in levels:
            for suffix in self.suffixes:
                updates.append(
                    DerivedSignalUpdate(
                        signal_name=self.signal_name_builder(level, suffix),
                        parent_signals=tuple(self.parent_signals_builder(payload, level)),
                        calibration_fields=dict(self.calibration_fields_builder(payload, level)),
                        data_fields=(dict(self.data_builder(payload, level)) if self.data_builder is not None else {}),
                    )
                )
        return updates


# ---------------------------------------------------------------------------
# Registry maps – YAML-driven callable resolution
# ---------------------------------------------------------------------------

_SIGNAL_NAME_BUILDERS: Final[dict[str, SignalNameBuilder]] = {
    "default_level_signal_name": _default_level_signal_name,
    "default_strain_signal_name": _default_strain_signal_name,
}

_PARENT_SIGNALS_BUILDERS: Final[dict[str, ParentSignalsBuilder]] = {
    "parent_signals_from_level": _parent_signals_from_level,
    "parent_signals_from_nested_sensors": _parent_signals_from_nested_sensors,
}

_CALIBRATION_FIELDS_BUILDERS: Final[dict[str, CalibrationFieldsBuilder]] = {
    "yaw_calibration_fields": _yaw_calibration_fields,
    "strain_calibration_fields": _strain_calibration_fields,
}

_DERIVED_DATA_BUILDERS: Final[dict[str, DerivedDataBuilder]] = {}

_SIGNAL_POSTPROCESSORS: Final[dict[str, SignalPostprocessor]] = {
    "default_signal_postprocessor": _default_signal_postprocessor,
}


def _resolve_registry_value(
    *,
    registry: Mapping[str, Any],
    raw_name: Any,
    context: str,
) -> Any:
    name = _coerce_string(raw_name, context=context)
    try:
        return registry[name]
    except KeyError as exc:
        raise ValueError(f"Unknown value '{name}' for {context}.") from exc

"""Signal key parsing and type coercion helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type LegacyRecord = dict[str, Any]
type LegacySignalMap = dict[str, LegacyRecord]


def _coerce_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected mapping data for {context}.")
    return value


def _coerce_string_sequence(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"Expected a list of strings for {context}.")
    return tuple(str(item) for item in value)


def _coerce_string(value: Any, *, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Expected a string for {context}.")
    return value


@dataclass(frozen=True, slots=True)
class SignalEventKey:
    """Parsed signal-property key.

    Parameters
    ----------
    signal_name
        Canonical signal identifier.
    property_name
        Property name carried by the raw configuration key.
    """

    signal_name: str
    property_name: str


@dataclass(frozen=True, slots=True)
class DelimitedSignalKeyParser:
    """Parse delimited signal-property keys.

    Parameters
    ----------
    signal_prefixes
        Raw key prefixes that belong to direct signal properties.
    separator
        Separator between the signal identifier and the property name.

    Examples
    --------
    >>> parser = DelimitedSignalKeyParser(signal_prefixes=("WF", "X/", "Y/", "Z/"))
    >>> parser.parse("WF_WTG_TP_STRAIN/status")
    SignalEventKey(signal_name='WF_WTG_TP_STRAIN', property_name='status')
    >>> parser.parse("acceleration/yaw_transformation") is None
    True
    """

    signal_prefixes: tuple[str, ...]
    separator: str = "/"

    def matches(self, raw_key: str) -> bool:
        """Return ``True`` when the raw key belongs to a direct signal.

        Parameters
        ----------
        raw_key
            Raw configuration key to test.

        Returns
        -------
        bool
            Whether the key starts with one of the configured signal prefixes.
        """
        return raw_key.startswith(self.signal_prefixes)

    def parse(self, raw_key: str) -> SignalEventKey | None:
        """Parse a raw key into a signal/property pair.

        Parameters
        ----------
        raw_key
            Raw configuration key containing a signal name and property name
            separated by :attr:`separator`.

        Returns
        -------
        SignalEventKey or None
            Parsed key, or *None* when the key does not match or lacks a
            separator.
        """
        if not self.matches(raw_key) or self.separator not in raw_key:
            return None

        signal_name, property_name = raw_key.split(self.separator, maxsplit=1)
        if not signal_name or not property_name:
            return None
        return SignalEventKey(signal_name=signal_name, property_name=property_name)

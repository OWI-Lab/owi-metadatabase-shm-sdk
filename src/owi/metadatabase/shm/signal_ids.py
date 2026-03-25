"""Typed parsing for SHM signal identifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

_ALLOWED_ORIENTATIONS: Final[frozenset[str]] = frozenset({"0", "T", "X", "Y", "Z", "SS", "FA"})
_NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\d+")


@dataclass(frozen=True)
class LegacySignalIdentifier:
    """Parsed representation of an SHM signal identifier."""

    raw: str
    parts: tuple[str, ...]
    subassembly: str
    signal_type: str
    lateral_position: int | None
    angular_position: int | None
    orientation: str | None

    def to_legacy_dict(self) -> dict[str, str | int | None]:
        """Return the historical dict shape used by archive payload code."""
        data: dict[str, str | int | None] = {
            "sa": self.subassembly,
            "type": self.signal_type,
            "lat": self.lateral_position,
            "deg": self.angular_position,
        }
        if len(self.parts) > 4:
            data["orientation"] = self.orientation
        return data


def _extract_number(token: str) -> int:
    match = _NUMBER_PATTERN.search(token)
    if match is None:
        raise ValueError(f"Found {match} for {token}")
    return int(match.group())


def _parse_position(parts: tuple[str, ...], index: int, prefix: str) -> int | None:
    if len(parts) > index and parts[index].startswith(prefix):
        return _extract_number(parts[index])
    return None


def _parse_orientation(parts: tuple[str, ...]) -> str | None:
    for index in (6, 5, 4):
        if len(parts) > index:
            token = parts[index]
            return token if token in _ALLOWED_ORIENTATIONS else "0"
    return None


def parse_legacy_signal_id(signal_id: str) -> LegacySignalIdentifier | None:
    """Parse an SHM signal identifier into a typed model."""
    parts = tuple(signal_id.split("_"))
    if len(parts) < 4:
        return None

    return LegacySignalIdentifier(
        raw=signal_id,
        parts=parts,
        subassembly=parts[2],
        signal_type=parts[3],
        lateral_position=_parse_position(parts, 4, "LAT"),
        angular_position=_parse_position(parts, 5, "DEG"),
        orientation=_parse_orientation(parts),
    )

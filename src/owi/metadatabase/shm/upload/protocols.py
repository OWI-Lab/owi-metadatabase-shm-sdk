"""Protocol definitions for SHM upload clients."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class SignalConfigUploadSource(Protocol):
    """Protocol for processors that feed turbine-scoped upload data."""

    signals_data: Mapping[str, Mapping[str, Mapping[str, Any]]]
    signals_derived_data: Mapping[str, Mapping[str, Mapping[str, Any]]]

    def signals_process_data(self) -> None:
        """Populate turbine-scoped signal dictionaries."""
        ...


class ShmSignalUploadClient(Protocol):
    """Protocol describing the SHM transport methods used by the uploader."""

    def get_sensor_type(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one SHM sensor type record."""
        ...

    def get_sensor(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one SHM sensor record."""
        ...

    def create_signal(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a signal record."""
        ...

    def get_signal(self, signal_id: str, **kwargs: Any) -> dict[str, Any]:
        """Resolve a signal record by backend identifier."""
        ...

    def create_signal_history(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a signal history record."""
        ...

    def create_signal_calibration(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a signal calibration record."""
        ...

    def create_derived_signal(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a derived signal record."""
        ...

    def create_derived_signal_history(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a derived signal history record."""
        ...

    def patch_derived_signal_history(
        self,
        history_id: int,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Patch a derived signal history record."""
        ...

    def create_derived_signal_calibration(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Create a derived signal calibration record."""
        ...

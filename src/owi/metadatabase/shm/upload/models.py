"""Upload request and result models for SHM signal upload."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..processing import SignalProcessingResult

SignalConfigMap = Mapping[str, Mapping[str, Any]]
SignalConfigMapByTurbine = Mapping[str, SignalConfigMap]


@dataclass(frozen=True)
class AssetSignalUploadRequest:
    """Input data for uploading one asset's SHM signals.

    Parameters
    ----------
    projectsite
        Parent SDK project site title.
    assetlocation
        Parent SDK asset location title.
    signals
        Archive-compatible main signal data keyed by signal identifier.
    derived_signals
        Archive-compatible derived signal data keyed by derived signal
        identifier.
    permission_group_ids
        Visibility groups applied to created SHM objects.
    sensor_serial_numbers_by_signal
        Optional map from signal identifier to the backend SHM sensor
        identifier stored on signal history rows.
    temperature_compensation_signal_ids
        Optional map from legacy temperature-compensation sensor token to
        backend SHM signal id.

    Examples
    --------
    >>> request = AssetSignalUploadRequest(
    ...     projectsite="Project A",
    ...     assetlocation="Asset-01",
    ...     signals={},
    ... )
    >>> request.result_key
    'Project A/Asset-01'
    """

    projectsite: str
    assetlocation: str
    signals: SignalConfigMap
    derived_signals: SignalConfigMap | None = None
    permission_group_ids: Sequence[int] | None = None
    sensor_serial_numbers_by_signal: Mapping[str, int] | None = None
    temperature_compensation_signal_ids: Mapping[str, int] | None = None

    @property
    def result_key(self) -> str:
        """Return a stable asset-scoped result key."""
        return f"{self.projectsite}/{self.assetlocation}"

    @classmethod
    def from_processing_result(
        cls,
        *,
        projectsite: str,
        assetlocation: str,
        processing_result: SignalProcessingResult,
        permission_group_ids: Sequence[int] | None = None,
        sensor_serial_numbers_by_signal: Mapping[str, int] | None = None,
        temperature_compensation_signal_ids: Mapping[str, int] | None = None,
    ) -> AssetSignalUploadRequest:
        """Build an upload request from a processed signal-config result.

        Parameters
        ----------
        projectsite
            Parent SDK project site title.
        assetlocation
            Parent SDK asset location title.
        processing_result
            Processed signal and derived-signal records emitted by a processor.
        permission_group_ids
            Visibility groups applied to created SHM objects.
        sensor_serial_numbers_by_signal
            Optional map from signal identifier to backend sensor serial
            number used for signal history rows.
        temperature_compensation_signal_ids
            Optional map from legacy temperature-compensation sensor token to
            backend SHM signal id.

        Returns
        -------
        AssetSignalUploadRequest
            Asset-scoped upload request that preserves the archive-compatible
            payload shape.

        Examples
        --------
        >>> from owi.metadatabase.shm.processing import ProcessedSignalRecord, SignalProcessingResult
        >>> signal = ProcessedSignalRecord()
        >>> signal.add_status("01/01/1972 00:00", "ok")
        >>> request = AssetSignalUploadRequest.from_processing_result(
        ...     projectsite="Project A",
        ...     assetlocation="Asset-01",
        ...     processing_result=SignalProcessingResult(signals={"SIG": signal}, derived_signals={}),
        ... )
        >>> request.signals["SIG"]["status"][0]["status"]
        'ok'
        """
        signals, derived_signals = processing_result.to_legacy_data()
        return cls(
            projectsite=projectsite,
            assetlocation=assetlocation,
            signals=signals,
            derived_signals=derived_signals or None,
            permission_group_ids=permission_group_ids,
            sensor_serial_numbers_by_signal=sensor_serial_numbers_by_signal,
            temperature_compensation_signal_ids=temperature_compensation_signal_ids,
        )


@dataclass(frozen=True)
class AssetSignalUploadResult:
    """Upload result for one asset.

    Parameters
    ----------
    asset_key
        Stable asset-scoped result key in ``projectsite/assetlocation`` form.
    signal_ids_by_name
        Backend ids for created main signals keyed by signal identifier.
    derived_signal_ids_by_name
        Backend ids for created derived signals keyed by signal identifier.
    results_main
        Raw backend responses for main signal creation calls.
    results_secondary
        Raw backend responses for signal history and calibration calls.
    results_derived_main
        Raw backend responses for derived signal creation calls.
    results_derived_secondary
        Raw backend responses for derived history, parent patch, and
        calibration calls.

    This keeps the legacy result bucket names so archive-style callers can
    migrate incrementally while the request model becomes generic.
    """

    asset_key: str
    signal_ids_by_name: Mapping[str, int]
    derived_signal_ids_by_name: Mapping[str, int]
    results_main: Sequence[dict[str, Any]]
    results_secondary: Sequence[dict[str, Any]]
    results_derived_main: Sequence[dict[str, Any]]
    results_derived_secondary: Sequence[dict[str, Any]]

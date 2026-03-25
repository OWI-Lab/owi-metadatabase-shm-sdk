"""Signal configuration processor hierarchy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any, cast

from ..json_utils import load_json_data
from .parsing import LegacySignalMap, SignalEventKey, _coerce_mapping
from .records import ProcessedDerivedSignalRecord, ProcessedSignalRecord, SignalProcessingResult
from .spec import SignalProcessorSpec, load_default_signal_processor_spec, load_signal_processor_spec
from .strategies import DerivedSignalUpdate


class SignalConfigProcessor(ABC):
    """ABC-backed base class for wind-farm signal config processors.

    Parameters
    ----------
    path_configs
        Directory or JSON file containing farm signal configuration events.
    turbines
        Optional subset of turbine stems to process during discovery.

    Notes
    -----
    Subclasses provide the farm-specific :class:`SignalProcessorSpec` used by
    the generic processing pipeline.
    """

    def __init__(
        self,
        path_configs: str | Path,
        turbines: Sequence[str] | None = None,
    ) -> None:
        self.path_configs = Path(path_configs)
        self.turbines = list(turbines) if turbines is not None else None
        self.signals_data: dict[str, LegacySignalMap] = {}
        self.signals_derived_data: dict[str, LegacySignalMap] = {}
        self.processor_spec = self.build_processor_spec()

    @abstractmethod
    def build_processor_spec(self) -> SignalProcessorSpec:
        """Return the farm-specific processor specification.

        Returns
        -------
        SignalProcessorSpec
            Specification controlling signal key parsing, derived-signal
            strategies, and postprocessors.
        """

    def process_events(self, events: Sequence[Mapping[str, Any]]) -> SignalProcessingResult:
        """Transform raw configuration events into typed signal records.

        Parameters
        ----------
        events
            Ordered raw configuration events loaded from one farm config.

        Returns
        -------
        SignalProcessingResult
            Typed signal and derived-signal records that can be converted to
            the archive-compatible uploader payload shape.

        Examples
        --------
        >>> from owi.metadatabase.shm.processing import (
        ...     ConfiguredSignalConfigProcessor,
        ...     DelimitedSignalKeyParser,
        ...     SignalProcessorSpec,
        ... )
        >>> spec = SignalProcessorSpec(
        ...     farm_name="Demo",
        ...     signal_key_parser=DelimitedSignalKeyParser(signal_prefixes=("WF_",)),
        ...     derived_signal_strategies={},
        ... )
        >>> processor = ConfiguredSignalConfigProcessor(path_configs='.', processor_spec=spec)
        >>> result = processor.process_events([{"WF_SIG/status": "ok"}])
        >>> result.to_legacy_data()[0]["WF_SIG"]["status"][0]["status"]
        'ok'
        """
        signals: dict[str, ProcessedSignalRecord] = {}
        derived_signals: dict[str, ProcessedDerivedSignalRecord] = {}
        current_time = self.processor_spec.default_initial_time

        for index, event in enumerate(events):
            current_time = self._resolve_event_time(
                event,
                index=index,
                current_time=current_time,
            )
            for raw_key, value in event.items():
                signal_key = self.processor_spec.signal_key_parser.parse(raw_key)
                if signal_key is not None:
                    self._apply_signal_property(
                        signals=signals,
                        signal_key=signal_key,
                        value=value,
                        timestamp=current_time,
                    )
                    continue

                strategy = self.processor_spec.derived_signal_strategies.get(raw_key)
                if strategy is None:
                    continue
                payload = _coerce_mapping(value, context=raw_key)
                self._apply_derived_updates(
                    derived_signals=derived_signals,
                    event_key=raw_key,
                    updates=strategy.emit_updates(raw_key, payload),
                    timestamp=current_time,
                )

        self._postprocess_signals(signals)
        return SignalProcessingResult(signals=signals, derived_signals=derived_signals)

    def signal_preprocess_data(
        self,
        path_config: str | Path,
    ) -> tuple[LegacySignalMap, LegacySignalMap]:
        """Process one configuration file into archive-compatible mappings.

        Parameters
        ----------
        path_config
            JSON configuration file to load and process.

        Returns
        -------
        tuple[LegacySignalMap, LegacySignalMap]
            Main-signal and derived-signal mappings ready for uploader seams.
        """
        events = self._load_events(path_config)
        return self.process_events(events).to_legacy_data()

    def signals_process_data(self) -> None:
        """Process all discovered configuration files under ``path_configs``.

        The processed results are stored on :attr:`signals_data` and
        :attr:`signals_derived_data`, keyed by turbine stem.
        """
        config_paths = self.processor_spec.config_discovery.discover(
            self.path_configs,
            turbines=self.turbines,
        )
        self.turbines = list(config_paths)
        for turbine, config_path in config_paths.items():
            signals_data, derived_data = self.signal_preprocess_data(config_path)
            self.signals_data[turbine] = signals_data
            self.signals_derived_data[turbine] = derived_data

    def _load_events(self, path_config: str | Path) -> list[Mapping[str, Any]]:
        payload = load_json_data(path_config)
        if not isinstance(payload, list):
            raise ValueError("Signal configuration files must contain a list of events.")

        events: list[Mapping[str, Any]] = []
        for index, event in enumerate(payload):
            if not isinstance(event, Mapping):
                raise ValueError(f"Signal configuration event {index} must be a mapping.")
            events.append(cast(Mapping[str, Any], event))
        return events

    def _resolve_event_time(
        self,
        event: Mapping[str, Any],
        *,
        index: int,
        current_time: str,
    ) -> str:
        if self.processor_spec.time_field in event:
            return str(event[self.processor_spec.time_field])
        if index == 0:
            return self.processor_spec.default_initial_time
        return current_time

    def _apply_signal_property(
        self,
        *,
        signals: MutableMapping[str, ProcessedSignalRecord],
        signal_key: SignalEventKey,
        value: Any,
        timestamp: str,
    ) -> None:
        record = signals.setdefault(signal_key.signal_name, ProcessedSignalRecord())
        property_name = signal_key.property_name

        if property_name == "status":
            record.add_status(timestamp, value)
        elif property_name == "name":
            alias_target = signals.setdefault(str(value), ProcessedSignalRecord())
            alias_target.add_status_alias(timestamp, signal_key.signal_name)
        elif property_name == "offset":
            record.add_offset(timestamp, value)
        elif property_name == "cwl":
            record.add_cwl(timestamp, value)
        else:
            record.set_scalar(property_name, value)

    def _apply_derived_updates(
        self,
        *,
        derived_signals: MutableMapping[str, ProcessedDerivedSignalRecord],
        event_key: str,
        updates: Sequence[DerivedSignalUpdate],
        timestamp: str,
    ) -> None:
        for update in updates:
            record = derived_signals.setdefault(update.signal_name, ProcessedDerivedSignalRecord())
            record.ensure_source_name(event_key, extra_fields=update.data_fields)
            record.set_parent_signals(update.parent_signals)
            record.add_calibration(timestamp, update.calibration_fields)

    def _postprocess_signals(
        self,
        signals: MutableMapping[str, ProcessedSignalRecord],
    ) -> None:
        for postprocessor in self.processor_spec.postprocessors:
            postprocessor(signals)


class ConfiguredSignalConfigProcessor(SignalConfigProcessor):
    """Signal processor backed by an explicit farm spec.

    Parameters
    ----------
    path_configs
        Directory or JSON file containing farm signal configuration events.
    processor_spec
        Explicit processor specification that defines parsing, derivation, and
        discovery behavior.
    turbines
        Optional subset of turbine stems to process during discovery.

    Examples
    --------
    >>> from owi.metadatabase.shm.processing import DelimitedSignalKeyParser, SignalProcessorSpec
    >>> spec = SignalProcessorSpec(
    ...     farm_name="Demo",
    ...     signal_key_parser=DelimitedSignalKeyParser(signal_prefixes=("WF_",)),
    ...     derived_signal_strategies={},
    ... )
    >>> processor = ConfiguredSignalConfigProcessor(path_configs='.', processor_spec=spec)
    >>> result = processor.process_events([{"WF_SIG/status": "ok"}])
    >>> result.to_legacy_data()[0]["WF_SIG"]["status"][0]["status"]
    'ok'
    """

    def __init__(
        self,
        path_configs: str | Path,
        processor_spec: SignalProcessorSpec,
        turbines: Sequence[str] | None = None,
    ) -> None:
        self._processor_spec = processor_spec
        super().__init__(path_configs=path_configs, turbines=turbines)

    def build_processor_spec(self) -> SignalProcessorSpec:
        """Return the explicit processor spec passed to the constructor.

        Returns
        -------
        SignalProcessorSpec
            The specification supplied at construction time.
        """
        return self._processor_spec

    @classmethod
    def from_yaml_spec(
        cls,
        *,
        path_configs: str | Path,
        processor_spec_path: str | Path,
        turbines: Sequence[str] | None = None,
    ) -> ConfiguredSignalConfigProcessor:
        """Construct a configured processor from a YAML-backed processor spec.

        Parameters
        ----------
        path_configs
            Directory or JSON file containing farm configuration events.
        processor_spec_path
            Path to a YAML processor specification file.
        turbines
            Optional subset of turbine stems to process during discovery.

        Returns
        -------
        ConfiguredSignalConfigProcessor
            Processor loaded with the given YAML spec.
        """
        return cls(
            path_configs=path_configs,
            processor_spec=load_signal_processor_spec(processor_spec_path),
            turbines=turbines,
        )


class DefaultSignalConfigProcessor(ConfiguredSignalConfigProcessor):
    """Built-in specialization of the generic signal processor.

    Parameters
    ----------
    path_configs
        Directory or JSON file containing default wind-farm configuration events.
    turbines
        Optional subset of turbine stems to process during discovery.
    processor_spec
        Optional override for the built-in default processor specification.
    """

    def __init__(
        self,
        path_configs: str | Path,
        turbines: Sequence[str] | None = None,
        processor_spec: SignalProcessorSpec | None = None,
    ) -> None:
        super().__init__(
            path_configs=path_configs,
            turbines=turbines,
            processor_spec=processor_spec or load_default_signal_processor_spec(),
        )

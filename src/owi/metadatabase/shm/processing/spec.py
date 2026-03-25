"""Signal processor specification and YAML loading."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .discovery import ConfigDiscovery, JsonStemConfigDiscovery
from .parsing import DelimitedSignalKeyParser, _coerce_mapping, _coerce_string, _coerce_string_sequence
from .strategies import (
    _CALIBRATION_FIELDS_BUILDERS,
    _DERIVED_DATA_BUILDERS,
    _PARENT_SIGNALS_BUILDERS,
    _SIGNAL_NAME_BUILDERS,
    _SIGNAL_POSTPROCESSORS,
    CalibrationFieldsBuilder,
    DerivedSignalStrategy,
    LevelBasedDerivedSignalStrategy,
    SignalPostprocessor,
    _resolve_registry_value,
)


@dataclass(frozen=True)
class SignalProcessorSpec:
    """Farm-specific configuration for signal processing.

    The YAML structure expected by this spec is designed to be flexible enough
    to cover a wide range of use cases while remaining human-friendly and
    avoiding excessive nesting. The top-level keys are:

    - ``farm_name``: A human-readable farm identifier used by the caller.
    - ``signal_key_parser``: A configuration for the signal key parser, which
      recognizes direct signal-property keys in the input data.
    - ``derived_signal_strategies``: A mapping from raw event keys to
      derived-signal strategies, which define how to generate derived signals
      based on specific events in the input data.
    - ``config_discovery``: A strategy used to discover configuration files on
      disk, allowing the processor to locate and load necessary configurations
      for processing signals.
    - ``postprocessors``: A list of pure normalization hooks applied after all
      events are processed, enabling additional transformations or clean-up
      steps on the processed signals.
    - ``time_field``: The event field used to update the active timestamp during
      processing.
    - ``default_initial_time``: The timestamp assigned to the first event when
      the payload omits one, ensuring that all events have a valid timestamp for
      processing.

    Parameters
    ----------
    farm_name
        Human-readable farm identifier used by the caller.
    signal_key_parser
        Parser that recognizes direct signal-property keys.
    derived_signal_strategies
        Mapping from raw event keys to derived-signal strategies.
    config_discovery
        Strategy used to discover configuration files on disk.
    postprocessors
        Pure normalization hooks applied after all events are processed.
    time_field
        Event field used to update the active timestamp.
    default_initial_time
        Timestamp assigned to the first event when the payload omits one.

    Examples
    --------
    >>> spec = SignalProcessorSpec(
    ...     farm_name="Demo Farm",
    ...     signal_key_parser=DelimitedSignalKeyParser(signal_prefixes=("WF_",)),
    ...     derived_signal_strategies={},
    ... )
    >>> spec.default_initial_time
    '01/01/1972 00:00'

    YAML example
    ~~~~~~~~~~~~

    .. code-block:: yaml
        farm_name: Demo Farm
        signal_key_parser:
          kind: delimited
          signal_prefixes: ["WF_"]
        derived_signal_strategies: {}
        config_discovery:
          kind: json_stem
        postprocessors: []
        time_field: time
        default_initial_time: '01/01/1972 00:00'

    """

    farm_name: str
    signal_key_parser: DelimitedSignalKeyParser
    derived_signal_strategies: Mapping[str, DerivedSignalStrategy]
    config_discovery: ConfigDiscovery = JsonStemConfigDiscovery()
    postprocessors: tuple[SignalPostprocessor, ...] = ()
    time_field: str = "time"
    default_initial_time: str = "01/01/1972 00:00"


# ---------------------------------------------------------------------------
# YAML config loading helpers
# ---------------------------------------------------------------------------


def _build_signal_key_parser_from_config(
    raw_config: Mapping[str, Any],
) -> DelimitedSignalKeyParser:
    kind = _coerce_string(raw_config.get("kind", "delimited"), context="signal_key_parser.kind")
    if kind != "delimited":
        raise ValueError(f"Unsupported signal key parser kind: {kind}.")

    return DelimitedSignalKeyParser(
        signal_prefixes=_coerce_string_sequence(
            raw_config.get("signal_prefixes"),
            context="signal_key_parser.signal_prefixes",
        ),
        separator=_coerce_string(
            raw_config.get("separator", "/"),
            context="signal_key_parser.separator",
        ),
    )


def _build_level_based_strategy_from_config(
    event_key: str,
    raw_config: Mapping[str, Any],
) -> LevelBasedDerivedSignalStrategy:
    signal_name_builder = _SIGNAL_NAME_BUILDERS["default_level_signal_name"]
    if "signal_name_builder" in raw_config:
        signal_name_builder = _resolve_registry_value(
            registry=_SIGNAL_NAME_BUILDERS,
            raw_name=raw_config["signal_name_builder"],
            context=f"derived_signal_strategies.{event_key}.signal_name_builder",
        )

    parent_signals_builder = _resolve_registry_value(
        registry=_PARENT_SIGNALS_BUILDERS,
        raw_name=raw_config.get("parent_signals_builder"),
        context=f"derived_signal_strategies.{event_key}.parent_signals_builder",
    )
    calibration_fields_builder: CalibrationFieldsBuilder = _resolve_registry_value(
        registry=_CALIBRATION_FIELDS_BUILDERS,
        raw_name=raw_config.get("calibration_fields_builder"),
        context=f"derived_signal_strategies.{event_key}.calibration_fields_builder",
    )

    data_builder = None
    if "data_builder" in raw_config:
        data_builder = _resolve_registry_value(
            registry=_DERIVED_DATA_BUILDERS,
            raw_name=raw_config["data_builder"],
            context=f"derived_signal_strategies.{event_key}.data_builder",
        )

    return LevelBasedDerivedSignalStrategy(
        suffixes=_coerce_string_sequence(
            raw_config.get("suffixes"),
            context=f"derived_signal_strategies.{event_key}.suffixes",
        ),
        signal_name_builder=signal_name_builder,
        parent_signals_builder=parent_signals_builder,
        calibration_fields_builder=calibration_fields_builder,
        data_builder=data_builder,
        levels_key=_coerce_string(
            raw_config.get("levels_key", "levels"),
            context=f"derived_signal_strategies.{event_key}.levels_key",
        ),
    )


def _build_derived_signal_strategy_from_config(
    event_key: str,
    raw_config: Mapping[str, Any],
) -> DerivedSignalStrategy:
    kind = _coerce_string(
        raw_config.get("kind", "level_based"),
        context=f"derived_signal_strategies.{event_key}.kind",
    )
    if kind != "level_based":
        raise ValueError(f"Unsupported derived signal strategy kind: {kind}.")
    return _build_level_based_strategy_from_config(event_key, raw_config)


def _build_config_discovery_from_config(raw_config: Mapping[str, Any]) -> ConfigDiscovery:
    kind = _coerce_string(raw_config.get("kind", "json_stem"), context="config_discovery.kind")
    if kind != "json_stem":
        raise ValueError(f"Unsupported config discovery kind: {kind}.")

    return JsonStemConfigDiscovery(
        suffix=_coerce_string(raw_config.get("suffix", ".json"), context="config_discovery.suffix")
    )


def load_signal_processor_spec(path: str | Path) -> SignalProcessorSpec:
    """Load a signal processor spec from a YAML document.

    The YAML document must conform to the structure expected by
    ``SignalProcessorSpec``.

    Parameters
    ----------
    path
        Path to the YAML document describing the processor spec.

    Returns
    -------
    SignalProcessorSpec
        Parsed processor specification.
    """
    raw_data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    config = _coerce_mapping(raw_data, context=str(path))

    raw_signal_key_parser = _coerce_mapping(
        config.get("signal_key_parser"),
        context="signal_key_parser",
    )
    raw_derived_signal_strategies = _coerce_mapping(
        config.get("derived_signal_strategies", {}),
        context="derived_signal_strategies",
    )
    raw_config_discovery = config.get("config_discovery", {"kind": "json_stem"})
    raw_postprocessors = config.get("postprocessors", ())

    return SignalProcessorSpec(
        farm_name=_coerce_string(config.get("farm_name"), context="farm_name"),
        signal_key_parser=_build_signal_key_parser_from_config(raw_signal_key_parser),
        derived_signal_strategies={
            event_key: _build_derived_signal_strategy_from_config(
                event_key,
                _coerce_mapping(
                    raw_strategy,
                    context=f"derived_signal_strategies.{event_key}",
                ),
            )
            for event_key, raw_strategy in raw_derived_signal_strategies.items()
        },
        config_discovery=_build_config_discovery_from_config(
            _coerce_mapping(raw_config_discovery, context="config_discovery")
        ),
        postprocessors=tuple(
            _resolve_registry_value(
                registry=_SIGNAL_POSTPROCESSORS,
                raw_name=postprocessor_name,
                context="postprocessors",
            )
            for postprocessor_name in _coerce_string_sequence(
                raw_postprocessors,
                context="postprocessors",
            )
        ),
        time_field=_coerce_string(config.get("time_field", "time"), context="time_field"),
        default_initial_time=_coerce_string(
            config.get("default_initial_time", "01/01/1972 00:00"),
            context="default_initial_time",
        ),
    )


def get_default_signal_processor_spec_path() -> Path:
    """Return the packaged YAML path for the built-in default processor spec.

    Returns
    -------
    Path
        Absolute path to ``default_signal_processor.yaml`` shipped with the
        package.
    """
    return Path(__file__).parent.parent / "config" / "default_signal_processor.yaml"


def load_default_signal_processor_spec() -> SignalProcessorSpec:
    """Load the built-in default processor spec from its YAML document.

    Returns
    -------
    SignalProcessorSpec
        Processor specification loaded from the packaged YAML file.
    """
    return load_signal_processor_spec(get_default_signal_processor_spec_path())


def default_signal_processor_spec() -> SignalProcessorSpec:
    """Return the built-in default processor spec for wind-farm signal configs.

    Returns
    -------
    SignalProcessorSpec
        Pre-loaded default specification.

    Examples
    --------
    >>> spec = default_signal_processor_spec()
    >>> tuple(spec.derived_signal_strategies)
    ('acceleration/yaw_transformation', 'strain/bending_moment')
    """
    return load_default_signal_processor_spec()

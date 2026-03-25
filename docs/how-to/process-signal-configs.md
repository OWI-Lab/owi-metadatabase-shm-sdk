# Process Signal Configs

This guide shows how to parse raw JSON signal configuration events into
typed records using the processing pipeline, optionally driven by a YAML spec.

## Prerequisites

- JSON configuration files (one per turbine) containing arrays of events
- Optionally, a YAML processor spec for farm-specific parsing rules

## Using the Default Processor

The built-in default processor handles the standard Norther wind farm format:

```python
from owi.metadatabase.shm import DefaultSignalConfigProcessor

processor = DefaultSignalConfigProcessor(
    path_configs="data/Norther/signal_configs/",
)
processor.signals_process_data()

# Processed data is now available
print(list(processor.signals_data.keys()))       # turbine names
print(list(processor.signals_derived_data.keys()))
```

## Using a Custom YAML Spec

For farms with non-standard signal naming:

```python
from owi.metadatabase.shm import ConfiguredSignalConfigProcessor

processor = ConfiguredSignalConfigProcessor.from_yaml_spec(
    path_configs="data/MyFarm/signal_configs/",
    processor_spec_path="config/my_farm_processor.yaml",
)
processor.signals_process_data()
```

## Processing a Single Event List

For programmatic use without file discovery:

```python
from owi.metadatabase.shm import (
    ConfiguredSignalConfigProcessor,
    DelimitedSignalKeyParser,
    SignalProcessorSpec,
)

spec = SignalProcessorSpec(
    farm_name="Demo",
    signal_key_parser=DelimitedSignalKeyParser(signal_prefixes=("WF_",)),
    derived_signal_strategies={},
)

processor = ConfiguredSignalConfigProcessor(path_configs=".", processor_spec=spec)
result = processor.process_events([
    {"time": "01/01/2023 00:00", "WF_SIG/status": "ok"},
    {"time": "01/06/2023 00:00", "WF_SIG/status": "replaced"},
])

signals, derived_signals = result.to_legacy_data()
print(signals["WF_SIG"]["status"])
# [{'time': '01/01/2023 00:00', 'status': 'ok'},
#  {'time': '01/06/2023 00:00', 'status': 'replaced'}]
```

## YAML Spec Format

```yaml
farm_name: "My Farm"
time_field: "time"
default_initial_time: "01/01/1972 00:00"

signal_key_parser:
  kind: delimited
  signal_prefixes:
    - "NRT"
    - "X/"
    - "Y/"
    - "Z/"
  separator: "/"

derived_signal_strategies:
  "acceleration/yaw_transformation":
    kind: level_based
    suffixes: ["_X", "_Y"]
    parent_signals_builder: acceleration_parent_signals
    calibration_fields_builder: yaw_calibration_fields

config_discovery:
  kind: json_stem
  suffix: ".json"

postprocessors:
  - backfill_status
```

See the [Signal Data Model](../explanation/signal-data-model.md) explanation
for details on how events map to the backend entity hierarchy.

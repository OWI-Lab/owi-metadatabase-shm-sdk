# OWI Metadatabase SHM Extension

SHM (Structural Health Monitoring) extension for the OWI Metadatabase SDK.

[![version](https://img.shields.io/pypi/v/owi-metadatabase-shm)](https://pypi.org/project/owi-metadatabase-shm/)
[![python versions](https://img.shields.io/pypi/pyversions/owi-metadatabase-shm)](https://pypi.org/project/owi-metadatabase-shm/)
[![license](https://img.shields.io/github/license/owi-lab/owi-metadatabase-shm-sdk)](https://github.com/OWI-Lab/owi-metadatabase-shm-sdk/blob/main/LICENSE)
[![pytest](https://img.shields.io/github/actions/workflow/status/owi-lab/owi-metadatabase-shm-sdk/ci.yml?label=pytest)](https://github.com/OWI-Lab/owi-metadatabase-shm-sdk/actions/workflows/ci.yml)
[![lint](https://img.shields.io/github/actions/workflow/status/owi-lab/owi-metadatabase-shm-sdk/ci.yml?label=lint)](https://github.com/OWI-Lab/owi-metadatabase-shm-sdk/actions/workflows/ci.yml)
[![issues](https://img.shields.io/github/issues/owi-lab/owi-metadatabase-shm-sdk)](https://github.com/OWI-Lab/owi-metadatabase-shm-sdk/issues)
[![Documentation](https://img.shields.io/badge/docs-zensical-blue)](https://owi-lab.github.io/owi-metadatabase-shm-sdk/)

This package extends
[`owi-metadatabase`](https://pypi.org/project/owi-metadatabase/) under the
`owi.metadatabase.*` namespace with a typed SHM layer for sensors, signals,
history, and calibration records.

The package is structured in the same style as the results SDK: low-level HTTP
transport stays in `ShmAPI`, while typed models, serializers, a registry, and
domain services sit above it. Upload workflows use the same typed surface and
stable helper modules instead of the removed legacy package.

📚 **[Read the Documentation](https://owi-lab.github.io/owi-metadatabase-shm-sdk/)**

## What the SDK Covers

- Query and create `SensorType`, `Sensor`, and `SensorCalibration` records.
- Query and create `Signal`, `DerivedSignal`, `SignalHistory`,
    `DerivedSignalHistory`, `SignalCalibration`, and
    `DerivedSignalCalibration` records.
- Process raw configuration files into upload-ready signal mappings.
- Upload sensors and signals through reusable orchestrators that can run
    against either the live backend or test doubles.

## Package Shape

The public surface is organized around a few clear layers:

- `ShmAPI`: low-level transport and endpoint operations.
- `models`, `serializers`, `registry`, `services`: typed entity layer for SHM
    records and repository-backed workflows.
- `processing`: signal configuration parsing and transformation.
- `upload`: sensor and signal upload orchestration.
- `json_utils`, `signal_ids`, `upload_context`, `upload.payloads`: stable
    helper modules used by processing and upload workflows.


## Installation

```bash
uv add owi-metadatabase-shm
```

Or as a core-package extra:

```bash
uv add "owi-metadatabase[shm]"
```

For local development:

```bash
uv sync --all-packages --all-extras --all-groups
```

## Quick Start

### Query the SHM backend

```python
from owi.metadatabase.shm import ShmAPI

api = ShmAPI(
    api_root="https://owimetadatabase.azurewebsites.net/api/v1",
    token="your-api-token",
)
print(api.ping())
```

### Work with the typed services

```python
from owi.metadatabase.shm import ApiShmRepository, SensorService, ShmAPI

api = ShmAPI(
    api_root="https://owimetadatabase.azurewebsites.net/api/v1",
    token="your-api-token",
)
repository = ApiShmRepository(api)
sensor_service = SensorService(repository=repository)

sensor_type = sensor_service.get_sensor_type(name="393B04")
print(sensor_type)
```

### Upload sensors

```python
from owi.metadatabase.shm import ShmAPI, ShmSensorUploader

api = ShmAPI(token="your-api-token")
uploader = ShmSensorUploader(shm_api=api)

# Upload sensor types, sensors, and calibrations
uploader.upload_sensor_types(sensor_types_data, permission_group_ids=[1])
uploader.upload_sensors("accelerometers", {"name": "393B04"}, sensors_data, [1])
```

### Process and upload signals

```python
from owi.metadatabase.shm import (
    DefaultSignalConfigProcessor,
    ShmAPI,
    ShmSignalUploader,
)

processor = DefaultSignalConfigProcessor(path_configs="data/signal_configs/")
processor.signals_process_data()

uploader = ShmSignalUploader.from_clients(shm_api=api, locations_client=..., geometry_client=...)
results = uploader.upload_from_processor(projectsite="MyFarm", processor=processor)
```

## Notebook Suite

The repository ships with two executable notebooks under `notebooks/`:

- `scripts/1.0.upload-sensors.ipynb`
- `scripts/2.0.upload-signals.ipynb`

They are designed to run top-to-bottom with bundled Norther example data and
exercise the public SDK surface without requiring a live backend.

Execute them with:

```bash
cd scripts
uv run jupyter nbconvert --to notebook --execute 1.0.upload-sensors.ipynb
uv run jupyter nbconvert --to notebook --execute 2.0.upload-signals.ipynb
```

## Documentation

Full documentation is available at
[owi-lab.github.io/owi-metadatabase-shm-sdk](https://owi-lab.github.io/owi-metadatabase-shm-sdk/).

## Development

```bash
uv sync --all-packages --all-extras --all-groups
uv run invoke qa
uv run invoke test
uv run invoke docs.build
cd scripts
uv run jupyter nbconvert --to notebook --execute 1.0.upload-sensors.ipynb
uv run jupyter nbconvert --to notebook --execute 2.0.upload-signals.ipynb
```

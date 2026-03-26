# Get Signal Data

This guide shows how to retrieve signal-domain data from the SHM extension,
including main signals, signal history, calibrations, and derived signals.

## Prerequisites

- The SDK installed (`pip install owi-metadatabase-shm`)
- A valid API token (see [Authenticate](authenticate.md))
- The project site and asset location already exist in the backend

## Query signals with the raw API client

Use `ShmAPI` when you want backend rows as a `DataFrame`.

```python
from owi.metadatabase.shm import ShmAPI

api = ShmAPI(
    api_root="https://owimetadatabase-dev.azurewebsites.net/api/v1",
    token="your-api-token",
)

signals = api.list_signals(asset_location=10)
derived_signals = api.list_derived_signals(asset_location=10)
signal_history = api.list_signal_history(signal_id=1)
signal_calibrations = api.list_signal_calibrations(signal_id=1)

print(signals["data"].columns)
print(derived_signals["data"].head())
```

For a single main signal, use the backend `signal_id` string directly:

```python
signal = api.get_signal("SG-01")
print(signal["id"])
print(signal["data"])
```

For other single-resource endpoints, pass backend filters as keyword arguments:

```python
history_row = api.get_signal_history(signal_id=1)
calibration_row = api.get_signal_calibration(signal_id=1)
derived_signal = api.get_derived_signal(derived_signal_id="DS-01")
```

## Query typed signal records with services

Use `SignalService` when you want validated models instead of raw rows.

```python
from owi.metadatabase.shm import (
    ApiShmRepository,
    ShmAPI,
    ShmEntityName,
    ShmEntityService,
    ShmQuery,
    SignalService,
)

api = ShmAPI(
    api_root="https://owimetadatabase-dev.azurewebsites.net/api/v1",
    token="your-api-token",
)

repository = ApiShmRepository(api)
entity_service = ShmEntityService(repository=repository)
signal_service = SignalService(entity_service=entity_service)

signal_query = ShmQuery(
    entity=ShmEntityName.SIGNAL,
    backend_filters={"signal_id": "SG-01"},
)

signal = signal_service.get_signal(signal_query)
signal_rows = signal_service.list_signals({"asset_location": 10})
derived_rows = signal_service.list_derived_signals({"asset_location": 10})
```

`ShmQuery` is useful when you want to keep the target entity explicit and pass
validated backend filters through one object.

## Retrieve history and calibration models

```python
history_rows = signal_service.list_signal_history({"signal_id": 1})
calibration_rows = signal_service.list_signal_calibrations({"signal_id": 1})
derived_history_rows = signal_service.list_derived_signal_history({"derived_signal_id": 7})
derived_calibration_rows = signal_service.list_derived_signal_calibrations({"derived_signal_id": 7})
```

These methods return typed models such as:

- `SignalRecord`
- `SignalHistoryRecord`
- `SignalCalibrationRecord`
- `DerivedSignalRecord`
- `DerivedSignalHistoryRecord`
- `DerivedSignalCalibrationRecord`

## Related pages

- [Get Sensor Data](get-sensor-data.md)
- [Reference: Typed Models](../reference/api/models.md)
- [Reference: Services](../reference/api/services.md)

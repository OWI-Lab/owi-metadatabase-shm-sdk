# Retrieve SHM Data

!!! example
    This tutorial walks you through the two main read paths in the SHM SDK:
    raw backend queries through `ShmAPI`, and typed record retrieval through
    the repository and service layer.

## Prerequisites

- Python 3.9+
- The SDK installed (`pip install owi-metadatabase-shm`)
- A valid API token (see [How to Authenticate](../how-to/authenticate.md))

## Step 1 — Create an API client

```python
from owi.metadatabase.shm import ShmAPI

api = ShmAPI(
    api_root="https://owimetadatabase-dev.azurewebsites.net/api/v1",
    token="your-api-token",
)
```

Start by checking connectivity:

```python
print(api.ping())  # "ok"
```

## Step 2 — Read raw sensor data

Use the low-level transport when you want backend rows as a `DataFrame`.

```python
sensor_types = api.list_sensor_types()
signals = api.list_signals(asset_location=10)

print(sensor_types["exists"])
print(sensor_types["data"].head())
print(signals["data"].head())
```

At this layer, every call returns a dictionary containing `data` and `exists`.

## Step 3 — Build the typed service stack

Wrap the API client when you want validated SHM models.

```python
from owi.metadatabase.shm import ApiShmRepository, SensorService, ShmEntityService, SignalService

repository = ApiShmRepository(api)
entity_service = ShmEntityService(repository=repository)
sensor_service = SensorService(entity_service=entity_service)
signal_service = SignalService(entity_service=entity_service)
```

## Step 4 — Retrieve typed sensor records

```python
sensor_type = sensor_service.get_sensor_type({"name": "393B04"})
sensors = sensor_service.list_sensors({"sensor_type_id": 3})

print(sensor_type)
print(sensors[0] if sensors else None)
```

The service layer returns validated models such as `SensorTypeRecord` and
`SensorRecord`.

## Step 5 — Retrieve one signal with `ShmQuery`

Use `ShmQuery` when you want to make the backend filters explicit.

```python
from owi.metadatabase.shm import ShmEntityName, ShmQuery

query = ShmQuery(
    entity=ShmEntityName.SIGNAL,
    backend_filters={"signal_id": "SG-01"},
)

signal = signal_service.get_signal(query)
print(signal)
```

For history and calibration rows, filter by backend numeric ids:

```python
history_rows = signal_service.list_signal_history({"signal_id": 1})
calibration_rows = signal_service.list_signal_calibrations({"signal_id": 1})

print(history_rows[:1])
print(calibration_rows[:1])
```

## What You Learned

- How to create an SHM API client for read operations.
- When to use the raw `ShmAPI` transport versus typed services.
- How to query sensors, signals, history, and calibrations.
- How `ShmQuery` packages backend filters for typed retrieval.

## Next Steps

- [How-to: Get Sensor Data](../how-to/get-sensor-data.md)
- [How-to: Get Signal Data](../how-to/get-signal-data.md)
- [Reference: Services](../reference/api/services.md)

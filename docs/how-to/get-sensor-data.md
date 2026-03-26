# Get Sensor Data

This guide shows how to retrieve sensor-domain data from the SHM extension.
Use it when you need to inspect sensor types, sensors, or calibrations without
going through the upload workflows.

## Prerequisites

- The SDK installed (`pip install owi-metadatabase-shm`)
- A valid API token (see [Authenticate](authenticate.md))
- An SHM-enabled API root

## Option 1: Query the raw API transport

Use `ShmAPI` when you want the backend response as a Pandas `DataFrame`.

```python
from owi.metadatabase.shm import ShmAPI

api = ShmAPI(
    api_root="https://owimetadatabase-dev.azurewebsites.net/api/v1",
    token="your-api-token",
)

sensor_type_result = api.list_sensor_types()
sensor_result = api.list_sensors(sensor_type_id=1)
calibration_result = api.list_sensor_calibrations(sensor_id=4)

print(sensor_type_result["exists"])
print(sensor_type_result["data"].head())
```

Each list method returns a dictionary with:

- `data`: a Pandas `DataFrame`
- `exists`: whether any rows were returned
- `response`: the raw backend response when available

## Option 2: Retrieve typed records with services

Use the repository and service layer when you want typed records instead of raw
rows.

```python
from owi.metadatabase.shm import ApiShmRepository, SensorService, ShmAPI, ShmEntityService

api = ShmAPI(
    api_root="https://owimetadatabase-dev.azurewebsites.net/api/v1",
    token="your-api-token",
)

repository = ApiShmRepository(api)
entity_service = ShmEntityService(repository=repository)
sensor_service = SensorService(entity_service=entity_service)

sensor_types = sensor_service.list_sensor_types({"name": "393B04"})
sensor_type = sensor_service.get_sensor_type({"name": "393B04"})
sensor = sensor_service.get_sensor({"serial_number": "SG-01", "sensor_type_id": 3})
```

The returned objects are validated SHM models such as `SensorTypeRecord` and
`SensorRecord`.

## Retrieve one calibration row

```python
calibration = sensor_service.get_sensor_calibration({"sensor_id": 4})

if calibration is not None:
    print(calibration.calibration_date)
    print(calibration.file)
```

## When to use each layer

- Use `ShmAPI` when you want raw `DataFrame` access or you are debugging the
  backend response.
- Use `SensorService` when you want validated models in application code.
- Use `ApiShmRepository` and `ShmEntityService` when you need a generic typed
  path across multiple SHM entities.

## Related pages

- [Get Signal Data](get-signal-data.md)
- [Reference: SHM API Transport](../reference/api/io.md)
- [Reference: Services](../reference/api/services.md)

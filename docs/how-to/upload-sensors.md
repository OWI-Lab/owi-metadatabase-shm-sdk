# Upload Sensors

This guide shows how to upload sensor records (physical devices) to the SHM
backend, grouped by sensor category and turbine.

## Prerequisites

- Sensor types already uploaded (see [Upload Sensor Types](upload-sensor-types.md))
- Per-turbine sensor data with serial numbers and cabinets

## Steps

### 1. Set up the uploader

```python
from owi.metadatabase.shm import ShmAPI, ShmSensorUploader

api = ShmAPI(
    api_root="https://owimetadatabase.azurewebsites.net/api/v1",
    token="your-api-token",
)

uploader = ShmSensorUploader(shm_api=api)
```

### 2. Prepare per-turbine sensor data

The data is a dict keyed by turbine identifier, with each turbine containing
sensor categories:

```python
sensors_data = {
    "WTG01": {
        "accelerometers": {
            "serial_numbers": ["SN001", "SN002"],
            "cabinets": ["CAB-A", "CAB-A"],
        }
    },
    "WTG02": {
        "accelerometers": {
            "serial_numbers": ["SN003"],
            "cabinets": ["CAB-B"],
        }
    },
}
```

### 3. Upload one sensor category

```python
results = uploader.upload_sensors(
    sensor_type_name="accelerometers",
    sensor_type_params={"name": "393B04"},
    sensors_data=sensors_data,
    permission_group_ids=[1, 2],
)
```

The uploader resolves the sensor type ID from `sensor_type_params`, collects
all serial numbers and cabinets across turbines, and creates one sensor
record per pair.

### 4. Filter by turbine (optional)

```python
results = uploader.upload_sensors(
    sensor_type_name="accelerometers",
    sensor_type_params={"name": "393B04"},
    sensors_data=sensors_data,
    permission_group_ids=[1, 2],
    turbines=["WTG01"],
)
```

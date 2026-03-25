# Upload Sensor Types

This guide shows how to upload sensor types to the SHM backend, optionally
attaching product images.

## Prerequisites

- A running API connection via `ShmAPI`
- Sensor type data as a list of dicts (typically loaded from JSON)

## Steps

### 1. Prepare the API client

```python
from owi.metadatabase.shm import ShmAPI, ShmSensorUploader

api = ShmAPI(
    api_root="https://owimetadatabase.azurewebsites.net/api/v1",
    token="your-api-token",
)

uploader = ShmSensorUploader(shm_api=api)
```

### 2. Load sensor type data

```python
from owi.metadatabase.shm import load_json_data

sensor_types = load_json_data("data/sensors/sensor_types.json")
```

The JSON file should contain a list of objects with `name`, `manufacturer`,
and optionally `photo` (filename relative to the images directory):

```json
[
    {
        "name": "393B04",
        "manufacturer": "PCB Piezotronics",
        "photo": "393B04.jpg"
    }
]
```

### 3. Upload

```python
results = uploader.upload_sensor_types(
    sensor_types_data=sensor_types,
    permission_group_ids=[1, 2],
    path_to_images="data/sensors/img/",
)
```

Each result dict contains the backend response including the created `id`.

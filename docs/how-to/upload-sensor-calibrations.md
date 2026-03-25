# Upload Sensor Calibrations

This guide shows how to upload sensor calibration records with optional PDF
datasheet attachments.

## Prerequisites

- Sensors already uploaded (see [Upload Sensors](upload-sensors.md))
- A signal-sensor map linking signal names to sensor lookup parameters
- A signal-calibration map with dates and filenames
- A directory of calibration PDF files

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

### 2. Prepare the mapping data

**Signal-sensor map** — maps each signal to its sensor lookup parameters:

```python
signal_sensor_map = {
    "WTG01": {
        "NRT_WTG_TP_ACC_AX": {
            "sensor_type_id": {"name": "393B04"},
            "serial_number": "SN001",
        }
    }
}
```

**Signal-calibration map** — maps each signal to calibration metadata:

```python
signal_calibration_map = {
    "WTG01": {
        "NRT_WTG_TP_ACC_AX": {
            "date": "2023-01-15",
            "filename": "SN001_calibration.pdf",
        }
    }
}
```

### 3. Upload

```python
results = uploader.upload_sensor_calibrations(
    signal_sensor_map_data=signal_sensor_map,
    signal_calibration_map_data=signal_calibration_map,
    path_to_datasheets="data/sensors/datasheets/",
)
```

The uploader resolves sensor IDs from the signal-sensor map (including nested
sensor type lookups), then creates a calibration for each signal with the
matching PDF attached when found on disk.

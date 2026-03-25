import math

from owi.metadatabase.shm.models import SensorTypeRecord, ShmEntityName
from owi.metadatabase.shm.serializers import DEFAULT_SERIALIZERS


def test_signal_serializer_parses_json_and_nan_values() -> None:
    serializer = DEFAULT_SERIALIZERS[ShmEntityName.SIGNAL]

    record = serializer.from_mapping(
        {
            "id": 4,
            "signal_id": "SG-01",
            "signal_type": "strain",
            "data_additional": '{"sheet": "signals.xlsx"}',
            "heading": math.nan,
        }
    )

    assert record.id == 4
    assert record.data_additional == {"sheet": "signals.xlsx"}
    assert record.heading is None


def test_signal_calibration_serializer_serializes_models_to_json_ready_payload() -> None:
    serializer = DEFAULT_SERIALIZERS[ShmEntityName.SIGNAL_CALIBRATION]

    payload = serializer.to_payload(
        {
            "signal_id": 9,
            "calibration_date": "2024-01-01T00:00:00",
            "data": {"offset": 1.25},
        }
    )

    assert payload["signal_id"] == 9
    assert payload["data"] == {"offset": 1.25}


def test_sensor_type_serializer_serializes_pydantic_models() -> None:
    serializer = DEFAULT_SERIALIZERS[ShmEntityName.SENSOR_TYPE]
    record = SensorTypeRecord(id=3, name="393B04", type="ACC")

    payload = serializer.to_payload(record)

    assert payload == {"id": 3, "name": "393B04", "type": "ACC"}

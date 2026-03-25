from owi.metadatabase.shm.models import SensorTypeRecord, ShmEntityName, ShmQuery, SignalRecord


def test_shm_query_roundtrips_backend_filters() -> None:
    query = ShmQuery(entity=ShmEntityName.SIGNAL, backend_filters={"signal_id": "SG-01"})

    assert query.to_backend_filters() == {"signal_id": "SG-01"}


def test_signal_record_ignores_unknown_backend_fields() -> None:
    record = SignalRecord.model_validate(
        {
            "id": 7,
            "signal_id": "SG-01",
            "signal_type": "acceleration",
            "backend_only": "ignored",
        }
    )

    assert record.id == 7
    assert record.signal_id == "SG-01"


def test_sensor_type_record_preserves_visibility_groups() -> None:
    record = SensorTypeRecord.model_validate({"id": 2, "name": "393B04", "visibility_groups": [1, 4]})

    assert record.visibility_groups == [1, 4]

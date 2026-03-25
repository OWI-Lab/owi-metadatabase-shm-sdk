from collections.abc import Mapping
from typing import Any

import pandas as pd

from owi.metadatabase.shm.models import SensorTypeRecord, ShmEntityName
from owi.metadatabase.shm.services import SensorService, ShmEntityService


class StubRepository:
    def __init__(self) -> None:
        self.last_create: tuple[ShmEntityName | str, Mapping[str, Any], Mapping[str, Any] | None] | None = None

    def list_records(self, entity_name: ShmEntityName | str, **filters: Any) -> pd.DataFrame:
        assert entity_name == ShmEntityName.SENSOR_TYPE
        assert filters == {"name": "393B04"}
        return pd.DataFrame([{"id": 2, "name": "393B04", "type": "ACC"}])

    def get_record(self, entity_name: ShmEntityName | str, **filters: Any) -> Mapping[str, Any]:
        assert entity_name == ShmEntityName.SENSOR_TYPE
        assert filters == {"name": "393B04"}
        return {
            "exists": True,
            "data": pd.DataFrame([{"id": 2, "name": "393B04", "type": "ACC"}]),
        }

    def create_record(
        self,
        entity_name: ShmEntityName | str,
        payload: Mapping[str, Any],
        files: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        self.last_create = (entity_name, payload, files)
        return {
            "exists": True,
            "data": pd.DataFrame([{"id": 5, **payload}]),
        }


def test_entity_service_list_records_deserializes_rows() -> None:
    service = ShmEntityService(repository=StubRepository())

    records = service.list_records(ShmEntityName.SENSOR_TYPE, {"name": "393B04"})
    first_record = records[0]

    assert len(records) == 1
    assert isinstance(first_record, SensorTypeRecord)
    assert first_record.id == 2
    assert first_record.name == "393B04"


def test_sensor_service_create_sensor_type_serializes_and_deserializes() -> None:
    repository = StubRepository()
    service = SensorService(entity_service=ShmEntityService(repository=repository))

    record = service.create_sensor_type({"name": "393B04", "type": "ACC"})

    assert repository.last_create == (
        ShmEntityName.SENSOR_TYPE,
        {"name": "393B04", "type": "ACC"},
        None,
    )
    assert record is not None
    assert record.id == 5
    assert record.type == "ACC"

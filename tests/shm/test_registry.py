import pytest

from owi.metadatabase.shm.models import ShmEntityName
from owi.metadatabase.shm.registry import default_registry


def test_default_registry_contains_all_required_entities() -> None:
    assert default_registry.names() == [
        "derived_signal",
        "derived_signal_calibration",
        "derived_signal_history",
        "sensor",
        "sensor_calibration",
        "sensor_type",
        "signal",
        "signal_calibration",
        "signal_history",
    ]


def test_default_registry_returns_expected_definition() -> None:
    definition = default_registry.get(ShmEntityName.SIGNAL)

    assert definition.name is ShmEntityName.SIGNAL
    assert definition.endpoint == "signal"


def test_default_registry_raises_for_unknown_entity() -> None:
    with pytest.raises(ValueError):
        default_registry.get("not-real")

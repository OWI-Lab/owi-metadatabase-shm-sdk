"""Dry-run upload transport clients.

The classes in this module are protocol-compatible stand-ins for the live
``ShmAPI`` mutation surface used by the upload orchestrators. They are intended
to record lookup, create, and patch operations without calling a backend.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

DryRunAction = Literal["lookup", "create", "patch"]


@dataclass(frozen=True)
class DryRunOperation:
    """One backend-facing operation captured by a dry-run upload client.

    Parameters
    ----------
    action
        Kind of operation the uploader requested.
    resource
        SHM resource name, such as ``"signal"`` or ``"sensor_type"``.
    payload
        Mutation payload for create or patch operations.
    filters
        Lookup filters for get-style operations.
    object_id
        Detail id for patch-style operations.
    """

    action: DryRunAction
    resource: str
    payload: Mapping[str, Any] | None = None
    filters: Mapping[str, Any] | None = None
    object_id: int | None = None


class DryRunUploadClient:
    """Base operation-recorder surface for dry-run upload clients.

    This base class defines the public recording surface. Concrete recording
    behavior is shared by the sensor and signal dry-run transports.
    """

    def __init__(self, *, starting_id: int = 1) -> None:
        self.starting_id = starting_id
        self._next_id = starting_id
        self._operations: list[DryRunOperation] = []

    @property
    def operations(self) -> tuple[DryRunOperation, ...]:
        """Recorded operations in uploader execution order."""
        return tuple(self._operations)

    def summary(self) -> Mapping[str, int]:
        """Return operation counts grouped by resource."""
        return dict(Counter(operation.resource for operation in self._operations))

    def _record(
        self,
        action: DryRunAction,
        resource: str,
        *,
        payload: Mapping[str, Any] | None = None,
        filters: Mapping[str, Any] | None = None,
        object_id: int | None = None,
    ) -> None:
        self._operations.append(
            DryRunOperation(
                action=action,
                resource=resource,
                payload=dict(payload) if payload is not None else None,
                filters=dict(filters) if filters is not None else None,
                object_id=object_id,
            )
        )

    def _lookup(
        self,
        resource: str,
        rows: Sequence[Mapping[str, Any]],
        filters: Mapping[str, Any],
    ) -> dict[str, Any]:
        lookup_filters = dict(filters)
        self._record("lookup", resource, filters=lookup_filters)
        row = next((dict(candidate) for candidate in rows if self._matches(candidate, lookup_filters)), None)
        return self._result(row)

    def _create(self, resource: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        request_payload = dict(payload)
        self._record("create", resource, payload=request_payload)
        row = {**request_payload, "id": self._next_record_id()}
        return row, self._result(row)

    def _patch(self, resource: str, object_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        request_payload = dict(payload)
        self._record("patch", resource, payload=request_payload, object_id=object_id)
        return self._result({"id": object_id, **request_payload})

    def _next_record_id(self) -> int:
        record_id = self._next_id
        self._next_id += 1
        return record_id

    @staticmethod
    def _matches(row: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
        return all(row.get(key) == value for key, value in filters.items())

    @staticmethod
    def _result(row: Mapping[str, Any] | None) -> dict[str, Any]:
        if row is None:
            return {"data": [], "exists": False, "id": None, "response": None}
        response = dict(row)
        return {"data": [response], "exists": True, "id": response.get("id"), "response": response}

    def _not_implemented(self, method_name: str) -> None:
        raise NotImplementedError(
            f"{self.__class__.__name__}.{method_name} recording behavior is not implemented yet."
        )


class DryRunSensorUploadClient(DryRunUploadClient):
    """Dry-run transport for :class:`ShmSensorUploader`.

    Parameters
    ----------
    starting_id
        First synthetic id to assign during dry-run creation.
    sensor_types
        Seed rows used by ``get_sensor_type`` lookups.
    sensors
        Seed rows used by ``get_sensor`` lookups.
    """

    def __init__(
        self,
        *,
        starting_id: int = 1,
        sensor_types: Sequence[Mapping[str, Any]] = (),
        sensors: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        super().__init__(starting_id=starting_id)
        self.sensor_types = tuple(dict(row) for row in sensor_types)
        self.sensors = tuple(dict(row) for row in sensors)
        self._created_sensor_types: list[dict[str, Any]] = []
        self._created_sensors: list[dict[str, Any]] = []

    def get_sensor_type(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one seeded sensor type row during dry-run upload."""
        return self._lookup("sensor_type", [*self.sensor_types, *self._created_sensor_types], kwargs)

    def get_sensor(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one seeded or created sensor row during dry-run upload."""
        return self._lookup("sensor", [*self.sensors, *self._created_sensors], kwargs)

    def create_sensor_type(self, payload: Mapping[str, Any], files: Any = None) -> dict[str, Any]:
        """Record a sensor type create operation."""
        row, result = self._create("sensor_type", payload)
        self._created_sensor_types.append(row)
        return result

    def create_sensor(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a sensor create operation."""
        row, result = self._create("sensor", payload)
        self._created_sensors.append(row)
        return result

    def create_sensor_calibration(self, payload: Mapping[str, Any], files: Any = None) -> dict[str, Any]:
        """Record a sensor calibration create operation."""
        _, result = self._create("sensor_calibration", payload)
        return result


class DryRunSignalUploadClient(DryRunUploadClient):
    """Dry-run transport for :class:`ShmSignalUploader`.

    Parameters
    ----------
    starting_id
        First synthetic id to assign during dry-run creation.
    sensor_types
        Seed rows used by temperature-compensation and sensor lookups.
    sensors
        Seed rows used by signal-history sensor lookups.
    signals
        Seed rows used by existing signal lookups.
    """

    def __init__(
        self,
        *,
        starting_id: int = 1,
        sensor_types: Sequence[Mapping[str, Any]] = (),
        sensors: Sequence[Mapping[str, Any]] = (),
        signals: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        super().__init__(starting_id=starting_id)
        self.sensor_types = tuple(dict(row) for row in sensor_types)
        self.sensors = tuple(dict(row) for row in sensors)
        self.signals = tuple(dict(row) for row in signals)

    def get_sensor_type(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one seeded sensor type row during dry-run upload."""
        self._not_implemented("get_sensor_type")

    def get_sensor(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve one seeded sensor row during dry-run upload."""
        self._not_implemented("get_sensor")

    def get_signal(self, signal_id: str, **kwargs: Any) -> dict[str, Any]:
        """Resolve one seeded or created signal row during dry-run upload."""
        self._not_implemented("get_signal")

    def create_signal(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a signal create operation."""
        self._not_implemented("create_signal")

    def create_signal_history(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a signal history create operation."""
        self._not_implemented("create_signal_history")

    def create_signal_calibration(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a signal calibration create operation."""
        self._not_implemented("create_signal_calibration")

    def create_derived_signal(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a derived signal create operation."""
        self._not_implemented("create_derived_signal")

    def create_derived_signal_history(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a derived signal history create operation."""
        self._not_implemented("create_derived_signal_history")

    def patch_derived_signal_history(self, history_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a derived signal history patch operation."""
        self._not_implemented("patch_derived_signal_history")

    def create_derived_signal_calibration(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Record a derived signal calibration create operation."""
        self._not_implemented("create_derived_signal_calibration")


__all__ = [
    "DryRunAction",
    "DryRunOperation",
    "DryRunSensorUploadClient",
    "DryRunSignalUploadClient",
    "DryRunUploadClient",
]

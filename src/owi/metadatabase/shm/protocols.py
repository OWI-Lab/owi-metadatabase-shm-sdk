"""Protocols for the SHM extension."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from .models import ShmEntityName, ShmQuery, ShmResourceRecord


@runtime_checkable
class SerializerProtocol(Protocol):
    """Protocol for resource serializers."""

    def to_payload(self, obj: Any) -> dict[str, Any]:
        """Serialize a validated domain object or mapping."""

    def from_mapping(self, mapping: Mapping[str, Any]) -> Any:
        """Deserialize a backend row into a typed domain object."""


@runtime_checkable
class EntityRegistryProtocol(Protocol):
    """Protocol for SHM entity registration and resolution."""

    def get(self, entity_name: ShmEntityName | str) -> Any:
        """Return the configured entity definition."""

    def names(self) -> list[str]:
        """Return the registered entity names."""


@runtime_checkable
class ShmRepositoryProtocol(Protocol):
    """Protocol for SHM persistence operations."""

    def list_records(self, entity_name: ShmEntityName | str, **filters: Any) -> pd.DataFrame:
        """Return backend rows for a collection query."""

    def get_record(self, entity_name: ShmEntityName | str, **filters: Any) -> Mapping[str, Any]:
        """Return a backend response for a single-resource query."""

    def create_record(
        self,
        entity_name: ShmEntityName | str,
        payload: Mapping[str, Any],
        files: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Create a resource and return the raw backend response."""


@runtime_checkable
class ShmEntityServiceProtocol(Protocol):
    """Protocol for high-level typed SHM resource services."""

    def list_records(
        self,
        entity_name: ShmEntityName | str,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> list[ShmResourceRecord]:
        """Return typed resources for the requested entity."""

    def get_record(
        self,
        entity_name: ShmEntityName | str,
        filters: ShmQuery | Mapping[str, Any] | None = None,
    ) -> ShmResourceRecord | None:
        """Return a single typed resource if one exists."""

    def create_record(
        self,
        entity_name: ShmEntityName | str,
        payload: Mapping[str, Any] | ShmResourceRecord,
        files: Mapping[str, Any] | None = None,
    ) -> ShmResourceRecord | None:
        """Create a typed resource from a payload or model instance."""

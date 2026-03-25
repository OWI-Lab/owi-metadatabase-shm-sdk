"""Shared context models for SHM upload workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignalUploadContext:
    """Resolved ids shared by signal upload payload builders."""

    site_id: int
    asset_location_id: int
    model_definition_id: int | str
    permission_group_ids: Sequence[int] | None
    subassembly_ids_by_type: Mapping[str, int]

    def subassembly_id_for(self, subassembly_type: str) -> int | None:
        """Return the configured subassembly id for a subassembly token."""
        return self.subassembly_ids_by_type.get(subassembly_type)

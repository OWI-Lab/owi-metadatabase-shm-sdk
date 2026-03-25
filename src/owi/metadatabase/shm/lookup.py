"""Parent-SDK lookup services for SHM workflows.

This module centralizes the parent SDK lookups required by SHM upload and
orchestration flows while keeping transport concerns outside the workflows
themselves.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd
from owi.metadatabase._utils.exceptions import APIException  # ty: ignore[unresolved-import]

from .upload_context import SignalUploadContext


class ParentLocationsLookupClient(Protocol):
    """Protocol for parent SDK location lookups used by SHM services."""

    def get_projectsite_detail(self, projectsite: str, **kwargs: Any) -> dict[str, Any]:
        """Return a single project site lookup response."""

    def get_assetlocation_detail(
        self,
        assetlocation: str,
        projectsite: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Return a single asset location lookup response."""


class ParentGeometryLookupClient(Protocol):
    """Protocol for parent SDK geometry lookups used by SHM services."""

    def get_subassemblies(
        self,
        projectsite: str | None = None,
        assetlocation: str | None = None,
        subassembly_type: str | None = None,
        model_definition: str | None = None,
    ) -> dict[str, Any]:
        """Return a subassembly lookup response."""


@dataclass(frozen=True)
class LookupRecord:
    """Normalized lookup record returned by SHM services."""

    data: pd.DataFrame
    record_id: int | None = None


@dataclass(frozen=True)
class AssetLookupContext:
    """Resolved lookup context for an SHM asset workflow."""

    site: LookupRecord
    asset: LookupRecord
    subassemblies: LookupRecord
    model_definition: int | str


class ShmLookupError(APIException):
    """Base exception for SHM lookup service failures."""


class ProjectSiteLookupError(ShmLookupError):
    """Raised when a project site lookup cannot be resolved."""


class AssetLocationLookupError(ShmLookupError):
    """Raised when an asset location lookup cannot be resolved."""


class SubassembliesLookupError(ShmLookupError):
    """Raised when a subassembly lookup cannot be resolved."""


class ModelDefinitionLookupError(ShmLookupError):
    """Raised when a SHM model definition cannot be derived from subassemblies."""


class SignalUploadContextError(ShmLookupError):
    """Raised when parent lookup data cannot be translated into upload ids."""


class ParentSDKLookupService:
    """Resolve parent-SDK lookup data for SHM workflows.

    Parameters
    ----------
    locations_client
        Parent SDK client that resolves project and asset location details.
    geometry_client
        Parent SDK client that resolves geometry subassemblies.
    """

    def __init__(
        self,
        locations_client: ParentLocationsLookupClient,
        geometry_client: ParentGeometryLookupClient,
    ) -> None:
        self.locations_client = locations_client
        self.geometry_client = geometry_client

    def get_projectsite(self, projectsite: str, **kwargs: Any) -> LookupRecord:
        """Resolve a project site detail lookup."""
        result = self.locations_client.get_projectsite_detail(projectsite=projectsite, **kwargs)
        return self._build_record(
            result=result,
            label=f"project site '{projectsite}'",
            error_type=ProjectSiteLookupError,
        )

    def get_assetlocation(
        self,
        assetlocation: str,
        projectsite: str | None = None,
        **kwargs: Any,
    ) -> LookupRecord:
        """Resolve an asset location detail lookup."""
        result = self.locations_client.get_assetlocation_detail(
            assetlocation=assetlocation,
            projectsite=projectsite,
            **kwargs,
        )
        label = f"asset location '{assetlocation}'"
        if projectsite is not None:
            label += f" in project site '{projectsite}'"
        return self._build_record(
            result=result,
            label=label,
            error_type=AssetLocationLookupError,
        )

    def get_subassemblies(
        self,
        assetlocation: str,
        projectsite: str | None = None,
        **kwargs: Any,
    ) -> LookupRecord:
        """Resolve a subassembly lookup."""
        result = self.geometry_client.get_subassemblies(
            projectsite=projectsite,
            assetlocation=assetlocation,
            **kwargs,
        )
        label = f"subassemblies for asset location '{assetlocation}'"
        if projectsite is not None:
            label += f" in project site '{projectsite}'"
        return self._build_record(
            result=result,
            label=label,
            error_type=SubassembliesLookupError,
        )

    def get_asset_context(
        self,
        projectsite: str | None,
        assetlocation: str,
    ) -> AssetLookupContext:
        """Resolve the lookup context needed for an SHM asset workflow.

        Parameters
        ----------
        projectsite
            Parent SDK project site title. When omitted, the service
            derives it from the asset-location lookup data.
        assetlocation
            Parent SDK asset location title.

        Returns
        -------
        AssetLookupContext
            Typed lookup records plus the resolved model definition.

        Examples
        --------
        >>> from unittest.mock import Mock
        >>> locations_client = Mock()
        >>> geometry_client = Mock()
        >>> locations_client.get_assetlocation_detail.return_value = {
        ...     "data": pd.DataFrame([{"id": 11, "projectsite_name": "Project A"}]),
        ...     "exists": True,
        ...     "id": 11,
        ... }
        >>> locations_client.get_projectsite_detail.return_value = {
        ...     "data": pd.DataFrame([{"id": 10, "title": "Project A"}]),
        ...     "exists": True,
        ...     "id": 10,
        ... }
        >>> geometry_client.get_subassemblies.return_value = {
        ...     "data": pd.DataFrame([{"id": 40, "subassembly_type": "TP", "model_definition": "MD-01"}]),
        ...     "exists": True,
        ... }
        >>> geometry_client.get_modeldefinition_id.return_value = {"id": 99}
        >>> service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)
        >>> context = service.get_asset_context(projectsite=None, assetlocation="Asset-01")
        >>> (context.site.record_id, context.asset.record_id, context.model_definition)
        (10, 11, 99)
        """
        asset = self.get_assetlocation(assetlocation=assetlocation, projectsite=projectsite)
        resolved_projectsite = projectsite or self._resolve_projectsite_name(asset, assetlocation)
        site = self.get_projectsite(projectsite=resolved_projectsite)
        subassemblies = self.get_subassemblies(assetlocation=assetlocation, projectsite=resolved_projectsite)
        model_definition = self.get_model_definition(
            subassemblies=subassemblies,
            assetlocation=assetlocation,
            projectsite=resolved_projectsite,
        )
        return AssetLookupContext(
            site=site,
            asset=asset,
            subassemblies=subassemblies,
            model_definition=model_definition,
        )

    def get_signal_upload_context(
        self,
        projectsite: str | None,
        assetlocation: str,
        permission_group_ids: Sequence[int] | None = None,
    ) -> SignalUploadContext:
        """Resolve the payload-builder context for SHM signal uploads.

        Parameters
        ----------
        projectsite
            Parent SDK project site title. When omitted, the service
            derives it from the asset-location lookup data.
        assetlocation
            Parent SDK asset location title.
        permission_group_ids
            Visibility groups applied to created SHM records.

        Returns
        -------
        SignalUploadContext
            Upload context compatible with legacy payload builders.

        Examples
        --------
        >>> from unittest.mock import Mock
        >>> locations_client = Mock()
        >>> geometry_client = Mock()
        >>> locations_client.get_projectsite_detail.return_value = {
        ...     "data": pd.DataFrame([{"id": 10, "title": "Project A"}]),
        ...     "exists": True,
        ...     "id": 10,
        ... }
        >>> locations_client.get_assetlocation_detail.return_value = {
        ...     "data": pd.DataFrame([{"id": 11, "title": "Asset-01"}]),
        ...     "exists": True,
        ...     "id": 11,
        ... }
        >>> geometry_client.get_subassemblies.return_value = {
        ...     "data": pd.DataFrame(
        ...         [
        ...             {"id": 40, "subassembly_type": "TP", "model_definition": "MD-01"},
        ...             {"id": 41, "subassembly_type": "TW", "model_definition": "MD-01"},
        ...         ]
        ...     ),
        ...     "exists": True,
        ... }
        >>> service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)
        >>> context = service.get_signal_upload_context("Project A", "Asset-01", permission_group_ids=[7])
        >>> context.site_id, context.asset_location_id, context.subassembly_id_for("TP")
        (10, 11, 40)
        """
        asset_context = self.get_asset_context(
            projectsite=projectsite,
            assetlocation=assetlocation,
        )
        return self.build_signal_upload_context(
            asset_context=asset_context,
            permission_group_ids=permission_group_ids,
        )

    @staticmethod
    def build_signal_upload_context(
        asset_context: AssetLookupContext,
        permission_group_ids: Sequence[int] | None = None,
    ) -> SignalUploadContext:
        """Translate parent lookup records into upload payload ids.

        Parameters
        ----------
        asset_context
            Normalized parent SDK lookup context.
        permission_group_ids
            Visibility groups applied to created SHM records.

        Returns
        -------
        SignalUploadContext
            Upload context compatible with legacy payload builders.

        Raises
        ------
        SignalUploadContextError
            If required parent lookup ids or subassembly columns are missing.

        Examples
        --------
        >>> asset_context = AssetLookupContext(
        ...     site=LookupRecord(pd.DataFrame([{"id": 10}]), record_id=10),
        ...     asset=LookupRecord(pd.DataFrame([{"id": 11}]), record_id=11),
        ...     subassemblies=LookupRecord(
        ...         pd.DataFrame(
        ...             [
        ...                 {"id": 40, "subassembly_type": "TP", "model_definition": "MD-01"},
        ...                 {"id": 41, "subassembly_type": "TW", "model_definition": "MD-01"},
        ...             ]
        ...         )
        ...     ),
        ...     model_definition="MD-01",
        ... )
        >>> upload_context = ParentSDKLookupService.build_signal_upload_context(asset_context, [3, 5])
        >>> upload_context.permission_group_ids
        [3, 5]
        """
        if asset_context.site.record_id is None:
            raise SignalUploadContextError("Project site lookup did not provide a record id.")
        if asset_context.asset.record_id is None:
            raise SignalUploadContextError("Asset location lookup did not provide a record id.")

        return SignalUploadContext(
            site_id=int(asset_context.site.record_id),
            asset_location_id=int(asset_context.asset.record_id),
            model_definition_id=asset_context.model_definition,
            permission_group_ids=(list(permission_group_ids) if permission_group_ids is not None else None),
            subassembly_ids_by_type=ParentSDKLookupService._build_subassembly_ids_by_type(asset_context.subassemblies),
        )

    def get_model_definition(
        self,
        subassemblies: LookupRecord,
        assetlocation: str,
        projectsite: str,
    ) -> int | str:
        """Resolve the model definition reference used by SHM payload builders.

        The lookup prefers the transition-piece model definition present on
        the subassembly rows and, when the parent geometry client exposes
        ``get_modeldefinition_id()``, upgrades a model-definition title into
        the corresponding backend id.
        """
        model_definition = self.get_transition_piece_model_definition(subassemblies=subassemblies)
        if isinstance(model_definition, int):
            return model_definition

        get_modeldefinition_id = getattr(self.geometry_client, "get_modeldefinition_id", None)
        if not callable(get_modeldefinition_id):
            return model_definition

        try:
            result = get_modeldefinition_id(
                assetlocation=assetlocation,
                projectsite=projectsite,
                model_definition=model_definition,
            )
        except ValueError as exc:
            raise ModelDefinitionLookupError(str(exc)) from exc

        if not isinstance(result, Mapping):
            return model_definition

        record_id = result.get("id")
        normalized_record_id = self._normalize_model_definition(record_id)
        if normalized_record_id is None:
            return model_definition

        if isinstance(normalized_record_id, int):
            return normalized_record_id

        try:
            return int(normalized_record_id)
        except (TypeError, ValueError):
            return model_definition

    @staticmethod
    def get_transition_piece_model_definition(
        subassemblies: LookupRecord,
    ) -> int | str:
        """Extract the transition-piece model definition from subassemblies."""
        if "subassembly_type" not in subassemblies.data or "model_definition" not in subassemblies.data:
            raise ModelDefinitionLookupError(
                "Subassembly lookup data must contain 'subassembly_type' and 'model_definition' columns."
            )

        transition_pieces = subassemblies.data[subassemblies.data["subassembly_type"] == "TP"]
        if transition_pieces.empty:
            raise ModelDefinitionLookupError("No transition-piece subassembly found in lookup result.")

        model_definitions = [
            normalized
            for value in transition_pieces["model_definition"].tolist()
            for normalized in [ParentSDKLookupService._normalize_model_definition(value)]
            if normalized is not None
        ]
        unique_definitions = list(dict.fromkeys(model_definitions))
        if not unique_definitions:
            raise ModelDefinitionLookupError("Transition-piece subassemblies do not define a model definition.")
        if len(unique_definitions) > 1:
            raise ModelDefinitionLookupError(
                "Transition-piece subassemblies map to multiple model definitions; the backend data is ambiguous."
            )
        return unique_definitions[0]

    @staticmethod
    def _normalize_model_definition(value: Any) -> int | str | None:
        """Normalize a model-definition value from parent lookup data."""
        if pd.isna(value):
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float) and value.is_integer():
            return int(value)

        text_value = str(value).strip()
        if not text_value:
            return None
        if text_value.isdigit():
            return int(text_value)
        return text_value

    @staticmethod
    def _resolve_projectsite_name(asset: LookupRecord, assetlocation: str) -> str:
        """Derive the project-site title from an asset lookup record."""
        for column_name in ("projectsite_name", "projectsite", "projectsite_title"):
            if column_name not in asset.data.columns or asset.data.empty:
                continue
            raw_value = asset.data[column_name].iloc[0]
            if pd.isna(raw_value):
                continue
            projectsite = str(raw_value).strip()
            if projectsite:
                return projectsite

        raise ProjectSiteLookupError(
            f"Could not derive project site for asset location '{assetlocation}' from the parent lookup data."
        )

    @staticmethod
    def _build_subassembly_ids_by_type(subassemblies: LookupRecord) -> dict[str, int]:
        """Build a stable subassembly id mapping from parent lookup data."""
        required_columns = {"id", "subassembly_type"}
        if not required_columns.issubset(subassemblies.data.columns):
            raise SignalUploadContextError("Subassembly lookup data must contain 'id' and 'subassembly_type' columns.")

        subassembly_ids_by_type: dict[str, int] = {}
        for row in subassemblies.data[["id", "subassembly_type"]].itertuples(index=False):
            row_id = row.id
            subassembly_type = row.subassembly_type
            if pd.isna(row_id) or pd.isna(subassembly_type):
                raise SignalUploadContextError("Subassembly lookup data contains null ids or subassembly types.")
            subassembly_ids_by_type.setdefault(str(subassembly_type), int(row_id))

        return subassembly_ids_by_type

    @staticmethod
    def _build_record(
        result: dict[str, Any],
        label: str,
        error_type: type[ShmLookupError],
    ) -> LookupRecord:
        """Normalize a parent SDK lookup response."""
        if not result.get("exists", False):
            raise error_type(f"Could not resolve {label}.")

        data = result.get("data")
        if not isinstance(data, pd.DataFrame):
            raise error_type(f"Lookup result for {label} did not contain a pandas DataFrame.")

        record_id = result.get("id")
        normalized_id = int(record_id) if record_id is not None else None
        return LookupRecord(data=data.copy(), record_id=normalized_id)

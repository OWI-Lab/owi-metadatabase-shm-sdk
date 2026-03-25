from __future__ import annotations

from unittest.mock import Mock

import pandas as pd
import pytest

from owi.metadatabase.shm.lookup import (
    AssetLocationLookupError,
    AssetLookupContext,
    LookupRecord,
    ModelDefinitionLookupError,
    ParentSDKLookupService,
    ProjectSiteLookupError,
    SignalUploadContextError,
    SubassembliesLookupError,
)


def test_get_asset_context_returns_typed_lookup_records() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    site_df = pd.DataFrame([{"id": 10, "title": "Project A"}])
    asset_df = pd.DataFrame([{"id": 11, "title": "Asset-01", "projectsite_name": "Project A"}])
    subassemblies_df = pd.DataFrame(
        [
            {"subassembly_type": "TP", "model_definition": "MD-01"},
            {"subassembly_type": "TW", "model_definition": "MD-01"},
        ]
    )
    locations_client.get_projectsite_detail.return_value = {"data": site_df, "exists": True, "id": 10}
    locations_client.get_assetlocation_detail.return_value = {"data": asset_df, "exists": True, "id": 11}
    geometry_client.get_subassemblies.return_value = {"data": subassemblies_df, "exists": True}

    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    context = service.get_asset_context(projectsite="Project A", assetlocation="Asset-01")

    locations_client.get_projectsite_detail.assert_called_once_with(projectsite="Project A")
    locations_client.get_assetlocation_detail.assert_called_once_with(
        assetlocation="Asset-01",
        projectsite="Project A",
    )
    geometry_client.get_subassemblies.assert_called_once_with(
        projectsite="Project A",
        assetlocation="Asset-01",
    )
    assert context.site.record_id == 10
    assert context.asset.record_id == 11
    assert context.model_definition == "MD-01"
    assert list(context.subassemblies.data["subassembly_type"]) == ["TP", "TW"]


def test_get_asset_context_derives_projectsite_from_asset_lookup() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    locations_client.get_assetlocation_detail.return_value = {
        "data": pd.DataFrame(
            [{"id": 11, "title": "Asset-01", "projectsite_name": "Project A"}]
        ),
        "exists": True,
        "id": 11,
    }
    locations_client.get_projectsite_detail.return_value = {
        "data": pd.DataFrame([{"id": 10, "title": "Project A"}]),
        "exists": True,
        "id": 10,
    }
    geometry_client.get_subassemblies.return_value = {
        "data": pd.DataFrame([{"id": 40, "subassembly_type": "TP", "model_definition": "MD-01"}]),
        "exists": True,
    }
    geometry_client.get_modeldefinition_id.return_value = {"id": 99}

    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    context = service.get_asset_context(projectsite=None, assetlocation="Asset-01")

    locations_client.get_assetlocation_detail.assert_called_once_with(
        assetlocation="Asset-01",
        projectsite=None,
    )
    locations_client.get_projectsite_detail.assert_called_once_with(projectsite="Project A")
    geometry_client.get_subassemblies.assert_called_once_with(
        projectsite="Project A",
        assetlocation="Asset-01",
    )
    geometry_client.get_modeldefinition_id.assert_called_once_with(
        assetlocation="Asset-01",
        projectsite="Project A",
        model_definition="MD-01",
    )
    assert context.model_definition == 99


def test_get_projectsite_raises_explicit_error_when_missing() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    locations_client.get_projectsite_detail.return_value = {"data": pd.DataFrame(), "exists": False, "id": None}
    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    with pytest.raises(ProjectSiteLookupError, match="Could not resolve project site 'Project A'"):
        service.get_projectsite("Project A")


def test_get_assetlocation_raises_explicit_error_when_missing() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    locations_client.get_assetlocation_detail.return_value = {"data": pd.DataFrame(), "exists": False, "id": None}
    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    with pytest.raises(AssetLocationLookupError, match="Could not resolve asset location 'Asset-01'"):
        service.get_assetlocation(assetlocation="Asset-01", projectsite="Project A")


def test_get_subassemblies_raises_explicit_error_when_missing() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    geometry_client.get_subassemblies.return_value = {"data": pd.DataFrame(), "exists": False}
    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    with pytest.raises(SubassembliesLookupError, match="Could not resolve subassemblies"):
        service.get_subassemblies(assetlocation="Asset-01", projectsite="Project A")


def test_transition_piece_model_definition_requires_tp_rows() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)
    locations_client.get_projectsite_detail.return_value = {
        "data": pd.DataFrame([{"id": 10, "title": "Project A"}]),
        "exists": True,
        "id": 10,
    }
    locations_client.get_assetlocation_detail.return_value = {
        "data": pd.DataFrame([{"id": 11, "title": "Asset-01"}]),
        "exists": True,
        "id": 11,
    }
    geometry_client.get_subassemblies.return_value = {
        "data": pd.DataFrame([{"subassembly_type": "TW", "model_definition": "MD-01"}]),
        "exists": True,
    }

    with pytest.raises(ModelDefinitionLookupError, match="No transition-piece subassembly"):
        service.get_asset_context(projectsite="Project A", assetlocation="Asset-01")


def test_transition_piece_model_definition_rejects_ambiguous_backend_data() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    locations_client.get_projectsite_detail.return_value = {
        "data": pd.DataFrame([{"id": 10, "title": "Project A"}]),
        "exists": True,
        "id": 10,
    }
    locations_client.get_assetlocation_detail.return_value = {
        "data": pd.DataFrame([{"id": 11, "title": "Asset-01"}]),
        "exists": True,
        "id": 11,
    }
    geometry_client.get_subassemblies.return_value = {
        "data": pd.DataFrame(
            [
                {"subassembly_type": "TP", "model_definition": "MD-01"},
                {"subassembly_type": "TP", "model_definition": "MD-02"},
            ]
        ),
        "exists": True,
    }
    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    with pytest.raises(ModelDefinitionLookupError, match="multiple model definitions"):
        service.get_asset_context(projectsite="Project A", assetlocation="Asset-01")


def test_get_signal_upload_context_builds_payload_builder_context() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    locations_client.get_projectsite_detail.return_value = {
        "data": pd.DataFrame([{"id": 10, "title": "Project A"}]),
        "exists": True,
        "id": 10,
    }
    locations_client.get_assetlocation_detail.return_value = {
        "data": pd.DataFrame([{"id": 11, "title": "Asset-01"}]),
        "exists": True,
        "id": 11,
    }
    geometry_client.get_subassemblies.return_value = {
        "data": pd.DataFrame(
            [
                {"id": 40, "subassembly_type": "TP", "model_definition": "MD-01"},
                {"id": 41, "subassembly_type": "TW", "model_definition": "MD-01"},
            ]
        ),
        "exists": True,
    }
    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    context = service.get_signal_upload_context(
        projectsite="Project A",
        assetlocation="Asset-01",
        permission_group_ids=[7, 11],
    )

    assert context.site_id == 10
    assert context.asset_location_id == 11
    assert context.model_definition_id == "MD-01"
    assert context.permission_group_ids == [7, 11]
    assert context.subassembly_ids_by_type == {"TP": 40, "TW": 41}


def test_get_signal_upload_context_uses_parent_geometry_modeldefinition_id_when_available() -> None:
    locations_client = Mock()
    geometry_client = Mock()
    locations_client.get_projectsite_detail.return_value = {
        "data": pd.DataFrame([{"id": 10, "title": "Project A"}]),
        "exists": True,
        "id": 10,
    }
    locations_client.get_assetlocation_detail.return_value = {
        "data": pd.DataFrame([{"id": 11, "title": "Asset-01"}]),
        "exists": True,
        "id": 11,
    }
    geometry_client.get_subassemblies.return_value = {
        "data": pd.DataFrame([{"id": 40, "subassembly_type": "TP", "model_definition": "MD-01"}]),
        "exists": True,
    }
    geometry_client.get_modeldefinition_id.return_value = {"id": 123, "multiple_modeldef": False}

    service = ParentSDKLookupService(locations_client=locations_client, geometry_client=geometry_client)

    context = service.get_signal_upload_context(projectsite="Project A", assetlocation="Asset-01")

    geometry_client.get_modeldefinition_id.assert_called_once_with(
        assetlocation="Asset-01",
        projectsite="Project A",
        model_definition="MD-01",
    )
    assert context.model_definition_id == 123


def test_build_signal_upload_context_requires_subassembly_id_columns() -> None:
    asset_context = AssetLookupContext(
        site=LookupRecord(pd.DataFrame([{"id": 10}]), record_id=10),
        asset=LookupRecord(pd.DataFrame([{"id": 11}]), record_id=11),
        subassemblies=LookupRecord(pd.DataFrame([{"subassembly_type": "TP", "model_definition": "MD-01"}])),
        model_definition="MD-01",
    )

    with pytest.raises(SignalUploadContextError, match="must contain 'id' and 'subassembly_type'"):
        ParentSDKLookupService.build_signal_upload_context(asset_context, permission_group_ids=None)

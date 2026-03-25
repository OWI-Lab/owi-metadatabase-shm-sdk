"""SHM  extension for OWI Metadatabase SDK.

This package extends the ``owi.metadatabase`` namespace with the
``shm`` extension.
"""

from .io import ShmAPI
from .json_utils import load_json_data
from .lookup import (
    AssetLocationLookupError,
    AssetLookupContext,
    LookupRecord,
    ModelDefinitionLookupError,
    ParentSDKLookupService,
    ProjectSiteLookupError,
    ShmLookupError,
    SignalUploadContextError,
    SubassembliesLookupError,
)
from .models import (
    DerivedSignalCalibrationRecord,
    DerivedSignalHistoryRecord,
    DerivedSignalRecord,
    SensorCalibrationRecord,
    SensorRecord,
    SensorTypeRecord,
    ShmEntityName,
    ShmQuery,
    SignalCalibrationRecord,
    SignalHistoryRecord,
    SignalRecord,
)
from .processing import (
    ConfiguredSignalConfigProcessor,
    DefaultSignalConfigProcessor,
    DelimitedSignalKeyParser,
    JsonStemConfigDiscovery,
    LevelBasedDerivedSignalStrategy,
    SignalConfigProcessor,
    SignalProcessingResult,
    SignalProcessorSpec,
    default_signal_processor_spec,
    get_default_signal_processor_spec_path,
    load_default_signal_processor_spec,
    load_signal_processor_spec,
)
from .registry import ShmEntityDefinition, ShmEntityRegistry, default_registry
from .serializers import DEFAULT_SERIALIZERS, ShmEntitySerializer
from .services import ApiShmRepository, SensorService, ShmEntityService, SignalService
from .signal_ids import LegacySignalIdentifier, parse_legacy_signal_id
from .upload import (
    AssetSignalUploadRequest,
    AssetSignalUploadResult,
    DerivedSignalCalibrationPayload,
    DerivedSignalHistoryPayload,
    DerivedSignalPayload,
    ParentSignalLookupError,
    ShmSensorUploader,
    ShmSignalUploader,
    ShmUploadError,
    SignalCalibrationPayload,
    SignalConfigUploadSource,
    SignalHistoryPayload,
    SignalPayload,
    UploadResultError,
)
from .upload_context import SignalUploadContext

__version__ = "0.1.0"

__all__ = [
    "ApiShmRepository",
    "AssetLocationLookupError",
    "AssetLookupContext",
    "LookupRecord",
    "ModelDefinitionLookupError",
    "ParentSignalLookupError",
    "ParentSDKLookupService",
    "ProjectSiteLookupError",
    "ConfiguredSignalConfigProcessor",
    "DEFAULT_SERIALIZERS",
    "DefaultSignalConfigProcessor",
    "DelimitedSignalKeyParser",
    "default_registry",
    "DerivedSignalCalibrationRecord",
    "DerivedSignalCalibrationPayload",
    "DerivedSignalHistoryRecord",
    "DerivedSignalHistoryPayload",
    "DerivedSignalRecord",
    "DerivedSignalPayload",
    "default_signal_processor_spec",
    "get_default_signal_processor_spec_path",
    "JsonStemConfigDiscovery",
    "LegacySignalIdentifier",
    "LevelBasedDerivedSignalStrategy",
    "load_default_signal_processor_spec",
    "load_json_data",
    "load_signal_processor_spec",
    "parse_legacy_signal_id",
    "SensorCalibrationRecord",
    "SensorRecord",
    "SensorService",
    "SensorTypeRecord",
    "SignalCalibrationPayload",
    "SignalConfigUploadSource",
    "SignalCalibrationRecord",
    "SignalHistoryRecord",
    "SignalHistoryPayload",
    "SignalPayload",
    "SignalUploadContext",
    "SignalUploadContextError",
    "ShmAPI",
    "ShmEntityDefinition",
    "ShmEntityName",
    "ShmEntityRegistry",
    "ShmEntitySerializer",
    "ShmEntityService",
    "ShmLookupError",
    "ShmQuery",
    "ShmSensorUploader",
    "ShmSignalUploader",
    "ShmUploadError",
    "SignalConfigProcessor",
    "SignalProcessingResult",
    "SignalProcessorSpec",
    "SignalRecord",
    "SignalService",
    "SubassembliesLookupError",
    "AssetSignalUploadRequest",
    "AssetSignalUploadResult",
    "UploadResultError",
    "__version__",
]

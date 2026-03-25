"""Upload subpackage for SHM signal and sensor upload orchestration.

Re-exports all public symbols so ``from owi.metadatabase.shm.upload import X``
works unchanged.
"""

from .errors import ParentSignalLookupError, ShmUploadError, UploadResultError
from .models import AssetSignalUploadRequest, AssetSignalUploadResult
from .payloads import (
    DerivedSignalCalibrationPayload,
    DerivedSignalHistoryPayload,
    DerivedSignalPayload,
    SensorCalibrationPayload,
    SensorPayload,
    SensorTypePayload,
    SignalCalibrationPayload,
    SignalHistoryPayload,
    SignalPayload,
    build_derived_signal_calibration_payloads,
    build_derived_signal_main_payload,
    build_derived_signal_parent_patch,
    build_derived_signal_status_payload,
    build_sensor_calibration_payloads,
    build_sensor_payloads,
    build_sensor_type_payloads,
    build_signal_calibration_payloads,
    build_signal_main_payload,
    build_signal_status_payloads,
)
from .protocols import ShmSignalUploadClient, SignalConfigUploadSource
from .sensors import ShmSensorUploadClient, ShmSensorUploader
from .signals import ShmSignalUploader

__all__ = [
    "AssetSignalUploadRequest",
    "AssetSignalUploadResult",
    "build_derived_signal_calibration_payloads",
    "build_derived_signal_main_payload",
    "build_derived_signal_parent_patch",
    "build_derived_signal_status_payload",
    "build_signal_calibration_payloads",
    "build_signal_main_payload",
    "build_signal_status_payloads",
    "DerivedSignalCalibrationPayload",
    "DerivedSignalHistoryPayload",
    "DerivedSignalPayload",
    "ParentSignalLookupError",
    "SensorCalibrationPayload",
    "SensorPayload",
    "SensorTypePayload",
    "SignalCalibrationPayload",
    "SignalHistoryPayload",
    "SignalPayload",
    "ShmSensorUploadClient",
    "ShmSensorUploader",
    "ShmSignalUploadClient",
    "ShmSignalUploader",
    "ShmUploadError",
    "SignalConfigUploadSource",
    "UploadResultError",
    "build_sensor_calibration_payloads",
    "build_sensor_payloads",
    "build_sensor_type_payloads",
]

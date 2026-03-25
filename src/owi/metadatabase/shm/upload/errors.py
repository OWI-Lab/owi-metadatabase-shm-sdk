"""SHM upload error hierarchy."""

from __future__ import annotations

from owi.metadatabase._utils.exceptions import APIException  # ty: ignore[unresolved-import]


class ShmUploadError(APIException):
    """Base exception for SHM upload orchestration failures."""


class UploadResultError(ShmUploadError):
    """Raised when a backend mutation result does not include the expected id."""


class ParentSignalLookupError(ShmUploadError):
    """Raised when a derived signal refers to unresolved parent signals."""

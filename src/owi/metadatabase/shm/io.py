"""API client for the shm extension.

This module exposes :class:`ShmAPI` as the low-level entry point
for SHM transport and persistence helpers.

Examples
--------
>>> from owi.metadatabase.shm import ShmAPI
>>> isinstance(ShmAPI(token="dummy"), ShmAPI)
True
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests
from owi.metadatabase._utils.exceptions import (  # ty: ignore[unresolved-import]
    APIConnectionError,
    InvalidParameterError,
)
from owi.metadatabase.io import API  # ty: ignore[unresolved-import]

QueryValue = str | float | int | Sequence[str | float | int] | None


@dataclass(frozen=True)
class ShmEndpoints:
    """Centralized route names for the SHM backend."""

    api_subdir: str = "/shm/routes/"
    sensor_type: str = "sensortype"
    sensor: str = "sensor"
    sensor_calibration: str = "sensorcalibration"
    signal: str = "signal"
    signal_history: str = "signalhistory"
    signal_calibration: str = "signalcalibration"
    derived_signal: str = "derivedsignal"
    derived_signal_history: str = "derivedsignalhistory"
    derived_signal_calibration: str = "derivedsignalcalibration"

    def mutation_path(self, endpoint: str) -> str:
        """Return a collection endpoint path with a trailing slash."""
        return endpoint.rstrip("/") + "/"

    def detail_path(self, endpoint: str, object_id: int) -> str:
        """Return a detail endpoint path with a trailing slash."""
        return f"{endpoint.rstrip('/')}/{object_id}/"


DEFAULT_SHM_ENDPOINTS = ShmEndpoints()


class ShmAPI(API):
    """Low-level API client for the SHM extension.

    Parameters
    ----------
    api_subdir : str, default="/shm/routes/"
        API sub-path appended to the base root.
    **kwargs
        Forwarded to :class:`owi.metadatabase.io.API`.

    Examples
    --------
    >>> api = ShmAPI(token="dummy")
    >>> api.ping()
    'ok'
    """

    def __init__(self, api_subdir: str = DEFAULT_SHM_ENDPOINTS.api_subdir, **kwargs: Any) -> None:
        self.endpoints: ShmEndpoints = kwargs.pop("endpoints", DEFAULT_SHM_ENDPOINTS)
        super().__init__(**kwargs)
        self.base_api_root = self.api_root
        self.api_root = self.api_root + api_subdir

    def ping(self) -> str:
        """Return a basic health response.

        Examples
        --------
        >>> api = ShmAPI(token="dummy")
        >>> api.ping()
        'ok'
        """
        return "ok"

    def _authenticated_request(self, method: str, url: str, payload: Any) -> requests.Response:
        """Send an authenticated JSON request and validate the response status."""
        headers = {"Content-Type": "application/json"}
        if self.header is not None:
            headers.update(self.header)
            response = requests.request(method, url, headers=headers, json=payload)
        elif self.auth is not None:
            response = requests.request(method, url, auth=self.auth, headers=headers, json=payload)
        else:
            raise InvalidParameterError("Either header or username/password authentication must be configured.")
        if response.status_code not in {200, 201}:
            raise APIConnectionError(
                message=f"Error {response.status_code}.\n{response.reason}",
                response=response,
            )
        return response

    def _send_multipart_request(
        self,
        endpoint: str,
        data: Mapping[str, Any],
        files: Mapping[str, Any] | None = None,
    ) -> requests.Response:
        """Send a multipart form-data request to a collection endpoint.

        Parameters
        ----------
        endpoint
            SHM route name for the target resource.
        data
            Form fields sent as the ``data`` part of the request.
        files
            Optional file mappings sent as the ``files`` part.

        Returns
        -------
        requests.Response
            Server response for the multipart request.
        """
        url = self.api_root + self.endpoints.mutation_path(endpoint)
        headers: dict[str, str] = {}
        if self.header is not None:
            headers.update(self.header)
            response = requests.post(url, headers=headers, data=data, files=files)
        elif self.auth is not None:
            response = requests.post(url, auth=self.auth, headers=headers, data=data, files=files)
        else:
            raise InvalidParameterError("Either header or username/password authentication must be configured.")
        if response.status_code not in {200, 201}:
            raise APIConnectionError(
                message=f"Error {response.status_code}.\n{response.reason}",
                response=response,
            )
        return response

    def _mutate_multipart_resource(
        self,
        endpoint: str,
        data: Mapping[str, Any],
        files: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a resource via multipart form-data.

        Parameters
        ----------
        endpoint
            SHM route name for the target resource.
        data
            Form fields for the resource payload.
        files
            Optional file attachments (images, PDFs, etc.).

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary.
        """
        response = self._send_multipart_request(endpoint, data, files=files)
        df = self._response_to_dataframe(response)
        response_id = df["id"].iloc[0] if "id" in df and not df.empty else None
        return {
            "data": df,
            "exists": not df.empty,
            "id": response_id,
            "response": response,
        }

    def _send_json_request(self, endpoint: str, payload: Any, method: str = "post") -> requests.Response:
        """Send a JSON mutation request to a collection endpoint."""
        url = self.api_root + self.endpoints.mutation_path(endpoint)
        return self._authenticated_request(method, url, payload)

    def _send_detail_json_request(
        self,
        endpoint: str,
        object_id: int,
        payload: Any,
        method: str = "patch",
    ) -> requests.Response:
        """Send a JSON mutation request to a detail endpoint."""
        url = self.api_root + self.endpoints.detail_path(endpoint, object_id)
        return self._authenticated_request(method, url, payload)

    @staticmethod
    def _response_to_dataframe(response: requests.Response) -> pd.DataFrame:
        """Convert a JSON response body into a DataFrame."""
        payload = response.json()
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            return pd.DataFrame([payload])
        return pd.DataFrame()

    def _list_resource(self, endpoint: str, **kwargs: QueryValue) -> dict[str, Any]:
        """Return rows for a list-style SHM resource endpoint."""
        df, info = self.process_data(endpoint, kwargs, "list")
        return {
            "data": df,
            "exists": info["existance"],
            "response": info.get("response"),
        }

    def _get_resource(self, endpoint: str, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single-row SHM resource result."""
        df, info = self.process_data(endpoint, kwargs, "single")
        return {
            "data": df,
            "exists": info["existance"],
            "id": info.get("id"),
            "response": info.get("response"),
        }

    def _mutate_resource(
        self,
        endpoint: str,
        payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        object_id: int | None = None,
        method: str | None = None,
    ) -> dict[str, Any]:
        """Create or patch rows for a SHM resource endpoint."""
        serialized_payload: Any = dict(payload) if isinstance(payload, Mapping) else [dict(item) for item in payload]

        request_method = method or ("patch" if object_id is not None else "post")
        if object_id is None:
            response = self._send_json_request(endpoint, serialized_payload, method=request_method)
        else:
            response = self._send_detail_json_request(
                endpoint,
                object_id,
                serialized_payload,
                method=request_method,
            )

        df = self._response_to_dataframe(response)
        response_id = df["id"].iloc[0] if "id" in df and not df.empty else object_id
        return {
            "data": df,
            "exists": not df.empty,
            "id": response_id,
            "response": response,
        }

    def get_signal(self, signal_id: str, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM signal by its backend signal identifier.

        Parameters
        ----------
        signal_id
            Backend-facing SHM signal identifier.
        **kwargs
            Additional query parameters forwarded to the SHM route.

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary containing ``data``,
            ``exists``, ``id``, and ``response``.

        Examples
        --------
        >>> from unittest.mock import patch
        >>> api = ShmAPI(token="dummy")
        >>> with patch.object(
        ...     ShmAPI,
        ...     "process_data",
        ...     return_value=(pd.DataFrame([{"id": 7, "signal_id": "SG-01"}]), {"existance": True, "id": 7}),
        ... ):
        ...     result = api.get_signal("SG-01")
        >>> result["id"]
        7
        """
        return self._get_resource(self.endpoints.signal, signal_id=signal_id, **kwargs)

    def get_sensor_type(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM sensor type by query parameters.

        Parameters
        ----------
        **kwargs
            Query parameters forwarded to the SHM sensor-type route.

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary containing ``data``,
            ``exists``, ``id``, and ``response``.
        """
        return self._get_resource(self.endpoints.sensor_type, **kwargs)

    def get_sensor(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM sensor by query parameters.

        Parameters
        ----------
        **kwargs
            Query parameters forwarded to the SHM sensor route.

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary containing ``data``,
            ``exists``, ``id``, and ``response``.
        """
        return self._get_resource(self.endpoints.sensor, **kwargs)

    def get_sensor_calibration(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM sensor calibration by query parameters."""
        return self._get_resource(self.endpoints.sensor_calibration, **kwargs)

    def get_signal_history(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM signal history row by query parameters."""
        return self._get_resource(self.endpoints.signal_history, **kwargs)

    def get_signal_calibration(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM signal calibration by query parameters."""
        return self._get_resource(self.endpoints.signal_calibration, **kwargs)

    def get_derived_signal(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM derived signal by query parameters."""
        return self._get_resource(self.endpoints.derived_signal, **kwargs)

    def get_derived_signal_history(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM derived signal history row by query parameters."""
        return self._get_resource(self.endpoints.derived_signal_history, **kwargs)

    def get_derived_signal_calibration(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return a single SHM derived signal calibration by query parameters."""
        return self._get_resource(self.endpoints.derived_signal_calibration, **kwargs)

    def create_signal(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a signal record.

        Examples
        --------
        >>> from unittest.mock import patch
        >>> api = ShmAPI(token="dummy")
        >>> with patch.object(ShmAPI, "_mutate_resource", return_value={"id": 12, "exists": True}) as mocker:
        ...     result = api.create_signal({"signal_id": "SG-01"})
        >>> mocker.assert_called_once_with(api.endpoints.signal, {"signal_id": "SG-01"})
        >>> result["id"]
        12
        """
        return self._mutate_resource(self.endpoints.signal, payload)

    def create_signal_history(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a signal history record."""
        return self._mutate_resource(self.endpoints.signal_history, payload)

    def create_signal_calibration(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a signal calibration record."""
        return self._mutate_resource(self.endpoints.signal_calibration, payload)

    def create_derived_signal(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a derived signal record."""
        return self._mutate_resource(self.endpoints.derived_signal, payload)

    def create_derived_signal_history(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a derived signal history record."""
        return self._mutate_resource(self.endpoints.derived_signal_history, payload)

    def patch_derived_signal_history(self, history_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Patch a derived signal history record by id."""
        return self._mutate_resource(
            self.endpoints.derived_signal_history,
            payload,
            object_id=history_id,
            method="patch",
        )

    def create_derived_signal_calibration(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a derived signal calibration record."""
        return self._mutate_resource(self.endpoints.derived_signal_calibration, payload)

    # ------------------------------------------------------------------
    # Sensor CRUD
    # ------------------------------------------------------------------

    def list_sensor_types(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM sensor types matching the query parameters.

        Parameters
        ----------
        **kwargs
            Query parameters forwarded to the sensor-type list route.

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary containing ``data``,
            ``exists``, and ``response``.
        """
        return self._list_resource(self.endpoints.sensor_type, **kwargs)

    def list_sensors(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM sensors matching the query parameters.

        Parameters
        ----------
        **kwargs
            Query parameters forwarded to the sensor list route.

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary containing ``data``,
            ``exists``, and ``response``.
        """
        return self._list_resource(self.endpoints.sensor, **kwargs)

    def list_sensor_calibrations(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM sensor calibrations matching the query parameters."""
        return self._list_resource(self.endpoints.sensor_calibration, **kwargs)

    def list_signals(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM signals matching the query parameters."""
        return self._list_resource(self.endpoints.signal, **kwargs)

    def list_signal_history(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM signal history rows matching the query parameters."""
        return self._list_resource(self.endpoints.signal_history, **kwargs)

    def list_signal_calibrations(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM signal calibrations matching the query parameters."""
        return self._list_resource(self.endpoints.signal_calibration, **kwargs)

    def list_derived_signals(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM derived signals matching the query parameters."""
        return self._list_resource(self.endpoints.derived_signal, **kwargs)

    def list_derived_signal_history(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM derived signal history rows matching the query parameters."""
        return self._list_resource(self.endpoints.derived_signal_history, **kwargs)

    def list_derived_signal_calibrations(self, **kwargs: QueryValue) -> dict[str, Any]:
        """Return all SHM derived signal calibrations matching the query parameters."""
        return self._list_resource(self.endpoints.derived_signal_calibration, **kwargs)

    def create_sensor_type(
        self,
        payload: Mapping[str, Any],
        files: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a sensor type record, optionally with an image attachment.

        Parameters
        ----------
        payload
            Form fields for the sensor type resource.
        files
            Optional file mapping (e.g. ``{"photo": open_file}``).

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary.
        """
        if files:
            return self._mutate_multipart_resource(self.endpoints.sensor_type, payload, files=files)
        return self._mutate_resource(self.endpoints.sensor_type, payload)

    def create_sensor(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a sensor record.

        Parameters
        ----------
        payload
            JSON payload for the sensor resource.

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary.
        """
        return self._mutate_resource(self.endpoints.sensor, payload)

    def create_sensor_calibration(
        self,
        payload: Mapping[str, Any],
        files: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a sensor calibration record, optionally with a PDF attachment.

        Parameters
        ----------
        payload
            Form fields for the sensor calibration resource.
        files
            Optional file mapping (e.g. ``{"datasheet": open_file}``).

        Returns
        -------
        dict[str, Any]
            Parent-SDK-style result dictionary.
        """
        if files:
            return self._mutate_multipart_resource(self.endpoints.sensor_calibration, payload, files=files)
        return self._mutate_resource(self.endpoints.sensor_calibration, payload)

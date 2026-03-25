from unittest.mock import patch

import pandas as pd
import pytest
import requests
from owi.metadatabase._utils.exceptions import (  # ty: ignore[unresolved-import]
    APIConnectionError,
    InvalidParameterError,
)

from owi.metadatabase.shm import ShmAPI
from owi.metadatabase.shm.io import DEFAULT_SHM_ENDPOINTS


def _make_response(status_code: int, payload: str = "{}", reason: str = "OK") -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.reason = reason
    response._content = payload.encode("utf-8")
    return response


def test_ping() -> None:
    api = ShmAPI(token="dummy")
    assert api.ping() == "ok"


def test_default_base_url() -> None:
    api = ShmAPI(token="dummy")
    assert api.api_root.startswith("https://")
    assert api.api_root.endswith("/shm/routes/")


def test_base_api_root_preserved() -> None:
    api = ShmAPI(token="dummy")
    assert not api.base_api_root.endswith("/shm/routes/")


def test_default_endpoints_match_archive_routes() -> None:
    api = ShmAPI(token="dummy")

    assert api.endpoints.sensor_type == "sensortype"
    assert api.endpoints.sensor == "sensor"
    assert api.endpoints.sensor_calibration == "sensorcalibration"
    assert api.endpoints.signal == "signal"
    assert api.endpoints.signal_history == "signalhistory"
    assert api.endpoints.signal_calibration == "signalcalibration"
    assert api.endpoints.derived_signal == "derivedsignal"
    assert api.endpoints.derived_signal_history == "derivedsignalhistory"
    assert api.endpoints.derived_signal_calibration == "derivedsignalcalibration"


def test_authenticated_request_uses_token_header_and_json_payload() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(201, '{"id": 12}', reason="Created")

    with patch("requests.request", return_value=response) as mocker:
        result = api._authenticated_request(
            "post",
            "https://example.test/api/v1/shm/signals/",
            {"name": "Tower sensor"},
        )

    assert result is response
    mocker.assert_called_once_with(
        "post",
        "https://example.test/api/v1/shm/signals/",
        headers={"Authorization": "Token dummy", "Content-Type": "application/json"},
        json={"name": "Tower sensor"},
    )


def test_authenticated_request_uses_basic_auth_when_configured() -> None:
    api = ShmAPI(uname="lambert", password="secret")
    response = _make_response(200)

    with patch("requests.request", return_value=response) as mocker:
        result = api._authenticated_request(
            "patch",
            "https://example.test/api/v1/shm/signals/7/",
            {"name": "Updated signal"},
        )

    assert result is response
    assert mocker.call_args.args == ("patch", "https://example.test/api/v1/shm/signals/7/")
    assert mocker.call_args.kwargs["auth"] == api.auth
    assert mocker.call_args.kwargs["headers"] == {"Content-Type": "application/json"}
    assert mocker.call_args.kwargs["json"] == {"name": "Updated signal"}


def test_authenticated_request_raises_api_connection_error_on_non_success_status() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(502, reason="Bad Gateway")

    with patch("requests.request", return_value=response), pytest.raises(APIConnectionError) as excinfo:
        api._authenticated_request(
            "post",
            "https://example.test/api/v1/shm/signals/",
            {"name": "Tower sensor"},
        )

    assert excinfo.value.response is response


def test_send_json_request_builds_trailing_slash_mutation_url() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(201, '{"id": 8}', reason="Created")

    with patch.object(ShmAPI, "_authenticated_request", return_value=response) as mocker:
        result = api._send_json_request("signals", {"name": "Tower sensor"}, method="post")

    assert result is response
    mocker.assert_called_once_with("post", api.api_root + "signals/", {"name": "Tower sensor"})


def test_send_detail_json_request_builds_detail_url() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(200, '{"id": 8}')

    with patch.object(ShmAPI, "_authenticated_request", return_value=response) as mocker:
        result = api._send_detail_json_request("signals", 8, {"name": "Tower sensor"}, method="patch")

    assert result is response
    mocker.assert_called_once_with("patch", api.api_root + "signals/8/", {"name": "Tower sensor"})


def test_list_resource_calls_process_data() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(ShmAPI, "process_data", return_value=(pd.DataFrame({"id": [1]}), {"existance": True})) as mocker:
        result = api._list_resource(api.endpoints.sensor, sensor_type=4)

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.sensor, {"sensor_type": 4}, "list")
    assert result["exists"] is True


def test_get_signal_calls_process_data_with_single_output() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(
        ShmAPI,
        "process_data",
        return_value=(pd.DataFrame({"id": [1], "signal_id": ["SG-01"]}), {"existance": True, "id": 1}),
    ) as mocker:
        result = api.get_signal("SG-01")

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.signal, {"signal_id": "SG-01"}, "single")
    assert result["exists"] is True
    assert result["id"] == 1


def test_get_sensor_type_calls_process_data_with_single_output() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(
        ShmAPI,
        "process_data",
        return_value=(
            pd.DataFrame({"id": [3], "description": ["Strain"]}),
            {"existance": True, "id": 3},
        ),
    ) as mocker:
        result = api.get_sensor_type(description="Strain")

    mocker.assert_called_once_with(
        DEFAULT_SHM_ENDPOINTS.sensor_type,
        {"description": "Strain"},
        "single",
    )
    assert result["exists"] is True
    assert result["id"] == 3


def test_get_sensor_calls_process_data_with_single_output() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(
        ShmAPI,
        "process_data",
        return_value=(
            pd.DataFrame({"id": [4], "serial_number": ["SG-01"]}),
            {"existance": True, "id": 4},
        ),
    ) as mocker:
        result = api.get_sensor(serial_number="SG-01", sensor_type_id=3)

    mocker.assert_called_once_with(
        DEFAULT_SHM_ENDPOINTS.sensor,
        {"serial_number": "SG-01", "sensor_type_id": 3},
        "single",
    )
    assert result["exists"] is True
    assert result["id"] == 4


@pytest.mark.parametrize(
    ("method_name", "endpoint", "filters"),
    [
        ("get_sensor_calibration", DEFAULT_SHM_ENDPOINTS.sensor_calibration, {"sensor_id": 4}),
        ("get_signal_history", DEFAULT_SHM_ENDPOINTS.signal_history, {"signal_id": 1}),
        ("get_signal_calibration", DEFAULT_SHM_ENDPOINTS.signal_calibration, {"signal_id": 1}),
        ("get_derived_signal", DEFAULT_SHM_ENDPOINTS.derived_signal, {"derived_signal_id": "DS-01"}),
        (
            "get_derived_signal_history",
            DEFAULT_SHM_ENDPOINTS.derived_signal_history,
            {"derived_signal_id": 7},
        ),
        (
            "get_derived_signal_calibration",
            DEFAULT_SHM_ENDPOINTS.derived_signal_calibration,
            {"derived_signal_id": 7},
        ),
    ],
)
def test_additional_get_methods_call_process_data(
    method_name: str,
    endpoint: str,
    filters: dict[str, object],
) -> None:
    api = ShmAPI(token="dummy")
    with patch.object(
        ShmAPI,
        "process_data",
        return_value=(pd.DataFrame({"id": [5]}), {"existance": True, "id": 5}),
    ) as mocker:
        result = getattr(api, method_name)(**filters)

    mocker.assert_called_once_with(endpoint, filters, "single")
    assert result["exists"] is True
    assert result["id"] == 5


def test_mutate_resource_posts_collection_endpoint() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(201, '{"id": 12, "name": "S-1"}', reason="Created")

    with patch("requests.request", return_value=response) as mocker:
        result = api._mutate_resource(api.endpoints.sensor, {"name": "S-1"})

    mocker.assert_called_once()
    assert mocker.call_args.args[1].endswith(DEFAULT_SHM_ENDPOINTS.mutation_path("sensor"))
    assert mocker.call_args.kwargs["json"] == {"name": "S-1"}
    assert result["id"] == 12


def test_mutate_resource_patches_detail_endpoint() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(200, '{"id": 7, "name": "S-1"}')

    with patch("requests.request", return_value=response) as mocker:
        result = api._mutate_resource(api.endpoints.sensor, {"name": "S-1"}, object_id=7)

    mocker.assert_called_once()
    assert mocker.call_args.args[1].endswith(DEFAULT_SHM_ENDPOINTS.detail_path("sensor", 7))
    assert result["id"] == 7


def test_patch_derived_signal_history_uses_detail_mutation_helper() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(ShmAPI, "_mutate_resource", return_value={"id": 9, "exists": True}) as mocker:
        result = api.patch_derived_signal_history(9, {"parent_signals": [1, 2]})

    mocker.assert_called_once_with(
        api.endpoints.derived_signal_history,
        {"parent_signals": [1, 2]},
        object_id=9,
        method="patch",
    )
    assert result["id"] == 9


def test_send_json_request_raises_without_auth() -> None:
    api = ShmAPI.__new__(ShmAPI)
    api.header = None
    api.auth = None
    api.api_root = "https://example.com"
    api.endpoints = DEFAULT_SHM_ENDPOINTS

    with pytest.raises(InvalidParameterError):
        api._send_json_request(api.endpoints.sensor, {"name": "S-1"})


def test_send_detail_json_request_raises_without_auth() -> None:
    api = ShmAPI.__new__(ShmAPI)
    api.header = None
    api.auth = None
    api.api_root = "https://example.com"
    api.endpoints = DEFAULT_SHM_ENDPOINTS

    with pytest.raises(InvalidParameterError):
        api._send_detail_json_request(api.endpoints.sensor, 1, {"name": "S-1"})


def test_send_json_request_raises_on_bad_status() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(400, reason="Bad Request")

    with patch("requests.request", return_value=response), pytest.raises(APIConnectionError):
        api._send_json_request(api.endpoints.sensor, {"name": "S-1"})


def test_send_json_request_with_basic_auth() -> None:
    api = ShmAPI(uname="user", password="pass")
    response = _make_response(201, '{"id": 1}', reason="Created")

    with patch("requests.request", return_value=response) as mocker:
        api._send_json_request(api.endpoints.sensor, {"name": "S-1"})

    assert mocker.call_args.kwargs.get("auth") is not None


def test_response_to_dataframe_handles_list_and_dict_payloads() -> None:
    list_response = _make_response(200, '[{"id": 1}, {"id": 2}]')
    dict_response = _make_response(200, '{"id": 3}')

    assert list(ShmAPI._response_to_dataframe(list_response)["id"]) == [1, 2]
    assert list(ShmAPI._response_to_dataframe(dict_response)["id"]) == [3]


def test_send_multipart_request_uses_token_and_data_files() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(201, '{"id": 15}', reason="Created")

    with patch("requests.post", return_value=response) as mocker:
        result = api._send_multipart_request(
            "sensortype",
            data={"description": "Strain"},
            files={"photo": ("img.png", b"PNG", "image/png")},
        )

    assert result is response
    mocker.assert_called_once()
    call_kwargs = mocker.call_args.kwargs
    assert call_kwargs["data"] == {"description": "Strain"}
    assert call_kwargs["files"] == {"photo": ("img.png", b"PNG", "image/png")}
    assert "Authorization" in call_kwargs["headers"]
    assert "Content-Type" not in call_kwargs["headers"]


def test_send_multipart_request_uses_basic_auth() -> None:
    api = ShmAPI(uname="user", password="pass")
    response = _make_response(201, '{"id": 16}', reason="Created")

    with patch("requests.post", return_value=response) as mocker:
        api._send_multipart_request("sensortype", data={"description": "Strain"})

    assert mocker.call_args.kwargs.get("auth") is not None


def test_send_multipart_request_raises_without_auth() -> None:
    api = ShmAPI.__new__(ShmAPI)
    api.header = None
    api.auth = None
    api.api_root = "https://example.com"
    api.endpoints = DEFAULT_SHM_ENDPOINTS

    with pytest.raises(InvalidParameterError):
        api._send_multipart_request("sensortype", data={"description": "Strain"})


def test_send_multipart_request_raises_on_bad_status() -> None:
    api = ShmAPI(token="dummy")
    response = _make_response(400, reason="Bad Request")

    with patch("requests.post", return_value=response), pytest.raises(APIConnectionError):
        api._send_multipart_request("sensortype", data={"description": "Strain"})


def test_list_sensor_types_calls_process_data() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(
        ShmAPI, "process_data", return_value=(pd.DataFrame({"id": [1, 2]}), {"existance": True})
    ) as mocker:
        result = api.list_sensor_types()

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.sensor_type, {}, "list")
    assert result["exists"] is True


def test_list_sensors_calls_process_data() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(
        ShmAPI, "process_data", return_value=(pd.DataFrame({"id": [3, 4]}), {"existance": True})
    ) as mocker:
        result = api.list_sensors(sensor_type_id=1)

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.sensor, {"sensor_type_id": 1}, "list")
    assert result["exists"] is True


@pytest.mark.parametrize(
    ("method_name", "endpoint", "filters"),
    [
        ("list_sensor_calibrations", DEFAULT_SHM_ENDPOINTS.sensor_calibration, {"sensor_id": 4}),
        ("list_signals", DEFAULT_SHM_ENDPOINTS.signal, {"asset_location": 10}),
        ("list_signal_history", DEFAULT_SHM_ENDPOINTS.signal_history, {"signal_id": 1}),
        ("list_signal_calibrations", DEFAULT_SHM_ENDPOINTS.signal_calibration, {"signal_id": 1}),
        ("list_derived_signals", DEFAULT_SHM_ENDPOINTS.derived_signal, {"asset_location": 10}),
        (
            "list_derived_signal_history",
            DEFAULT_SHM_ENDPOINTS.derived_signal_history,
            {"derived_signal_id": 7},
        ),
        (
            "list_derived_signal_calibrations",
            DEFAULT_SHM_ENDPOINTS.derived_signal_calibration,
            {"derived_signal_id": 7},
        ),
    ],
)
def test_additional_list_methods_call_process_data(
    method_name: str,
    endpoint: str,
    filters: dict[str, object],
) -> None:
    api = ShmAPI(token="dummy")
    with patch.object(
        ShmAPI,
        "process_data",
        return_value=(pd.DataFrame({"id": [1, 2]}), {"existance": True}),
    ) as mocker:
        result = getattr(api, method_name)(**filters)

    mocker.assert_called_once_with(endpoint, filters, "list")
    assert result["exists"] is True


def test_create_sensor_type_json_delegates_to_mutate_resource() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(ShmAPI, "_mutate_resource", return_value={"id": 10, "exists": True}) as mocker:
        result = api.create_sensor_type({"description": "Strain"})

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.sensor_type, {"description": "Strain"})
    assert result["id"] == 10


def test_create_sensor_type_multipart_delegates_to_multipart_resource() -> None:
    api = ShmAPI(token="dummy")
    fake_files = {"photo": ("img.png", b"PNG", "image/png")}
    with patch.object(ShmAPI, "_mutate_multipart_resource", return_value={"id": 11, "exists": True}) as mocker:
        result = api.create_sensor_type({"description": "Strain"}, files=fake_files)

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.sensor_type, {"description": "Strain"}, files=fake_files)
    assert result["id"] == 11


def test_create_sensor_delegates_to_mutate_resource() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(ShmAPI, "_mutate_resource", return_value={"id": 20, "exists": True}) as mocker:
        result = api.create_sensor({"serial_number": "ACC-01", "sensor_type_id": 5})

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.sensor, {"serial_number": "ACC-01", "sensor_type_id": 5})
    assert result["id"] == 20


def test_create_sensor_calibration_json_delegates_to_mutate_resource() -> None:
    api = ShmAPI(token="dummy")
    with patch.object(ShmAPI, "_mutate_resource", return_value={"id": 30, "exists": True}) as mocker:
        result = api.create_sensor_calibration({"sensor": 20, "date": "2025-01-01"})

    mocker.assert_called_once_with(DEFAULT_SHM_ENDPOINTS.sensor_calibration, {"sensor": 20, "date": "2025-01-01"})
    assert result["id"] == 30


def test_create_sensor_calibration_multipart_delegates_to_multipart_resource() -> None:
    api = ShmAPI(token="dummy")
    fake_files = {"datasheet": ("cal.pdf", b"PDF", "application/pdf")}
    with patch.object(ShmAPI, "_mutate_multipart_resource", return_value={"id": 31, "exists": True}) as mocker:
        result = api.create_sensor_calibration({"sensor": 20, "date": "2025-01-01"}, files=fake_files)

    mocker.assert_called_once_with(
        DEFAULT_SHM_ENDPOINTS.sensor_calibration,
        {"sensor": 20, "date": "2025-01-01"},
        files=fake_files,
    )
    assert result["id"] == 31

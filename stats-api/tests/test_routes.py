from unittest.mock import patch, MagicMock
from http import HTTPStatus


@patch("stats_api.service.StatsService.get_today_page_data")
def test_today_route_success(mock_service, client):
    mock_data = MagicMock()
    mock_data.model_dump.return_value = {"some_key": "some_value"}
    mock_service.return_value = mock_data

    response = client.get("/stats/today?date=2024-03-05") # TODO check format

    assert response.status_code == HTTPStatus.OK
    assert b"some_value" in response.data


@patch("stats_api.service.StatsService.get_monthly_downloads")
def test_get_monthly_downloads_csv_success(mock_service, client):
    mock_service.return_value = "month,count\n2024-01,500"

    response = client.get(
        "/stats/get_monthly_downloads?latest_hour=2024-03-05T12:00:00" # TODO check format
    )

    assert response.status_code == HTTPStatus.OK
    assert b"month,count" in response.data


def test_handle_http_exception_400(client):
    response = client.get("/stats/get_monthly_downloads")

    assert response.status_code == 400
    assert b"Bad Request" in response.data
    assert b"400" in response.data


def test_handle_http_exception_404(client):
    response = client.get("/non-existent")

    assert response.status_code == 404
    assert b"Not Found" in response.data


@patch("stats_api.service.StatsService.get_downloads_page_data")
def test_handle_non_http_exception_500(mock_service, client):
    mock_service.side_effect = RuntimeError("Generic sensitive runtime error")

    response = client.get("/stats/monthly_downloads")
    html = response.get_data(as_text=True)

    assert response.status_code == 500
    assert b"Internal Server Error" in response.data
    assert "Generic sensitive runtime error" not in html

from datetime import date, datetime
from http import HTTPStatus
from unittest.mock import patch

from stats_api.models import TodayPageData


@patch("stats_api.service.StatsService.get_today_page_data")
def test_today_route_success(mock_service, client):
    mock_service.return_value = TodayPageData(
        arxiv_current_time=datetime.now(),
        arxiv_requested_date=date(2026, 3, 3),
        arxiv_timezone="",
        total_requests=10,
    )

    response = client.get("/stats/today?date=20260303")

    assert response.status_code == HTTPStatus.OK


@patch("stats_api.service.StatsService.get_monthly_downloads")
def test_get_monthly_downloads_csv_success(mock_service, client):
    mock_service.return_value = "month,count\n2026-03-01,500"

    response = client.get("/stats/get_monthly_downloads?latest_hour=2026030312")

    assert response.status_code == HTTPStatus.OK


def test_handle_http_exception_400(client):
    response = client.get("/stats/get_monthly_downloads")

    assert response.status_code == 400


def test_handle_http_exception_404(client):
    response = client.get("/stats/non-existent")

    assert response.status_code == 404


@patch("stats_api.service.StatsService.get_downloads_page_data")
def test_handle_non_http_exception_500(mock_service, client):
    mock_service.side_effect = RuntimeError("Generic sensitive runtime error")

    response = client.get("/stats/monthly_downloads")
    html = response.get_data(as_text=True)

    assert response.status_code == 500
    assert b"Internal Server Error" in response.data
    assert "Generic sensitive runtime error" not in html


def test_main_route_cached_long(client):
    response = client.get("/stats/main")

    assert response.headers["Surrogate-Control"].startswith("max-age=31557600,")


@patch("stats_api.service.StatsService.get_today_page_data")
def test_today_route_cache_depends_on_date(mock_service, client):
    mock_service.return_value = TodayPageData(
        arxiv_current_time=datetime.now(),
        arxiv_requested_date=date(2000, 1, 1),
        arxiv_timezone="",
        total_requests=10,
    )

    past = client.get("/stats/today?date=20000101")
    current = client.get("/stats/today")

    assert past.headers["Surrogate-Control"].startswith("max-age=31557600,")
    assert current.headers["Surrogate-Control"].startswith("max-age=3600,")


def test_error_responses_are_not_cached(client):
    response = client.get("/stats/get_monthly_downloads")

    assert response.status_code == 400
    assert "Surrogate-Control" not in response.headers


def test_static_files_cached_a_day(app, client):
    static = app.static_url_path

    response = client.get(f"{static}/css/arXiv.css")
    missing = client.get(f"{static}/css/missing.css")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["Surrogate-Control"].startswith("max-age=86400,")
    assert response.headers["Surrogate-Key"] == "stats static"
    assert missing.status_code == HTTPStatus.NOT_FOUND
    assert "Surrogate-Control" not in missing.headers


def test_static_files_are_served_under_stats(client):
    page = client.get("/stats/main").get_data(as_text=True)

    assert 'href="/stats/static/css/arXiv.css' in page
    assert 'href="/static/' not in page
    assert client.get("/stats/static/css/arXiv.css").status_code == HTTPStatus.OK
    assert client.get("/static/css/arXiv.css").status_code == HTTPStatus.NOT_FOUND

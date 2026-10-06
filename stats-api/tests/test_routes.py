import re
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


def test_monthly_downloads_csv_total_matches_page_total(client):
    page = client.get("/stats/monthly_downloads").get_data(as_text=True)
    page_total = re.search(r"Total number of downloads.*?= ([\d,]+)", page, re.DOTALL)
    latest_hour = re.search(r"latest_hour=(\d+)", page)
    assert page_total
    assert latest_hour

    csv = client.get(
        f"/stats/get_monthly_downloads?latest_hour={latest_hour.group(1)}"
    ).get_data(as_text=True)
    csv_total = sum(int(row.split(",")[1]) for row in csv.splitlines()[1:])

    assert csv_total == int(page_total.group(1).replace(",", ""))

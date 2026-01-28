from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from flask import Response

from stats_api.utils import (
    url_param_to_date,
    url_param_to_arxiv_datetime,
    set_fastly_headers,
    get_utc_start_and_end_times,
    format_as_csv,
    utc_to_arxiv_local,
)
from stats_api.models import HourlyRequests_


def test_url_param_to_date(app):
    result = url_param_to_date("20251001")

    assert result == date(2025, 10, 1)


def test_url_param_to_arxiv_datetime(app):
    with app.app_context():
        app.config["ARXIV_TIMEZONE"] = "America/New_York"

        result = url_param_to_arxiv_datetime("2024121215")

        assert result == datetime(2024, 12, 12, 15, tzinfo=ZoneInfo("America/New_York"))


def test_set_fastly_headers_with_keys(app):
    with app.app_context():

        @set_fastly_headers(keys=["first-mock-key", "second-mock-key"])
        def mock_function():
            return Response()

        result = mock_function()

        assert result.headers["Surrogate-Key"] == "first-mock-key second-mock-key"


def test_get_utc_start_and_end_times_est(app):
    with app.app_context():
        start, end = get_utc_start_and_end_times(date(2025, 11, 11))

        assert start == datetime(2025, 11, 11, 5, tzinfo=timezone.utc)
        assert end == datetime(2025, 11, 12, 4, tzinfo=timezone.utc)


def test_get_utc_start_and_end_times_edt(app):
    with app.app_context():
        start, end = get_utc_start_and_end_times(date(2025, 4, 1))

        assert start == datetime(2025, 4, 1, 4, tzinfo=timezone.utc)
        assert end == datetime(2025, 4, 2, 3, tzinfo=timezone.utc)


def test_format_as_csv():
    mock_models = [
        HourlyRequests_(start_dttm=datetime(2025, 10, 10, 0), request_count=3000000),
        HourlyRequests_(start_dttm=datetime(2025, 10, 10, 1), request_count=4000000),
    ]

    result = format_as_csv(mock_models)

    assert (
        result
        == "hour,requests\r\n2025-10-10 00:00:00,3000000\r\n2025-10-10 01:00:00,4000000\r\n"
    )


def test_utc_to_arxiv_local(app):
    with app.app_context():
        app.config["ARXIV_TIMEZONE"] = "America/New_York"
        mock_datetime = datetime(2025, 10, 1, 14)

        result = utc_to_arxiv_local(mock_datetime)

        assert result == datetime(2025, 10, 1, 10, tzinfo=ZoneInfo("America/New_York"))

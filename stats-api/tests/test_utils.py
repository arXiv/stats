from datetime import UTC, date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from flask import Response

from stats_api.models import HourlyRequests_
from stats_api.utils import (
    HOUR,
    format_as_csv,
    get_utc_start_and_end_times,
    max_age_for_requested_date,
    set_fastly_headers,
    url_param_to_arxiv_datetime,
    url_param_to_date,
    utc_to_arxiv_local,
)


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

        assert start == datetime(2025, 11, 11, 5, tzinfo=UTC)
        assert end == datetime(2025, 11, 12, 4, tzinfo=UTC)


def test_get_utc_start_and_end_times_edt(app):
    with app.app_context():
        start, end = get_utc_start_and_end_times(date(2025, 4, 1))

        assert start == datetime(2025, 4, 1, 4, tzinfo=UTC)
        assert end == datetime(2025, 4, 2, 3, tzinfo=UTC)


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


@pytest.mark.parametrize(
    ("max_age", "expected"),
    [(None, 31557600), (3600, 3600), (lambda: 60, 60)],
)
def test_set_fastly_headers_max_age(app, max_age, expected):
    with app.app_context():

        @set_fastly_headers(max_age=max_age)
        def mock_function():
            return Response()

        result = mock_function()

        assert result.headers["Surrogate-Control"] == (
            f"max-age={expected}, stale-while-revalidate=60, stale-if-error=86400"
        )


@pytest.mark.parametrize(
    ("now", "query", "expected"),
    [
        # yesterday is complete once its last hour has been aggregated
        (datetime(2025, 11, 11, 4), "?date=20251110", 31557600),
        (datetime(2025, 11, 11, 1), "?date=20251110", HOUR),
        (datetime(2025, 11, 11, 12), "?date=20251111", HOUR),
        (datetime(2025, 11, 11, 12), "?date=20251112", HOUR),
        (datetime(2025, 11, 11, 12), "", HOUR),
        (datetime(2025, 11, 11, 12), "?date=not-a-date", HOUR),
    ],
)
def test_max_age_for_requested_date(app, now, query, expected):
    now = now.replace(tzinfo=ZoneInfo("America/New_York"))

    with (
        app.test_request_context(f"/stats/today{query}"),
        patch("stats_api.utils.get_arxiv_current_time", return_value=now),
    ):
        assert max_age_for_requested_date() == expected

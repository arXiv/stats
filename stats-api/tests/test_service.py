from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from werkzeug.exceptions import ServiceUnavailable

from stats_api.models import HourlyRequests_, MonthlyDownloads_
from stats_api.service import StatsService


@patch("stats_api.service.SiteUsageRepository")
def test_get_submissions_page_data(MockSiteUsageRepository, app):
    with app.app_context():
        MockSiteUsageRepository.get_total_submissions.return_value = 2000000

        result = StatsService.get_submissions_page_data(date(2025, 11, 11))

        assert result.arxiv_age_in_years == 34
        assert result.total_submissions == 1999844
        assert result.total_submissions_adjusted == 2002275


@patch("stats_api.service.SiteUsageRepository")
def test_get_downloads_page_data_same_day(MockSiteUsageRepository, app):
    with app.app_context():
        MockSiteUsageRepository.get_latest_hour_for_downloads.return_value = datetime(
            2025, 11, 10, 15
        )

        result = StatsService.get_downloads_page_data()

        assert result.arxiv_latest_month == date(2025, 11, 1)


@patch("stats_api.service.SiteUsageRepository")
def test_get_downloads_page_data_crossover(MockSiteUsageRepository, app):
    with app.app_context():
        MockSiteUsageRepository.get_latest_hour_for_downloads.return_value = datetime(
            2025, 11, 1, 3
        )

        result = StatsService.get_downloads_page_data()

        assert result.arxiv_latest_month == date(2025, 10, 1)


@patch("stats_api.service.SiteUsageRepository")
def test_combine_monthly_downloads(MockSiteUsageRepository, app):
    mock_total_downloads = 20000

    mock_monthly_downloads = [
        MonthlyDownloads_(month=date(2025, 10, 1), downloads=10000),
        MonthlyDownloads_(month=date(2025, 11, 1), downloads=15000),
    ]

    with app.app_context():
        MockSiteUsageRepository.get_total_downloads_for_hour_range.return_value = (
            mock_total_downloads
        )
        MockSiteUsageRepository.get_monthly_downloads.return_value = (
            mock_monthly_downloads
        )

        result = StatsService._combine_monthly_downloads(
            datetime(2025, 12, 1, 12), mock_total_downloads, mock_monthly_downloads
        )

        assert result == [
            MonthlyDownloads_(month=date(2025, 10, 1), downloads=10000),
            MonthlyDownloads_(month=date(2025, 11, 1), downloads=15000),
            MonthlyDownloads_(month=date(2025, 12, 1), downloads=20000),
        ]


@patch("stats_api.service.SiteUsageRepository")
def test_get_monthly_downloads_uses_utc_month(MockSiteUsageRepository, app):
    with app.app_context():
        MockSiteUsageRepository.get_total_downloads_for_hour_range.return_value = 7
        MockSiteUsageRepository.get_monthly_downloads.return_value = []

        # 2025-12-01 03:00 utc, still november in arxiv local time
        result = StatsService.get_monthly_downloads(
            datetime(2025, 11, 30, 22, tzinfo=ZoneInfo("America/New_York"))
        )

        MockSiteUsageRepository.get_total_downloads_for_hour_range.assert_called_once_with(
            datetime(2025, 12, 1), datetime(2025, 12, 1, 3)
        )
        MockSiteUsageRepository.get_monthly_downloads.assert_called_once_with(
            date(2025, 12, 1)
        )
        assert result == "month,downloads\r\n2025-12-01,7\r\n"


@patch("stats_api.service.SiteUsageRepository")
def test_get_downloads_page_data_no_data(MockSiteUsageRepository, app):
    with app.app_context():
        MockSiteUsageRepository.get_latest_hour_for_downloads.return_value = None

        with pytest.raises(ServiceUnavailable):
            StatsService.get_downloads_page_data()


@patch("stats_api.service.SiteUsageRepository")
def test_get_hourly_requests_csv_hours_are_arxiv_local(MockSiteUsageRepository, app):
    """today_js.html labels each bar with characters 11-12 of the hour, as written"""
    with app.app_context():
        # 2025-11-02 is the end of dst; 01:00 happens twice in arxiv local time
        MockSiteUsageRepository.get_hourly_requests.return_value = [
            HourlyRequests_(start_dttm=datetime(2025, 11, 2, 5), request_count=1),
            HourlyRequests_(start_dttm=datetime(2025, 11, 2, 6), request_count=2),
        ]

        result = StatsService.get_hourly_requests(date(2025, 11, 2))

        assert result.splitlines() == [
            "hour,requests",
            "2025-11-02 01:00:00-04:00,1",
            "2025-11-02 01:00:00-05:00,2",
        ]

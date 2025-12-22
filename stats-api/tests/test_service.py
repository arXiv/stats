from unittest.mock import patch
from datetime import date, datetime, timezone

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

from datetime import date, datetime, timezone

from stats_api.repository import SiteUsageRepository


def test_get_total_requests(app):
    with app.app_context():
        start = datetime(2025, 11, 10, 10, tzinfo=timezone.utc)
        end = datetime(2025, 11, 12, 0, tzinfo=timezone.utc)

        result = SiteUsageRepository.get_total_requests(start, end)

        assert result == 14700000


def test_get_hourly_requests(app):
    with app.app_context():
        start = datetime(2025, 11, 10, 10, tzinfo=timezone.utc)
        end = datetime(2025, 11, 11, 4, tzinfo=timezone.utc)

        result = SiteUsageRepository.get_hourly_requests(start, end)

        assert len(result) == 3


def test_get_total_submissions(app):
    with app.app_context():
        result = SiteUsageRepository.get_total_submissions(date(2025, 1, 1))

        assert result == 42000


def test_get_monthly_submissions(app):
    with app.app_context():
        result = SiteUsageRepository.get_monthly_submissions()

        assert len(result) == 3


def test_get_latest_hour_for_downloads(app):
    with app.app_context():
        result = SiteUsageRepository.get_latest_hour_for_downloads()

        assert result == datetime(2025, 12, 2, 6)


def test_get_total_downloads_for_hour_range(app):
    with app.app_context():
        result = SiteUsageRepository.get_total_downloads_for_hour_range(
            datetime(2025, 12, 1), datetime(2025, 12, 1, 14)
        )

        assert result == 5


def test_get_total_downloads(app):
    with app.app_context():
        result = SiteUsageRepository.get_total_downloads(date(2025, 11, 1))

        assert result == 2500000


def test_get_monthly_downloads(app):
    with app.app_context():
        result = SiteUsageRepository.get_monthly_downloads(date(2025, 12, 1))

        assert len(result) == 2

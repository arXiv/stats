import pytest
from stats_api.app import create_app
from tests.data.site_usage import (
    mock_hourly_requests,
    mock_monthly_submissions,
    mock_hourly_downloads,
    mock_monthly_downloads,
)


@pytest.fixture(scope="module")
def app():
    app = create_app("TEST")
    with app.app_context():
        from stats_api.config.database import db

        db.create_all()
        db.session.add_all(
            mock_hourly_requests
            + mock_monthly_submissions
            + mock_hourly_downloads
            + mock_monthly_downloads
        )
        db.session.commit()

    yield app


@pytest.fixture(scope="module")
def client(app):
    yield app.test_client()

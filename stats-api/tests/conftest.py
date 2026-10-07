from typing import Any

import pytest

from stats_api.app import create_app
from stats_api.config.app import Config, Database
from tests.data.site_usage import (
    mock_hourly_downloads,
    mock_hourly_requests,
    mock_monthly_downloads,
    mock_monthly_submissions,
)


def make_test_config(**overrides: Any) -> Config:
    """ignores .env"""
    values: dict[str, Any] = {
        "SERVER_NAME": "arxiv.org",
        "BASE_SERVER": "arxiv.org",
        "AUTH_SERVER": "arxiv.org",
        "HELP_SERVER": "info.arxiv.org",
        "DB": Database(drivername="sqlite", database=":memory:"),
    }
    return Config(_env_file=None, **(values | overrides))


@pytest.fixture(scope="module")
def app():
    app = create_app(make_test_config())
    assert (
        app.config["SQLALCHEMY_DATABASE_URI"].render_as_string() == "sqlite:///:memory:"
    )

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

import os
import sys
import pytest

os.environ["ENV"] = "TEST"

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch
from datetime import datetime, timezone, date

from cloudevents.http import CloudEvent

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import (
    get_download_count,
    write_to_db,
    validate_cloud_event,
    validate_month,
    validate_inputs,
)
from stats_entities.site_usage import SiteUsageBase, HourlyDownloads, MonthlyDownloads
from stats_functions.exception import NoRetryError


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    SiteUsageBase.metadata.create_all(engine)

    SessionFactory = sessionmaker(bind=engine)

    with SessionFactory() as session:
        session.add_all(
            [
                HourlyDownloads(
                    start_dttm=datetime(2025, 11, 2, 10),
                    category="",
                    country="",
                    download_type="",
                    archive="",
                    primary_count=1000,
                    cross_count=1,
                ),
                HourlyDownloads(
                    start_dttm=datetime(2025, 11, 3, 12),
                    category="",
                    country="",
                    download_type="",
                    archive="",
                    primary_count=500,
                    cross_count=1,
                ),
                HourlyDownloads(
                    start_dttm=datetime(2025, 11, 4, 9),
                    category="",
                    country="",
                    download_type="",
                    archive="",
                    primary_count=1500,
                    cross_count=1,
                ),
            ]
        )
        session.add_all([MonthlyDownloads(month=date(2025, 11, 1), downloads=10000)])
        session.commit()

    return SessionFactory


def test_get_download_count_success(session_factory):
    with patch("main.SessionFactory", session_factory):
        count = get_download_count(datetime(2025, 11, 1), datetime(2025, 11, 30, 23))

    assert count == 3000


def test_validate_month_valid():
    result = validate_month("2025-11-01")

    assert result == date(2025, 11, 1)


def test_validate_month_invalid():
    with pytest.raises(ValueError):
        validate_month("2025-13-01")


@patch("main.parse_cloud_event_time")
@patch("main.event_time_exceeds_retry_window")
def test_validate_cloud_event(mock_retry_check, mock_parse_time):
    mock_parse_time.return_value = datetime(2025, 9, 12, 16, 30, tzinfo=timezone.utc)
    mock_retry_check.return_value = False
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-11-01T12:00:00Z",
    }
    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    result = validate_cloud_event(mock_cloud_event)

    assert result == date(2025, 8, 1)


@patch("main.parse_cloud_event_time")
@patch("main.event_time_exceeds_retry_window")
def test_validate_cloud_event_january(mock_retry_check, mock_parse_time):
    mock_parse_time.return_value = datetime(2026, 1, 2, 16, 30, tzinfo=timezone.utc)
    mock_retry_check.return_value = False
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-11-01T12:00:00Z",
    }
    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    result = validate_cloud_event(mock_cloud_event)

    assert result == date(2025, 12, 1)


@patch("main.parse_cloud_event_time")
@patch("main.event_time_exceeds_retry_window")
def test_validate_cloud_event_retry_exceeded(mock_retry_check, mock_parse_time):
    mock_retry_check.return_value = True
    mock_parse_time.return_value = datetime.now(timezone.utc)

    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-11-01T12:00:00Z",
    }
    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    with pytest.raises(NoRetryError):
        validate_cloud_event(mock_cloud_event)


def test_validate_inputs_from_attributes():
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-11-01T12:00:00Z",
        "month": "2025-10-1"
    }
    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    result = validate_inputs(mock_cloud_event)

    assert result == date(2025, 10, 1)


@patch("main.validate_cloud_event")
def test_validate_inputs_fallback_to_event_time(mock_val_cloud):
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-11-01T12:00:00Z",
    }    
    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})
    mock_val_cloud.return_value = date(2025, 8, 1)

    result = validate_inputs(mock_cloud_event)

    assert result == date(2025, 8, 1)
    mock_val_cloud.assert_called_once()


def test_write_to_db_success(session_factory):
    mock_month = date(2025, 11, 1)
    mock_count = 25000

    with patch("main.SessionFactory", session_factory):
        write_to_db(mock_month, mock_count)

    with session_factory() as session:
        results = session.query(MonthlyDownloads).filter_by(month=mock_month).all()

        assert len(results) == 1
        assert results[0].downloads == mock_count

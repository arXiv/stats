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
    get_submission_count,
    write_to_db,
    validate_cloud_event,
    validate_month,
    validate_inputs,
)
from entities import ReadBase, Document
from stats_entities.site_usage import SiteUsageBase, MonthlySubmissions
from stats_functions.exception import NoRetryError


@pytest.fixture
def read_session_factory():
    engine = create_engine("sqlite:///:memory:")
    ReadBase.metadata.create_all(engine)

    ReadSessionFactory = sessionmaker(bind=engine)

    with ReadSessionFactory() as session:
        session.add_all(
            [
                Document(
                    document_id=1,
                    paper_id="2510.00001",
                    title="title1",
                    submitter_email="",
                    dated=1,
                ),
                Document(
                    document_id=2,
                    paper_id="2510.00002",
                    title="title2",
                    submitter_email="",
                    dated=2,
                ),
                Document(
                    document_id=3,
                    paper_id="2511.00003",
                    title="title3",
                    submitter_email="",
                    dated=3,
                ),
            ]
        )

        session.commit()

    yield ReadSessionFactory

    engine.dispose()


@pytest.fixture
def write_session_factory():
    engine = create_engine("sqlite:///:memory:")
    SiteUsageBase.metadata.create_all(engine)

    yield sessionmaker(bind=engine)

    engine.dispose()


def test_get_submission_count_success(read_session_factory):
    with patch("main.ReadSessionFactory", read_session_factory):
        count = get_submission_count(date(2025, 11, 1))

    assert count == 1


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
    }

    mock_data = {"message": {"data": "", "attributes": {"month": "2025-10-1"}}}

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data=mock_data)

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


def test_write_to_db_success(write_session_factory):
    mock_month = date(2025, 11, 1)
    mock_count = 2

    with patch("main.WriteSessionFactory", write_session_factory):
        write_to_db(mock_month, mock_count)

    with write_session_factory() as session:
        results = session.query(MonthlySubmissions).filter_by(month=mock_month).all()

        assert len(results) == 1
        assert results[0].count == mock_count


def test_validate_month_valid():
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }
    mock_data = {"message": {"data": "", "attributes": {"month": "2025-11-01"}}}

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data=mock_data)

    result = validate_month(mock_cloud_event)

    assert result == date(2025, 11, 1)


def test_validate_month_invalid():
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }
    mock_data = {"message": {"data": "", "attributes": {"month": "2025-13-01"}}}

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data=mock_data)

    with pytest.raises(ValueError):
        validate_month(mock_cloud_event)

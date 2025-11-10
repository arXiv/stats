import os
import sys
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, date
from cloudevents.http import CloudEvent

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import MonthlySubmissionsJob, NoRetryError
from entities import ReadBase, Document


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    ReadBase.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    with Session() as session:
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

    return engine


def test_get_submission_count_success(db_session):
    mock_job_instance = MagicMock(autospec=MonthlySubmissionsJob)
    mock_job_instance.instantiate_connection_pool.return_value = (None, db_session)
    mock_month = date(2025, 11, 1)

    count = MonthlySubmissionsJob.get_submission_count(mock_job_instance, mock_month)

    assert count == 1


def test_validate_cloud_event():
    mock_job_instance = MagicMock(autospec=MonthlySubmissionsJob)
    mock_job_instance.hour_delay = 1
    mock_job_instance._event_time_exceeds_retry_window.return_value = False

    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    result = MonthlySubmissionsJob._validate_cloud_event(
        mock_job_instance, cloud_event=mock_cloud_event
    )

    assert result == date(2025, 8, 1)


@patch("main.datetime")
def test_event_time_exceeds_retry_window_true(mock_datetime_method):
    mock_datetime_method.now.return_value = datetime(
        2025, 10, 15, 10, 30, 0, tzinfo=timezone.utc
    )
    mock_event_time = datetime(2025, 10, 15, 9, 39, 0, tzinfo=timezone.utc)

    mock_job_instance = MagicMock(autospec=MonthlySubmissionsJob)
    mock_job_instance.MAX_EVENT_AGE_IN_MINUTES = 50

    result = MonthlySubmissionsJob._event_time_exceeds_retry_window(
        mock_job_instance, mock_event_time
    )

    assert result


@patch("main.datetime")
def test_event_time_exceeds_retry_window_false(mock_datetime_method):
    mock_datetime_method.now.return_value = datetime(
        2025, 10, 15, 10, 30, 0, tzinfo=timezone.utc
    )
    mock_event_time = datetime(2025, 10, 15, 9, 41, 0, tzinfo=timezone.utc)

    mock_job_instance = MagicMock(autospec=MonthlySubmissionsJob)
    mock_job_instance.MAX_EVENT_AGE_IN_MINUTES = 50

    result = MonthlySubmissionsJob._event_time_exceeds_retry_window(
        mock_job_instance, mock_event_time
    )

    assert not result


def test_validate_month_valid():
    mock_job_instance = MagicMock(autospec=MonthlySubmissionsJob)

    mock_input_month_valid = "2025-11"

    result = MonthlySubmissionsJob._validate_month(
        mock_job_instance, mock_input_month_valid
    )

    assert result == date(2025, 11, 1)


def test_validate_month_invalid():
    mock_job_instance = MagicMock(autospec=MonthlySubmissionsJob)

    mock_input_month_invalid = "2025-15"

    with pytest.raises(NoRetryError):
        MonthlySubmissionsJob._validate_month(
            mock_job_instance, mock_input_month_invalid
        )

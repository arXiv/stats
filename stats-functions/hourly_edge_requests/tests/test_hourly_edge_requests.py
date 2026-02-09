import os
import sys
import pytest

os.environ["ENV"] = "TEST"

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch
from datetime import datetime, timezone
from cloudevents.http import CloudEvent

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastly.model.stats import Stats
from fastly.model.results import Results

from models import FastlyStatsApiResponse
from main import (
    get_timestamps,
    get_fastly_stats,
    sum_requests,
    write_to_db,
    validate_cloud_event,
    validate_hour,
    validate_inputs,
)

from stats_functions.exception import NoRetryError
from stats_entities.site_usage import SiteUsageBase, HourlyRequests


mock_fastly_response_valid = Stats(
    **{
        "stats": {
            "ACC": Results(
                **{
                    "edge_requests": 31,
                    "extra_field": 54602588,
                    "another_extra_field": 18272,
                }
            ),
            "AMS": Results(
                **{
                    "edge_requests": 31,
                    "extra_field": 54602588,
                }
            ),
        }
    }
)

mock_fastly_response_missing_edge_requests = Stats(
    **{
        "ACC": Results(
            **{
                "edge_requests": 31,
                "extra_field": 54602588,
                "another_extra_field": 18272,
            }
        ),
        "AMS": Results(
            **{
                "extra_field": 54602588,
            }
        ),
    }
)


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    SiteUsageBase.metadata.create_all(engine)

    yield sessionmaker(bind=engine)

    engine.dispose()


def test_get_timestamps():
    mock_hour = datetime(2025, 11, 4, 12, 0, 0, 0, tzinfo=timezone.utc)

    start_time, end_time = get_timestamps(mock_hour)

    assert start_time == 1762257600
    assert end_time == 1762261199


@patch("main.stats_api")
@patch("main.fastly")
def test_get_fastly_stats_valid_response(mock_fastly, mock_fastly_stats_api):
    mock_fastly_stats_api.StatsApi.return_value.get_service_stats.return_value = (
        mock_fastly_response_valid
    )

    result = get_fastly_stats(1762257600, 1762261199)

    mock_fastly_stats_api.StatsApi.return_value.get_service_stats.assert_called_once()
    assert isinstance(result, FastlyStatsApiResponse)


@patch("main.stats_api")
@patch("main.fastly")
def test_get_fastly_stats_missing_edge_requests(mock_fastly, mock_fastly_stats_api):
    mock_fastly_stats_api.StatsApi.return_value.get_service_stats.return_value = (
        mock_fastly_response_missing_edge_requests
    )

    with pytest.raises(NoRetryError):
        get_fastly_stats(1762257600, 1762261199)


def test_sum_requests():
    result = sum_requests(
        FastlyStatsApiResponse(**mock_fastly_response_valid.to_dict()),
    )

    assert result == 62


def test_write_to_db_success(session_factory):
    mock_start_dttm = datetime(2025, 11, 4, 14)
    mock_request_count = 10000

    with patch("main.SessionFactory", session_factory):
        write_to_db(mock_start_dttm, mock_request_count)

    with session_factory() as session:
        results = (
            session.query(HourlyRequests).filter_by(start_dttm=mock_start_dttm).all()
        )

        assert len(results) == 1
        assert results[0].request_count == mock_request_count


@patch("main.event_time_exceeds_retry_window")
@patch("main.config")
def test_validate_cloud_event(mock_config, mock_retry_check):
    mock_config.hour_delay = 1
    mock_retry_check.return_value = False

    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    result = validate_cloud_event(mock_cloud_event)

    assert result == datetime(2025, 9, 12, 15, 0, tzinfo=timezone.utc)


def test_validate_hour_valid():
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }
    mock_data = {"message": {"data": "", "attributes": {"hour": "2025-11-0412"}}}

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data=mock_data)

    result = validate_hour(mock_cloud_event)

    assert result == datetime(2025, 11, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_validate_hour_invalid():
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }
    mock_data = {"message": {"data": "", "attributes": {"hour": "2025-11-0425"}}}

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data=mock_data)

    with pytest.raises(ValueError):
        validate_hour(mock_cloud_event)


def test_validate_inputs_from_attributes():
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-11-01T12:00:00Z",
    }

    mock_data = {"message": {"data": "", "attributes": {"hour": "2025-10-0312"}}}

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data=mock_data)

    result = validate_inputs(mock_cloud_event)

    assert result == datetime(2025, 10, 3, 12, tzinfo=timezone.utc)


@patch("main.validate_cloud_event")
def test_validate_inputs_fallback_to_event_time(mock_val_cloud):
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-08-01T12:00:00Z",
    }
    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})
    mock_val_cloud.return_value = datetime(2025, 8, 1, 11)

    result = validate_inputs(mock_cloud_event)

    assert result == datetime(2025, 8, 1, 11)
    mock_val_cloud.assert_called_once()

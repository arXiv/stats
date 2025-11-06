import os
import sys
import pytest


sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from cloudevents.http import CloudEvent

from fastly.model.stats import Stats
from fastly.model.results import Results
from models import FastlyStatsApiResponse
from main import HourlyEdgeRequestsJob, NoRetryError


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


def test_get_timestamps():
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)

    mock_hour = datetime(2025, 11, 4, 12)

    start_time, end_time = HourlyEdgeRequestsJob._get_timestamps(
        mock_job_instance, mock_hour
    )

    assert start_time == 1762275600
    assert end_time == 1762279199


@patch("main.stats_api")
@patch("main.fastly")
def test_get_fastly_stats_valid_response(mock_fastly, mock_fastly_stats_api):
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance._get_timestamps.return_value = (1762275600, 1762279199)

    mock_fastly_stats_api.StatsApi.return_value.get_service_stats.return_value = (
        mock_fastly_response_valid
    )

    result = HourlyEdgeRequestsJob.get_fastly_stats(mock_job_instance, "")

    mock_fastly_stats_api.StatsApi.return_value.get_service_stats.assert_called_once()
    assert isinstance(result, FastlyStatsApiResponse)


@patch("main.stats_api")
@patch("main.fastly")
def test_get_fastly_stats_missing_edge_requests(mock_fastly, mock_fastly_stats_api):
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
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance._get_timestamps.return_value = (1762275600, 1762279199)

    mock_fastly_stats_api.StatsApi.return_value.get_service_stats.return_value = (
        mock_fastly_response_missing_edge_requests
    )

    with pytest.raises(NoRetryError):
        HourlyEdgeRequestsJob.get_fastly_stats(mock_job_instance, "")


def test_sum_requests():
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)

    result = HourlyEdgeRequestsJob.sum_requests(
        mock_job_instance,
        FastlyStatsApiResponse(**mock_fastly_response_valid.to_dict()),
    )

    assert result == 62


def test_validate_cloud_event():
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance.hour_delay = 1
    mock_job_instance._event_time_exceeds_retry_window.return_value = False

    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    result = HourlyEdgeRequestsJob._validate_cloud_event(
        mock_job_instance, cloud_event=mock_cloud_event
    )

    assert result == datetime(2025, 9, 12, 15, 30, 0, tzinfo=timezone.utc)


@patch("main.datetime")
def test_event_time_exceeds_retry_window_true(mock_datetime_method):
    """ """
    mock_datetime_method.now.return_value = datetime(
        2025, 10, 15, 10, 30, 0, tzinfo=timezone.utc
    )
    mock_event_time = datetime(2025, 10, 15, 9, 39, 0, tzinfo=timezone.utc)

    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance.MAX_EVENT_AGE_IN_MINUTES = 50

    result = HourlyEdgeRequestsJob._event_time_exceeds_retry_window(
        mock_job_instance, mock_event_time
    )

    assert result == True


@patch("main.datetime")
def test_event_time_exceeds_retry_window_false(mock_datetime_method):
    """ """
    mock_datetime_method.now.return_value = datetime(
        2025, 10, 15, 10, 30, 0, tzinfo=timezone.utc
    )
    mock_event_time = datetime(2025, 10, 15, 9, 41, 0, tzinfo=timezone.utc)

    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance.MAX_EVENT_AGE_IN_MINUTES = 50

    result = HourlyEdgeRequestsJob._event_time_exceeds_retry_window(
        mock_job_instance, mock_event_time
    )

    assert not result


def test_validate_date_valid():
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)

    mock_input_hour_valid = "2025-11-0412"

    result = HourlyEdgeRequestsJob._validate_date(
        mock_job_instance, mock_input_hour_valid
    )

    assert result == datetime(2025, 11, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_validate_date_invalid():
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)

    mock_input_hour_invalid = "2025-11-0425"

    with pytest.raises(NoRetryError):
        HourlyEdgeRequestsJob._validate_date(mock_job_instance, mock_input_hour_invalid)

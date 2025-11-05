import os
import sys
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch, MagicMock
from cloudevents.http import CloudEvent
from fastly.model.stats import Stats
from datetime import datetime

from main import HourlyEdgeRequestsJob

mock_fastly_response_valid = Stats(
    **{
        "ACC": {
            "edge_requests": 31,
            "extra_field": 54602588,
            "another_extra_field": 18272,
        },
        "AMS": {
            "edge_requests": 31,
            "extra_field": 54602588,
        },
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


def test_get_fastly_stats_valid_response():
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance.fastly_api_client = MagicMock()
    mock_job_instance.fastly_api_client.return_value = mock_fastly_response_valid

    result = HourlyEdgeRequestsJob.get_fastly_stats(mock_job_instance, "")

    assert result


def test_get_fastly_stats_missing_edge_requests():
    mock_fastly_response_missing_edge_requests = Stats(
        **{
            "stats": {
                "ACC": {
                    "edge_requests": 31,
                    "extra_field": 54602588,
                    "another_extra_field": 18272,
                },
                "AMS": {
                    "extra_field": 54602588,
                },
            }
        }
    )
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance.fastly_api_client = MagicMock()
    mock_job_instance.fastly_api_client.return_value = (
        mock_fastly_response_missing_edge_requests
    )

    result = HourlyEdgeRequestsJob.get_fastly_stats(mock_job_instance, "")

    # assert ValidationError


def test_get_fastly_stats_invalid_pop():
    mock_fastly_response_invalid_pop = Stats(
        **{
            "stats": {
                "BLU": {
                    "edge_requests": 31,
                    "extra_field": 54602588,
                    "another_extra_field": 18272,
                },
            }
        }
    )
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)
    mock_job_instance.fastly_api_client = MagicMock()
    mock_job_instance.fastly_api_client.return_value = mock_fastly_response_invalid_pop

    result = HourlyEdgeRequestsJob.get_fastly_stats(mock_job_instance, "")

    # assert ValidationError


def test_sum_requests():
    mock_job_instance = MagicMock(autospec=HourlyEdgeRequestsJob)

    result = HourlyEdgeRequestsJob.sum_requests(
        mock_job_instance, mock_fastly_response_valid
    )

    assert result == 61


def test_validate_cloud_event():
    pass


def test_validate_inputs_valid():
    mock_input_hour_valid = "2025-11-0412"
    pass


def test_validate_inputs_invalid():
    mock_input_hour_invalid = "2025-11-0425"
    pass

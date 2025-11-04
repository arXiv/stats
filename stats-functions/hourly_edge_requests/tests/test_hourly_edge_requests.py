import os
import sys
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch, MagicMock
from cloudevents.http import CloudEvent

from main import HourlyEdgeRequestsJob, NoRetryError
from models import FastlyStatsResponse


mock_fastly_response_valid = {
    "stats": {
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
}


def test_get_timestamps():
    mock_hour = ""


def test_get_fastly_stats_valid_response():
    pass


def test_get_fastly_stats_missing_edge_requests():
    mock_fastly_response_missing_edge_requests = {
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


def test_get_fastly_stats_invalid_pop():
    mock_fastly_response_invalid_pop = {
        "stats": {
            "BLU": {
                "edge_requests": 31,
                "extra_field": 54602588,
                "another_extra_field": 18272,
            },
        }
    }


def test_sum_requests():
    mock_response_model = FastlyStatsResponse(**mock_fastly_response_valid)


def test_validate_cloud_event():
    pass


def test_validate_inputs_valid():
    mock_input_hour_valid = "2025-11-0412"


def test_validate_inputs_invalid():
    mock_input_hour_invalid = "2025-11-0425"

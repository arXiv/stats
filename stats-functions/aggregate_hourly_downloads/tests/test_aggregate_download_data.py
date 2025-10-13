import os
import sys
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from cloudevents.http import CloudEvent
from arxiv.taxonomy.definitions import CATEGORIES

from main import (
    PaperCategories,
    DownloadData,
    DownloadKey,
    DownloadCounts,
    AggregateHourlyDownloadsJob,
    NoRetryError,
)


def test_process_cats_basic():
    """
    Assert AggregateHourlyDownloadsJob.process_paper_categories works as expected
    """
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    data = [
        ("1234.5678", "math.GM", 1),
        ("1234.5679", "hep-lat", 1),
        ("1234.5679", "q-fin.CP", 0),
        ("1234.5679", "q-fin.PM", 0),
    ]

    result = AggregateHourlyDownloadsJob.process_paper_categories(
        mock_job_instance, data
    )

    expected1 = PaperCategories("1234.5678")
    expected1.add_primary("math.GM")
    expected2 = PaperCategories("1234.5679")
    expected2.add_primary("hep-lat")
    expected2.add_cross("q-fin.CP")
    expected2.add_cross("q-fin.PM")
    expected = {
        "1234.5678": expected1,
        "1234.5679": expected2,
    }
    assert result == expected


def test_paper_categories_basic():
    """
    Assert PaperCategories works as expected
    """

    # initial creation
    item = PaperCategories("1234.5678")
    assert item.paper_id == "1234.5678"
    assert item.primary is None
    assert item.crosses == set()

    # add a crosslist
    item.add_cross("hep-lat")
    assert item.paper_id == "1234.5678"
    assert item.primary is None
    assert item.crosses == {CATEGORIES["hep-lat"]}

    # add a primary listing
    item.add_primary("physics.ins-det")
    assert item.paper_id == "1234.5678"
    assert item.primary == CATEGORIES["physics.ins-det"]
    assert item.crosses == {CATEGORIES["hep-lat"]}

    # add another crosslist
    item.add_cross("q-bio.PE")
    assert item.paper_id == "1234.5678"
    assert item.primary == CATEGORIES["physics.ins-det"]
    assert item.crosses == {CATEGORIES["hep-lat"], CATEGORIES["q-bio.PE"]}


def test_paper_categories_subsumed():
    """
    Assert that only the canonical archive is used in the case where a subsumed name is present
    Subsumed = a deprecated archive name, replaced by a name that is now a subcategory of an archive
    """

    # converts to canon correctly
    item = PaperCategories("1234.5678")
    item.add_cross("chao-dyn")
    assert item.paper_id == "1234.5678"
    assert item.primary is None
    assert item.crosses == {CATEGORIES["nlin.CD"]}

    # doesn't duplicate cross
    item.add_cross("chao-dyn")
    assert item.primary is None
    assert item.crosses == {CATEGORIES["nlin.CD"]}

    # doesn't duplicate even if alt name is used
    item.add_cross("nlin.CD")
    assert item.primary is None
    assert item.crosses == {CATEGORIES["nlin.CD"]}

    # adding as primary uses canonical name and removes duplicate entry in cross
    item.add_primary("chao-dyn")
    assert item.primary == CATEGORIES["nlin.CD"]
    assert item.crosses == set()

    # can't add a matching crosslist
    item.add_cross("nlin.CD")
    assert item.primary == CATEGORIES["nlin.CD"]
    assert item.crosses == set()

    # can add alternately named crosslist
    item.add_cross("chao-dyn")
    assert item.primary == CATEGORIES["nlin.CD"]
    assert item.crosses == set()


def test_paper_categories_alias():
    """
    Assert that only the canonical archive is used in the case where a category alias is present
    Alias = a name that allows a category to exist in two archives at once, not deprecated
    """

    # converts to canon correctly
    item = PaperCategories("1234.5678")
    item.add_cross("cs.SY")
    assert item.paper_id == "1234.5678"
    assert item.primary is None
    assert item.crosses == {CATEGORIES["eess.SY"]}

    # doesnt duplicate cross
    item.add_cross("cs.SY")
    assert item.primary is None
    assert item.crosses == {CATEGORIES["eess.SY"]}

    # doesn't duplicate even if alt name is used
    item.add_cross("eess.SY")
    assert item.primary is None
    assert item.crosses == {CATEGORIES["eess.SY"]}

    # adding as primary uses canonical name and removes duplicate entry in cross
    item.add_primary("cs.SY")
    assert item.primary == CATEGORIES["eess.SY"]
    assert item.crosses == set()

    # cant add a matching crosslist
    item.add_cross("eess.SY")
    assert item.primary == CATEGORIES["eess.SY"]
    assert item.crosses == set()

    # can add alternately named crosslist
    item.add_cross("cs.SY")
    assert item.primary == CATEGORIES["eess.SY"]
    assert item.crosses == set()


def test_aggregate_data():
    """
    Assert that AggregateHourlyDownloadsJob.aggregate_data works as expected
    """
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    paper1 = PaperCategories("1234.5678")
    paper1.add_primary("math.GM")
    paper1.add_cross("q-fin.CP")
    paper1.add_cross("q-fin.PM")

    paper2 = PaperCategories("1234.5679")
    paper2.add_primary("hep-lat")

    paper3 = PaperCategories("1234.5680")
    paper3.add_primary("hep-lat")
    paper3.add_cross("q-fin.CP")
    paper3.add_cross("math.GM")
    paper_categories = {
        "1234.5678": paper1,
        "1234.5679": paper2,
        "1234.5680": paper3,
    }

    hour = datetime(2024, 7, 26, 13, 0)

    download_data = [
        DownloadData("1234.5678", "USA", "pdf", hour, 10),
        DownloadData("1234.5678", "Ireland", "pdf", hour, 5),
        DownloadData("1234.5679", "Ireland", "pdf", hour, 3),
        DownloadData("1234.5680", "Ireland", "pdf", hour, 1),
    ]

    # from first entry
    key1 = DownloadKey(hour, "USA", "pdf", "math", "math.GM")
    key2 = DownloadKey(hour, "USA", "pdf", "q-fin", "q-fin.CP")
    key3 = DownloadKey(hour, "USA", "pdf", "q-fin", "q-fin.PM")
    # from second entry
    key4 = DownloadKey(hour, "Ireland", "pdf", "math", "math.GM")
    key5 = DownloadKey(hour, "Ireland", "pdf", "q-fin", "q-fin.CP")
    key6 = DownloadKey(hour, "Ireland", "pdf", "q-fin", "q-fin.PM")
    # from 3rd entry
    key7 = DownloadKey(hour, "Ireland", "pdf", "hep-lat", "hep-lat")
    # 4th entry uses existing keys
    expected = {
        key1: DownloadCounts(10, 0),
        key2: DownloadCounts(0, 10),
        key3: DownloadCounts(0, 10),
        key4: DownloadCounts(5, 1),
        key5: DownloadCounts(0, 6),
        key6: DownloadCounts(0, 5),
        key7: DownloadCounts(4, 0),
    }

    result = AggregateHourlyDownloadsJob.aggregate_data(
        mock_job_instance, download_data, paper_categories
    )

    # test one by one for debugging
    assert key1 in result.keys()
    assert result[key1] == DownloadCounts(10, 0)
    assert key2 in result.keys()
    assert result[key2] == DownloadCounts(0, 10)
    assert key3 in result.keys()
    assert result[key3] == DownloadCounts(0, 10)
    assert key4 in result.keys()
    assert result[key4] == DownloadCounts(5, 1)
    assert key5 in result.keys()
    assert result[key5] == DownloadCounts(0, 6)
    assert key6 in result.keys()
    assert result[key6] == DownloadCounts(0, 5)
    assert key7 in result.keys()
    assert result[key7] == DownloadCounts(4, 0)

    assert result == expected


def test_validate_inputs_cloud_event_valid():
    """Assert that _validate_inputs successfully detects cloud event"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    expected_start_time = "2025-09-12 13:00:00"
    expected_end_time = "2025-09-12 13:59:59"
    mock_job_instance._validate_cloud_event.return_value = (
        expected_start_time,
        expected_end_time,
    )

    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    start_time, end_time = AggregateHourlyDownloadsJob._validate_inputs(
        mock_job_instance, cloud_event=mock_cloud_event
    )

    assert start_time == expected_start_time
    assert end_time == expected_end_time


def test_validate_cloud_event_valid():
    """Assert that _validate_cloud_event sets start and end time correctly with valid cloud event"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)
    mock_job_instance.hour_delay = 3
    mock_job_instance._event_time_exceeds_retry_window.return_value = False

    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    start_time, end_time = AggregateHourlyDownloadsJob._validate_cloud_event(
        mock_job_instance, cloud_event=mock_cloud_event
    )

    assert start_time == "2025-09-12 13:00:00"
    assert end_time == "2025-09-12 13:59:59"


def test_validate_inputs_dates_valid():
    """Assert that _validate_inputs successfully detects valid dates"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    expected_start_time = "2025-09-12 16:00:00"
    expected_end_time = "2025-09-12 16:59:59"
    mock_job_instance._validate_dates.return_value = (
        expected_start_time,
        expected_end_time,
    )

    start_time = "2025-09-1216"
    end_time = "2025-09-1216"

    start_time, end_time = AggregateHourlyDownloadsJob._validate_inputs(
        mock_job_instance, start_time=start_time, end_time=end_time
    )

    assert start_time == expected_start_time
    assert end_time == expected_end_time


def test_validate_inputs_dates_invalid():
    """Assert that _validate_inputs successfully detects dates"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)
    mock_job_instance._validate_dates.side_effect = NoRetryError

    start_time = ""
    end_time = ""

    with pytest.raises(NoRetryError):
        AggregateHourlyDownloadsJob._validate_inputs(
            mock_job_instance, start_time=start_time, end_time=end_time
        )


def test_validate_dates_valid():
    """Assert that _validate_dates executes successfully
    when valid start and end times are provided"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    start_time = "2025-09-1216"
    end_time = "2025-09-1216"

    start_time, end_time = AggregateHourlyDownloadsJob._validate_dates(
        mock_job_instance, start_time=start_time, end_time=end_time
    )

    assert start_time == "2025-09-12 16:00:00"
    assert end_time == "2025-09-12 16:59:59"


def test_validate_dates_invalid_date_range():
    """Assert that _validate_dates raises an error when start time is after end time"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    start_time = "2025-09-1001"
    end_time = "2025-09-0901"

    with pytest.raises(NoRetryError):
        AggregateHourlyDownloadsJob._validate_dates(
            mock_job_instance, start_time=start_time, end_time=end_time
        )


def test_validate_inputs_invalid_date_length():
    """Assert that _validate_dates raises an error when hours are not provided"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    start_time = "2025-09-10"
    end_time = "2025-09-10"

    with pytest.raises(NoRetryError):
        AggregateHourlyDownloadsJob._validate_dates(
            mock_job_instance, start_time=start_time, end_time=end_time
        )


def test_validate_inputs_missing():
    """Assert that _validate_inputs raises an error when neither a cloud event
    nor input dates are provided"""
    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)

    with pytest.raises(NoRetryError):
        AggregateHourlyDownloadsJob._validate_inputs(mock_job_instance)


@patch("main.datetime")
def test_event_time_exceeds_retry_window_true(mock_datetime_method):
    """ """
    mock_datetime_method.now.return_value = datetime(
        2025, 10, 15, 10, 30, 0, tzinfo=timezone.utc
    )
    mock_event_time = datetime(2025, 10, 15, 9, 39, 0, tzinfo=timezone.utc)

    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)
    mock_job_instance.MAX_EVENT_AGE_IN_MINUTES = 50

    mock_result = AggregateHourlyDownloadsJob._event_time_exceeds_retry_window(
        mock_job_instance, mock_event_time
    )

    assert mock_result == True


@patch("main.datetime")
def test_event_time_exceeds_retry_window_false(mock_datetime_method):
    """ """
    mock_datetime_method.now.return_value = datetime(
        2025, 10, 15, 10, 30, 0, tzinfo=timezone.utc
    )
    mock_event_time = datetime(2025, 10, 15, 9, 41, 0, tzinfo=timezone.utc)

    mock_job_instance = MagicMock(autospec=AggregateHourlyDownloadsJob)
    mock_job_instance.MAX_EVENT_AGE_IN_MINUTES = 50

    mock_result = AggregateHourlyDownloadsJob._event_time_exceeds_retry_window(
        mock_job_instance, mock_event_time
    )

    assert not mock_result

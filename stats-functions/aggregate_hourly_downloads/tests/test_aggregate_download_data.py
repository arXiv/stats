import os
import sys
import pytest
from unittest.mock import MagicMock

os.environ["ENV"] = "TEST"

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import datetime, timezone
from unittest.mock import patch
from cloudevents.http import CloudEvent

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from entities import ReadBase, DocumentCategory, Metadata
from models import PaperCategories, DownloadData, DownloadKey, DownloadCounts
from main import (
    process_table_rows,
    get_paper_categories,
    process_paper_categories,
    aggregate_data,
    insert_into_database,
    query_logs,
    get_start_and_end_times,
    validate_cloud_event,
    validate_hour,
    validate_inputs,
)

from arxiv.taxonomy.definitions import CATEGORIES
from stats_entities.site_usage import SiteUsageBase, HourlyDownloads
from stats_functions.exception import NoRetryError


mock_rows_from_bq = [
    {
        "paper_id": "2301.00001",
        "geo_country": "US",
        "download_type": "e-print",
        "start_dttm": datetime(2026, 2, 9, 10, 45, 12),
        "num_downloads": 10,
    },
    {
        "paper_id": "2301.00002",
        "geo_country": "DE",
        "download_type": "pdf",
        "start_dttm": datetime(2026, 2, 9, 10, 45, 12),
        "num_downloads": 5,
    },
    {
        "paper_id": "not_an_id",  # bad id
        "geo_country": "FR",
        "download_type": "pdf",
        "start_dttm": datetime(2026, 2, 9, 11, 20, 0),
        "num_downloads": 1,
    },
    {
        "paper_id": "2301.00003",
        "geo_country": "UK",
        # "download_type" is missing
        "start_dttm": datetime(2026, 2, 9, 11, 20, 0),
        "num_downloads": 2,
    },
]


@pytest.fixture
def read_session_factory():
    engine = create_engine("sqlite:///:memory:")
    ReadBase.metadata.create_all(engine)

    ReadSessionFactory = sessionmaker(bind=engine)

    with ReadSessionFactory() as session:
        session.add_all(
            [
                DocumentCategory(document_id="1", category="cs.CR", is_primary="1"),
                DocumentCategory(document_id="1", category="cs.LO", is_primary="0"),
                Metadata(
                    metadata_id="1",
                    document_id="1",
                    paper_id="cs/0004010",
                    is_current="0",
                ),
                Metadata(
                    metadata_id="2",
                    document_id="1",
                    paper_id="cs/0004010",
                    is_current="1",
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


def test_process_table_rows_success_valid_and_invalid_rows():
    (
        download_data,
        paper_ids,
        time_period_str,
        bad_id_count,
        problem_row_count,
        time_periods,
    ) = process_table_rows(mock_rows_from_bq)

    assert len(download_data) == 2
    assert download_data[0].paper_id == "2301.00001"
    assert download_data[0].download_type == "src"
    assert download_data[0].time == datetime(2026, 2, 9, 10, 0)

    assert "2301.00001" in paper_ids
    assert "2301.00002" in paper_ids
    assert len(paper_ids) == 2

    assert bad_id_count == 1  # bad id row
    assert problem_row_count == 1  # missing key row

    assert len(time_periods) == 1
    assert time_periods[0] == datetime(2026, 2, 9, 10, 0)
    assert "2026-02-09 10:00:00" in time_period_str


def test_get_paper_categories_success(read_session_factory):
    with patch("main.ReadSessionFactory", read_session_factory):
        result = get_paper_categories(
            [
                "cs/0004010",
            ]
        )

        assert len(result) == 2
        assert result[0][1] == "cs.CR"
        assert result[1][1] == "cs.LO"


def test_insert_into_database_success(write_session_factory):
    mock_aggregated_data = {
        DownloadKey(
            time=datetime(2025, 11, 1, 12),
            country="US",
            download_type="pdf",
            archive="cs",
            category_id="cs.AI",
        ): DownloadCounts(primary=150, cross=25),
        DownloadKey(
            time=datetime(2025, 11, 1, 12),
            country="Ireland",
            download_type="pdf",
            archive="physics",
            category_id="physics.gen-ph",
        ): DownloadCounts(primary=40, cross=5),
    }
    mock_time_periods = [datetime(2025, 11, 1, 12)]

    with patch("main.WriteSessionFactory", write_session_factory):
        insert_into_database(mock_aggregated_data, mock_time_periods)

    with write_session_factory() as session:
        results = (
            session.query(HourlyDownloads)
            .filter_by(start_dttm=datetime(2025, 11, 1, 12))
            .all()
        )

        assert len(results) == 2
        assert results[0].primary_count == 150
        assert results[1].cross_count == 5


@patch("main.bigquery.Client")
@patch("main.config")
def test_query_logs_success(mock_config, mock_client_class):
    mock_config.project = "test-project"
    mock_config.logs_query = "SELECT * FROM logs"
    mock_config.paper_id_regex = "regex1"

    mock_client = mock_client_class.return_value
    mock_query_job = MagicMock()
    mock_rows = MagicMock()

    mock_rows.total_rows = 10
    mock_query_job.result.return_value = mock_rows
    mock_client.query.return_value = mock_query_job

    result = query_logs("2023-01-01", "2023-01-02")

    assert result == mock_rows
    mock_client_class.assert_called_once_with(project="test-project")

    args, kwargs = mock_client.query.call_args
    assert args[0] == "SELECT * FROM logs"


@patch("main.bigquery.Client")
@patch("main.logger")
def test_query_logs_empty_results_raises_error(mock_logger, mock_client_class):
    mock_rows = MagicMock()
    mock_rows.total_rows = 0
    mock_client_class.return_value.query.return_value.result.return_value = mock_rows

    with pytest.raises(NoRetryError):
        query_logs("2023-01-01", "2023-01-02")


def test_process_cats_basic():
    data = [
        ("1234.5678", "math.GM", 1),
        ("1234.5679", "hep-lat", 1),
        ("1234.5679", "q-fin.CP", 0),
        ("1234.5679", "q-fin.PM", 0),
    ]

    result = process_paper_categories(data)

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

    result = aggregate_data(download_data, paper_categories)

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


@patch("main.event_time_exceeds_retry_window")
@patch("main.config")
def test_validate_cloud_event(mock_config, mock_retry_check):
    mock_config.hour_delay = 3
    mock_retry_check.return_value = False

    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data={})

    result = validate_cloud_event(mock_cloud_event)

    assert result == datetime(2025, 9, 12, 13, 0, tzinfo=timezone.utc)


def test_validate_hour_valid():
    mock_attributes = {
        "type": "mock_type",
        "source": "mock_source",
        "time": "2025-09-12T16:30:00Z",
    }
    mock_data = {"message": {"data": "", "attributes": {"hour": "2025-11-0412"}}}

    mock_cloud_event = CloudEvent(attributes=mock_attributes, data=mock_data)

    result = validate_hour(mock_cloud_event)

    assert result == datetime(2025, 11, 4, 12, 0, tzinfo=timezone.utc)


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


def test_get_start_and_end_times():
    start_time, end_time = get_start_and_end_times(
        datetime(2025, 9, 12, 16, 0, tzinfo=timezone.utc)
    )

    assert start_time == "2025-09-12 16:00:00"
    assert end_time == "2025-09-12 16:59:59"


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

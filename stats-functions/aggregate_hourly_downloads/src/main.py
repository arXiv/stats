import os
import logging
from typing import Set, Dict, List, Tuple, Any, Union
from datetime import datetime, timedelta, timezone

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud.sql.connector import Connector
from google.cloud.sql.connector import IPTypes

from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator, _EmptyRowIterator

from sqlalchemy import Row
from sqlalchemy.orm import sessionmaker, aliased

from config import get_config
from entities import DocumentCategory, Metadata
from models import (
    PaperCategories,
    DownloadData,
    DownloadCounts,
    DownloadKey,
    AggregationResult,
)

from stats_entities.site_usage import HourlyDownloads

from stats_functions.exception import NoRetryError
from stats_functions.utils import (
    set_up_cloud_logging,
    get_engine,
    event_time_exceeds_retry_window,
    parse_cloud_event_time,
)

from arxiv.identifier import Identifier, IdentifierException


config = get_config(os.getenv("ENV"))

logging.basicConfig(level=config.log_level)
logger = logging.getLogger(__name__)

set_up_cloud_logging(config)

ReadSessionFactory = None
WriteSessionFactory = None

if config.env != "TEST":
    connector = Connector(ip_type=IPTypes.PUBLIC, refresh_strategy="LAZY")
    ReadSessionFactory = sessionmaker(bind=get_engine(connector, config.read_db))
    WriteSessionFactory = sessionmaker(bind=get_engine(connector, config.write_db))


def process_table_rows(
    rows: Union[RowIterator, _EmptyRowIterator],
) -> Tuple[List[DownloadData], Set[str], str, int, int, List[datetime]]:
    """
    processes rows of data from bigquery
    returns the list of download data, a set of all unique paper_ids and a string of the time periods this covers
    """
    # process and store returned data
    paper_ids = set()  # only look things up for each paper once
    download_data: List[DownloadData] = []  # not a dictionary because no unique keys
    problem_rows: List[Tuple[Any], Exception] = []
    problem_row_count = 0
    bad_id_count = 0
    time_periods = []
    for row in rows:
        try:
            d_type = (
                "src" if row["download_type"] == "e-print" else row["download_type"]
            )  # combine e-print and src downloads
            paper_id = Identifier(row["paper_id"]).id
            download_data.append(
                DownloadData(
                    paper_id=paper_id,
                    country=row["geo_country"],
                    download_type=d_type,
                    time=row["start_dttm"].replace(
                        minute=0, second=0, microsecond=0
                    ),  # bucketing by hour
                    num=row["num_downloads"],
                )
            )
            paper_ids.add(paper_id)
        except IdentifierException:
            bad_id_count += 1
            continue  # dont count this download
        except Exception as e:
            problem_row_count += 1
            problem_rows.append((tuple(row), e)) if len(problem_rows) < 20 else None
            continue  # dont count this download
        time_period = row["start_dttm"].replace(minute=0, second=0, microsecond=0)
        if time_period not in time_periods:
            time_periods.append(time_period)

    time_period_str = ", ".join(
        [date.strftime("%Y-%m-%d %H:%M:%S") for date in time_periods]
    )
    if problem_row_count > 30:
        logger.warning(
            f"{time_period_str}: Problem processing {problem_row_count} rows \n Selection of problem row errors: {problem_rows}"
        )

    return (
        download_data,
        paper_ids,
        time_period_str,
        bad_id_count,
        problem_row_count,
        time_periods,
    )


def get_paper_categories(paper_ids: Set[str]) -> Dict[str, PaperCategories]:
    # get the category data for papers
    meta = aliased(Metadata)
    dc = aliased(DocumentCategory)

    with ReadSessionFactory() as session:
        logger.info("Executing read database query")
        paper_cats = (
            session.query(meta.paper_id, dc.category, dc.is_primary)
            .join(meta, dc.document_id == meta.document_id)
            .filter(meta.paper_id.in_(paper_ids))
            .filter(meta.is_current == 1)
            .all()
        )
    logger.info("Read database query successfully executed; session closed")

    return paper_cats


def process_paper_categories(
    data: List[Row[Tuple[str, str, int]]],
) -> Dict[str, PaperCategories]:
    # format paper categories into dictionary
    paper_categories: Dict[str, PaperCategories] = {}
    for row in data:
        paper_id, cat, is_primary = row
        entry = paper_categories.setdefault(paper_id, PaperCategories(paper_id))
        if is_primary == 1:
            entry.add_primary(cat)
        else:
            entry.add_cross(cat)

    return paper_categories


def aggregate_data(
    download_data: List[DownloadData],
    paper_categories: Dict[str, PaperCategories],
) -> Dict[DownloadKey, DownloadCounts]:
    """creates a dictionary of download counts by time, country, download type, and category
    goes through each download entry, matches it with its caegories and adds the number of downloads to the count
    """
    logger.info("Aggregating download data")
    all_data: Dict[DownloadKey, DownloadCounts] = {}
    missing_data: List[str] = []
    missing_data_count = 0
    for entry in download_data:
        try:
            cats = paper_categories[entry.paper_id]
        except KeyError:
            missing_data_count += 1
            (
                missing_data.append(entry.paper_id) if len(missing_data) < 20 else None
            )  # dont make the list too long
            continue  # dont process this paper

        # record primary
        key = DownloadKey(
            entry.time,
            entry.country,
            entry.download_type,
            cats.primary.in_archive,
            cats.primary.id,
        )
        value = all_data.get(key, DownloadCounts())
        value.primary += entry.num
        all_data[key] = value

        # record for each cross
        for cat in cats.crosses:
            key = DownloadKey(
                entry.time,
                entry.country,
                entry.download_type,
                cat.in_archive,
                cat.id,
            )
            value = all_data.get(key, DownloadCounts())
            value.cross += entry.num
            all_data[key] = value

    if missing_data_count > 10:
        time = download_data[0].time
        logger.warning(
            f"{time} Could not find category data for {missing_data_count} paper_ids (may be invalid) \n Example paper_ids with no category data: {missing_data}"
        )

    return all_data


def insert_into_database(
    aggregated_data: Dict[DownloadKey, DownloadCounts],
    time_periods: List[datetime],
) -> int:
    """adds the data from an hour of downloads into the database
    uses bulk insert and update statements to increase efficiency
    first compiles all the keys for the data we would like to add and checks for their presence in the database
    present items are added to run update for, and removed from the aggregated dictionary
    remaining items are inserted
    data with duplicate keys will be overwritten to allow for reruns with updates
    returns the number of rows added and updated
    """
    data_to_insert = [
        HourlyDownloads(
            country=key.country,
            download_type=key.download_type,
            archive=key.archive,
            category=key.category,
            primary_count=counts.primary,
            cross_count=counts.cross,
            start_dttm=key.time,
        )
        for key, counts in aggregated_data.items()
    ]

    with WriteSessionFactory() as session:
        logger.info("Executing write database transaction")
        # remove previous data for the time period
        session.query(HourlyDownloads).filter(
            HourlyDownloads.start_dttm.in_(time_periods)
        ).delete(synchronize_session=False)

        # add data
        for i in range(
            0, len(data_to_insert), config.max_query_to_write
        ):  # to conform to db stack size limit
            session.bulk_save_objects(data_to_insert[i : i + config.max_query_to_write])

        session.commit()

    logger.info("Write database transaction successfully committed; session closed")

    return len(data_to_insert)


def perform_aggregation(
    rows: Union[RowIterator, _EmptyRowIterator],
) -> AggregationResult:
    logger.info("Processing results of log query")
    (
        download_data,
        paper_ids,
        time_period_str,
        bad_id_count,
        problem_row_count,
        time_periods,
    ) = process_table_rows(rows)

    fetched_count = len(download_data)
    unique_id_count = len(paper_ids)

    # find categories for all the papers
    query_results = get_paper_categories(paper_ids)
    paper_categories = process_paper_categories(query_results)
    if len(paper_categories) == 0:
        logger.error(f"{time_period_str}: No category data retrieved from database!")
        raise NoRetryError

    # aggregate download data
    aggregated_data = aggregate_data(download_data, paper_categories)

    # write all_data to tables
    add_count = insert_into_database(aggregated_data, time_periods)
    result = AggregationResult(
        time_period_str,
        add_count,
        fetched_count,
        unique_id_count,
        bad_id_count,
        problem_row_count,
    )
    return result


def query_logs(start_time: str, end_time: str) -> RowIterator:
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "paper_id_regex", "STRING", config.paper_id_regex
            ),
            bigquery.ScalarQueryParameter(
                "download_type_regex", "STRING", config.download_type_regex
            ),
            bigquery.ScalarQueryParameter(
                "paper_id_optional_version_regex",
                "STRING",
                config.paper_id_optional_version_regex,
            ),
            bigquery.ScalarQueryParameter("start_time", "STRING", start_time),
            bigquery.ScalarQueryParameter("end_time", "STRING", end_time),
        ]
    )

    logger.info("Initializing bigquery client")
    bq_client = bigquery.Client(project=config.project)
    logger.info("Executing log query in bigquery")
    query_job = bq_client.query(config.logs_query, job_config=job_config)
    logger.info("Log query successfully executed")

    rows = query_job.result()

    if rows.total_rows > 0:
        return rows
    else:
        logger.error("No log data returned from bigquery!")
        raise NoRetryError


def get_start_and_end_times(hour: datetime) -> tuple[datetime, datetime]:
    start_time = f"{hour.strftime('%Y-%m-%d %H')}:00:00"
    end_time = f"{hour.strftime('%Y-%m-%d %H')}:59:59"

    return start_time, end_time


def validate_cloud_event(cloud_event: CloudEvent) -> datetime:
    event_time = parse_cloud_event_time(cloud_event)

    if event_time_exceeds_retry_window(config, event_time):
        raise NoRetryError

    return (event_time - timedelta(hours=config.hour_delay)).replace(minute=0)


def validate_hour(cloud_event: CloudEvent) -> datetime:
    hour = cloud_event.data["message"]["attributes"]["hour"]

    return (
        datetime.strptime(hour, "%Y-%m-%d%H")
        .replace(tzinfo=timezone.utc)
        .replace(minute=0)
    )


def validate_inputs(cloud_event: CloudEvent) -> datetime:
    try:
        hour = validate_hour(cloud_event)
        logger.info("Received valid hour as attribute")

    except (KeyError, ValueError):
        hour = validate_cloud_event(cloud_event)
        logger.info("Received valid event time")

    except NoRetryError:
        raise

    logger.info(f"Parameters for job: hour={hour}")
    return hour


@functions_framework.cloud_event
def aggregate_hourly_downloads(cloud_event: CloudEvent):
    try:
        hour = validate_inputs(cloud_event)
        start_time, end_time = get_start_and_end_times(hour)

        log_query_result = query_logs(start_time, end_time)
        aggregation_result = perform_aggregation(log_query_result)

        logger.info(aggregation_result.single_run_str())

    except NoRetryError:
        logger.exception(
            "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
        )
        return

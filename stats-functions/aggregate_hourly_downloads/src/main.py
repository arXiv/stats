import json
import base64
import os
from typing import Set, Dict, List, Literal, Tuple, Any, Union
from datetime import datetime, timedelta, timezone
from dateutil import parser

from arxiv.taxonomy.category import Category
from arxiv.taxonomy.definitions import CATEGORIES

from arxiv.identifier import Identifier, IdentifierException

import functions_framework
from cloudevents.http import CloudEvent

from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator, _EmptyRowIterator
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Enum,
    PrimaryKeyConstraint,
    Row,
)
from sqlalchemy.orm import (
    Session,
    aliased,
    declarative_base,
)

MAX_QUERY_TO_WRITE = 1000  # the latexmldb we write to has a stack size limit
HOUR_DELAY = 3  # how many hours back to run the hourly query, gives time for logs to make it to gcp

# setup logging
if not (os.environ.get("LOG_LOCALLY", False)):
    import google.cloud.logging

    client = google.cloud.logging.Client()
    client.setup_logging()
import logging

log_level_str = os.getenv("LOG_LEVEL", "INFO")
log_level = getattr(logging, log_level_str.upper(), logging.INFO)
logging.basicConfig(level=log_level)

# setup BigQuery client
project = "arxiv-production" if os.getenv("ENV") == "PROD" else "arxiv-development"
bq_client = bigquery.Client(
    project=project
)  # fastly download logs live in production project

DownloadType = Literal["pdf", "html", "src"]

QUERY_START = """
    SELECT paper_id, geo_country, download_type, TIMESTAMP_TRUNC(start_dttm, HOUR) as start_dttm, COUNT(*) as num_downloads, 
    FROM (
    SELECT
        STRING(json_payload.remote_addr) as remote_addr,
        REGEXP_EXTRACT(STRING(json_payload.path), r"^/[^/]+/([a-zA-Z-]+/[0-9]{7}|[0-9]{4}\.[0-9]{4,5})") as paper_id,
        STRING(json_payload.geo_country) as geo_country,
        REGEXP_EXTRACT(STRING(json_payload.path), r"^/(html|pdf|src|e-print)/") as download_type,
        FARM_FINGERPRINT(STRING(json_payload.user_agent)) AS user_agent_hash, --hoping to further distinguish between devices on the same ip
        TIMESTAMP_TRUNC(timestamp, MINUTE) AS start_dttm
    FROM arxiv_logs._AllLogs
    WHERE log_id = "fastly_log_ingest" --only look at fastly logs
    AND STRING(json_payload.state) != "HIT_SYNTH" --dont count blocks and captcha
    AND REGEXP_CONTAINS(STRING(json_payload.path), "^/(html|pdf|src|e-print)/") --only use download paths
    AND REGEXP_CONTAINS(JSON_VALUE(json_payload, "$.status"), "^2[0-9][0-9]$") --only succesfful responses
    AND JSON_VALUE(json_payload, "$.status") != "206" --dont count partial content
    AND REGEXP_CONTAINS(STRING(json_payload.path), r"^/[^/]+/([a-zA-Z-]+/[0-9]{7}|[0-9]{4}\.[0-9]{4,5})(v[0-9]+)?$") --only paths that end with a paperid
    AND JSON_VALUE(json_payload, "$.method") = "GET" --only count actual downloads
    """

QUERY_END = """
    GROUP BY 1,2,3,4,5,6
    )
    GROUP BY 1,2,3,4
"""

# setup read and write databases
ReadBase = declarative_base()
WriteBase = declarative_base()


class DocumentCategory(ReadBase):
    __tablename__ = "arXiv_document_category"

    document_id = Column(Integer, primary_key=True, nullable=False, index=True)
    category = Column(String, primary_key=True, nullable=False, index=True)
    is_primary = Column(Integer, nullable=False)


class Metadata(ReadBase):
    __tablename__ = "arXiv_metadata"

    metadata_id = Column(Integer, primary_key=True)
    document_id = Column(Integer, nullable=False, index=True)
    paper_id = Column(String(64), nullable=False)
    is_current = Column(Integer)


class HourlyDownloads(WriteBase):
    __tablename__ = "hourly_downloads"
    country = Column(String(255), primary_key=True)
    download_type = Column(
        String(16),
        Enum("pdf", "html", "src", name="download_type_enum"),
        primary_key=True,
    )
    archive = Column(String(16))
    category = Column(String(32), primary_key=True)
    primary_count = Column(Integer)
    cross_count = Column(Integer)
    start_dttm = Column(DateTime, primary_key=True)
    __table_args__ = (
        PrimaryKeyConstraint("country", "download_type", "category", "start_dttm"),
    )


# instantiate db connections
read_engine = create_engine(os.getenv("READ_DB_URI"))
ReadBase.metadata.create_all(read_engine)

write_engine = create_engine(os.getenv("WRITE_DB_URI"))
WriteBase.metadata.create_all(write_engine)


class PaperCategories:
    paper_id: str
    primary: Category
    crosses: Set[Category]

    def __init__(self, id: str):
        self.paper_id = id
        self.primary = None
        self.crosses = set()

    def add_primary(self, cat: str):
        if self.primary != None:  # this function should only get called once per paper
            logging.error(
                f"Multiple primary categories for {self.paper_id}: {self.primary} and {cat}"
            )
            self.add_cross(cat)  # add as a cross just to keep data
        else:
            catgory = CATEGORIES[cat]
            canon = catgory.get_canonical()
            self.primary = canon
            self.crosses.discard(
                canon
            )  # removes from crosses if present, the same category cant be both primary and cross.
            # This is relevant because an alternate name may be listed as a cross list

    def add_cross(self, cat: str):
        catgory = CATEGORIES[cat]
        canon = catgory.get_canonical()
        # avoid dupliciates of categories with other names
        if self.primary is None or canon != self.primary:
            self.crosses.add(canon)

    def __eq__(self, other):
        if not isinstance(other, PaperCategories):
            return False
        return (
            self.paper_id == other.paper_id
            and self.primary == other.primary
            and self.crosses == other.crosses
        )

    def __repr__(self):
        crosses_str = ", ".join(cat.id for cat in self.crosses)
        return (
            f"Paper: {self.paper_id} Primary: {self.primary.id} Crosses: {crosses_str}"
        )


class DownloadData:
    def __init__(
        self,
        paper_id: str,
        country: str,
        download_type: DownloadType,
        time: datetime,
        num: int,
    ):
        self.paper_id = paper_id
        self.country = country
        self.download_type = download_type
        self.time = time
        self.num = num

    def __repr__(self) -> str:
        return (
            f"DownloadData(paper_id='{self.paper_id}', country='{self.country}', "
            f"download_type='{self.download_type}', time='{self.time}', "
            f"num={self.num})"
        )


class DownloadCounts:
    def __init__(self, primary: int = 0, cross: int = 0):
        self.primary = primary
        self.cross = cross

    def __eq__(self, other):
        if isinstance(other, DownloadCounts):
            return self.primary == other.primary and self.cross == other.cross
        else:
            return False

    def __repr__(self):
        return f"Count(primary: {self.primary}, cross: {self.cross})"


class DownloadKey:
    def __init__(
        self,
        time: datetime,
        country: str,
        download_type: DownloadType,
        archive: str,
        category_id: str,
    ):
        self.time = time
        self.country = country
        self.download_type = download_type
        self.archive = archive
        self.category = category_id

    def __eq__(self, other):
        if isinstance(other, DownloadKey):
            return (
                self.country == other.country
                and self.download_type == other.download_type
                and self.category == other.category
                and self.time.date() == other.time.date()
                and self.time.hour == other.time.hour
            )
        return False

    def __hash__(self):
        return hash(
            (
                self.time.date(),
                self.time.hour,
                self.country,
                self.download_type,
                self.category,
            )
        )

    def __repr__(self):
        return f"Key(type: {self.download_type}, cat: {self.category}, country: {self.country}, day: {self.time.day} hour: {self.time.hour})"


class AggregationResult:
    def __init__(
        self,
        time_period_str: str,
        output_count: int,
        fetched_count: int,
        unique_ids_count: int,
        bad_id_count: int,
        problem_row_count: int,
    ):
        self.time_period_str = time_period_str
        self.output_count = output_count
        self.fetched_count = fetched_count
        self.unique_ids_count = unique_ids_count
        self.bad_id_count = bad_id_count
        self.problem_row_count = problem_row_count

    def single_run_str(self) -> str:
        return f"{self.time_period_str}: SUCCESS! rows created: {self.output_count}, fetched rows: {self.fetched_count}, unique_ids: {self.unique_ids_count}, invalid_ids: {self.bad_id_count}, other unprocessable rows: {self.problem_row_count}"

    def table_row_str(self) -> str:
        return f"{self.time_period_str:<20} {self.output_count:<7} {self.fetched_count:<12} {self.unique_ids_count:<10} {self.bad_id_count:<7} {self.problem_row_count:<10}"

    def table_header() -> str:
        return f"{'Time Period':<20} {'New Rows':<7} {'Fetched Rows':<12} {'Unique IDs':<10} {'Bad IDs':<7} {'Problems':<10} {'Time Taken':<10}"


def process_table_rows(
    rows: Union[RowIterator, _EmptyRowIterator],
) -> Tuple[List[DownloadData], Set[str], str, int, int, List[datetime]]:
    """processes rows of data from bigquery
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
        except IdentifierException as e:
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
        logging.warning(
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


def perform_aggregation(
    rows: Union[RowIterator, _EmptyRowIterator],
) -> AggregationResult:
    """performs the entire aggregation process for a set of data recieved from bigquery"""
    # process and store returned data
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
    if len(paper_ids) == 0:
        logging.critical("No data retrieved from BigQuery")
        return  # this will prevent retries

    # find categories for all the papers
    paper_categories = get_paper_categories(paper_ids)
    if len(paper_categories) == 0:
        logging.critical(f"{time_period_str}: No category data retrieved from database")
        return  # this will prevent retries

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


@functions_framework.cloud_event
def aggregate_hourly_downloads(
    # cloud_event: CloudEvent
):
    """get downloads data and aggregate but category country and download type"""
    # pubsub_timestamp = parser.isoparse(cloud_event["time"]).replace(tzinfo=timezone.utc)
    date_string = "2025-09-02 18:42:00"
    format_string = "%Y-%m-%d %H:%M:%S"
    pubsub_timestamp = datetime.strptime(date_string, format_string)

    # get and check enviroment data
    enviro = os.environ.get("ENV")
    write_db_uri = os.environ.get("WRITE_DB_URI")
    if any(v is None for v in (enviro, write_db_uri)):
        logging.critical(f"Missing enviroment variable(s)")
        return  # dont bother retrying
    elif enviro == "PROD":
        if "development" in write_db_uri:
            logging.warning(f"Referencing development project in production!")
    elif enviro == "DEV":
        if "production" in write_db_uri:
            logging.warning(f"Referencing production project in development!")
    else:
        logging.error(f"Unknown Enviroment: {enviro}")
        return  # dont bother retrying

    active_hour = pubsub_timestamp - timedelta(
        hours=HOUR_DELAY
    )  # give some time for logs to make it to gcp
    time_selection = f"and timestamp between TIMESTAMP('{active_hour.strftime('%Y-%m-%d %H')}:00:00') and TIMESTAMP('{active_hour.strftime('%Y-%m-%d %H')}:59:59')"
    result = process_an_hour(time_selection, write_db_uri)
    logging.info(result.single_run_str())


def get_paper_categories(paper_ids: Set[str]) -> Dict[str, PaperCategories]:
    # get the category data for papers
    meta = aliased(Metadata)
    dc = aliased(DocumentCategory)

    # Setup database connection
    # read_db_uri = os.getenv("READ_DB_URI")
    # engine = create_engine(read_db_uri)
    session = Session(bind=engine)

    paper_cats = (
        session.query(meta.paper_id, dc.category, dc.is_primary)
        .join(meta, dc.document_id == meta.document_id)
        .filter(meta.paper_id.in_(paper_ids))
        .filter(meta.is_current == 1)
        .all()
    )

    return process_paper_categories(paper_cats)


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
    download_data: List[DownloadData], paper_categories: Dict[str, PaperCategories]
) -> Dict[DownloadKey, DownloadCounts]:
    """creates a dictionary of download counts by time, country, download type, and category
    goes through each download entry, matches it with its caegories and adds the number of downloads to the count
    """
    all_data: Dict[DownloadKey, DownloadCounts] = {}
    missing_data: List[str] = []
    missing_data_count = 0
    for entry in download_data:
        try:
            cats = paper_categories[entry.paper_id]
        except KeyError as e:
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
                entry.time, entry.country, entry.download_type, cat.in_archive, cat.id
            )
            value = all_data.get(key, DownloadCounts())
            value.cross += entry.num
            all_data[key] = value

    if missing_data_count > 10:
        time = download_data[0].time
        logging.warning(
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

    # remove previous data for the time period
    write_session.query(HourlyDownloads).filter(
        HourlyDownloads.start_dttm.in_(time_periods)
    ).delete(synchronize_session=False)

    # add data
    for i in range(0, len(data_to_insert), MAX_QUERY_TO_WRITE):
        write_session.bulk_save_objects(data_to_insert[i : i + MAX_QUERY_TO_WRITE])

    write_session.commit()
    write_session.close()
    return len(data_to_insert)


def process_an_hour(time_selection: str, write_db_uri: str) -> AggregationResult:
    """manages an hour's process of fetching data, prcoessing it, writing to a database and logging it"""
    query = f"{QUERY_START}\n{time_selection}\n{QUERY_END}"
    query_job = bq_client.query(query)
    download_result = query_job.result()
    return perform_aggregation(download_result, write_db_uri)

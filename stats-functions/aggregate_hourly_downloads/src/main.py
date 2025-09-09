import os
import logging
from typing import Set, Dict, List, Literal, Tuple, Any, Union
from datetime import datetime, timedelta, timezone
from dateutil import parser

from arxiv.taxonomy.category import Category
from arxiv.taxonomy.definitions import CATEGORIES
from arxiv.identifier import Identifier, IdentifierException

import functions_framework
from cloudevents.http import CloudEvent

import google.cloud.logging
from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator, _EmptyRowIterator

from google.cloud.sql.connector import Connector, IPTypes
import pymysql

from models import ReadBase, WriteBase, DocumentCategory, Metadata, HourlyDownloads

# from sqlalchemy import URL
from sqlalchemy import create_engine, Row
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker, aliased


logger = logging.getLogger(__name__)


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
            logger.error(
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
        download_type: Literal["pdf", "html", "src"],
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
        download_type: Literal["pdf", "html", "src"],
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


class AggregateHourlyDownloadsJob:
    MAX_QUERY_TO_WRITE = 1000  # the latexmldb we write to has a stack size limit
    HOUR_DELAY = 3  # how many hours back to run the hourly query, gives time for logs to make it to gcp
    LOGS_QUERY = """
                    SELECT
                        paper_id,
                        geo_country,
                        download_type,
                        TIMESTAMP_TRUNC(start_dttm, HOUR) as start_dttm,
                        COUNT(*) as num_downloads,
                    FROM
                        (
                        SELECT
                            STRING(json_payload.remote_addr) as remote_addr,
                            REGEXP_EXTRACT(STRING(json_payload.path), r"^/[^/]+/([a-zA-Z-]+/[0-9]{7}|[0-9]{4}\.[0-9]{4,5})") as paper_id,
                            STRING(json_payload.geo_country) as geo_country,
                            REGEXP_EXTRACT(STRING(json_payload.path), r"^/(html|pdf|src|e-print)/") as download_type,
                            FARM_FINGERPRINT(STRING(json_payload.user_agent)) AS user_agent_hash,
                            TIMESTAMP_TRUNC(timestamp, MINUTE) AS start_dttm
                        FROM
                            arxiv_logs._AllLogs
                        WHERE
                            log_id = "fastly_log_ingest"
                            AND STRING(json_payload.state) != "HIT_SYNTH"
                            AND REGEXP_CONTAINS(STRING(json_payload.path), "^/(html|pdf|src|e-print)/")
                            AND REGEXP_CONTAINS(JSON_VALUE(json_payload, "$.status"), "^2[0-9][0-9]$")
                            AND JSON_VALUE(json_payload, "$.status") != "206"
                            AND REGEXP_CONTAINS(STRING(json_payload.path), r"^/[^/]+/([a-zA-Z-]+/[0-9]{7}|[0-9]{4}\.[0-9]{4,5})(v[0-9]+)?$")
                            AND JSON_VALUE(json_payload, "$.method") = "GET"
                            AND timestamp between TIMESTAMP( @start_time ) and TIMESTAMP( @end_time )
                        GROUP BY
                            1,
                            2,
                            3,
                            4,
                            5,
                            6
                                        )
                    GROUP BY
                        1,
                        2,
                        3,
                        4
                """

    def __init__(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_locally = os.getenv("LOG_LOCALLY", False)
        self.env = os.getenv("ENV")

        logging.basicConfig()
        logger.setLevel(self.log_level)

        logger.info("Initializing aggregate hourly downloads job")

        if not (self.log_locally):
            logger.info("Initializing cloud logging")
            client = google.cloud.logging.Client()
            client.setup_logging()

        logger.info("Checking environment variables")
        _read_db_instance = os.getenv("READ_DB_INSTANCE")
        _write_db_instance = os.getenv("WRITE_DB_INSTANCE")

        if (self.env == "PROD" and "development" in _write_db_instance) or (
            self.env == "DEV" and "production" in _write_db_instance
        ):
            logger.error(
                f"Referencing a database in another environment! Check database configuration"
            )
            return

        logger.info("Initializing bigquery client")
        project = "arxiv-production" if self.env == "PROD" else "arxiv-development"
        self.bq_client = bigquery.Client(project=project)

        logger.info("Instantiating database interfaces")
        self._read_db_engine = self._connect_with_connector(
            _read_db_instance,
            os.getenv("READ_DB_USER"),
            os.getenv("READ_DB_PW"),
            os.getenv("READ_DB_NAME"),
        )
        ReadBase.metadata.create_all(self._read_db_engine)
        self.ReadSession = sessionmaker(bind=self._read_db_engine)

        self._write_db_engine = self._connect_with_connector(
            _write_db_instance,
            os.getenv("WRITE_DB_USER"),
            os.getenv("WRITE_DB_PW"),
            os.getenv("WRITE_DB_NAME"),
        )
        WriteBase.metadata.create_all(self._write_db_engine)
        self.WriteSession = sessionmaker(bind=self._write_db_engine)

        logger.info("Initialization of aggregate hourly downloads job complete")

    def _connect_with_connector(
        self, instance_name, db_user, db_password, db_name
    ) -> Engine:
        """
        Initializes a connection pool for a Cloud SQL instance of MySQL.
        Uses the Cloud SQL Python Connector package.
        """
        ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

        # initialize Cloud SQL Python Connector object
        connector = Connector(ip_type=ip_type, refresh_strategy="LAZY")

        def getconn() -> pymysql.connections.Connection:
            conn: pymysql.connections.Connection = connector.connect(
                instance_name,
                "pymysql",
                user=db_user,
                password=db_password,
                db=db_name,
            )
            return conn

        return create_engine("mysql+pymysql://", creator=getconn)

    def process_table_rows(
        self,
        rows: Union[RowIterator, _EmptyRowIterator],
    ) -> Tuple[List[DownloadData], Set[str], str, int, int, List[datetime]]:
        """processes rows of data from bigquery
        returns the list of download data, a set of all unique paper_ids and a string of the time periods this covers
        """
        # process and store returned data
        paper_ids = set()  # only look things up for each paper once
        download_data: List[DownloadData] = (
            []
        )  # not a dictionary because no unique keys
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

    def perform_aggregation(
        self,
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
        ) = self.process_table_rows(rows)
        fetched_count = len(download_data)
        unique_id_count = len(paper_ids)
        if len(paper_ids) == 0:
            logger.critical("No log data retrieved from bigquery")
            return  # this will prevent retries

        # find categories for all the papers
        paper_categories = self.get_paper_categories(paper_ids)
        if len(paper_categories) == 0:
            logger.critical(
                f"{time_period_str}: No category data retrieved from database"
            )
            return

        # aggregate download data
        aggregated_data = self.aggregate_data(download_data, paper_categories)

        # write all_data to tables
        add_count = self.insert_into_database(aggregated_data, time_periods)
        result = AggregationResult(
            time_period_str,
            add_count,
            fetched_count,
            unique_id_count,
            bad_id_count,
            problem_row_count,
        )
        return result

    def get_paper_categories(self, paper_ids: Set[str]) -> Dict[str, PaperCategories]:
        # get the category data for papers
        meta = aliased(Metadata)
        dc = aliased(DocumentCategory)

        with self.ReadSession() as session:
            paper_cats = (
                session.query(meta.paper_id, dc.category, dc.is_primary)
                .join(meta, dc.document_id == meta.document_id)
                .filter(meta.paper_id.in_(paper_ids))
                .filter(meta.is_current == 1)
                .all()
            )

        return self.process_paper_categories(paper_cats)

    def process_paper_categories(
        self,
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
        self,
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
            except KeyError as e:
                missing_data_count += 1
                (
                    missing_data.append(entry.paper_id)
                    if len(missing_data) < 20
                    else None
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
        self,
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
        with self.WriteSession() as session:
            session.query(HourlyDownloads).filter(
                HourlyDownloads.start_dttm.in_(time_periods)
            ).delete(synchronize_session=False)

            # add data
            for i in range(0, len(data_to_insert), self.MAX_QUERY_TO_WRITE):
                session.bulk_save_objects(
                    data_to_insert[i : i + self.MAX_QUERY_TO_WRITE]
                )

            session.commit()

        return len(data_to_insert)

    def process_an_hour(self, start_time: str, end_time: str) -> AggregationResult:
        logger.info("Querying logs in bigquery")
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_time", "STRING", start_time),
                bigquery.ScalarQueryParameter("end_time", "STRING", end_time),
            ]
        )
        query_job = self.bq_client.query(self.LOGS_QUERY, job_config=job_config)
        return self.perform_aggregation(query_job.result())

    def run(self, cloud_event: CloudEvent):
        logger.info("Running aggregate hourly downloads job")
        pubsub_timestamp = parser.isoparse(cloud_event["time"]).replace(
            tzinfo=timezone.utc
        )

        active_hour = pubsub_timestamp - timedelta(
            hours=self.HOUR_DELAY
        )  # give some time for logs to make it to gcp
        start_time = f"{active_hour.strftime('%Y-%m-%d %H')}:00:00"
        end_time = f"{active_hour.strftime('%Y-%m-%d %H')}:59:59"

        logger.info(
            f"Query parameters for bigquery: start time={start_time}, end time={end_time}"
        )

        result = self.process_an_hour(start_time, end_time)
        if result is not None:
            logger.info(result.single_run_str())


@functions_framework.cloud_event
def aggregate_hourly_downloads(cloud_event: CloudEvent):
    job = AggregateHourlyDownloadsJob()
    job.run(cloud_event)


if __name__ == "__main__":
    aggregate_hourly_downloads()

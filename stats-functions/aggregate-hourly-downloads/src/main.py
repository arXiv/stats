import os
import argparse
import logging
from typing import Set, Dict, List, Tuple, Any, Union
from datetime import datetime, timedelta, timezone
from dateutil import parser

from arxiv.identifier import Identifier, IdentifierException

import functions_framework
from cloudevents.http import CloudEvent

import google.cloud.logging
from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator, _EmptyRowIterator

from google.cloud.sql.connector import Connector, IPTypes
import pymysql

from entities import ReadBase, WriteBase, DocumentCategory, Metadata, HourlyDownloads
from models import PaperCategories, DownloadData, DownloadCounts, DownloadKey, AggregationResult

from sqlalchemy import create_engine, Row
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker, aliased


logger = logging.getLogger(__name__)


class AggregateHourlyDownloadsJob:
    MAX_QUERY_TO_WRITE = os.getenv("MAX_QUERY_TO_WRITE", 1000)
    HOUR_DELAY = os.getenv("HOUR_DELAY", 3)
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
        self.env = os.getenv("ENV")

        self._set_up_logging()

        logger.info("Initializing aggregate hourly downloads job")

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
        _ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

        self._read_db_connector, self._read_db_engine = self._connect_with_connector(
            _ip_type,
            _read_db_instance,
            os.getenv("READ_DB_USER"),
            os.getenv("READ_DB_PW"),
            os.getenv("READ_DB_NAME"),
        )
        ReadBase.metadata.create_all(self._read_db_engine)
        self.ReadSession = sessionmaker(bind=self._read_db_engine)

        self._write_db_connector, self._write_db_engine = self._connect_with_connector(
            _ip_type,
            _write_db_instance,
            os.getenv("WRITE_DB_USER"),
            os.getenv("WRITE_DB_PW"),
            os.getenv("WRITE_DB_NAME"),
        )
        WriteBase.metadata.create_all(self._write_db_engine)
        self.WriteSession = sessionmaker(bind=self._write_db_engine)

        logger.info("Initialization of aggregate hourly downloads job complete")

    def _set_up_logging(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_locally = os.getenv("LOG_LOCALLY", False)

        logging.basicConfig()
        logger.setLevel(self.log_level)

        if not (self.log_locally):
            logger.info("Initializing cloud logging")
            self.cloud_logging_client = google.cloud.logging.Client()
            self.cloud_logging_client.setup_logging()

    @staticmethod
    def _connect_with_connector(
        ip_type, instance_name, db_user, db_password, db_name
    ) -> Engine:
        """
        Initializes a connection pool for a Cloud SQL instance of MySQL.
        Uses the Cloud SQL Python Connector package.
        """
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

        pool = create_engine("mysql+pymysql://", creator=getconn)
        return (connector, pool)

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
            logger.error("No log data retrieved from bigquery")
            return  # this will prevent retries

        # find categories for all the papers
        paper_categories = self.get_paper_categories(paper_ids)
        if len(paper_categories) == 0:
            logger.error(
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
            logger.info("Executing read database query")
            paper_cats = (
                session.query(meta.paper_id, dc.category, dc.is_primary)
                .join(meta, dc.document_id == meta.document_id)
                .filter(meta.paper_id.in_(paper_ids))
                .filter(meta.is_current == 1)
                .all()
            )
        logger.info("Read database query successfully executed; session closed")

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
            logger.info("Executing write database transaction")
            session.query(HourlyDownloads).filter(
                HourlyDownloads.start_dttm.in_(time_periods)
            ).delete(synchronize_session=False)

            # add data
            for i in range(
                0, len(data_to_insert), self.MAX_QUERY_TO_WRITE
            ):  # to conform to db stack size limit
                session.bulk_save_objects(
                    data_to_insert[i : i + self.MAX_QUERY_TO_WRITE]
                )

            session.commit()
        logger.info("Write database transaction successfully committed; session closed")

        return len(data_to_insert)

    def query_logs(self, start_time: str, end_time: str) -> AggregationResult:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_time", "STRING", start_time),
                bigquery.ScalarQueryParameter("end_time", "STRING", end_time),
            ]
        )
        logger.info("Executing log query in bigquery")
        query_job = self.bq_client.query(self.LOGS_QUERY, job_config=job_config)
        logger.info("Log query successfully executed")

        return query_job.result()

    def validate_inputs(self, cloud_event: CloudEvent = None, start_time: str = None, end_time: str = None):
        logger.info("Validating inputs")
        
        if cloud_event:
            logger.info("Received cloud event trigger")
            pubsub_timestamp = parser.isoparse(cloud_event["time"]).replace(
                tzinfo=timezone.utc
            )

            active_hour = pubsub_timestamp - timedelta(
                hours=self.HOUR_DELAY
            )  # give some time for logs to make it to gcp

            start_time = f"{active_hour.strftime('%Y-%m-%d %H')}:00:00"
            end_time = f"{active_hour.strftime('%Y-%m-%d %H')}:59:59"
        
        elif start_time and end_time:
            logger.info("Received start and end times")
            date_format = '%Y-%m-%d%H'
            
            try:
                assert len(start_time)==12 and len(end_time)==12
                valid_start_time = datetime.strptime(start_time, date_format)
                valid_end_time = datetime.strptime(end_time, date_format)
                assert valid_start_time <= valid_end_time
            except (AssertionError, ValueError):
                logger.error("Invalid date input(s)!")
                return (None, None)
            
            start_time = f"{valid_start_time.strftime('%Y-%m-%d %H')}:00:00"
            end_time = f"{valid_end_time.strftime('%Y-%m-%d %H')}:59:59"

        else:
            logger.error("Must receive either a cloud event or valid start and end times!")

        logger.info(
            f"Query parameters for bigquery: start time={start_time}, end time={end_time}"
        )

        return (start_time, end_time)

    def run(self, cloud_event: CloudEvent = None, start_time: str = None, end_time: str = None):
        logger.info("Running aggregate hourly downloads job")

        start_time, end_time = self.validate_inputs(cloud_event=cloud_event, start_time=start_time, end_time=end_time)

        if start_time and end_time:
            log_query_result = self.query_logs(start_time, end_time)
            aggregation_result = self.perform_aggregation(log_query_result)

        self._read_db_connector.close()
        self._write_db_connector.close()
        logger.info("Database connectors successfully closed")

        if aggregation_result:
            logger.info(aggregation_result.single_run_str())


@functions_framework.cloud_event
def aggregate_hourly_downloads(cloud_event: CloudEvent):
    job = AggregateHourlyDownloadsJob()
    job.run(cloud_event=cloud_event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-time', dest='start_time', help="The start time in 'YYYY-MM-DDHH' format", required=True)
    parser.add_argument('--end-time', dest='end_time', help="The end time in 'YYYY-MM-DDHH' format", required=True)

    args = parser.parse_args()

    job = AggregateHourlyDownloadsJob()
    job.run(start_time=args.start_time, end_time=args.end_time)

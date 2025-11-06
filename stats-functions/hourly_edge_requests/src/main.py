import os
import argparse
import logging
from google.cloud import logging as gc_logging

from datetime import datetime, timedelta, timezone
from dateutil import parser

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud.sql.connector import Connector, IPTypes
import pymysql

import fastly
from fastly.api import stats_api
from fastly.model.stats import Stats

from sqlalchemy import create_engine, delete
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker

from stats_entities.site_usage import HourlyRequests
from models import Database, FastlyStatsApiResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class NoRetryError(Exception):
    pass


class HourlyEdgeRequestsJob:
    MAX_EVENT_AGE_IN_MINUTES = 50  # to limit retries
    FASTLY_SERVICE_ID = {"arxiv.org": "umpGzwE2hXfa2aRXsOQXZ4"}
    FASTLY_NODE_NUMBER = 0  # existing convention, corresponds to 'fastly'

    def __init__(self):
        self.hour_delay = os.getenv("HOUR_DELAY", 1)

        self.env = os.getenv("ENV")
        self.write_db = Database(
            os.getenv("WRITE_DB_INSTANCE"),
            os.getenv("WRITE_DB_USER"),
            os.getenv("WRITE_DB_PW"),
            os.getenv("WRITE_DB_NAME"),
        )
        self.project = "arxiv-production" if self.env == "PROD" else "arxiv-development"
        self.ip_type = (
            IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC
        )
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_locally = os.getenv("LOG_LOCALLY", False)

        self.cloud_logging_client = None
        self.write_connector = None

        self._set_up_logging()
        logger.info("Initialization of hourly edge requests job complete")

    def _set_up_logging(self):
        logging.basicConfig()
        logger.setLevel(self.log_level)

        if not (self.log_locally):
            logger.info("Initializing cloud logging")
            self.cloud_logging_client = gc_logging.Client(project=self.project)
            self.cloud_logging_client.setup_logging()

    @staticmethod
    def instantiate_connection_pool(ip_type, db: Database) -> tuple[Connector, Engine]:
        connector = Connector(ip_type=ip_type, refresh_strategy="LAZY")

        def getconn() -> pymysql.connections.Connection:
            conn: pymysql.connections.Connection = connector.connect(
                db.instance_name,
                "pymysql",
                user=db.username,
                password=db.password,
                db=db.db_name,
            )
            return conn

        pool = create_engine("mysql+pymysql://", creator=getconn)

        return connector, pool

    def _configure_fastly(self):
        self.fastly_config = fastly.Configuration()
        self.fastly_config.api_token = os.getenv("FASTLY_TOKEN")

        if not self.fastly_config.api_token:
            logger.error("Fastly API token missing! Check environment configuration")
            raise NoRetryError

    def _get_timestamps(self, hour: datetime) -> tuple[int, int]:
        """transform datetime into start and end unix/epoch timestamps"""
        start_time = int(hour.replace(minute=0, second=0, microsecond=0).timestamp())
        end_time = int(hour.replace(minute=59, second=59, microsecond=0).timestamp())

        return start_time, end_time

    def get_fastly_stats(self, hour: datetime) -> Stats:
        start_time, end_time = self._get_timestamps(hour)

        with fastly.ApiClient(self.fastly_config) as client:
            api_instance = stats_api.StatsApi(client)
            options = {
                "service_id": self.FASTLY_SERVICE_ID["arxiv.org"],
                "start_time": start_time,
                "end_time": end_time,
            }

            response = api_instance.get_service_stats(**options)

            try:
                return FastlyStatsApiResponse(**response.to_dict())
            except ValidationError:
                logger.exception(
                    "Could not validate response payload! Check response format"
                )
                raise NoRetryError

    def sum_requests(self, response: FastlyStatsApiResponse) -> int:
        return sum(response.stats[pop].edge_requests for pop in response.stats.keys())

    def write_to_db(self, request_count: int, hour: datetime) -> int:
        self.write_connector, write_pool = self.instantiate_connection_pool(
            self.ip_type, self.write_db
        )
        Session = sessionmaker(bind=write_pool)

        with Session() as session:
            logger.info("Beginning write database session")

            # mark existing rows for deletion
            delete_stmt = delete(HourlyRequests).where(
                HourlyRequests.start_dttm == hour
            )
            result = session.execute(delete_stmt)
            logger.info(f"Number of existing rows to be deleted: {result.rowcount}")

            # add new data to be inserted to the session queue
            new_hourly_requests = HourlyRequests(
                start_dttm=hour, source_id=1, request_count=request_count
            )
            session.add_all(new_hourly_requests)
            logger.info(f"Requests for hour {hour}: {request_count}")

            # commit both the deletion and the insertion as a single transaction
            # will rollback both if one fails
            session.commit()

        logger.info("Write database transaction successfully committed; session closed")

    def _event_time_exceeds_retry_window(self, event_time: datetime) -> bool:
        """Prevent infinite retries by dismissing event timestamps that are too old"""
        current_time = datetime.now(timezone.utc)
        max_event_age = timedelta(minutes=self.MAX_EVENT_AGE_IN_MINUTES)

        if (current_time - event_time) > max_event_age:
            return True
        else:
            return False

    def _validate_cloud_event(self, cloud_event: CloudEvent) -> datetime:
        # take a timezone-aware RFC 3339 string and parse to a datetime object
        # assumes utc timezone
        event_time = parser.isoparse(cloud_event["time"]).replace(tzinfo=timezone.utc)

        if self._event_time_exceeds_retry_window(event_time):
            raise NoRetryError

        # subtract delay
        return event_time - timedelta(hours=self.hour_delay)

    def _validate_date(self, hour: str) -> datetime:
        date_format = "%Y-%m-%d%H"

        try:
            assert len(hour) == 12
            valid_hour = datetime.strptime(hour, date_format)
            return valid_hour.replace(tzinfo=timezone.utc)

        except (AssertionError, ValueError):
            logger.error("Invalid input time! Check input")
            raise NoRetryError

    def _validate_inputs(
        self,
        cloud_event: CloudEvent = None,
        hour: str = None,
    ) -> datetime:
        try:
            if cloud_event:
                logger.info("Received cloud event trigger")
                hour = self._validate_cloud_event(cloud_event)
            elif hour:
                logger.info("Received hour input")
                hour = self._validate_date(hour)
            else:
                logger.error("Must receive either a cloud event or valid hour input!")
                raise NoRetryError

        except NoRetryError:
            raise

        logger.info(f"Query parameters for fastly: hour={hour}")
        return hour

    def _cleanup(self):
        if self.cloud_logging_client:
            self.cloud_logging_client.close()

        if self.write_connector:
            self.write_connector.close()

        if self.fastly_api_client:
            self.fastly_api_client.close()

    def run(self, cloud_event: CloudEvent = None, hour: str = None):
        try:
            hour = self._validate_inputs(cloud_event=cloud_event, hour=hour)
            self._configure_fastly()
            response = self.get_fastly_stats(hour)
            request_count = self.sum_requests(response)
            self.write_to_db(request_count)

        except NoRetryError:
            logger.exception(
                "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
            )
            return


@functions_framework.cloud_event
def get_hourly_edge_requests(cloud_event: CloudEvent):
    job = HourlyEdgeRequestsJob()
    job.run(cloud_event=cloud_event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hour",
        dest="hour",
        help="The hour to be processed, UTC, in 'YYYY-MM-DDHH' format",
        required=True,
    )

    args = parser.parse_args()

    job = HourlyEdgeRequestsJob()
    job.run(hour=args.hour)

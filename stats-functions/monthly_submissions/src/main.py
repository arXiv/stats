import os
import argparse
import logging
from google.cloud import logging as gc_logging

from datetime import datetime, timedelta, timezone, date
from dateutil import parser
from dateutil.relativedelta import relativedelta

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud.sql.connector import Connector, IPTypes
import pymysql

from sqlalchemy import create_engine, select, delete
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from entities import Document

from stats_entities.site_usage import MonthlySubmissions
from models import Database

logger = logging.getLogger(__name__)


class NoRetryError(Exception):
    pass


class MonthlySubmissionsJob:
    MAX_EVENT_AGE_IN_MINUTES = 50  # to limit retries

    def __init__(self):
        self.env = os.getenv("ENV")
        self.read_db = Database(
            os.getenv("READ_DB_INSTANCE"),
            os.getenv("READ_DB_USER"),
            os.getenv("READ_DB_PW"),
            os.getenv("READ_DB_NAME"),
        )
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
        self.log_locally = True if os.getenv("LOG_LOCALLY") else False

        self.cloud_logging_client = None
        self.read_connector = None
        self.write_connector = None

        self._set_up_logging()
        logger.info("Initialization of monthly submissions job complete")

    def _set_up_logging(self):
        logging.basicConfig()
        logger.setLevel(self.log_level)

        if not self.log_locally:
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

    def get_submission_count(self, month: date):
        self.read_connector, read_pool = self.instantiate_connection_pool(
            self.ip_type, self.read_db
        )
        ReadSession = sessionmaker(bind=read_pool)

        month_str = month.strftime("%y%m")

        with ReadSession() as session:
            logger.info("Beginning read database session")

            select_stmt = (
                select(func.count())
                .where(Document.paper_id.like(f"{month_str}%"))
                .select_from(Document)
            )
            return session.scalar(select_stmt)

    def write_to_db(self, month: str, count: int):
        self.write_connector, write_pool = self.instantiate_connection_pool(
            self.ip_type, self.write_db
        )
        WriteSession = sessionmaker(bind=write_pool)

        with WriteSession() as session:
            logger.info("Beginning write database session")

            # mark existing rows for deletion
            delete_stmt = delete(MonthlySubmissions).where(
                MonthlySubmissions.month == month
            )
            result = session.execute(delete_stmt)
            logger.info(f"Number of existing rows to be deleted: {result.rowcount}")

            # add new data to be inserted to the session queue
            new_monthly_submissions = MonthlySubmissions(month=month, count=count)
            session.add(new_monthly_submissions)
            logger.info(f"Submissions for month {month}: {count}")

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

    def _validate_cloud_event(self, cloud_event: CloudEvent) -> date:
        # take a timezone-aware RFC 3339 string and parse to a datetime object
        # assumes utc timezone
        event_time = parser.isoparse(cloud_event["time"]).replace(tzinfo=timezone.utc)

        if self._event_time_exceeds_retry_window(event_time):
            raise NoRetryError

        # set to previous month
        return (event_time - relativedelta(months=1)).replace(day=1).date()

    def _validate_month(self, month: str) -> date:
        try:
            return datetime.strptime(month, "%Y-%m").date()

        except ValueError:
            logger.error("Invalid input month! Check input")
            raise NoRetryError

    def _validate_inputs(
        self,
        cloud_event: CloudEvent = None,
        month: str = None,
    ) -> date:
        try:
            if cloud_event:
                logger.info("Received cloud event trigger")
                month = self._validate_cloud_event(cloud_event)
            elif month:
                logger.info("Received hour input")
                month = self._validate_date(month)
            else:
                logger.error("Must receive either a cloud event or valid hour input!")
                raise NoRetryError

        except NoRetryError:
            raise

        logger.info(f"Parameters for job: month={month}")
        return month

    def _cleanup(self):
        if self.cloud_logging_client:
            self.cloud_logging_client.close()

        if self.read_connector:
            self.read_connector.close()

        if self.write_connector:
            self.write_connector.close()

    def run(self, cloud_event: CloudEvent = None, month: str = None):
        try:
            month = self._validate_inputs(cloud_event=cloud_event, month=month)
            count = self.get_submission_count(month)
            self.write_to_db(month, count)

        except NoRetryError:
            logger.exception(
                "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
            )
            return

        finally:
            self._cleanup()
            logger.info("Cleanup complete")


@functions_framework.cloud_event
def get_monthly_submissions(cloud_event: CloudEvent):
    job = MonthlySubmissionsJob()
    job.run(cloud_event=cloud_event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--month",
        type=str,
        dest="month",
        help="The month to be processed, in 'YYYY-MM' format",
        required=True,
    )

    args = parser.parse_args()

    job = MonthlySubmissionsJob()
    job.run(hour=args.month)

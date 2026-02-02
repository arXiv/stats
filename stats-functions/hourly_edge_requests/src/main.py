import os
import logging
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud.sql.connector import Connector
from google.cloud.sql.connector import IPTypes

import fastly
from fastly.api import stats_api
from fastly.model.stats import Stats

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from config import get_config
from models import FastlyStatsApiResponse
from pydantic import ValidationError

from stats_entities.site_usage import HourlyRequests
from stats_functions.exception import NoRetryError
from stats_functions.utils import (
    set_up_cloud_logging,
    get_engine,
    event_time_exceeds_retry_window,
    parse_cloud_event_time,
)

config = get_config(os.getenv("ENV"))

logging.basicConfig(level=config.log_level)
logger = logging.getLogger(__name__)

set_up_cloud_logging(config)

SessionFactory = None

if config.env != "TEST":
    connector = Connector(ip_type=IPTypes.PUBLIC, refresh_strategy="LAZY")
    SessionFactory = sessionmaker(bind=get_engine(connector, config.db))


def get_timestamps(hour: datetime) -> tuple[int, int]:
    """transform datetime into start and end unix/epoch timestamps"""
    start_time = int(hour.replace(minute=0, second=0, microsecond=0).timestamp())
    end_time = int(hour.replace(minute=59, second=59, microsecond=0).timestamp())

    return start_time, end_time


def get_fastly_stats(start_time: int, end_time: int) -> Stats:
    with fastly.ApiClient(fastly.Configuration()) as client:
        api_instance = stats_api.StatsApi(client)
        options = {
            "service_id": config.fastly_service_id,
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


def sum_requests(response: FastlyStatsApiResponse) -> int:
    return sum(response.stats[pop].edge_requests for pop in response.stats.keys())


def write_to_db(hour: datetime, count: int):
    with SessionFactory() as session:
        logger.info("Beginning write database session")

        delete_stmt = delete(HourlyRequests).where(HourlyRequests.start_dttm == hour)
        result = session.execute(delete_stmt)
        logger.info(f"Number of existing rows to be deleted: {result.rowcount}")

        new_hourly_requests = HourlyRequests(
            start_dttm=hour, source_id=0, request_count=count
        )
        session.add(new_hourly_requests)
        logger.info(f"Requests for hour {hour}: {count}")

        # commit both the deletion and the insertion as a single transaction
        session.commit()

    logger.info("Write database transaction successfully committed; session closed")


# def _validate_cloud_event(self, cloud_event: CloudEvent) -> datetime:
#     # take a timezone-aware RFC 3339 string and parse to a datetime object
#     # assumes utc timezone
#     event_time = parser.isoparse(cloud_event["time"]).replace(tzinfo=timezone.utc)

#     if self._event_time_exceeds_retry_window(event_time):
#         raise NoRetryError

#     # subtract delay
#     return event_time - timedelta(hours=self.hour_delay)

# def _validate_date(self, hour: str) -> datetime:
#     date_format = "%Y-%m-%d%H"

#     try:
#         assert len(hour) == 12
#         valid_hour = datetime.strptime(hour, date_format)

#         # assumes utc timezone
#         return valid_hour.replace(tzinfo=timezone.utc)

#     except (AssertionError, ValueError):
#         logger.error("Invalid input time! Check input")
#         raise NoRetryError

# def _validate_inputs(
#     self,
#     cloud_event: CloudEvent = None,
#     hour: str = None,
# ) -> datetime:
#     try:
#         if cloud_event:
#             logger.info("Received cloud event trigger")
#             hour = self._validate_cloud_event(cloud_event)
#         elif hour:
#             logger.info("Received hour input")
#             hour = self._validate_date(hour)
#         else:
#             logger.error("Must receive either a cloud event or valid hour input!")
#             raise NoRetryError

#     except NoRetryError:
#         raise

#     # round down to the start of the hour
#     hour = hour.replace(minute=0, second=0, microsecond=0)

#     logger.info(f"Query parameters for fastly: hour={hour}")
#     return hour


@functions_framework.cloud_event
def get_hourly_edge_requests(cloud_event: CloudEvent):
    try:
        hour = validate_inputs(cloud_event)
        start_time, end_time = get_timestamps(hour)
        response = get_fastly_stats(start_time, end_time)
        count = sum_requests(response)
        write_to_db(hour, count)

    except NoRetryError:
        logger.exception(
            "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
        )
        return

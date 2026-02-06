import os
import logging
from datetime import datetime, timedelta, timezone

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud.sql.connector import Connector
from google.cloud.sql.connector import IPTypes

import fastly
from fastly.api import stats_api
from fastly.exceptions import ApiException

from sqlalchemy.orm import sessionmaker

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


def get_fastly_stats(start_time: int, end_time: int) -> FastlyStatsApiResponse:
    with fastly.ApiClient(fastly.Configuration()) as client:
        api_instance = stats_api.StatsApi(client)
        options = {
            "service_id": config.fastly_service_id["arxiv.org"],
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
        except ApiException as e:
            if e.status == 400:
                logger.exception("Bad request to Fastly API! Check message")
                raise NoRetryError from e


def sum_requests(response: FastlyStatsApiResponse) -> int:
    return sum(response.stats[pop].edge_requests for pop in response.stats.keys())


def write_to_db(hour: datetime, count: int):
    with SessionFactory() as session:
        logger.info("Beginning write database session")

        session.query(HourlyRequests).where(HourlyRequests.start_dttm == hour).delete()
        session.add(HourlyRequests(start_dttm=hour, source_id=0, request_count=count))

        logger.info(f"Requests for hour {hour}: {count}")

        # commit both the deletion and the insertion as a single transaction
        session.commit()

    logger.info("Write database transaction successfully committed; session closed")


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

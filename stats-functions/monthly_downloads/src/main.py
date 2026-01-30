import os
import logging
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud.sql.connector import Connector
from google.cloud.sql.connector import IPTypes


from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from config import get_config

from stats_entities.site_usage import HourlyDownloads, MonthlyDownloads

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

if config.env != "TEST":
    connector = Connector(ip_type=IPTypes.PUBLIC, refresh_strategy="LAZY")
    SessionFactory = sessionmaker(bind=get_engine(connector, config.db))


def get_first_and_last_hour(month: date) -> tuple[datetime, datetime]:
    first_hour = datetime(month.year, month.month, month.day)
    last_hour = (
        (month + relativedelta(months=1)) - relativedelta(microseconds=1)
    ).replace(minute=0, second=0, microsecond=0)

    return first_hour, last_hour


def get_download_count(start: datetime, end: datetime):
    with SessionFactory() as session:
        logger.info("Beginning database session")

        return session.execute(
            select(func.sum(HourlyDownloads.primary_count))
            .where(HourlyDownloads.start_dttm >= start)
            .where(HourlyDownloads.start_dttm <= end)
        ).scalar()


def write_to_db(month: date, count: int):
    with SessionFactory() as session:
        logger.info("Beginning write database session")

        session.query(MonthlyDownloads).where(MonthlyDownloads.month == month).delete()
        session.add(MonthlyDownloads(month=month, downloads=count))

        logger.info(f"Downloads for month {month}: {count}")

        # commit both the deletion and the insertion as a single transaction
        session.commit()

    logger.info("Write database transaction successfully committed; session closed")


def validate_cloud_event(cloud_event: CloudEvent) -> date:
    event_time = parse_cloud_event_time(cloud_event)

    if event_time_exceeds_retry_window(config, event_time):
        raise NoRetryError

    return (event_time - relativedelta(months=1)).replace(day=1).date()


def validate_month(month: str) -> date:
    return datetime.strptime(month, "%Y-%m-%d").replace(day=1).date()


def validate_inputs(cloud_event: CloudEvent) -> date:
    try:
        month = validate_month(cloud_event["month"])
        logger.info("Received valid month as attribute")

    except (KeyError, ValueError):
        month = validate_cloud_event(cloud_event)
        logger.info("Received valid event time")

    except NoRetryError:
        raise

    logger.info(f"Parameters for job: month={month}")
    return month


@functions_framework.cloud_event
def get_monthly_submissions(cloud_event: CloudEvent):
    try:
        month = validate_inputs(cloud_event=cloud_event)
        start, end = get_first_and_last_hour(month)
        count = get_download_count(start, end)
        write_to_db(month, count)

    except NoRetryError:
        logger.exception(
            "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
        )
        return

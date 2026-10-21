import logging
import os
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import functions_framework
from arxiv_functions.exception import NoRetryError
from arxiv_functions.utils import (
    event_time_exceeds_retry_window,
    get_engine_unix_socket,
    parse_cloud_event_time,
    set_up_cloud_logging,
)
from cloudevents.http import CloudEvent
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from stats_entities.site_usage import HourlyDownloads, MonthlyDownloads

from config import get_config

config = get_config(os.getenv("ENV"))

logger = logging.getLogger(__name__)
set_up_cloud_logging(config)

engine = None
SessionFactory = None


def get_month_range(month: date) -> tuple[datetime, datetime]:
    """the arXiv-local month as a [start, end) range of naive UTC datetimes, to match the
    naive UTC start_dttm column in the DB"""
    start = datetime(month.year, month.month, 1, tzinfo=ZoneInfo(config.arxiv_timezone))
    end = start + relativedelta(months=1)

    return (
        start.astimezone(UTC).replace(tzinfo=None),
        end.astimezone(UTC).replace(tzinfo=None),
    )


def get_download_count(start: datetime, end: datetime) -> int | None:
    with SessionFactory() as session:
        logger.info("Beginning database session")

        return session.execute(
            select(func.sum(HourlyDownloads.primary_count))
            .where(HourlyDownloads.start_dttm >= start)
            .where(HourlyDownloads.start_dttm < end)
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
        logger.exception("Event time exceeds retry window!")
        raise NoRetryError

    return (event_time - relativedelta(months=1)).replace(day=1).date()


def validate_month(cloud_event: CloudEvent) -> date:
    month = cloud_event.data["message"]["attributes"]["month"]

    # the arXiv-local month, stored as-is in the Date column
    return datetime.strptime(month, "%Y-%m-%d").replace(day=1).date()  # noqa: DTZ007


def validate_inputs(cloud_event: CloudEvent) -> date:
    try:
        month = validate_month(cloud_event)
        logger.info("Received valid month as attribute")

    except (KeyError, ValueError):
        month = validate_cloud_event(cloud_event)
        logger.info("Received valid event time")

    except NoRetryError:
        raise

    logger.info(f"Parameters for job: month={month}")
    return month


@functions_framework.cloud_event
def get_monthly_downloads(cloud_event: CloudEvent):
    global engine, SessionFactory

    if config.env != "TEST" and SessionFactory is None:
        logger.info("Initializing engine and sessionmaker")
        engine = get_engine_unix_socket(config.db)
        SessionFactory = sessionmaker(bind=engine)

    try:
        month = validate_inputs(cloud_event)
        start, end = get_month_range(month)
        count = get_download_count(start, end)

        # no hourly rows: SUM is NULL. Writing it would replace the stored total with NULL
        if count is None:
            logger.error(
                f"No hourly downloads for month {month}; stored total left unchanged"
            )
            raise NoRetryError

        write_to_db(month, count)

    except NoRetryError:
        logger.exception(
            "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
        )
        return

import logging
import os
from datetime import date, datetime

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
from stats_entities.site_usage import MonthlySubmissions

from config import get_config
from entities import Document

config = get_config(os.getenv("ENV"))

logger = logging.getLogger(__name__)
set_up_cloud_logging(config)

read_engine = None
ReadSessionFactory = None

write_engine = None
WriteSessionFactory = None


def get_submission_count(month: date) -> int:
    month_str = month.strftime("%y%m")

    with ReadSessionFactory() as session:
        logger.info("Beginning read database session")

        return session.execute(
            select(func.count())
            .where(Document.paper_id.like(f"{month_str}%"))
            .select_from(Document)
        ).scalar()


def write_to_db(month: date, count: int):
    with WriteSessionFactory() as session:
        logger.info("Beginning write database session")

        session.query(MonthlySubmissions).where(
            MonthlySubmissions.month == month
        ).delete()
        session.add(MonthlySubmissions(month=month, count=count))

        logger.info(f"Submissions for month {month}: {count}")

        # commit both the deletion and the insertion as a single transaction
        session.commit()

    logger.info("Write database transaction successfully committed; session closed")


def validate_cloud_event(cloud_event: CloudEvent) -> list[date]:
    """Scheduled runs recount the previous month and the current month so far.

    Recounting the previous month every day keeps it correct after the
    month-end announcement, which can land after midnight UTC on the 1st.
    """
    event_time = parse_cloud_event_time(cloud_event)

    if event_time_exceeds_retry_window(config, event_time):
        logger.exception("Event time exceeds retry window!")
        raise NoRetryError

    current_month = event_time.replace(day=1).date()
    return [current_month - relativedelta(months=1), current_month]


def validate_month(cloud_event: CloudEvent) -> date:
    month = cloud_event.data["message"]["attributes"]["month"]

    # naive UTC; immediately truncated to a date, matching the Date column in the DB
    return datetime.strptime(month, "%Y-%m-%d").replace(day=1).date()  # noqa: DTZ007


def validate_inputs(cloud_event: CloudEvent) -> list[date]:
    try:
        months = [validate_month(cloud_event)]
        logger.info("Received valid month as attribute")

    except (KeyError, ValueError):
        months = validate_cloud_event(cloud_event)
        logger.info("Received valid event time")

    except NoRetryError:
        raise

    logger.info(f"Parameters for job: months={[str(m) for m in months]}")
    return months


@functions_framework.cloud_event
def get_monthly_submissions(cloud_event: CloudEvent):
    global read_engine, ReadSessionFactory, write_engine, WriteSessionFactory

    if config.env != "TEST":
        if ReadSessionFactory is None:
            logger.info("Initializing read engine and sessionmaker")
            read_engine = get_engine_unix_socket(config.read_db)
            ReadSessionFactory = sessionmaker(bind=read_engine)
        if WriteSessionFactory is None:
            logger.info("Initializing write engine and sessionmaker")
            write_engine = get_engine_unix_socket(config.write_db)
            WriteSessionFactory = sessionmaker(bind=write_engine)

    try:
        for month in validate_inputs(cloud_event=cloud_event):
            count = get_submission_count(month)
            write_to_db(month, count)

    except NoRetryError:
        logger.exception(
            "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
        )
        return

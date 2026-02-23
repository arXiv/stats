import os
import logging
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import functions_framework
from cloudevents.http import CloudEvent

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from config import get_config

from stats_entities.site_usage import MonthlySubmissions
from entities import Document

from stats_functions.exception import NoRetryError
from stats_functions.utils import (
    set_up_cloud_logging,
    get_engine_unix_socket,
    event_time_exceeds_retry_window,
    parse_cloud_event_time,
)

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


def validate_cloud_event(cloud_event: CloudEvent) -> date:
    event_time = parse_cloud_event_time(cloud_event)

    if event_time_exceeds_retry_window(config, event_time):
        logger.exception("Event time exceeds retry window!")
        raise NoRetryError

    return (event_time - relativedelta(months=1)).replace(day=1).date()


def validate_month(cloud_event: CloudEvent) -> date:
    month = cloud_event.data["message"]["attributes"]["month"]

    return datetime.strptime(month, "%Y-%m-%d").replace(day=1).date()


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
        month = validate_inputs(cloud_event=cloud_event)
        count = get_submission_count(month)
        write_to_db(month, count)

    except NoRetryError:
        logger.exception(
            "A NoRetry exception has been raised! Will not retry. Fix the problem and manually run the function to patch data as needed."
        )
        return

import csv
import io
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from functools import wraps
from zoneinfo import ZoneInfo

from flask import current_app
from pydantic import BaseModel


def url_param_to_date(param: str) -> date:
    """transforms a url date param parsed as a string into a date object"""
    return datetime.strptime(param, "%Y%m%d").date()


def url_param_to_arxiv_datetime(param: str) -> datetime:
    """transforms a url datetime param parsed as a string into a datetime object"""
    return datetime.strptime(param, "%Y%m%d%H").replace(
        tzinfo=ZoneInfo(current_app.config["ARXIV_TIMEZONE"])
    )


def set_fastly_headers(keys: list[str] = ["stats"]):
    def decorator(function: Callable) -> Callable:
        @wraps(function)
        def decorated_function(*args, **kwargs):
            response = function(*args, **kwargs)
            max_age = current_app.config["FASTLY_MAX_AGE"]

            response.headers["Surrogate-Control"] = f"max-age={max_age}"
            response.headers["Surrogate-Key"] = " ".join(keys)

            return response

        return decorated_function

    return decorator


def get_arxiv_current_time() -> datetime:
    return datetime.now(tz=ZoneInfo(current_app.config["ARXIV_TIMEZONE"]))


def get_utc_start_and_end_times(date: date) -> tuple[datetime, datetime]:
    """take a non-aware date object, assume arxiv local time,
    return start and end datetimes representing the beginning of the
    first and last hour of that day, utc
    """
    start = datetime(
        date.year,
        date.month,
        date.day,
        0,
        tzinfo=ZoneInfo(current_app.config["ARXIV_TIMEZONE"]),
    ).astimezone(UTC)
    end = datetime(
        date.year,
        date.month,
        date.day,
        23,
        tzinfo=ZoneInfo(current_app.config["ARXIV_TIMEZONE"]),
    ).astimezone(UTC)
    return start, end


def format_as_csv(models: Sequence[BaseModel]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=models[0].model_dump().keys())
    writer.writeheader()
    for model in models:
        writer.writerow(model.model_dump())

    return output.getvalue()


def utc_to_arxiv_local(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC).astimezone(
        ZoneInfo(current_app.config["ARXIV_TIMEZONE"])
    )

import csv
import io
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Response, current_app, request
from pydantic import BaseModel


def url_param_to_date(param: str) -> date:
    """transforms a url date param parsed as a string into a date object"""
    return datetime.strptime(param, "%Y%m%d").date()


def url_param_to_arxiv_datetime(param: str) -> datetime:
    """transforms a url datetime param parsed as a string into a datetime object"""
    return datetime.strptime(param, "%Y%m%d%H").replace(
        tzinfo=ZoneInfo(current_app.config["ARXIV_TIMEZONE"])
    )


HOUR = 3600
DAY = 86400

# a date's hourly data is complete once its last hour is aggregated
DATE_COMPLETE_AFTER = timedelta(hours=3)


def max_age_for_requested_date() -> int:
    """the year-long max age for a completed date, an hour for one still filling in"""
    requested = request.args.get("date", type=url_param_to_date)
    complete_before = (get_arxiv_current_time() - DATE_COMPLETE_AFTER).date()

    if requested is not None and requested < complete_before:
        return current_app.config["FASTLY_MAX_AGE"]
    return HOUR


def set_fastly_headers(
    keys: list[str] = ["stats"], max_age: int | Callable[[], int] | None = None
):
    """max_age in seconds, or a function returning it per request; defaults to
    FASTLY_MAX_AGE. Fastly may serve a stale copy for a minute while it refetches, and for
    a day if stats-api is failing.
    """

    def decorator(function: Callable) -> Callable:
        @wraps(function)
        def decorated_function(*args, **kwargs):
            response = function(*args, **kwargs)
            if max_age is None:
                age = current_app.config["FASTLY_MAX_AGE"]
            elif isinstance(max_age, int):
                age = max_age
            else:
                age = max_age()

            return add_surrogate_headers(response, keys, age)

        return decorated_function

    return decorator


def add_surrogate_headers(
    response: Response, keys: list[str], max_age: int
) -> Response:
    response.headers["Surrogate-Control"] = (
        f"max-age={max_age}, stale-while-revalidate=60, stale-if-error={DAY}"
    )
    response.headers["Surrogate-Key"] = " ".join(keys)

    return response


def set_static_fastly_headers(response: Response) -> Response:
    if request.endpoint == "static" and response.status_code < 400:
        add_surrogate_headers(response, ["stats", "static"], DAY)

    return response


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

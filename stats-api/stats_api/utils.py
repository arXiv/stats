from flask import current_app
import io
import csv
from pydantic import BaseModel
from typing import List, Tuple
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from flask import Response
from functools import wraps


def url_param_to_date(param: str):
    return datetime.strptime(param, "%Y%m%d").date()


def set_fastly_headers(keys: List[str] = ["stats"]) -> Response:
    def decorator(function):
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


def get_utc_start_and_end_times(date: date) -> Tuple[datetime, datetime]:
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
    ).astimezone(timezone.utc)
    end = datetime(
        date.year,
        date.month,
        date.day,
        23,
        tzinfo=ZoneInfo(current_app.config["ARXIV_TIMEZONE"]),
    ).astimezone(timezone.utc)
    return start, end


def format_as_csv(models: List[BaseModel]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=models[0].model_dump().keys())
    writer.writeheader()
    for model in models:
        writer.writerow(model.model_dump())

    return output.getvalue()


def utc_to_arxiv_local(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc).astimezone(
        ZoneInfo(current_app.config["ARXIV_TIMEZONE"])
    )

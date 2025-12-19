from flask import current_app
import io
import csv
from pydantic import BaseModel
from typing import List, Tuple
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def get_arxiv_current_date() -> date:
    return datetime.now(ZoneInfo(current_app.config["ARXIV_TIMEZONE"])).date()


def get_utc_start_and_end_times(date: date) -> Tuple[datetime, datetime]:
    """take a non-aware date object, assume arxiv local time,
    return start and end datetimes representing the first and last hour of that day,
    transformed to utc"""
    start = datetime(
        date.year,
        date.month,
        date.day,
        23,
        tzinfo=ZoneInfo(current_app.config["ARXIV_TIMEZONE"]),
    ).astimezone(timezone.utc)
    end = datetime(
        date.year,
        date.month,
        date.day,
        0,
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

from collections.abc import Callable
from datetime import date, datetime, timedelta

from flask import Response, request

from stats_api.utils import get_arxiv_current_time, url_param_to_date

HOUR = 3600
DAY = 86400
YEAR = 31557600

# a date's hourly data is complete once its last hour is aggregated
DATE_COMPLETE_AFTER = timedelta(hours=3)


def max_age_for_date(requested: date | None, now: datetime) -> int:
    complete_before = (now - DATE_COMPLETE_AFTER).date()

    if requested is not None and requested < complete_before:
        return YEAR
    return HOUR


def _max_age_for_requested_date() -> int:
    requested = request.args.get("date", type=url_param_to_date)

    return max_age_for_date(requested, get_arxiv_current_time())


# endpoint -> (surrogate keys, max age in seconds or a function returning it)
CACHE_POLICY: dict[str, tuple[list[str], int | Callable[[], int]]] = {
    "stats_ui.main": (["stats", "main"], YEAR),
    "stats_ui.today": (["stats", "today"], _max_age_for_requested_date),
    "stats_ui.monthly_submissions": (["stats", "submissions", "monthly"], DAY),
    "stats_ui.monthly_downloads": (["stats", "downloads", "monthly"], HOUR),
    "stats_api.get_hourly_requests": (
        ["stats", "requests", "hourly"],
        _max_age_for_requested_date,
    ),
    "stats_api.get_monthly_submissions": (["stats", "submissions", "monthly"], DAY),
    "stats_api.get_monthly_downloads": (["stats", "downloads", "monthly"], YEAR),
    "static": (["stats", "static"], DAY),
}


def set_fastly_headers(response: Response) -> Response:
    policy = CACHE_POLICY.get(request.endpoint or "")
    if policy is None or response.status_code >= 400:
        return response

    keys, max_age = policy
    age = max_age if isinstance(max_age, int) else max_age()

    response.headers["Surrogate-Control"] = (
        f"max-age={age}, stale-while-revalidate=60, stale-if-error={DAY}"
    )
    response.headers["Surrogate-Key"] = " ".join(keys)

    return response

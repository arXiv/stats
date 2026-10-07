from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from flask import Response

from stats_api.cache import (
    CACHE_POLICY,
    HOUR,
    YEAR,
    max_age_for_date,
    set_fastly_headers,
)

NY = ZoneInfo("America/New_York")


@pytest.mark.parametrize(
    ("requested", "now", "expected"),
    [
        # yesterday is complete once its last hour has been aggregated
        (date(2025, 11, 10), datetime(2025, 11, 11, 4, tzinfo=NY), YEAR),
        (date(2025, 11, 10), datetime(2025, 11, 11, 1, tzinfo=NY), HOUR),
        (date(2025, 11, 11), datetime(2025, 11, 11, 12, tzinfo=NY), HOUR),
        (date(2025, 11, 12), datetime(2025, 11, 11, 12, tzinfo=NY), HOUR),
        (None, datetime(2025, 11, 11, 12, tzinfo=NY), HOUR),
    ],
)
def test_max_age_for_date(requested, now, expected):
    assert max_age_for_date(requested, now) == expected


def test_every_route_has_a_cache_policy(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}

    assert endpoints == set(CACHE_POLICY)


@pytest.mark.parametrize(
    ("path", "status", "expected"),
    [
        ("/stats/monthly_downloads", 200, ("max-age=3600,", "stats downloads monthly")),
        (
            "/stats/monthly_submissions",
            200,
            ("max-age=86400,", "stats submissions monthly"),
        ),
        ("/stats/monthly_downloads", 500, None),
        ("/stats/not-a-route", 200, None),
    ],
)
def test_set_fastly_headers(app, path, status, expected):
    with app.test_request_context(path):
        response = set_fastly_headers(Response(status=status))

    if expected is None:
        assert "Surrogate-Control" not in response.headers
    else:
        control, keys = expected
        assert response.headers["Surrogate-Control"] == (
            f"{control} stale-while-revalidate=60, stale-if-error=86400"
        )
        assert response.headers["Surrogate-Key"] == keys

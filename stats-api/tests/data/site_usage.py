from datetime import date, datetime
from stats_entities.site_usage import (
    HourlyRequests,
    MonthlySubmissions,
    HourlyDownloads,
)

"""
cases covered: 
- multiple request sources for the same day
- hours spanning multiple days utc but same day US/New_York
"""
mock_hourly_requests = [
    HourlyRequests(
        start_dttm=datetime(2025, 11, 10, 10),
        source_id=0,
        request_count=3000000,
    ),
    HourlyRequests(
        start_dttm=datetime(2025, 11, 10, 11),
        source_id=0,
        request_count=4000000,
    ),
    HourlyRequests(
        start_dttm=datetime(2025, 11, 11, 4),
        source_id=0,
        request_count=4400000,
    ),
    HourlyRequests(
        start_dttm=datetime(2025, 11, 11, 5),
        source_id=0,
        request_count=3300000,
    ),
    HourlyRequests(
        start_dttm=datetime(2025, 11, 10, 12),
        source_id=1,
        request_count=3000,
    ),
]

mock_monthly_submissions = [
    MonthlySubmissions(month=date(2024, 12, 1), count=20000),
    MonthlySubmissions(month=date(2025, 1, 1), count=22000),
    MonthlySubmissions(month=date(2025, 5, 1), count=25000),
]

mock_hourly_downloads = [
    HourlyDownloads(
        country="united states",
        download_type="html",
        archive="astro-ph",
        category="astro-ph",
        primary_count=10,
        cross_count=0,
        start_dttm=datetime(2025, 11, 5, 6),
    ),
    HourlyDownloads(
        country="germany",
        download_type="pdf",
        archive="astro-ph",
        category="astro-ph",
        primary_count=2,
        cross_count=2,
        start_dttm=datetime(2025, 11, 5, 7),
    ),
    HourlyDownloads(
        country="united states",
        download_type="pdf",
        archive="cs",
        category="cs.AI",
        primary_count=3,
        cross_count=1,
        start_dttm=datetime(2025, 11, 6, 6),
    ),
    HourlyDownloads(
        country="germany",
        download_type="pdf",
        archive="astro-ph",
        category="astro-ph",
        primary_count=5,
        cross_count=2,
        start_dttm=datetime(2025, 12, 1, 7),
    ),
    HourlyDownloads(
        country="united states",
        download_type="pdf",
        archive="cs",
        category="cs.AI",
        primary_count=5,
        cross_count=1,
        start_dttm=datetime(2025, 12, 2, 6),
    ),
]

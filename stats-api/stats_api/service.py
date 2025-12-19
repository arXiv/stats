from flask import current_app
from datetime import date
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta

from stats_api.respository import SiteUsageRepository
from stats_api.utils import get_utc_start_and_end_times, format_as_csv
from stats_api.models import (
    TodayPageData,
    DownloadsPageData,
    SubmissionsPageData,
)

import logging

logger = logging.getLogger(__name__)


class StatsService:
    @staticmethod
    def get_today_page_data(date: date) -> TodayPageData:
        """assumes date is arxiv local"""
        start, end = get_utc_start_and_end_times(date)
        total_requests = SiteUsageRepository.get_total_requests(start, end)

        return TodayPageData(
            arxiv_current_date=date,
            arxiv_timezone=current_app.config["ARXIV_TIMEZONE"],
            total_requests=total_requests,
        )

    @staticmethod
    def get_submissions_page_data(date: date) -> SubmissionsPageData:
        """assumes date is arxiv local"""
        time_delta = relativedelta(date - current_app.config["ARXIV_START_DATE"])
        submissions = SiteUsageRepository.get_total_submissions(date)

        total_submissions = submissions - current_app.config["TOTAL_DELETED_PAPERS"]
        total_adjusted = (
            submissions
            - current_app.config["TOTAL_DELETED_PAPERS"]
            + current_app.config["TOTAL_MIGRATED_PAPERS"]
        )

        return SubmissionsPageData(
            arxiv_current_date=date,
            arxiv_start_date=current_app.config["ARXIV_START_DATE"],
            arxiv_age_in_years=time_delta.years,
            total_submissions=total_submissions,
            total_migrated=current_app.config["TOTAL_MIGRATED_PAPERS"],
            total_deleted=current_app.config["TOTAL_DELETED_PAPERS"],
            total_submissions_adjusted=total_adjusted,
        )

    @staticmethod
    def get_downloads_page_data() -> DownloadsPageData:
        latest_hour = SiteUsageRepository.get_latest_hour_for_downloads()
        total_downloads = SiteUsageRepository.get_total_downloads(latest_hour)

        arxiv_latest_hour = latest_hour.astimezone(
            ZoneInfo(current_app.config["ARXIV_TIMEZONE"])
        )

        return DownloadsPageData(
            arxiv_latest_month=date(arxiv_latest_hour.year, arxiv_latest_hour.month, 1),
            total_downloads=total_downloads,
        )

    @staticmethod
    def get_hourly_requests(date: date) -> str:
        """assumes date is arxiv local"""
        start, end = get_utc_start_and_end_times(date)
        hourly_requests = SiteUsageRepository.get_hourly_requests(start, end)

        return format_as_csv(hourly_requests)  # type: ignore

    @staticmethod
    def get_monthly_downloads() -> str:
        monthly_downloads = SiteUsageRepository.get_monthly_downloads()

        return format_as_csv(monthly_downloads)  # type: ignore

    @staticmethod
    def get_monthly_submissions() -> str:
        monthly_submissions = SiteUsageRepository.get_monthly_submissions()

        return format_as_csv(monthly_submissions)  # type: ignore

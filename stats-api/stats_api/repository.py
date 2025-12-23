from datetime import date, datetime
from typing import List
from sqlalchemy import func, desc

from stats_api.config.database import db
from stats_api.models import MonthlyDownloads, HourlyRequests_, MonthlySubmissions_
from stats_entities.site_usage import (
    HourlyDownloads,
    MonthlySubmissions,
    HourlyRequests,
)


class SiteUsageRepository:
    """all returned date/datetime objects are timezone naive, but utc"""

    @staticmethod
    def get_total_requests(start: datetime, end: datetime) -> int:
        """start and end should be utc"""
        return db.session.execute(
            db.select(func.sum(HourlyRequests.request_count)).where(
                HourlyRequests.source_id == 0,
                HourlyRequests.start_dttm >= start,
                HourlyRequests.start_dttm <= end,
            )
        ).scalar()

    @staticmethod
    def get_hourly_requests(start: datetime, end: datetime) -> List[HourlyRequests_]:
        """start and end should be utc"""
        results = (
            db.session.execute(
                db.select(HourlyRequests).where(
                    HourlyRequests.source_id == 0,
                    HourlyRequests.start_dttm >= start,
                    HourlyRequests.start_dttm <= end,
                )
            )
            .scalars()
            .all()
        )

        return [HourlyRequests_.model_validate(row) for row in results]

    @staticmethod
    def get_total_submissions(date: date) -> int:
        return db.session.execute(
            db.select(func.sum(MonthlySubmissions.count)).where(
                MonthlySubmissions.month <= date
            )
        ).scalar()

    @staticmethod
    def get_monthly_submissions() -> List[MonthlySubmissions_]:
        results = db.session.execute(db.select(MonthlySubmissions)).scalars().all()

        return [MonthlySubmissions_.model_validate(row) for row in results]

    @staticmethod
    def get_latest_hour_for_downloads() -> datetime:
        return db.session.execute(
            db.select(func.max(HourlyDownloads.start_dttm))
        ).scalar()

    @staticmethod
    def get_total_downloads(hour: datetime) -> int:
        """hour should be utc"""
        return db.session.execute(
            db.select(func.sum(HourlyDownloads.primary_count)).where(
                HourlyDownloads.start_dttm <= hour
            )
        ).scalar()

    @staticmethod
    def get_monthly_downloads() -> List[MonthlyDownloads]:
        results = db.session.execute(
            db.select(
                func.extract("year", HourlyDownloads.start_dttm).label("year"),
                func.extract("month", HourlyDownloads.start_dttm).label("month"),
                func.sum(HourlyDownloads.primary_count).label("downloads"),
            )
            .group_by("year", "month")
            .order_by(desc("year"), desc("month"))
        ).all()  # TODO denormalize table or otherwise optimize

        return [
            MonthlyDownloads(
                month=date(row.year, row.month, 1), downloads=row.downloads
            )
            for row in results
        ]

from datetime import date, datetime
from typing import List
from sqlalchemy import func, desc

from stats_api.config.database import db
from stats_api.models import MonthlyDownloads_, HourlyRequests_, MonthlySubmissions_
from stats_entities.site_usage import (
    HourlyDownloads,
    MonthlyDownloads,
    MonthlySubmissions,
    HourlyRequests,
)


class SiteUsageRepository:
    """accepts and returns timezone naive, but utc date/datetime objects"""

    @staticmethod
    def get_total_requests(start: datetime, end: datetime) -> int:
        return db.session.execute(
            db.select(func.sum(HourlyRequests.request_count)).where(
                HourlyRequests.source_id == 0,
                HourlyRequests.start_dttm >= start,
                HourlyRequests.start_dttm <= end,
            )
        ).scalar()

    @staticmethod
    def get_hourly_requests(start: datetime, end: datetime) -> List[HourlyRequests_]:
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
    def get_total_downloads_for_hour_range(
        start_hour: datetime, end_hour: datetime
    ) -> int:
        return db.session.execute(
            db.select(func.sum(HourlyDownloads.primary_count))
            .where(HourlyDownloads.start_dttm >= start_hour)
            .where(HourlyDownloads.start_dttm <= end_hour)
        ).scalar()

    @staticmethod
    def get_total_downloads(month: date) -> int:
        """month object should represent the first day of that month"""
        return db.session.execute(
            db.select(func.sum(MonthlyDownloads.downloads)).where(
                MonthlyDownloads.month < month
            )
        ).scalar()

    @staticmethod
    def get_monthly_downloads(month: date) -> List[MonthlyDownloads_]:
        """month object should represent the first day of that month"""
        results = db.session.execute(
            db.select(MonthlyDownloads.month, MonthlyDownloads.downloads)
            .where(MonthlyDownloads.month < month)
            .order_by(MonthlyDownloads.month)
        ).all()

        return [MonthlyDownloads_.model_validate(row) for row in results]

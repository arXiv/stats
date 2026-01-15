from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime


class OrmBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, extra="ignore", populate_by_name=True
    )


class TodayPageData(BaseModel):
    arxiv_current_time: datetime
    arxiv_requested_date: date
    arxiv_timezone: str
    total_requests: int


class DownloadsPageData(BaseModel):
    arxiv_latest_month: date
    total_downloads: int


class SubmissionsPageData(BaseModel):
    arxiv_current_date: date
    arxiv_start_date: date
    arxiv_age_in_years: int
    total_submissions: int
    total_migrated: int
    total_deleted: int
    total_submissions_adjusted: int


class HourlyRequests_(OrmBase):
    hour: datetime = Field(alias="start_dttm")
    requests: int = Field(alias="request_count")


class MonthlySubmissions_(OrmBase):
    month: date
    submissions: int = Field(alias="count")


class MonthlyDownloads(BaseModel):
    month: date
    downloads: int

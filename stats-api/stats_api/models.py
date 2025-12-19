from pydantic import BaseModel, ConfigDict
from datetime import date, datetime


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class TodayPageData(BaseModel): # TODO update template
    # current_dt: date
    # requested_dt: date
    # business_tz: str
    # normal_count: int
    # admin_count: int
    # num_nodes: int
    arxiv_current_date: date
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
    start_dttm: datetime
    request_count: int


class MonthlySubmissions_(OrmBase):
    month: date
    count: int


class MonthlyDownloads(BaseModel):
    month: date
    downloads: int

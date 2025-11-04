from sqlalchemy import Column, String, Integer, Date, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import declarative_base


SiteUsageBase = declarative_base()


class HourlyDownloads(SiteUsageBase):
    __tablename__ = "hourly_downloads"

    country = Column(String(255), primary_key=True)
    download_type = Column(
        String(16),
        Enum("pdf", "html", "src", name="download_type_enum"),
        primary_key=True,
    )
    archive = Column(String(16))
    category = Column(String(32), primary_key=True)
    primary_count = Column(Integer)
    cross_count = Column(Integer)
    start_dttm = Column(DateTime, primary_key=True)


class HistoricalHourlyRequests(SiteUsageBase):
    __tablename__ = "historical_hourly_requests"

    ymd = Column(Date, primary_key=True)
    hour = Column(Integer, primary_key=True)
    node_num = Column(Integer, primary_key=True)
    access_type = Column(String(1), primary_key=True)
    connections = Column(Integer)


class HourlyRequests(SiteUsageBase):
    __tablename__ = "hourly_requests"

    start_dttm = Column(DateTime, primary_key=True)
    source_id = Column(
        TINYINT(unsigned=True), ForeignKey("request_sources.id"), primary_key=True
    )
    request_count = Column(Integer)


class RequestSources(SiteUsageBase):
    __tablename__ = "request_sources"

    id = Column(TINYINT(unsigned=True), primary_key=True, autoincrement=False)
    description = Column(String(255))

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
    month = Column(Date)


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
        TINYINT(unsigned=True).with_variant(Integer, "sqlite"), ForeignKey("requests_source.id"), primary_key=True
    )
    request_count = Column(Integer)


class RequestsSource(SiteUsageBase):
    __tablename__ = "requests_source"

    id = Column(TINYINT(unsigned=True).with_variant(Integer, "sqlite"), primary_key=True, autoincrement=False)
    description = Column(String(255))


class MonthlySubmissions(SiteUsageBase):
    __tablename__ = "monthly_submissions"

    month = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False)

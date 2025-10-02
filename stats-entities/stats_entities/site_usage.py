from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Enum,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import (
    declarative_base,
)

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

    __table_args__ = (
        PrimaryKeyConstraint("country", "download_type", "category", "start_dttm"),
    )
    
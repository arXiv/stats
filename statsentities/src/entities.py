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

ReadBase = declarative_base()
WriteBase = declarative_base()


class DocumentCategory(ReadBase):
    __tablename__ = "arXiv_document_category"

    document_id = Column(Integer, primary_key=True, nullable=False, index=True)
    category = Column(String, primary_key=True, nullable=False, index=True)
    is_primary = Column(Integer, nullable=False)


class Metadata(ReadBase):
    __tablename__ = "arXiv_metadata"

    metadata_id = Column(Integer, primary_key=True)
    document_id = Column(Integer, nullable=False, index=True)
    paper_id = Column(String(64), nullable=False)
    is_current = Column(Integer)


class HourlyDownloads(WriteBase):
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

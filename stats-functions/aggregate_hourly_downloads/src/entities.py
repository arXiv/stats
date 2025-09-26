from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import declarative_base

ReadBase = declarative_base()


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

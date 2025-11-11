from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base

ReadBase = declarative_base()


class Document(ReadBase):
    __tablename__ = "arXiv_documents"

    document_id = Column(Integer, primary_key=True)
    paper_id = Column(String(20), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    authors = Column(Text)
    submitter_email = Column(String(64), nullable=False, index=True)
    submitter_id = Column(Integer, index=True)
    dated = Column(Integer, nullable=False, index=True)
    primary_subject_class = Column(String(16))
    created = Column(DateTime)

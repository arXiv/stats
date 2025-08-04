"""
models.py

This module contains ORM models to be used by the API for querying and aggregating data from the database.
It includes a model for the hourly download data table, as well as a helper function to retrieve models by name.

Classes:
    HourlyDownloadData:
        A class to represent the hourly download data sheet in the database.

Functions:
    get_model(model_name):
        Returns the ORM model specified by the model name.

Modules:
    sqlalchemy: SQL toolkit and Object-Relational Mapping (ORM) library.
    sqlalchemy.orm: Provides the base class for ORM models and other ORM utilities.

Usage:
    Import the necessary models from this module to interact with the database.
    Use the get_model function to retrieve models by name.
"""

from sqlalchemy import Column, String, Integer, DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class HourlyDownloadData(Base):
    """
    A class to represent the hourly download data sheet in the database.
    Refer to category/archive guide for more detailed information on attributes.

    ...

    Attributes:
    country (int):
        Country where the data originates from. Uncapitalized.
        Occasionally contains odd names such as Europe, (Unknown country.)
    download_type (str):
        Represents the format the download was in, pdf, html, source, etc.
    archive (str):
        The exact archive the downloads belongs to.
    category (str):
        The exact category the downloads belongs to.
    primary_count (str):
        File downloads whose primary category is the one in the row.
    cross_count (int):
        File downloads whose secondary categories include the one in the row.
    start_dttm (str):
        represents the time frame in which this data was captured under.
        Saved in a YYYY-MM--DD HH:MM:SS format.

    """

    __tablename__ = "hourly_download_data"
    country = Column(String, nullable=False)
    download_type = Column(String, nullable=False)
    archive = Column(String, nullable=False)
    category = Column(String, nullable=False)
    primary_count = Column(Integer, nullable=False)
    cross_count = Column(Integer, nullable=False)
    start_dttm = Column(DateTime, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("country", "download_type", "category", "start_dttm"),
    )


def get_model(model_name):
    """
    Returns the ORM model specified.

    Args:
        model_name: str
            the string representing the model being requested.

    Returns:
        The ORM model (A class) representing the requested sheet.
        A None if the argument is bad
    """
    models = {"hourly": HourlyDownloadData}
    if model_name in models:
        return models.get(model_name)
    # return none if the model does not exist
    else:
        return None

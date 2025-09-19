from sqlalchemy import Column, String, Integer, DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import declarative_base

SiteUsageBase = declarative_base()


class HourlyDownloadData(SiteUsageBase):
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

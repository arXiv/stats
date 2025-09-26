from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

from stats_entities.site_usage import HourlyDownloads


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


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
    models = {"hourly": HourlyDownloads}
    if model_name in models:
        return models.get(model_name)
    # return none if the model does not exist
    else:
        return None

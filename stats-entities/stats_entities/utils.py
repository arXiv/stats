from sqlalchemy import Column, String, Integer, DateTime, PrimaryKeyConstraint
from stats_entities.entities import HourlyDownloads


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

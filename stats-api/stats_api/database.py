from flask_sqlalchemy import SQLAlchemy

# from stats_entities.site_usage import SiteUsageBase
from stats_entities import site_usage


db = SQLAlchemy(model_class=site_usage.SiteUsageBase)

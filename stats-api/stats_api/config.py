import os
from datetime import date

from dotenv import load_dotenv

# use variables in environment first, .env file second
load_dotenv()


class Config:
    HOST = os.environ.get("HOST") or "0.0.0.0"
    PORT = os.environ.get("PORT") or 8080
    DEBUG = False
    ARXIV_START_DATE = date(year=1991, month=8, day=1)
    ARXIV_TIMEZONE = "America/New_York"
    TOTAL_MIGRATED_PAPERS = 2431
    TOTAL_DELETED_PAPERS = 156  # TODO add to tfvars for easier updates


class TestConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URI")


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("PROD_DATABASE_URI")

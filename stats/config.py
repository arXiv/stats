import os
from dotenv import load_dotenv

# use variables in environment first, .env file second
load_dotenv()


class Config:
    HOST = os.environ.get("HOST") or "0.0.0.0"
    PORT = os.environ.get("PORT") or 8080
    DEBUG = False


class TestConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")

from datetime import date
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="ignore"
    )

class Database(BaseConfig):
    drivername: str
    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None

class Config(BaseConfig):
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = False
    ARXIV_START_DATE: date = date(1991, 8, 1)
    ARXIV_TIMEZONE: str = "America/New_York"
    TOTAL_MIGRATED_PAPERS: int = 2431
    TOTAL_DELETED_PAPERS: int = 156  # TODO add to tfvars for easier updates
    DB: Database


class TestConfig(Config):
    DEBUG: bool = True
    TESTING: bool = True
    DB: Database = Database(drivername="sqlite", database=":memory:")


class DevConfig(Config):
    DEBUG: bool = True


class ProdConfig(Config):
    pass
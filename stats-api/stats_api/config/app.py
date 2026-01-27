from datetime import date
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pydantic_core.core_schema import ValidationInfo

from stats_api.config.urls import _URLS


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Url(BaseConfig):
    name: Optional[str]
    rel_path: Optional[str]
    domain: Optional[str]


class Query(BaseConfig):
    unix_socket: str


class Database(BaseConfig):
    drivername: str
    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    query: Optional[Query] = None


class Config(BaseConfig):
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = False

    ARXIV_START_DATE: date = date(1991, 8, 1)
    ARXIV_TIMEZONE: str = "America/New_York"
    TOTAL_MIGRATED_PAPERS: int = 2431
    TOTAL_DELETED_PAPERS: int = 156  # TODO add to tfvars for easier updates

    FASTLY_MAX_AGE: int = 31557600

    DB: Optional[Database] = None

    PREFERRED_URL_SCHEME: str = "https"  # Flask configuration
    SERVER_NAME: str = "arxiv.org"  # Flask configuration
    BASE_SERVER: str = SERVER_NAME
    HELP_SERVER: str = "info.arxiv.org"
    AUTH_SERVER: str = BASE_SERVER
    URLS: Optional[dict[str, str]] = None

    @field_validator("URLS")
    def construct_urls(cls, v, info: ValidationInfo):
        domain_map = {
            "base": info.data.get("BASE_SERVER"),
            "help": info.data.get("HELP_SERVER"),
            "auth": info.data.get("AUTH_SERVER"),
        }
        urls = [Url(**i) for i in _URLS]

        return {
            url.name: f"{info.data.get('PREFERRED_URL_SCHEME')}://{domain_map[url.domain]}{url.rel_path}"
            for url in urls
        }


class TestConfig(Config):
    DEBUG: bool = True
    TESTING: bool = True  # Flask configuration


class DevConfig(Config):
    DEBUG: bool = False
    SERVER_NAME: str = "dev.arxiv.org"
    HELP_SERVER: str = "info.dev.arxiv.org"


class ProdConfig(Config):
    pass

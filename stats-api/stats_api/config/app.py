from datetime import date

from pydantic import field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

from stats_api.config.urls import _URLS


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Url(BaseConfig):
    name: str
    rel_path: str
    domain: str


class Query(BaseConfig):
    unix_socket: str


class Database(BaseConfig):
    drivername: str
    username: str | None = None
    password: str | None = None
    host: str | None = None
    port: int | None = None
    database: str
    query: Query | None = None


class Config(BaseConfig):
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = False

    ARXIV_START_DATE: date = date(1991, 8, 1)
    ARXIV_TIMEZONE: str = "America/New_York"
    TOTAL_MIGRATED_PAPERS: int = 2431
    TOTAL_DELETED_PAPERS: int

    DB: Database

    PREFERRED_URL_SCHEME: str = "https"  # Flask configuration
    SERVER_NAME: str  # Flask configuration
    BASE_SERVER: str
    HELP_SERVER: str
    AUTH_SERVER: str
    URLS: dict[str, str] | None = None

    # Root URL of the design-system asset route (CSS, fonts, logos, chrome JS)
    BRAND_STATIC_BASE: str | None = None

    @field_validator("URLS")
    def construct_urls(cls, v, info: ValidationInfo):
        domain_map = {
            "base": info.data.get("BASE_SERVER"),
            "help": info.data.get("HELP_SERVER"),
            "auth": info.data.get("AUTH_SERVER"),
        }
        urls = [Url.model_validate(i) for i in _URLS]

        return {
            url.name: f"{info.data.get('PREFERRED_URL_SCHEME')}://{domain_map[url.domain]}{url.rel_path}"
            for url in urls
        }

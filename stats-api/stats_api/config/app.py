from datetime import date
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Urls(BaseConfig):
    scheme: str = "https"
    base: str = scheme + "://"

    base_server: str = "arxiv.org"
    help_server: str = "info.arxiv.org"
    auth_server: str = base_server

    home: str = base + base_server + "/"
    search_box: str = base + base_server + "/search"
    search_advanced: str = base + base_server + "/search/advanced"
    create: str = base + base_server + "/user/create"

    account: str = base + auth_server + "/user"
    login: str = base + auth_server + "/login"
    logout: str = base + auth_server + "/logout"

    help: str = base + help_server + "/help"
    about: str = base + help_server + "/about"
    contact: str = base + help_server + "/help/contact.html"
    subscribe: str = base + help_server + "/help/subscribe"
    copyright: str = base + help_server + "/help/license/index.html"
    privacy_policy: str = base + help_server + "/help/policies/privacy_policy.html"
    a11y: str = base + help_server + "/help/web_accessibility.html"


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
    URLS: Urls = Urls()

    # SERVER_NAME: str = Urls.base_server  # Flask configuration
    # PREFERRED_URL_SCHEME: str = Urls.scheme  # Flask configuration


class TestConfig(Config):
    DEBUG: bool = True
    TESTING: bool = True


class DevConfig(Config):
    DEBUG: bool = False
    URLS: Urls = Urls(BASE_SERVER="dev.arxiv.org", HELP_SERVER="info.dev.arxiv.org")


class ProdConfig(Config):
    pass

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="allow",
    )


class DatabaseConfig(BaseConfig):
    instance_name: str
    user: str
    password: str
    database: str
    unix_socket: Optional[str] = None


class FunctionConfig(BaseConfig):
    env: str
    project: str = ""
    log_level: str = "INFO"
    log_locally: bool = False
    max_event_age_in_minutes: int = 50

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


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
    env: str = "DEV"
    log_level: str = "INFO"
    log_locally: bool = False
    max_event_age_in_minutes: Optional[int] = None

    @computed_field
    @property
    def project(self) -> str:
        project_map = {
            "DEV": "arxiv-development",
            "PROD": "arxiv-production",
        }

        return project_map[self.env]

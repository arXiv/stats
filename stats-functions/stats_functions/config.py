from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pydantic_core.core_schema import ValidationInfo

from google.cloud.sql.connector import IPTypes


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
    )

class ConnectorConfig(BaseConfig):
    ip_type: str = "PUBLIC"
    refresh_strategy: str = "LAZY"

    @field_validator("ip_type")
    def set_ip_type(cls, v, info: ValidationInfo):
        ip_type_map = {
            "PUBLIC": IPTypes.PUBLIC,
            "PRIVATE": IPTypes.PRIVATE
        }

        return ip_type_map[info.data.get("ip_type")]

class DatabaseConfig(BaseConfig):
    instance_name: str
    user: str
    password: str
    database: str
    unix_socket: Optional[str] = None


class FunctionConfig(BaseConfig):
    env: str = "DEV"
    project: str = None
    log_level: str = "INFO"
    log_locally: bool = False
    max_event_age_in_minutes: Optional[int] = None

    @field_validator("project")
    def set_project(cls, v, info: ValidationInfo):
        project_map = {
            "DEV": "arxiv-development",
            "PROD": "arxiv-production",
        }

        return project_map[info.data.get("env")]
    
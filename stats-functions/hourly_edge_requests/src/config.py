from typing import Optional
from stats_functions.config import Database, FunctionConfig


class Config(FunctionConfig):
    db: Optional[Database] = None

    max_event_age_in_minutes: int = 50
    fastly_service_id: dict = {"arxiv.org": "umpGzwE2hXfa2aRXsOQXZ4"}
    fastly_node_number: int = 0  # existing convention, corresponds to 'fastly'
    hour_delay: int = 1

    fastly_api_token: str


class TestConfig(Config):
    log_level: str = "DEBUG"
    log_locally: bool = True

    fastly_api_token: str = "mock_token"


class DevConfig(Config):
    log_level: str = "DEBUG"


class ProdConfig(Config):
    pass


config_map = {
    "TEST": TestConfig,
    "DEV": DevConfig,
    "PROD": ProdConfig,
}


def get_config(environment: str) -> Config:
    return config_map[environment]()

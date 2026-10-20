
from arxiv_functions.config import DatabaseConfig, FunctionConfig


class Config(FunctionConfig):
    db: DatabaseConfig | None = None

    max_event_age_in_minutes: int = 50

    arxiv_timezone: str = "America/New_York"


class TestConfig(Config):
    log_locally: bool = True


class DevConfig(Config):
    pass


class ProdConfig(Config):
    pass


config_map = {
    "TEST": TestConfig,
    "DEV": DevConfig,
    "PROD": ProdConfig,
}


def get_config(environment: str) -> Config:
    return config_map[environment]()

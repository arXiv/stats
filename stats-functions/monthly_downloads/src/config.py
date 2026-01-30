from typing import Optional
from stats_functions.config import FunctionConfig, DatabaseConfig

class Config(FunctionConfig):
    db: Optional[DatabaseConfig] = None

    max_event_age_in_minutes: int = 50

class TestConfig(Config):
    log_level: str = "DEBUG"
    log_locally: bool = True

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
    config_class = config_map[environment]
    return config_class()

from typing import Optional
from stats_functions.config import FunctionConfig, DatabaseConfig


class Config(FunctionConfig):
    read_db: Optional[DatabaseConfig] = None
    write_db: Optional[DatabaseConfig] = None

    max_event_age_in_minutes: int = 50
    max_query_to_write: int = 1000
    hour_delay: int = 3

    paper_id_regex: str = r"^/[^/]+/([a-zA-Z-]+/[0-9]{7}|[0-9]{4}\.[0-9]{4,5})"
    download_type_regex: str = r"^/(html|pdf|src|e-print)/"
    paper_id_optional_version_regex: str = paper_id_regex + r"(v[0-9]+)?$"
    logs_query: str = """
                SELECT
                    paper_id,
                    geo_country,
                    download_type,
                    TIMESTAMP_TRUNC(start_dttm, HOUR) as start_dttm,
                    COUNT(*) as num_downloads,
                FROM
                    (
                    SELECT
                        STRING(json_payload.remote_addr) as remote_addr,
                        REGEXP_EXTRACT(STRING(json_payload.path), @paper_id_regex) as paper_id,
                        STRING(json_payload.geo_country) as geo_country,
                        REGEXP_EXTRACT(STRING(json_payload.path), @download_type_regex) as download_type,
                        FARM_FINGERPRINT(STRING(json_payload.user_agent)) AS user_agent_hash,
                        TIMESTAMP_TRUNC(timestamp, MINUTE) AS start_dttm
                    FROM
                        arxiv_logs._AllLogs
                    WHERE
                        log_id = "fastly_log_ingest"
                        AND STRING(json_payload.state) != "HIT_SYNTH"
                        AND REGEXP_CONTAINS(STRING(json_payload.path), @download_type_regex)
                        AND REGEXP_CONTAINS(JSON_VALUE(json_payload, "$.status"), "^2[0-9][0-9]$")
                        AND JSON_VALUE(json_payload, "$.status") != "206"
                        AND REGEXP_CONTAINS(STRING(json_payload.path), @paper_id_optional_version_regex)
                        AND JSON_VALUE(json_payload, "$.method") = "GET"
                        AND timestamp between TIMESTAMP( @start_time ) and TIMESTAMP( @end_time )
                    GROUP BY
                        1,
                        2,
                        3,
                        4,
                        5,
                        6
                                    )
                GROUP BY
                    1,
                    2,
                    3,
                    4
            """


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
    return config_map[environment]()

from google.cloud.logging import Client
from google.cloud.sql.connector import Connector
from cloudevents.http import CloudEvent

from pymysql.connections import Connection
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine

from datetime import datetime, timedelta, timezone
from dateutil import parser

from stats_functions.config import FunctionConfig, DatabaseConfig


def set_up_cloud_logging(config: FunctionConfig):
    if not config.log_locally:
        cloud_logging_client = Client(project=config.project)
        cloud_logging_client.setup_logging()


def get_engine(connector: Connector, db: DatabaseConfig) -> Engine:
    def get_conn() -> Connection:
        return connector.connect(
            db.instance_name,
            "pymysql",
            user=db.user,
            password=db.password,
            db=db.database,
        )
    
    return create_engine("mysql+pymysql://", creator=get_conn)


def event_time_exceeds_retry_window(config: FunctionConfig, event_time: datetime) -> bool:
    """
    Prevent infinite retries by dismissing event timestamps that are too old
    
    Example use:

        if event_time_exceeds_retry_window(config, event_time):
            raise NoRetryError
    """
    current_time = datetime.now(timezone.utc)
    max_event_age = timedelta(minutes=config.max_event_age_in_minutes)

    if (current_time - event_time) > max_event_age:
        return True
    else:
        return False
    
def parse_cloud_event_time(cloud_event: CloudEvent) -> datetime:
    return parser.isoparse(cloud_event["time"]).replace(tzinfo=timezone.utc)

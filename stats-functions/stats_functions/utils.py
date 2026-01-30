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
    """
    Attach a cloud logging handler to the standard logging module

    Example use:

        logging.basicConfig(level=config.log_level)
        logger = logging.getLogger(__name__)

        set_up_cloud_logging(config)
    """
    if config.env != "TEST" and not config.log_locally:
        cloud_logging_client = Client(project=config.project)
        cloud_logging_client.setup_logging()


def get_engine(connector: Connector, db: DatabaseConfig) -> Engine:
    """
    Instantiate a sqlalchemy database engine configured to use cloud sql python connector

    Example use:

        if config.env != "TEST":
            connector = Connector(ip_type=IPTypes.PUBLIC, refresh_strategy="LAZY")
            SessionFactory = sessionmaker(bind=get_engine(connector, config.db))
    """

    def get_conn() -> Connection:
        return connector.connect(
            db.instance_name,
            "pymysql",
            user=db.user,
            password=db.password,
            db=db.database,
        )

    return create_engine("mysql+pymysql://", creator=get_conn)


def event_time_exceeds_retry_window(
    config: FunctionConfig, event_time: datetime
) -> bool:
    """
    Helper to prevent infinite retries by dismissing event timestamps that are too old

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
    """
    Parse the event time from a cloud event and return it as a timezone-aware datetime object
    """
    return parser.isoparse(cloud_event["time"]).replace(tzinfo=timezone.utc)

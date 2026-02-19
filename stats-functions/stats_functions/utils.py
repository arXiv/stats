from google.cloud.logging import Client
# from google.cloud.sql.connector import Connector
from cloudevents.http import CloudEvent

# from pymysql.connections import Connection
from sqlalchemy import create_engine, Engine, URL

from datetime import datetime, timedelta, timezone
from dateutil import parser

from stats_functions.config import FunctionConfig, DatabaseConfig, Database


def set_up_cloud_logging(config: FunctionConfig):
    """
    Attach a cloud logging handler to the standard logging module

    Example use:

        logging.basicConfig(level=config.log_level)
        logger = logging.getLogger(__name__)

        set_up_cloud_logging(config)
    """
    if config.env != "TEST" and not config.log_locally:
        cloud_logging_client = Client()
        # cloud_logging_client = Client(project=config.project)
        cloud_logging_client.setup_logging()


def get_engine_unix_socket(db: Database) -> Engine:
    """
    Initializes a Unix socket connection pool for a Cloud SQL instance of MySQL

    Example use:

        SessionFactory = None

        if config.env != "TEST":
            SessionFactory = sessionmaker(bind=get_engine_unix_socket(config.db))

    """
    return create_engine(
        URL.create(
            drivername=db.drivername,
            username=db.username,
            password=db.password,
            database=db.database,
            query={"unix_socket": db.query.unix_socket},
        )
    )


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

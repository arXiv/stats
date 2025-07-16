import json
import os
import logging
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Table,
    MetaData,
    PrimaryKeyConstraint,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from datetime import datetime

logger = logging.getLogger(__name__)


# Function to load test data from JSON
def load_test_data():
    # Dynamically get the project root and construct the absolute path to the test data
    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )  # Get the absolute path to the project root
    print(project_root)
    data_file = os.path.join(
        project_root, "tests", "data", "test_download_data.json"
    )  # Construct the path

    try:
        with open(data_file, "r") as f:
            data = json.load(f)

        # Convert 'start_dttm' to datetime objects
        for row in data:
            row["start_dttm"] = datetime.strptime(
                row["start_dttm"], "%Y-%m-%d %H:%M:%S"
            )

        return data
    except Exception as e:
        logger.error(f"Error loading test data: {e}")
        return []


def setup_database(engine, db_name):
    """Create table and insert test data."""
    try:
        logger.error(f"Setting up {db_name} database...")

        # Ensure table exists
        metadata.create_all(engine)

        # Create a sessionmaker bound to the PostgreSQL and MySQL engines
        Session = sessionmaker()

        # Create a session
        session = Session(bind=engine)

        # Insert test data
        session.execute(hourly_download_data.insert(), test_data)

        # Commit the transaction
        session.commit()
        logger.info(f"Test data inserted into {db_name} successfully!")

    except SQLAlchemyError as e:
        logger.error(f"Error in {db_name}: {e}")
    finally:
        session.close()  # Always close the session to avoid resource leaks


if __name__ == "__main__":
    # Database connection URLs (matching Docker Compose)
    POSTGRES_URL = "postgresql+pg8000://test_user:test_pass@localhost:5432/test_db"
    MYSQL_URL = "mysql+pymysql://test_user:test_pass@localhost:3306/test_db"

    # Create database engines
    pg_engine = create_engine(POSTGRES_URL, echo=True)
    mysql_engine = create_engine(MYSQL_URL, echo=True)

    # Define metadata
    metadata = MetaData()

    # Define the table schema
    hourly_download_data = Table(
        "hourly_download_data",
        metadata,
        Column("country", String(255), nullable=False),
        Column("download_type", String(16), nullable=False),
        Column("archive", String(16), nullable=True),
        Column("category", String(32), nullable=False),
        Column("primary_count", Integer, nullable=True),
        Column("cross_count", Integer, nullable=True),
        Column("start_dttm", DateTime, nullable=False),
        # PrimaryKeyConstraint("country", "download_type", "category", "start_dttm")
    )

    # Load test data
    test_data = load_test_data()

    setup_database(pg_engine, "PostgreSQL")
    setup_database(mysql_engine, "MySQL")

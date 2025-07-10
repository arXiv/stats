import os
import logging
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URI")
engine = create_engine(DATABASE_URL)
logger.info("Database engine instantiated")

session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(session_factory) # uses a scoped session for thread safety

def use_session(func):
    """
    Decorator to manage a database session for a function
    The wrapped function must take the session as its first argument
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = Session()
        try:
            result = func(session, *args, **kwargs)
            return result
        except Exception as e:
            print(f"Exception: {e}") # TODO: configure logging
        finally:
            session.remove()
    return wrapper
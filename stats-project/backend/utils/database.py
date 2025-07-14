import os
import logging
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URI")

logger.debug("instantiating database engine")
engine = create_engine(DATABASE_URL)
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(session_factory) # uses a scoped session for thread safety

def use_session(func):
    """
    Decorator to manage a database session for a function
    The wrapped function must take the session as its first argument
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug("creating new scoped session")
        session = Session()
        try:
            result = func(session, *args, **kwargs)
            return result
        except Exception as e:
            raise(e)
        finally:
            session.remove()
    return wrapper
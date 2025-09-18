import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from nta_user_svc.config import DATABASE_URL

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Use SQLAlchemy 2.0 style engine
    engine = create_engine(DATABASE_URL, future=True)
except Exception as e:
    logger.error("Failed to create database engine", exc_info=True)
    raise

# sessionmaker configured for SQLAlchemy 2.0
# Note: do not pass future=True to sessionmaker in SQLAlchemy 2.0 (deprecated).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy Session.
    Uses scoped_session so the session factory is thread-safe in production/tests.
    Ensures proper cleanup and logs exceptions.
    """
    session_factory = scoped_session(SessionLocal)
    db: Session = session_factory()
    try:
        yield db
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
    finally:
        # remove() ensures the scoped session registry is cleared for this thread
        try:
            session_factory.remove()
        except Exception as e:
            logger.error("Error while removing scoped session", exc_info=True)

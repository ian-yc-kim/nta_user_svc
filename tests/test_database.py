import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from nta_user_svc.database import get_db


def test_get_db_yields_session():
    """Ensure get_db yields a SQLAlchemy Session instance."""
    gen = get_db()
    try:
        db = next(gen)
        assert isinstance(db, Session)
    finally:
        try:
            gen.close()
        except Exception as e:
            logging.error("Error closing get_db generator", exc_info=True)
            raise


def test_get_db_exec_query():
    """Ensure a simple query can be executed using the yielded session."""
    gen = get_db()
    try:
        db = next(gen)
        result = db.execute(text("select 1"))
        # Use scalar_one_or_none for compatibility with SQLAlchemy 2.0
        val = result.scalar_one_or_none()
        assert val == 1
    finally:
        try:
            gen.close()
        except Exception:
            logging.error("Error closing get_db generator", exc_info=True)
            raise

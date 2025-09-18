from sqlalchemy import Column, PrimaryKeyConstraint, String
from sqlalchemy.orm import declarative_base

# Keep Base here for Alembic and model imports
Base = declarative_base()

# Provide backward-compatible get_db import so existing imports that
# reference nta_user_svc.models.base.get_db continue to work when tests
# or other modules import it directly from models.base.
# The actual implementation lives in nta_user_svc.database
try:
    from nta_user_svc.database import get_db  # type: ignore
except Exception:
    # If database.py is not yet available (e.g., during certain static analysis steps),
    # avoid hard failure. Tests/runtime will import the real function when available.
    get_db = None  # type: ignore

"""Add functional lower(...) indexes on profiles.name and profiles.location

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2025-09-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import logging

# revision identifiers, used by Alembic.
revision = "2b3c4d5e6f7a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    bind = op.get_bind()
    try:
        return bind.dialect.name
    except Exception:
        # Fallback if bind not available
        return ""


def upgrade() -> None:
    """Create ix_profiles_lower_name and ix_profiles_lower_location indexes.

    Use concurrent creation on PostgreSQL when possible to avoid long locks.
    Fall back to standard CREATE INDEX IF NOT EXISTS for other dialects (e.g., sqlite).
    """
    logger = logging.getLogger("alembic.migrations.add_lower_indexes_profiles")
    dialect = _dialect_name()

    # SQL expressions for indexes
    idx_name_sql = "ix_profiles_lower_name"
    idx_location_sql = "ix_profiles_lower_location"

    try:
        if dialect == "postgresql":
            # Use CONCURRENTLY to avoid locking issues in production Postgres
            op.execute(sa.text(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {idx_name_sql} ON profiles (lower(name));"))
            op.execute(sa.text(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {idx_location_sql} ON profiles (lower(location));"))
        else:
            # Generic safe fallback (SQLite and others)
            op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {idx_name_sql} ON profiles (lower(name));"))
            op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {idx_location_sql} ON profiles (lower(location));"))
    except Exception as e:
        logger.error("Failed to create lower(...) indexes on profiles", exc_info=True)
        raise


def downgrade() -> None:
    """Drop ix_profiles_lower_name and ix_profiles_lower_location indexes.

    Use CONCURRENTLY on PostgreSQL where appropriate.
    """
    logger = logging.getLogger("alembic.migrations.add_lower_indexes_profiles")
    dialect = _dialect_name()

    idx_name_sql = "ix_profiles_lower_name"
    idx_location_sql = "ix_profiles_lower_location"

    try:
        if dialect == "postgresql":
            # DROP INDEX CONCURRENTLY
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {idx_name_sql};"))
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {idx_location_sql};"))
        else:
            op.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name_sql};"))
            op.execute(sa.text(f"DROP INDEX IF EXISTS {idx_location_sql};"))
    except Exception as e:
        logger.error("Failed to drop lower(...) indexes on profiles", exc_info=True)
        raise

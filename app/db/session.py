import logging
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL
from app.db.models import Base


logger = logging.getLogger(__name__)
_engine = None
_session_factory = None
_db_available = False
_last_unavailable_reason = "Database has not been initialized yet."
SCHEMA_SQL_PATH = Path(__file__).resolve().parents[2] / "db_schema.sql"


def _apply_sql_schema(connection) -> None:
    if not SCHEMA_SQL_PATH.exists():
        logger.warning("Schema file not found at %s; skipping SQL bootstrap.", SCHEMA_SQL_PATH)
        return

    raw_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in raw_sql.split(";") if stmt.strip()]
    for statement in statements:
        connection.execute(text(statement))


def _apply_compatibility_migrations(connection) -> None:
    """Keep older persistent databases compatible with the current ORM models."""
    statements = [
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS domain_url TEXT",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active'",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS domain_owner VARCHAR(255)",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255)",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS config_json JSONB",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE project_audiences ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE project_audiences ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'project_audiences_project_id_audience_key'
            ) THEN
                ALTER TABLE project_audiences
                ADD CONSTRAINT project_audiences_project_id_audience_key
                UNIQUE (project_id, audience);
            END IF;
        END $$;
        """,
    ]
    for statement in statements:
        connection.execute(text(statement))


def initialize_database() -> bool:
    global _engine, _session_factory, _db_available, _last_unavailable_reason

    try:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with _engine.begin() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            _apply_sql_schema(connection)
            _apply_compatibility_migrations(connection)
        Base.metadata.create_all(_engine)
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        _db_available = True
        _last_unavailable_reason = ""
        logger.info("Database connected and ready.")
        return True
    except Exception as exc:
        _engine = None
        _session_factory = None
        _db_available = False
        _last_unavailable_reason = str(exc)
        logger.warning("Database unavailable; continuing without persistence. Reason: %s", exc)
        return False


def is_database_available() -> bool:
    return _db_available and _session_factory is not None


def get_database_status() -> dict:
    return {
        "available": is_database_available(),
        "reason": None if is_database_available() else _last_unavailable_reason,
    }


def mark_database_unavailable(exc: Exception) -> None:
    global _db_available, _session_factory, _engine, _last_unavailable_reason
    _db_available = False
    _session_factory = None
    _engine = None
    _last_unavailable_reason = str(exc)
    logger.warning("Database became unavailable during runtime. Reason: %s", exc)


@contextmanager
def db_session_context():
    if not is_database_available():
        logger.warning("Database session requested while DB is unavailable.")
        yield None
        return

    session = _session_factory()
    try:
        yield session
    except SQLAlchemyError as exc:
        session.rollback()
        mark_database_unavailable(exc)
        raise
    finally:
        session.close()

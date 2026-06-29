import sys
from pathlib import Path

from sqlalchemy import create_engine, text

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import DATABASE_URL  # noqa: E402


engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 5})

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS domain_url TEXT;"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active';"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS domain_owner VARCHAR(255);"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255);"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS config_json JSONB;"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;"))
    conn.commit()
    print("Project table migration successful")

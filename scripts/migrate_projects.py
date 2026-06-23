from sqlalchemy import create_engine, text
import os

DATABASE_URL = 'postgresql://helpcentre_user:helpcentre_pass@127.0.0.1:5432/helpcentre_db'
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS domain_owner VARCHAR(255);"))
    conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255);"))
    conn.commit()
    print("Migration successful")

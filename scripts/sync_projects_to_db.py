#!/usr/bin/env python3

import json
import sys
from pathlib import Path

from sqlalchemy import text

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import db_session_context, initialize_database
from app.core.project_manager import project_manager


def sync_projects() -> None:
    if not initialize_database():
        raise RuntimeError("Database is unavailable; cannot sync projects.")

    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database is unavailable; cannot sync projects.")

        for project_id, cfg in project_manager.projects.items():
            db.execute(
                text(
                    """
                    INSERT INTO projects (id, name, description, enabled, status, config_json)
                    VALUES (:id, :name, :description, :enabled, :status, CAST(:config_json AS jsonb))
                    ON CONFLICT (id)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        enabled = EXCLUDED.enabled,
                        status = EXCLUDED.status,
                        config_json = EXCLUDED.config_json,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "id": project_id,
                    "name": cfg.get("name", project_id.replace("_", " ").title()),
                    "description": cfg.get("description", ""),
                    "enabled": bool(cfg.get("enabled", True)),
                    "status": "active" if bool(cfg.get("enabled", True)) else "disabled",
                    "config_json": json.dumps(cfg),
                },
            )

            audiences = cfg.get("audiences", [])
            for audience in audiences:
                db.execute(
                    text(
                        """
                        INSERT INTO project_audiences (project_id, audience, enabled)
                        VALUES (:project_id, :audience, :enabled)
                        ON CONFLICT (project_id, audience)
                        DO UPDATE SET
                            enabled = EXCLUDED.enabled
                        """
                    ),
                    {
                        "project_id": project_id,
                        "audience": audience,
                        "enabled": bool(cfg.get("enabled", True)),
                    },
                )

        db.commit()


if __name__ == "__main__":
    sync_projects()
    print("Projects and audiences synced to PostgreSQL.")

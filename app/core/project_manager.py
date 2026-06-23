import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ProjectManager:
    def __init__(self, config_file: str = "config/projects.yaml"):
        self.config_file = Path(config_file)
        self.projects = self._load_projects_from_yaml()
        self._db_projects_cache = {}

    def _load_projects_from_yaml(self) -> Dict:
        if not self.config_file.exists():
            logger.warning(f"Projects config YAML not found: {self.config_file}")
            return {}
        try:
            with self.config_file.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            return data.get("projects", {})
        except Exception as e:
            logger.error(f"Failed to load projects from YAML: {e}")
            return {}

    def refresh_from_db(self) -> None:
        """Fetch all projects from the database and cache them."""
        from app.db.session import db_session_context, is_database_available
        if not is_database_available():
            return

        try:
            from app.db.models import Project
            with db_session_context() as db:
                if db:
                    projects = db.query(Project).all()
                    self._db_projects_cache = {
                        p.id: (p.config_json if isinstance(p.config_json, dict) else json.loads(p.config_json))
                        for p in projects if p.config_json
                    }
                    logger.info(f"Loaded {len(self._db_projects_cache)} projects from database.")
        except Exception as e:
            logger.error(f"Failed to refresh projects from DB: {e}")

    def get_project(self, project_id: str) -> Dict:
        # 1. Try DB cache first (Source of Truth)
        if project_id in self._db_projects_cache:
            return self._db_projects_cache[project_id]

        # 2. Try fetching from DB if not in cache
        from app.db.session import db_session_context, is_database_available
        if is_database_available():
            try:
                from app.db.models import Project
                with db_session_context() as db:
                    if db:
                        p = db.query(Project).filter(Project.id == project_id).first()
                        if p and p.config_json:
                            cfg = p.config_json if isinstance(p.config_json, dict) else json.loads(p.config_json)
                            self._db_projects_cache[project_id] = cfg
                            return cfg
            except Exception as e:
                logger.error(f"Error fetching project {project_id} from DB: {e}")

        # 3. Fallback to YAML (useful for initial bootstrap or if DB is down)
        if project_id in self.projects:
            return self.projects[project_id]

        raise KeyError(f"Project {project_id} not found")

    def get_active_projects(self) -> List[str]:
        # Combine YAML and DB project IDs, prioritizing DB enabled status
        all_ids = set(self.projects.keys()) | set(self._db_projects_cache.keys())
        active = []
        for pid in all_ids:
            try:
                cfg = self.get_project(pid)
                if cfg.get("enabled", False):
                    active.append(pid)
            except KeyError:
                continue
        return active

    def get_audiences(self, project_id: str) -> List[str]:
        return self.get_project(project_id).get("audiences", [])

    def get_collection_name(self, project_id: str, audience: str) -> str:
        proj = self.get_project(project_id)
        collections = proj.get("collections", {})
        if audience not in collections:
            raise KeyError(f"Audience {audience} not in project {project_id}")
        return collections[audience]

    def get_llm_config(self, project_id: str) -> Dict:
        return self.get_project(project_id).get("llm", {})

    def get_system_role(self, project_id: str) -> str:
        return self.get_llm_config(project_id).get(
            "system_role",
            "You are a careful medical assistant. Use the provided project knowledge base as the primary source and answer with clear, safe, clinically grounded language.",
        )

    def get_prompt_rules(self, project_id: str) -> List[str]:
        rules = self.get_llm_config(project_id).get("prompt_rules", [])
        if isinstance(rules, str):
            return [rules]
        if not isinstance(rules, list):
            return []
        return [str(rule).strip() for rule in rules if str(rule).strip()]

    def get_kb_path(self, project_id: str) -> Path:
        proj = self.get_project(project_id)
        base = proj.get("knowledge_base", {}).get("base_path")
        if not base:
            raise KeyError(f"knowledge_base.base_path not set for project {project_id}")
        return Path(base)


# Singleton
project_manager = ProjectManager()

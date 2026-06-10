import yaml
from pathlib import Path
from typing import Dict, List

class ProjectManager:
    def __init__(self, config_file: str = "config/projects.yaml"):
        self.config_file = Path(config_file)
        self.projects = self._load_projects()

    def _load_projects(self) -> Dict:
        if not self.config_file.exists():
            raise FileNotFoundError(f"Projects config not found: {self.config_file}")
        with self.config_file.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data.get("projects", {})

    def get_project(self, project_id: str) -> Dict:
        if project_id not in self.projects:
            raise KeyError(f"Project {project_id} not found")
        return self.projects[project_id]

    def get_active_projects(self) -> List[str]:
        return [pid for pid, cfg in self.projects.items() if cfg.get("enabled", False)]

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

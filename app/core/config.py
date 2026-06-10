import os
from pathlib import Path

from dotenv import load_dotenv

from .project_manager import project_manager


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
VECTOR_DB_DIR = BASE_DIR / "vector_db"

# Load collections and knowledge-base paths from projects.yaml for the 'tb' project
try:
    tb_proj = project_manager.get_project("tb")
except Exception:
    tb_proj = None

if tb_proj:
    KNOWLEDGE_BASES = {
        "general": {
            "folder": BASE_DIR / tb_proj["knowledge_base"]["base_path"] / "general" / "md",
            "csv": BASE_DIR / tb_proj["knowledge_base"]["base_path"] / "sources.csv",
            "output": DATA_DIR / "general_chunks.json",
        },
        "clinicians": {
            "folder": BASE_DIR / tb_proj["knowledge_base"]["base_path"] / "clinicians" / "md",
            "csv": BASE_DIR / tb_proj["knowledge_base"]["base_path"] / "sources.csv",
            "output": DATA_DIR / "clinicians_chunks.json",
        },
    }
    COLLECTION_NAMES = {
        "general": tb_proj.get("collections", {}).get("general", "DSI_TB_GENERAL"),
        "clinicians": tb_proj.get("collections", {}).get("clinicians", "DSI_TB_CLINICIANS"),
    }
else:
    KNOWLEDGE_BASES = {}
    COLLECTION_NAMES = {}

FALLBACK_COLLECTION_NAME = os.environ.get("LEGACY_COLLECTION_NAME", "DSI_TB")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "models/gemini-embedding-2")
EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "gemini")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1536"))
VECTOR_BACKEND = os.environ.get("VECTOR_BACKEND", "postgres")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "64"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://helpcentre_user:helpcentre_pass@postgres_helpcentre:5432/helpcentre_db",
)

CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")

# ===== Auth / JWT settings =====
# In production set JWT_SECRET to a strong random value via the environment.
JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))  # 12h default

# Role / membership constants
ROLE_SUPER_ADMIN = "super_admin"
ROLE_PROJECT_ADMIN = "project_admin"


def normalize_audience(audience: str | None) -> str:
    if audience in COLLECTION_NAMES:
        return audience
    return "general"

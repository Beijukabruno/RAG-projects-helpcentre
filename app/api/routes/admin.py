import csv
import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db.persistence import get_last_records, get_last_records_for_project
from app.db.session import get_database_status


router = APIRouter()


@router.get("/admin/last-records", include_in_schema=False)
def get_last_records_endpoint(n: int = 100):
    return {"database": get_database_status(), "records": get_last_records(n)}


@router.get("/admin/projects/{project_id}/last-records", include_in_schema=False)
def get_project_last_records(project_id: str, n: int = 5, audience: str | None = None):
    return {
        "database": get_database_status(),
        "project_id": project_id,
        "audience": audience,
        "records": get_last_records_for_project(project_id, audience=audience, limit=n),
    }


@router.get("/admin/last-records-csv", include_in_schema=False)
def get_last_records_csv(n: int = 100):
    records = get_last_records(n)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "session_id",
            "is_user",
            "message",
            "llm_prompt",
            "llm_model",
            "llm_answer",
            "sources",
            "toxicity_input",
            "toxicity_output",
            "created_at",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record.get("id"),
                record.get("session_id"),
                record.get("is_user"),
                record.get("message"),
                record.get("llm_prompt"),
                record.get("llm_model"),
                record.get("llm_answer"),
                record.get("sources"),
                record.get("toxicity_input"),
                record.get("toxicity_output"),
                record.get("created_at"),
            ]
        )
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=last_records.csv"},
    )


@router.get("/admin/projects/{project_id}/last-records-csv", include_in_schema=False)
def get_project_last_records_csv(project_id: str, n: int = 5, audience: str | None = None):
    records = get_last_records_for_project(project_id, audience=audience, limit=n)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "session_id",
            "project_id",
            "audience",
            "is_user",
            "message",
            "llm_prompt",
            "llm_model",
            "llm_answer",
            "sources",
            "toxicity_input",
            "toxicity_output",
            "created_at",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record.get("id"),
                record.get("session_id"),
                record.get("project_id"),
                record.get("audience"),
                record.get("is_user"),
                record.get("message"),
                record.get("llm_prompt"),
                record.get("llm_model"),
                record.get("llm_answer"),
                record.get("sources"),
                record.get("toxicity_input"),
                record.get("toxicity_output"),
                record.get("created_at"),
            ]
        )
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={project_id}_last_records.csv"},
    )

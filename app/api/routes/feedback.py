from fastapi import APIRouter

from app.db.persistence import persist_feedback
from app.db.session import get_database_status
from app.schemas import RatingRequest, ProjectScopedRatingRequest


router = APIRouter()


@router.post(
    "/tb/feedback/rate",
    summary="TB - Rate service",
    description="Capture 1-5 star feedback for the latest TB chatbot answer.",
    tags=["TB"],
)
async def tb_rate_service(rating_request: ProjectScopedRatingRequest):
    stored = persist_feedback(
        rating_request.rating,
        project_id="tb",
        audience=rating_request.audience,
        feedback_text=rating_request.feedback,
    )
    response = {"message": "Thank you for your feedback!", "rating": rating_request.rating, "stored": stored}
    if not stored:
        response["database"] = get_database_status()
    return response


@router.post(
    "/cervical_cancer/feedback/rate",
    summary="Cervical Cancer - Rate service",
    description="Capture 1-5 star feedback for the latest cervical cancer chatbot answer.",
    tags=["Cervical Cancer"],
)
async def cervical_cancer_rate_service(rating_request: ProjectScopedRatingRequest):
    stored = persist_feedback(
        rating_request.rating,
        project_id="cervical_cancer",
        audience=rating_request.audience,
        feedback_text=rating_request.feedback,
    )
    response = {"message": "Thank you for your feedback!", "rating": rating_request.rating, "stored": stored}
    if not stored:
        response["database"] = get_database_status()
    return response


@router.post(
    "/maternal_health/feedback/rate",
    summary="Maternal Health - Rate service",
    description="Capture 1-5 star feedback for the latest maternal health chatbot answer.",
    tags=["Maternal Health"],
)
async def maternal_health_rate_service(rating_request: ProjectScopedRatingRequest):
    stored = persist_feedback(
        rating_request.rating,
        project_id="maternal_health",
        audience=rating_request.audience,
        feedback_text=rating_request.feedback,
    )
    response = {"message": "Thank you for your feedback!", "rating": rating_request.rating, "stored": stored}
    if not stored:
        response["database"] = get_database_status()
    return response


@router.post(
    "/rate",
    summary="Rate service",
    description="Capture 1-5 star feedback for the latest chatbot answer.",
    include_in_schema=False,
)
async def rate_service(rating_request: RatingRequest):
    stored = persist_feedback(
        rating_request.rating,
        project_id=rating_request.project_id,
        audience=rating_request.audience,
        feedback_text=rating_request.feedback,
    )
    response = {"message": "Thank you for your feedback!", "rating": rating_request.rating, "stored": stored}
    if not stored:
        response["database"] = get_database_status()
    return response

from fastapi import APIRouter, Depends
from schemas.api_request_models import MentorMappingRequest
from services.mentor_mapping_service import assign_mentors_service,service_get_all_mentor_mappings
from security.dependencies import require_roles

router = APIRouter(
    prefix="/mentor-mapping",
    tags=["Mentor Mapping"]
)


@router.post("/assign")
def assign_mentors(
    payload: MentorMappingRequest,
    _=Depends(require_roles("ADMIN", "SUPER_ADMIN", "HOD"))
):
    assign_mentors_service(payload)
    return {"message": "Mentors mapped and roles updated successfully"}

@router.get("/all")
def get_all_mappings(
    _=Depends(require_roles("ADMIN", "SUPER_ADMIN", "HOD"))
):
    """
    Used by UI to display
    'Assigned to Course / Year / Section'
    beside faculty names.
    """
    return service_get_all_mentor_mappings()
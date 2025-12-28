from fastapi import APIRouter, Depends
from security.dependencies import require_roles
from services.hod_service import assign_hod_service
from schemas.api_request_models import AssignHODRequest 
# , remove_hod_service

router = APIRouter(prefix="/hod", tags=["HOD Assignment"])

@router.post("/assign")
def assign_hod(payload : AssignHODRequest, _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))):
    return assign_hod_service(payload)

# @router.delete("/remove/{faculty_id}")
# def remove_hod(faculty_id: str, _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))):
#     return remove_hod_service(faculty_id)

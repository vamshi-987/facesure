from fastapi import APIRouter, Depends
from security.dependencies import require_roles
from services.faculty_service import (
    register_faculty,
    update_faculty_service,
    delete_faculty_service,
    service_get_faculty_by_id,
    service_get_all_faculty,
    service_get_faculty_by_college,
    filter_faculty_service
)
from schemas.api_request_models import (
    FacultyCreateRequest,
    FacultyUpdateRequest,
    FacultyFilterRequest
)

router = APIRouter(prefix="/faculty", tags=["Faculty"])


# ==================================================
# CREATE FACULTY
# ==================================================
@router.post("/create")
def create_faculty(
    payload: FacultyCreateRequest,
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN"))
):
    return register_faculty(
        faculty_id=payload.id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        password=payload.password,
        college=payload.college,
        years=payload.years,
        courses=payload.courses
    )


# ==================================================
# GET FACULTY BY ID
# ==================================================
@router.get("/{faculty_id}")
def get_faculty(
    faculty_id: str,
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN", "FACULTY","HOD"))
):
    return service_get_faculty_by_id(faculty_id)


# ==================================================
# UPDATE FACULTY
# ==================================================
@router.put("/update/{faculty_id}")
def update_faculty(
    faculty_id: str,
    payload: FacultyUpdateRequest,
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN"))
):
    return update_faculty_service(
        faculty_id,
        payload.dict(exclude_unset=True)
    )


# ==================================================
# DELETE FACULTY
# ==================================================
@router.delete("/delete/{faculty_id}")
def delete_faculty(
    faculty_id: str,
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN"))
):
    return delete_faculty_service(faculty_id)


# ==================================================
# GET ALL FACULTY
# ==================================================
@router.get("/")
def get_all_faculty(
    _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))
):
    return service_get_all_faculty()


# ==================================================
# GET FACULTY BY COLLEGE
# ==================================================
@router.get("/college/{college}")
def get_faculty_college(
    college: str,
    _=Depends(require_roles("ADMIN", "SUPER_ADMIN", "HOD"))
):
    return service_get_faculty_by_college(college)


# ==================================================
# FILTER FACULTY
# ==================================================
@router.post("/filter")
def filter_faculty(
    payload: FacultyFilterRequest,
    _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))
):
    return filter_faculty_service(payload.dict(exclude_unset=True))

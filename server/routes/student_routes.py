from fastapi import APIRouter, Depends
from security.dependencies import require_roles
from services.student_service import (
    register_student,
    update_student_service,
    delete_student_service,
    promote_students_service,
    filter_students_service,
    get_student_service,
    register_student_face_service
)
from schemas.api_request_models import (
    StudentCreateRequest,
    StudentSelfUpdateRequest,
    StudentAdminUpdateRequest,
    PromoteStudentsRequest,
    StudentFilterRequest,
    StudentFaceRegisterRequest
)

router = APIRouter(prefix="/student", tags=["Student"])


# ======================================================
# ADMIN / SUPER_ADMIN -> CREATE STUDENT (NO FACE)
# ======================================================
@router.post("/create")
def create_student(payload: StudentCreateRequest, _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))):
    return register_student(
        student_id=payload.id,
        name=payload.name,
        phone=payload.phone,
        year=payload.year,
        course=payload.course,
        section=payload.section,
        college=payload.college,
        password=payload.password,
        created_by=payload.created_by,
        father_mobile=payload.father_mobile,
        mother_mobile=payload.mother_mobile
    )


from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter
from fastapi import Request

# Instantiate Limiter
limiter = Limiter(key_func=get_remote_address)

# ======================================================
# STUDENT -> REGISTER FACE (AFTER LOGIN)
# ======================================================
@router.post("/register-face")
@limiter.limit("5/minute")
def register_student_face(request: Request, payload: StudentFaceRegisterRequest, _=Depends(require_roles("STUDENT"))):
    return register_student_face_service(
        student_id=payload.student_id,
        image_b64=payload.image_b64
    )


# ======================================================
# STUDENT -> UPDATE OWN PROFILE (limited fields only)
# ======================================================
@router.put("/update/{student_id}")
def update_student_self(student_id: str, payload: StudentSelfUpdateRequest, _=Depends(require_roles("STUDENT"))):
    return update_student_service(
        student_id,
        payload.dict(exclude_unset=True)
    )


# ======================================================
# ADMIN -> UPDATE STUDENT (all fields including parent contacts)
# ======================================================
@router.put("/admin/update/{student_id}")
def update_student_admin(student_id: str, payload: StudentAdminUpdateRequest, _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))):
    return update_student_service(
        student_id,
        payload.dict(exclude_unset=True)
    )


# ======================================================
# ADMIN -> DELETE STUDENT
# ======================================================
@router.delete("/delete/{student_id}")
def delete_student(student_id: str, _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))):
    return delete_student_service(student_id)


# ======================================================
# ADMIN -> PROMOTE STUDENTS
# ======================================================
@router.post("/promote")
def promote_students(payload: PromoteStudentsRequest, _=Depends(require_roles("ADMIN"))):
    return promote_students_service(
        payload.year,
        payload.college,
        payload.new_year
    )


# ======================================================
# ADMIN / SUPER_ADMIN -> FILTER STUDENTS
# ======================================================
@router.post("/filter")
def filter_students(payload: StudentFilterRequest, _=Depends(require_roles("ADMIN", "SUPER_ADMIN"))):
    return filter_students_service(payload.dict(exclude_unset=True))


# ======================================================
# GET STUDENT BY ID
# ======================================================
@router.get("/{student_id}")
def get_student(student_id: str, _=Depends(require_roles("ADMIN", "SUPER_ADMIN", "STUDENT", "HOD", "MENTOR"))):
    return get_student_service(student_id)
from fastapi import APIRouter, Depends, HTTPException

from services.request_service import (
    create_new_request,
    approve_request,
    reject_request,
    service_get_hod_pending_requests,
    service_delete_requested_request,
    mark_left,
    service_get_student_requests,
    service_get_hod_requests,
    service_get_guard_approved_requests,
    service_get_all_requests,
    service_get_todays_approved,
    service_get_student_todays_requests,
    service_get_mentor_pending_requests,
    service_get_mentor_todays_requests,
    mentor_approve_request,
    mentor_reject_request
)

from security.dependencies import require_roles
from schemas.api_request_models import (
    RequestCreate,
    ApproveRequestBody,
    RejectRequestBody,
    MentorActionBody   # 👈 mentor comment body
)

router = APIRouter(prefix="/request", tags=["Requests"])

# ==================================================
# STUDENT
# ==================================================
@router.post("/create")
def create_request(payload: RequestCreate, _=Depends(require_roles("STUDENT"))):
    return create_new_request(payload.student_id, payload.reason)


@router.get("/student/{student_id}")
def student_reqs(student_id: str, _=Depends(require_roles("STUDENT"))):
    return service_get_student_requests(student_id)


@router.get("/student/history/{student_id}")
def student_history_for_staff(student_id: str, _=Depends(require_roles("MENTOR", "HOD", "ADMIN"))):
    """Allow MENTOR/HOD/ADMIN to fetch a student's request history."""
    return service_get_student_requests(student_id)


@router.get("/student/today/{student_id}")
def student_todays_reqs(
    student_id: str,
    _=Depends(require_roles("STUDENT"))
):
    return service_get_student_todays_requests(student_id)


@router.delete("/{req_id}")
def delete_requested_request(
    req_id: str,
    student_id=Depends(require_roles("STUDENT"))
):
    return service_delete_requested_request(req_id, student_id)

# ==================================================
# MENTOR
# ==================================================
@router.get("/mentor/pending/{mentor_id}")
def mentor_pending_requests(
    mentor_id: str,
    _=Depends(require_roles("MENTOR"))
):
    return service_get_mentor_pending_requests(mentor_id)


@router.get("/mentor/today/{mentor_id}")
def mentor_todays_requests(
    mentor_id: str,
    _=Depends(require_roles("MENTOR"))
):
    return service_get_mentor_todays_requests(mentor_id)


@router.post("/{req_id}/mentor/approve")
def mentor_approve(
    req_id: str,
    payload: MentorActionBody,
    _=Depends(require_roles("MENTOR"))
):
    return mentor_approve_request(
        req_id,
        payload.mentor_id,
        payload.mentor_name,
        payload.remark,
        payload.parent_contacted
    )


@router.post("/{req_id}/mentor/reject")
def mentor_reject(
    req_id: str,
    payload: MentorActionBody,
    _=Depends(require_roles("MENTOR"))
):
    return mentor_reject_request(
        req_id,
        payload.mentor_id,
        payload.mentor_name,
        payload.remark,
        payload.parent_contacted
    )

# ==================================================
# HOD
# ==================================================
@router.get("/hod/pending/{hod_id}")
def hod_pending_requests(
    hod_id: str,
    _=Depends(require_roles("HOD"))
):
    return service_get_hod_pending_requests(hod_id)


@router.get("/hod/{hod_id}")
def hod_reqs(hod_id: str, _=Depends(require_roles("HOD"))):
    return service_get_hod_requests(hod_id)


@router.post("/{req_id}/approve")
def approve(
    req_id: str,
    payload: ApproveRequestBody,
    _=Depends(require_roles("HOD"))
):
    return approve_request(req_id, payload.hod_id, payload.hod_name)


@router.post("/{req_id}/reject")
def reject(
    req_id: str,
    payload: RejectRequestBody,
    _=Depends(require_roles("HOD"))
):
    return reject_request(req_id, payload.hod_id, payload.hod_name)

# ==================================================
# GUARD
# ==================================================
@router.post("/{req_id}/left")
def left(req_id: str, _=Depends(require_roles("GUARD"))):
    return mark_left(req_id)


@router.get("/guard/approved/{college}")
def guard_approved_requests(
    college: str,
    _=Depends(require_roles("GUARD"))
):
    return service_get_guard_approved_requests(college)

# ==================================================
# ADMIN
# ==================================================
@router.get("/all")
def all_requests(_=Depends(require_roles("ADMIN"))):
    return service_get_all_requests()


@router.get("/approved/today")
def today(_=Depends(require_roles("ADMIN"))):
    return service_get_todays_approved()


@router.get("/debug/mentor/{mentor_id}")
def debug_mentor(mentor_id: str, _=Depends(require_roles("MENTOR", "ADMIN"))):
    """Debug endpoint to see what's happening with mentor requests"""
    from data.student_mentor_repo import get_students_for_mentor
    from data.requests_repo import get_all_requests as get_all_reqs_db
    from extensions.mongo import db
    
    # Direct MongoDB query to see what's stored
    mappings = list(db["student_mentor_mapping"].find({"mentor_id": mentor_id}))
    print(f"\n[DEBUG] Mappings for mentor {mentor_id}:")
    for m in mappings:
        print(f"  - student_id: {m['student_id']} (type: {type(m['student_id']).__name__})")
        print(f"    mentor_id: {m['mentor_id']}")
    
    student_ids = get_students_for_mentor(mentor_id)
    print(f"\n[DEBUG] get_students_for_mentor({mentor_id}) returned: {student_ids}")
    print(f"[DEBUG] Types: {[type(sid).__name__ for sid in student_ids]}")
    
    all_requests = list(get_all_reqs_db())
    print(f"\n[DEBUG] Total requests in DB: {len(all_requests)}")
    
    if all_requests:
        print(f"[DEBUG] First request student_id: {all_requests[0]['student_id']} (type: {type(all_requests[0]['student_id']).__name__})")
        print(f"[DEBUG] Request statuses in DB: {set(r.get('status') for r in all_requests)}")
    
    student_ids_str = [str(sid) for sid in student_ids]
    
    matching_requests = []
    for r in all_requests:
        student_id_in_req = str(r["student_id"])
        if student_id_in_req in student_ids_str:
            matching_requests.append({
                "student_id": student_id_in_req,
                "student_name": r.get("student_name"),
                "status": r.get("status"),
                "_id": str(r["_id"])
            })
    
    print(f"\n[DEBUG] Matching requests found: {len(matching_requests)}")
    for mr in matching_requests:
        print(f"  - {mr}")
    
    return {
        "mentor_id": mentor_id,
        "assigned_students": student_ids_str,
        "mappings_count": len(mappings),
        "total_requests_in_db": len(all_requests),
        "matching_requests": matching_requests,
        "request_statuses": list(set(r.get("status") for r in all_requests))
    }

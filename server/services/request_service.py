from datetime import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status
import base64

from core.global_response import success
from extensions.mongo import client

from data.requests_repo import (
    create_request,
    get_request_by_id,
    get_requests_by_student,
    get_requests_by_hod,
    get_all_requests,
    update_request,
    delete_request_if_requested,
    auto_mark_unchecked,
    has_active_request,
    count_todays_requests,
    get_todays_approved_requests,
    get_todays_requests_for_hod,
    get_todays_requests_for_student,
    get_todays_requests_for_mentor,
    get_approved_requests_for_guard_college
)

from data.student_hod_repo import get_hods_for_student,get_students_for_hod
from data.student_mentor_repo import get_students_for_mentor
from data.student_repo import get_student_by_id
from data.faces_repo import get_face_by_user

# ==========================================================
# STATUS CONSTANTS
# ==========================================================
REQUESTED = "REQUESTED"

PENDING_MENTOR = "PENDING_MENTOR"
APPROVED_BY_MENTOR = "APPROVED_BY_MENTOR"
REJECTED_BY_MENTOR = "REJECTED_BY_MENTOR"

PENDING_HOD = "PENDING_HOD"
APPROVED = "APPROVED"
REJECTED = "REJECTED"

LEFT_CAMPUS = "LEFT_CAMPUS"
APPROVED_NOT_LEFT = "APPROVED_NOT_LEFT"



# ==========================================================
# INTERNAL HELPERS
# ==========================================================
def _auto_clean():
    try:
        auto_mark_unchecked()
    except Exception as e:
        print("[AUTO CLEAN FAILED]", e)


def _clean(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def _stringify_ids(doc: dict):
    """
    Convert ObjectId fields to string (NO logic change)
    """
    for key in ["_id", "student_id", "mentor_id", "hod_id"]:
        if key in doc and isinstance(doc[key], ObjectId):
            doc[key] = str(doc[key])
    return doc

# ==========================================================
# CREATE REQUEST (STUDENT)
# ==========================================================
def create_new_request(student_id: str, reason: str):
    try:
        with client.start_session() as s:
            with s.start_transaction():

                _auto_clean()

                student = get_student_by_id(student_id)
                if not student:
                    raise HTTPException(404, "Student not found")

                # Active request check
                if has_active_request(student_id, session=s):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="You already have an active request"
                    )

                # Daily limit
                if count_todays_requests(student_id, session=s) >= 3:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Daily request limit exceeded"
                    )

                # Must have HOD mapping
                if not get_hods_for_student(student_id):
                    raise HTTPException(404, "No HOD assigned")

                doc = {
                    "student_id": str(student["_id"]),
                    "student_name": student["name"],
                    "year": student["year"],
                    "course": student["course"],
                    "section": student["section"],
                    "college": student["college"],
                    
                    "father_mobile": student.get("father_mobile"),
                    "mother_mobile": student.get("mother_mobile"),

                    "reason": reason,
                    "request_time": datetime.utcnow(),

                    "mentor_id": None,
                    "mentor_name": None,
                    "mentor_remark": None,

                    "hod_id": None,
                    "hod_name": None,

                    "status": REQUESTED
                }

                res = create_request(doc)
                created = get_request_by_id(res.inserted_id)

        return success("Request submitted", _clean(created))

    except HTTPException:
        raise
    except Exception as e:
        print("CREATE REQUEST ERROR:", e)
        raise HTTPException(500, "Failed to create request")


# ==========================================================
# MENTOR – FETCH & AUTO-PENDING
# ==========================================================
def service_get_mentor_pending_requests(mentor_id: str):
    try:
        auto_mark_unchecked()
        
        student_ids = get_students_for_mentor(mentor_id)
        
        if not student_ids:
            return success("Mentor pending requests", [])

        student_ids_str = [str(sid) for sid in student_ids]

        reqs = list(get_all_requests())
        
        result = []

        for r in reqs:
            student_id_in_req = str(r.get("student_id", ""))
            
            if student_id_in_req not in student_ids_str:
                continue

            if r.get("status") == REQUESTED:
                update_request(r["_id"], {"status": PENDING_MENTOR})
                r["status"] = PENDING_MENTOR

            if r.get("status") in [PENDING_MENTOR]:
                r["_id"] = str(r["_id"])
                try:
                    face = get_face_by_user(r.get("student_id"))
                    r["student_face"] = (
                        base64.b64encode(face.get("image_data")).decode()
                        if face and face.get("image_data") else None
                    )
                except Exception as face_err:
                    print(f"[WARN] Failed to get face for student {r.get('student_id')}: {face_err}")
                    r["student_face"] = None
                
                r = _stringify_ids(r)
                result.append(r)

        return success("Mentor pending requests", result)

    except Exception as e:
        print("MENTOR FETCH ERROR:", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(500, "Failed to fetch mentor requests")


def service_get_mentor_todays_requests(mentor_id: str):
    """Get today's pending requests for a mentor and auto-clean old ones"""
    try:
        # Auto-clean old requests first
        auto_mark_unchecked()
        
        # First, get all student IDs for this mentor to update their request statuses
        student_ids = get_students_for_mentor(mentor_id)
        student_ids_str = [str(sid) for sid in student_ids]
        
        # Update all REQUESTED requests to PENDING_MENTOR for this mentor's students
        all_reqs = list(get_all_requests())
        for r in all_reqs:
            student_id_in_req = str(r.get("student_id", ""))
            if student_id_in_req in student_ids_str and r.get("status") == REQUESTED:
                update_request(r["_id"], {"status": PENDING_MENTOR})
        
        # Now get today's requests
        reqs = get_todays_requests_for_mentor(mentor_id)
        
        result = []
        for r in reqs:
            # Only include requests that are pending mentor approval
            if r.get("status") != PENDING_MENTOR:
                continue
                
            r["_id"] = str(r["_id"])
            try:
                face = get_face_by_user(r.get("student_id"))
                r["student_face"] = (
                    base64.b64encode(face.get("image_data")).decode()
                    if face and face.get("image_data") else None
                )
            except Exception as face_err:
                print(f"[WARN] Failed to get face for student {r.get('student_id')}: {face_err}")
                r["student_face"] = None
            
            r = _stringify_ids(r)
            result.append(r)
        
        return success("Mentor today's requests", result)

    except Exception as e:
        print("MENTOR TODAY FETCH ERROR:", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(500, "Failed to fetch mentor today's requests")


# ==========================================================
# MENTOR – APPROVE / REJECT (WITH COMMENT)
# ==========================================================
def mentor_approve_request(request_id, mentor_id, mentor_name, remark, parent_contacted=False):
    req = get_request_by_id(request_id)

    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Request {request_id} not found"
        )
    
    current_status = req.get("status")
    
    if current_status != PENDING_MENTOR:
        # Build diagnostic message
        status_map = {
            REQUESTED: "Request just created, mentor has not fetched pending requests yet",
            APPROVED_BY_MENTOR: "Already approved by mentor",
            REJECTED_BY_MENTOR: "Already rejected by mentor",
            PENDING_HOD: "Waiting for HOD approval (passed mentor stage)",
            APPROVED: "Already approved by HOD",
            REJECTED: "Rejected by HOD",
            LEFT_CAMPUS: "Student already left campus",
            APPROVED_NOT_LEFT: "Approved but student hasn't left yet"
        }
        
        detail_msg = status_map.get(
            current_status,
            f"Invalid status: {current_status}"
        )
        
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve: {detail_msg}"
        )

    update_request(request_id, {
        "status": APPROVED_BY_MENTOR,
        "mentor_id": mentor_id,
        "mentor_name": mentor_name,
        "mentor_remark": remark,   # ✅ aligned
        "parent_contacted": parent_contacted,
        "mentor_action_time": datetime.utcnow()
    })

    return success("Approved by mentor")


def mentor_reject_request(request_id, mentor_id, mentor_name, remark, parent_contacted=False):
    req = get_request_by_id(request_id)

    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Request {request_id} not found"
        )
    
    current_status = req.get("status")
    
    if current_status != PENDING_MENTOR:
        # Build diagnostic message
        status_map = {
            REQUESTED: "Request just created, mentor has not fetched pending requests yet",
            APPROVED_BY_MENTOR: "Already approved by mentor",
            REJECTED_BY_MENTOR: "Already rejected by mentor",
            PENDING_HOD: "Waiting for HOD approval (passed mentor stage)",
            APPROVED: "Already approved by HOD",
            REJECTED: "Rejected by HOD",
            LEFT_CAMPUS: "Student already left campus",
            APPROVED_NOT_LEFT: "Approved but student hasn't left yet"
        }
        
        detail_msg = status_map.get(
            current_status,
            f"Invalid status: {current_status}"
        )
        
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject: {detail_msg}"
        )

    update_request(request_id, {
        "status": REJECTED_BY_MENTOR,
        "mentor_id": mentor_id,
        "mentor_name": mentor_name,
        "mentor_remark": remark,   # ✅ aligned
        "parent_contacted": parent_contacted,
        "mentor_action_time": datetime.utcnow()
    })

    return success("Rejected by mentor")



# ==========================================================
# HOD – FETCH (MENTOR APPROVED ONLY)
# ==========================================================
def service_get_hod_pending_requests(hod_id: str):
    try:
        auto_mark_unchecked()
        _auto_clean()

        student_ids = {
            str(m["student_id"])
            for m in get_students_for_hod(hod_id)
        }

        if not student_ids:
            return success("HOD pending requests", [])

        reqs = get_all_requests()
        result = []

        for r in reqs:
            if str(r.get("student_id", "")) not in student_ids:
                continue

            if r.get("status") not in [APPROVED_BY_MENTOR, PENDING_HOD]:
                continue

            if r.get("status") == APPROVED_BY_MENTOR:
                update_request(
                    r["_id"],
                    {"status": PENDING_HOD}
                )
                r["status"] = PENDING_HOD

            r["_id"] = str(r["_id"])
            try:
                face = get_face_by_user(r.get("student_id"))
                r["student_face"] = (
                    base64.b64encode(face.get("image_data")).decode()
                    if face and face.get("image_data") else None
                )
            except Exception as face_err:
                print(f"[WARN] Failed to get face for student {r.get('student_id')}: {face_err}")
                r["student_face"] = None
            
            r = _stringify_ids(r)
            
            r.pop("father_mobile", None)
            r.pop("mother_mobile", None)
            
            result.append(r)

        return success("HOD pending requests", result)

    except Exception as e:
        print("HOD FETCH ERROR:", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(500, "Failed to fetch HOD requests")



# ==========================================================
# HOD – APPROVE / REJECT (UNCHANGED)
# ==========================================================
def approve_request(request_id, hod_id, hod_name):
    req = get_request_by_id(request_id)

    if not req or req["status"] != PENDING_HOD:
        raise HTTPException(409, "Invalid approval")

    update_request(request_id, {
        "status": APPROVED,
        "hod_id": hod_id,
        "hod_name": hod_name,
        "approval_time": datetime.utcnow()
    })

    return success("Request approved")


def reject_request(request_id, hod_id, hod_name):
    req = get_request_by_id(request_id)

    if not req or req["status"] != PENDING_HOD:
        raise HTTPException(409, "Invalid rejection")

    update_request(request_id, {
        "status": REJECTED,
        "hod_id": hod_id,
        "hod_name": hod_name,
        "rejection_time": datetime.utcnow()
    })

    return success("Request rejected")


# ==========================================================
# GUARD – MARK LEFT (UNCHANGED)
# ==========================================================
def mark_left(request_id):
    update_request(request_id, {
        "status": LEFT_CAMPUS,
        "left_time": datetime.utcnow()
    })
    return success("Student marked left")


# ==========================================================
# READ-ONLY SERVICES (UNCHANGED)
# ==========================================================
def service_get_student_requests(student_id):
    auto_mark_unchecked()
    reqs = get_requests_by_student(student_id)
    reqs = [_stringify_ids(r) for r in reqs]
    return success("Student requests", reqs)



def service_get_hod_requests(hod_id):
    auto_mark_unchecked()
    reqs = get_requests_by_hod(hod_id)
    reqs = [_stringify_ids(r) for r in reqs]
    return success("HOD requests", reqs)



def service_get_all_requests():
    auto_mark_unchecked()
    reqs = get_all_requests()
    reqs = [_stringify_ids(r) for r in reqs]
    return success("All requests", reqs)



def service_get_todays_approved():
    auto_mark_unchecked()
    return success("Today approved", get_todays_approved_requests())


def service_get_student_todays_requests(student_id):
    auto_mark_unchecked()
    reqs = get_todays_requests_for_student(student_id)
    reqs = [_stringify_ids(r) for r in reqs]
    return success("Today's student requests", reqs)



def service_get_guard_approved_requests(college: str):
    auto_mark_unchecked()
    reqs = get_approved_requests_for_guard_college(college)

    for r in reqs:
        r["_id"] = str(r["_id"])
        face = get_face_by_user(r["student_id"])
        r["student_face"] = (
            base64.b64encode(face["image_data"]).decode()
            if face else None
        )

    return success("Guard approved requests", reqs)


def service_delete_requested_request(request_id: str, student_id: str):
    req = get_request_by_id(request_id)

    if not req:
        raise HTTPException(404, "Request not found")

    if req["student_id"] != student_id:
        raise HTTPException(403, "Not allowed")

    if req["status"] != REQUESTED:
        raise HTTPException(409, "Only REQUESTED can be deleted")

    delete_request_if_requested(request_id)
    return success("Request deleted")

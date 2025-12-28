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
    get_approved_requests_for_guard_college
)

from data.student_hod_repo import get_hods_for_student,get_students_for_hod
from data.student_mentor_repo import get_students_for_mentor
from data.student_repo import get_student_by_id
from data.faces_repo import get_face_by_user

# ==========================================================
# STATUS CONSTANTS (BACKWARD SAFE)
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

                # ❌ Active request check
                if has_active_request(student_id, session=s):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="You already have an active request"
                    )

                # ❌ Daily limit
                if count_todays_requests(student_id, session=s) >= 3:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Daily request limit exceeded"
                    )

                # ✅ Must have HOD mapping
                if not get_hods_for_student(student_id):
                    raise HTTPException(404, "No HOD assigned")

                doc = {
                    "student_id": student["_id"],
                    "student_name": student["name"],
                    "year": student["year"],
                    "course": student["course"],
                    "section": student["section"],
                    "college": student["college"],

                    "reason": reason,
                    "request_time": datetime.utcnow(),

                    "mentor_id": None,
                    "mentor_name": None,
                    "mentor_comment": None,

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
        student_ids = get_students_for_mentor(mentor_id)

        reqs = list(
            get_all_requests()
        )

        result = []

        for r in reqs:
            if r["student_id"] not in student_ids:
                continue

            if r["status"] == REQUESTED:
                update_request(r["_id"], {"status": PENDING_MENTOR})
                r["status"] = PENDING_MENTOR

            if r["status"] in [PENDING_MENTOR]:
                r["_id"] = str(r["_id"])
                face = get_face_by_user(r["student_id"])
                r["student_face"] = (
                    base64.b64encode(face["image_data"]).decode()
                    if face else None
                )
                result.append(r)

        return success("Mentor pending requests", result)

    except Exception as e:
        print("MENTOR FETCH ERROR:", e)
        raise HTTPException(500, "Failed to fetch mentor requests")


# ==========================================================
# MENTOR – APPROVE / REJECT (WITH COMMENT)
# ==========================================================
def mentor_approve_request(request_id, mentor_id, mentor_name, remark):
    req = get_request_by_id(request_id)

    if not req or req["status"] != PENDING_MENTOR:
        raise HTTPException(409, "Invalid mentor action")

    update_request(request_id, {
        "status": APPROVED_BY_MENTOR,
        "mentor_id": mentor_id,
        "mentor_name": mentor_name,
        "mentor_remark": remark,   # ✅ aligned
        "mentor_action_time": datetime.utcnow()
    })

    return success("Approved by mentor")


def mentor_reject_request(request_id, mentor_id, mentor_name, remark):
    req = get_request_by_id(request_id)

    if not req or req["status"] != PENDING_MENTOR:
        raise HTTPException(409, "Invalid mentor action")

    update_request(request_id, {
        "status": REJECTED_BY_MENTOR,
        "mentor_id": mentor_id,
        "mentor_name": mentor_name,
        "mentor_remark": remark,   # ✅ aligned
        "mentor_action_time": datetime.utcnow()
    })

    return success("Rejected by mentor")



# ==========================================================
# HOD – FETCH (MENTOR APPROVED ONLY)
# ==========================================================
def service_get_hod_pending_requests(hod_id: str):
    try:
        _auto_clean()

        # ✅ FIXED: extract student_id properly
        student_ids = {
            m["student_id"]
            for m in get_students_for_hod(hod_id)
        }

        if not student_ids:
            return success("HOD pending requests", [])

        reqs = get_all_requests()
        result = []

        for r in reqs:
            # student not under this HOD
            if r["student_id"] not in student_ids:
                continue

            # only mentor-approved or pending-hod
            if r["status"] not in [APPROVED_BY_MENTOR, PENDING_HOD]:
                continue

            # convert mentor-approved → pending-hod
            if r["status"] == APPROVED_BY_MENTOR:
                update_request(
                    r["_id"],
                    {"status": PENDING_HOD}
                )
                r["status"] = PENDING_HOD

            r["_id"] = str(r["_id"])
            face = get_face_by_user(r["student_id"])
            r["student_face"] = (
                base64.b64encode(face["image_data"]).decode()
                if face else None
            )
            r = _stringify_ids(r)
            result.append(r)

        return success("HOD pending requests", result)

    except Exception as e:
        print("HOD FETCH ERROR:", e)
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
    reqs = get_requests_by_student(student_id)
    reqs = [_stringify_ids(r) for r in reqs]
    return success("Student requests", reqs)



def service_get_hod_requests(hod_id):
    reqs = get_requests_by_hod(hod_id)
    reqs = [_stringify_ids(r) for r in reqs]
    return success("HOD requests", reqs)



def service_get_all_requests():
    reqs = get_all_requests()
    reqs = [_stringify_ids(r) for r in reqs]
    return success("All requests", reqs)



def service_get_todays_approved():
    return success("Today approved", get_todays_approved_requests())


def service_get_student_todays_requests(student_id):
    reqs = get_todays_requests_for_student(student_id)
    reqs = [_stringify_ids(r) for r in reqs]
    return success("Today's student requests", reqs)



def service_get_guard_approved_requests(college: str):
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

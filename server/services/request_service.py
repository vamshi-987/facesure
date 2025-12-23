from datetime import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status
import base64

from core.global_response import success
from extensions.mongo import client, db

from schemas.request_schema import Request
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
    get_pending_requests_for_hod,
    get_approved_requests_for_guard_college
)

from data.student_hod_repo import get_hods_for_student
from data.student_repo import get_student_by_id
from data.faces_repo import get_face_by_user


# ==========================================================
# INTERNAL: AUTO CLEAN (NON-CRITICAL)
# ==========================================================
def _auto_clean():
    try:
        auto_mark_unchecked()
    except Exception as e:
        print("[AUTO-CLEAN] Failed:", e)


def _clean_request(doc: dict):
    if not doc:
        return doc
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# ==========================================================
# CREATE REQUEST
# ==========================================================
def create_new_request(student_id: str, reason: str):
    try:
        with client.start_session() as s:
            with s.start_transaction():

                _auto_clean()

                student = get_student_by_id(student_id)
                if not student:
                    raise HTTPException(404, "Student not found")

                # ----------------------------------
                # RULE 1: Active request check
                # ----------------------------------
                if has_active_request(student_id, session=s):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="You already have an active request"
                    )

                # ----------------------------------
                # RULE 2: Max 3 requests per day
                # ----------------------------------
                today_count = count_todays_requests(student_id, session=s)
                if today_count >= 3:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Daily request limit (3) exceeded"
                    )

                # ----------------------------------
                # EXISTING LOGIC (unchanged)
                # ----------------------------------
                hod_mappings = get_hods_for_student(student_id)
                if not hod_mappings:
                    raise HTTPException(404, "No HOD assigned to student")

                req_doc = {
                    "student_id": student["_id"],
                    "student_name": student["name"],
                    "year": student["year"],
                    "course": student["course"],
                    "section": student["section"],
                    "college": student["college"],

                    "reason": reason,
                    "request_time": datetime.utcnow(),

                    "hod_id": None,
                    "hod_name": None,
                    "status": "REQUESTED"
                }

                res = create_request(req_doc)
                created = get_request_by_id(res.inserted_id)
                created = _clean_request(created)  # ✅ FIX

        return success("Request submitted", created)

    except HTTPException:
        raise
    except Exception as e:
        print("CREATE REQUEST ERROR:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create request"
        )





# ==========================================================
# APPROVE REQUEST
# ==========================================================
def approve_request(request_id, hod_id, hod_name):
    try:
        with client.start_session() as s:
            with s.start_transaction():
                
                _auto_clean()

                req = get_request_by_id(request_id)
                if not req:
                    raise HTTPException(404, "Request not found")

                if req.get("hod_id"):
                    raise HTTPException(409, "Request already processed")

                update_request(request_id, {
                    "status": "APPROVED",
                    "hod_id": hod_id,
                    "hod_name": hod_name,
                    "approval_time": datetime.utcnow()
                })

                updated = get_request_by_id(request_id)
                updated = _clean_request(updated)  # ✅ FIX

        return success("Request approved", updated)

    except Exception:
        raise


# ==========================================================
# REJECT REQUEST
# ==========================================================
def reject_request(request_id, hod_id, hod_name):
    try:
        with client.start_session() as s:
            with s.start_transaction():
                
                _auto_clean()

                req = get_request_by_id(request_id)
                if not req:
                    raise HTTPException(404, "Request not found")

                if req.get("hod_id"):
                    raise HTTPException(409, "Request already processed")

                update_request(request_id, {
                    "status": "REJECTED",
                    "hod_id": hod_id,
                    "hod_name": hod_name,
                    "rejection_time": datetime.utcnow()
                })

                updated = get_request_by_id(request_id)
                updated = _clean_request(updated)  # ✅ FIX

        return success("Request rejected", updated)

    except Exception:
        raise



# ==========================================================
# MARK LEFT CAMPUS
# ==========================================================
def mark_left(request_id):
    try:
        with client.start_session() as s:
            with s.start_transaction():

                _auto_clean()

                update_request(request_id, {
                    "status": "LEFT_CAMPUS",
                    "left_time": datetime.utcnow()
                })

                updated = get_request_by_id(request_id)
                updated = _clean_request(updated)  # ✅ FIX

        return success("Student marked as left campus", updated)

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while marking left"
        )


# ==========================================================
# READ-ONLY SERVICES
# ==========================================================
def service_get_student_requests(student_id):
    try:
        return success("Student requests", get_requests_by_student(student_id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch student requests"
        )


def service_get_hod_pending_requests(hod_id: str):
    try:
        with client.start_session() as s:
            with s.start_transaction():

                reqs = get_pending_requests_for_hod(hod_id)

                cleaned = []

                for r in reqs:
                    # 🔁 REQUESTED → PENDING (first HOD view)
                    if r.get("status") == "REQUESTED":
                        update_request(
                            r["_id"],
                            {"status": "PENDING"}
                        )
                        r["status"] = "PENDING"

                    # stringify _id for frontend
                    if "_id" in r:
                        r["_id"] = str(r["_id"])

                    face_doc = get_face_by_user(r["student_id"]) 
                    r["student_face"] = (
                        base64.b64encode(face_doc["image_data"]).decode()
                        if face_doc else None
                    ) 

                    cleaned.append(r)

        return success("Pending requests", cleaned)

    except Exception as e:
        print("HOD PENDING ERROR:", e)
        raise


def service_get_hod_requests(hod_id):
    try:
        return success("HOD requests", get_requests_by_hod(hod_id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch HOD requests"
        )


def service_get_all_requests():
    try:
        return success("All requests", get_all_requests())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch all requests"
        )


def service_get_todays_approved():
    try:
        return success("Today approved", get_todays_approved_requests())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch today's approvals"
        )


# ==========================================================
# TODAY'S HOD REQUESTS (ENRICHED)
# ==========================================================
def service_get_hod_todays_requests(hod_id):
    try:
        _auto_clean()

        reqs = get_todays_requests_for_hod(hod_id)
        enriched = []

        for r in reqs:
            stu = get_student_by_id(r["student_id"])
            if not stu:
                continue

            face_doc = get_face_by_user(r["student_id"])
            face_b64 = None
            if face_doc:
                face_b64 = base64.b64encode(face_doc["image_data"]).decode()

            enriched.append({
                "request_id": str(r["_id"]),
                "student_id": r["student_id"],
                "student_name": r["student_name"],
                "year": r["year"],
                "course": r["course"],
                "section": r["section"],
                "reason": r["reason"],
                "status": r["status"],
                "student_face": face_b64,
                "student_phone": stu["phone"],
                "college": stu["college"],
                "request_time": str(r["request_time"])
            })

        return success("Today's HOD requests", enriched)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch today's HOD requests"
        )


# ==========================================================
# TODAY'S STUDENT REQUESTS
# ==========================================================
def service_get_student_todays_requests(student_id):
    try:
        todays = get_todays_requests_for_student(student_id)

        enriched = []
        for r in todays:
            enriched.append({
                "request_id": str(r["_id"]),
                "reason": r["reason"],
                "status": r["status"],
                "request_time": str(r.get("request_time")),
                "approval_time": str(r.get("approval_time")),
                "rejection_time": str(r.get("rejection_time")),
                "left_time": str(r.get("left_time")),
                "hod_id": r.get("hod_id"),
                "hod_name": r.get("hod_name")
            })

        return success("Today's student requests", enriched)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch today's student requests"
        )

def service_get_request_by_id(request_id: str):
    req = get_request_by_id(request_id)
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return success("Request fetched", req)


def service_get_guard_approved_requests(guard_college: str):
    try:
        reqs = get_approved_requests_for_guard_college(guard_college)

        cleaned = []
        for r in reqs:
            if "_id" in r:
                r["_id"] = str(r["_id"])   # ✅ CRITICAL FIX

            face_doc = get_face_by_user(r["student_id"])
            face_b64 = None
            if face_doc:
                face_b64 = base64.b64encode(face_doc["image_data"]).decode()

            r["student_face"] = face_b64
            cleaned.append(r)

        return success("Approved requests for guard", cleaned)

    except Exception as e:
        print("GUARD APPROVED ERROR:", e)  # 👈 helps debugging
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch guard approved requests"
        )

def service_delete_requested_request(request_id: str, student_id: str):
    """
    Allows a student to delete ONLY their REQUESTED request.
    """
    try:
        with client.start_session() as s:
            with s.start_transaction():

                req = get_request_by_id(request_id)
                if not req:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Request not found"
                    )

                # 🔐 Ownership check
                if req["student_id"] != student_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You cannot delete someone else's request"
                    )

                # ❌ Only REQUESTED allowed
                if req["status"] != "REQUESTED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Only REQUESTED requests can be deleted"
                    )

                result = delete_request_if_requested(request_id, session=s)

                if result.deleted_count == 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Request could not be deleted"
                    )

        return success("Request deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        print("DELETE REQUEST ERROR:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete request"
        )
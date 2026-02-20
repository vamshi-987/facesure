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
    get_requests_filtered,
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

from data.student_hod_repo import get_hods_for_student, get_students_for_hod
from data.student_mentor_repo import get_students_for_mentor
from data.student_repo import get_student_by_id
from data.faces_repo import get_face_by_user
from data.admin_repo import get_admin_by_id
from data.faculty_repo import get_faculty_by_id, get_hods_by_college, get_mentors_by_college, get_all_mentors
from data.student_mentor_repo import get_mentors_for_hod_scope

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
                if count_todays_requests(student_id, session=s) >= 10:
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
# GUARD – MARK LEFT (with parent SMS notification)
# ==========================================================
def mark_left(request_id):
    req = get_request_by_id(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if req.get("status") != APPROVED:
        raise HTTPException(409, "Only approved requests can be marked as left")

    update_request(request_id, {
        "status": LEFT_CAMPUS,
        "left_time": datetime.utcnow()
    })

    # Send SMS to both parents
    try:
        from services.sms_service import send_left_campus_notification
        father_mobile = req.get("father_mobile") or ""
        mother_mobile = req.get("mother_mobile") or ""
        if not father_mobile or not mother_mobile:
            sid = req.get("student_id")
            if sid is not None:
                sid = str(sid)
            student = get_student_by_id(sid)
            if student:
                father_mobile = father_mobile or student.get("father_mobile") or ""
                mother_mobile = mother_mobile or student.get("mother_mobile") or ""
        if not father_mobile and not mother_mobile:
            print("[SMS] No parent numbers for request", request_id, "- add father_mobile/mother_mobile on student")
        else:
            hod_name = req.get("hod_name") or ""
            hod_phone = ""
            if req.get("hod_id"):
                hod_doc = get_faculty_by_id(str(req["hod_id"]))
                if hod_doc:
                    hod_name = hod_name or hod_doc.get("name") or ""
                    hod_phone = hod_doc.get("phone") or hod_doc.get("mobile") or ""
            send_left_campus_notification(
                student_roll=req.get("student_id") or "",
                student_name=req.get("student_name") or "",
                reason=req.get("reason") or "",
                father_mobile=father_mobile,
                mother_mobile=mother_mobile,
                hod_name=hod_name,
                hod_phone=hod_phone,
            )
    except Exception as e:
        print("[SMS] Parent notification failed:", e)
        import traceback
        traceback.print_exc()

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


# ==========================================================
# CUSTOM VIEW – FILTER OPTIONS (HODs, Mentors for UI)
# ==========================================================
def service_get_filter_options(user_id: str, role_name: str):
    """Return { hods: [{id, name}], mentors: [{id, name}] } for filter UI based on role."""
    hods = []
    mentors = []
    if role_name == "SUPER_ADMIN":
        from data.faculty_repo import get_all_hods
        all_hods = get_all_hods()
        hods = [{"id": h["_id"], "name": h.get("name", "")} for h in all_hods]
        all_mentors = get_all_mentors()
        mentors = [{"id": m["_id"], "name": m.get("name", "")} for m in all_mentors]
    elif role_name == "ADMIN":
        admin_doc = get_admin_by_id(user_id)
        if admin_doc and admin_doc.get("college"):
            college = admin_doc["college"]
            hods = [{"id": h["_id"], "name": h.get("name", "")} for h in get_hods_by_college(college)]
            mentors = [{"id": m["_id"], "name": m.get("name", "")} for m in get_mentors_by_college(college)]
    elif role_name == "HOD":
        mentor_ids = get_mentors_for_hod_scope(user_id)
        if mentor_ids:
            for mid in mentor_ids:
                fac = get_faculty_by_id(mid)
                if fac:
                    mentors.append({"id": mid, "name": fac.get("name", "")})
    return success("Filter options", {"hods": hods, "mentors": mentors})


# ==========================================================
# CUSTOM VIEW – FILTER REQUESTS (ROLE-AWARE, READ-ONLY)
# ==========================================================
# UI status -> DB statuses (AND across fields)
_STATUS_APPROVED = [APPROVED, APPROVED_NOT_LEFT, LEFT_CAMPUS]
_STATUS_REJECTED = [REJECTED, REJECTED_BY_MENTOR]
_STATUS_PENDING = [REQUESTED, PENDING_MENTOR, PENDING_HOD, APPROVED_BY_MENTOR]
_STATUS_LEFT = [LEFT_CAMPUS]

_ALL_DB_STATUSES = {
    REQUESTED,
    PENDING_MENTOR,
    APPROVED_BY_MENTOR,
    REJECTED_BY_MENTOR,
    PENDING_HOD,
    "MENTOR_UNCHECKED",
    "HOD_UNCHECKED",
    "UNCHECKED",
    APPROVED,
    REJECTED,
    LEFT_CAMPUS,
    APPROVED_NOT_LEFT,
}


def _status_filter_to_db(statuses):
    if not statuses:
        return None
    out = set()
    for s in statuses:
        raw = (s or "").strip()
        if not raw:
            continue
        s_norm = raw.lower()
        s_upper = raw.upper()

        # Allow filtering by exact DB statuses too
        if s_upper in _ALL_DB_STATUSES:
            out.add(s_upper)
            continue

        if s_norm == "approved":
            out.update(_STATUS_APPROVED)
        elif s_norm == "rejected":
            out.update(_STATUS_REJECTED)
        elif s_norm == "pending":
            out.update(_STATUS_PENDING)
        elif s_norm == "left":
            out.update(_STATUS_LEFT)
    return list(out) if out else None


def service_filter_requests(filters: dict, user_id: str, role_name: str):
    """
    Apply role-aware scope and filter; return paginated list. Does not modify any request status.
    - SUPER_ADMIN: no restrictions; can filter anything.
    - ADMIN: all filter fields, but restricted to their college only.
    - HOD: restricted to their college + assigned students (year/course from student_hod).
    - MENTOR: restricted to their college + assigned students (course/year/section from student_mentor_mapping).
    """
    from pymongo import DESCENDING, ASCENDING

    page = max(1, filters.get("page") or 1)
    page_size = min(100, max(1, filters.get("pageSize") or 20))
    sort_by = filters.get("sortBy") or "request_time"
    sort_order = filters.get("sortOrder") or "desc"
    sort_dir = ASCENDING if sort_order == "asc" else DESCENDING

    # Build base query with role scope
    query = {}

    if role_name == "SUPER_ADMIN":
        allowed_student_ids = None  # no scope, no college
    elif role_name == "ADMIN":
        allowed_student_ids = None
        admin_doc = get_admin_by_id(user_id)
        if not admin_doc or not admin_doc.get("college"):
            raise HTTPException(status_code=403, detail="Admin college not found")
        query["college"] = admin_doc["college"]
    elif role_name == "HOD":
        faculty_doc = get_faculty_by_id(user_id)
        if not faculty_doc or not faculty_doc.get("college"):
            raise HTTPException(status_code=403, detail="HOD college not found")
        query["college"] = faculty_doc["college"]
        rows = get_students_for_hod(user_id)
        allowed_student_ids = [str(r["student_id"]) for r in rows]
        if not allowed_student_ids:
            return success("Filtered requests", {"total": 0, "page": page, "pageSize": page_size, "items": []})
        query["student_id"] = {"$in": allowed_student_ids}
    elif role_name == "MENTOR":
        faculty_doc = get_faculty_by_id(user_id)
        if not faculty_doc or not faculty_doc.get("college"):
            raise HTTPException(status_code=403, detail="Mentor college not found")
        query["college"] = faculty_doc["college"]
        student_ids = get_students_for_mentor(user_id)
        allowed_student_ids = [str(sid) for sid in student_ids]
        if not allowed_student_ids:
            return success("Filtered requests", {"total": 0, "page": page, "pageSize": page_size, "items": []})
        query["student_id"] = {"$in": allowed_student_ids}
    else:
        raise HTTPException(status_code=403, detail="Role not allowed for custom view")

    # Apply filters (AND across fields). Only use fields allowed for role (admin gets all).
    if filters.get("studentId"):
        sid = str(filters["studentId"]).strip()
        if sid:
            if allowed_student_ids is not None and sid not in allowed_student_ids:
                return success("Filtered requests", {"total": 0, "page": page, "pageSize": page_size, "items": []})
            query["student_id"] = sid
    if filters.get("studentIds"):
        ids = [str(x).strip() for x in filters["studentIds"] if x]
        if ids:
            if allowed_student_ids is not None:
                ids = [x for x in ids if x in allowed_student_ids]
            if ids:
                query["student_id"] = {"$in": ids}
            else:
                return success("Filtered requests", {"total": 0, "page": page, "pageSize": page_size, "items": []})

    if filters.get("name"):
        name = str(filters["name"]).strip()
        if name:
            query["student_name"] = {"$regex": name, "$options": "i"}

    if filters.get("year") is not None:
        query["year"] = filters["year"]
    if filters.get("years"):
        query["year"] = {"$in": list(filters["years"])}

    if filters.get("course"):
        query["course"] = filters["course"]
    if filters.get("courses"):
        query["course"] = {"$in": list(filters["courses"])}

    if filters.get("section"):
        query["section"] = filters["section"]
    if filters.get("sections"):
        query["section"] = {"$in": list(filters["sections"])}

    # College: only Superadmin can filter by any college; Admin/HOD/Mentor already scoped above
    if role_name == "SUPER_ADMIN" and filters.get("college"):
        query["college"] = filters["college"]

    # Date range (request_time)
    if filters.get("startDate") or filters.get("endDate"):
        date_q = {}
        if filters.get("startDate"):
            try:
                start = datetime.strptime(filters["startDate"][:10], "%Y-%m-%d")
                date_q["$gte"] = start
            except ValueError:
                pass
        if filters.get("endDate"):
            try:
                end = datetime.strptime(filters["endDate"][:10], "%Y-%m-%d")
                end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
                date_q["$lte"] = end
            except ValueError:
                pass
        if date_q:
            query["request_time"] = date_q

    # Status
    statuses = filters.get("statuses") or ([filters["status"]] if filters.get("status") else None)
    db_statuses = _status_filter_to_db(statuses)
    if db_statuses:
        query["status"] = {"$in": db_statuses}

    # hodId/hodIds: Admin, Superadmin
    if role_name in ("ADMIN", "SUPER_ADMIN"):
        hod_ids = filters.get("hodIds") or ([filters["hodId"]] if filters.get("hodId") else [])
        hod_ids = [str(x).strip() for x in hod_ids if x]
        if hod_ids:
            query["hod_id"] = hod_ids[0] if len(hod_ids) == 1 else {"$in": hod_ids}

    # mentorId/mentorIds: Admin, Superadmin, HOD (HOD only allowed mentors in scope)
    if role_name in ("ADMIN", "SUPER_ADMIN"):
        mentor_ids = filters.get("mentorIds") or ([filters["mentorId"]] if filters.get("mentorId") else [])
        mentor_ids = [str(x).strip() for x in mentor_ids if x]
        if mentor_ids:
            query["mentor_id"] = mentor_ids[0] if len(mentor_ids) == 1 else {"$in": mentor_ids}
    elif role_name == "HOD":
        allowed_mentor_ids = set(get_mentors_for_hod_scope(user_id))
        mentor_ids = filters.get("mentorIds") or ([filters["mentorId"]] if filters.get("mentorId") else [])
        mentor_ids = [str(x).strip() for x in mentor_ids if x]
        mentor_ids = [m for m in mentor_ids if m in allowed_mentor_ids]
        if mentor_ids:
            query["mentor_id"] = mentor_ids[0] if len(mentor_ids) == 1 else {"$in": mentor_ids}

    skip = (page - 1) * page_size
    items, total = get_requests_filtered(query, skip=skip, limit=page_size, sort_by=sort_by, sort_order=sort_dir)
    items = [_stringify_ids(r) for r in items]
    return success("Filtered requests", {"total": total, "page": page, "pageSize": page_size, "items": items})

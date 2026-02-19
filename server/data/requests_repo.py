from extensions.mongo import db
from bson import ObjectId
from datetime import datetime
from utils.time_utils import ist_today_range_utc

requests = db["requests"]

# ==========================================================
# CREATE
# ==========================================================
def create_request(doc):
    return requests.insert_one(doc)


# ==========================================================
# READ
# ==========================================================
def get_request_by_id(request_id):
    try:
        return requests.find_one({"_id": ObjectId(request_id)})
    except Exception:
        return None


def get_requests_by_student(student_id):
    return list(
        requests.find({"student_id": student_id})
        .sort("request_time", -1)
    )


def get_requests_by_hod(hod_id):
    return list(
        requests.find({"hod_id": hod_id})
        .sort("request_time", -1)
    )


def get_all_requests():
    return list(
        requests.find()
        .sort("request_time", -1)
    )


def get_requests_filtered(query: dict, skip: int = 0, limit: int = 20, sort_by: str = "request_time", sort_order: int = -1):
    """Returns (list of request docs, total count) for custom filter view. Does not modify status."""
    total = requests.count_documents(query)
    cursor = (
        requests.find(query)
        .sort(sort_by, sort_order)
        .skip(skip)
        .limit(limit)
    )
    return list(cursor), total


# ==========================================================
# UPDATE / DELETE
# ==========================================================
def update_request(request_id, updates):
    return requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": updates}
    )


def delete_request(request_id):
    return requests.delete_one(
        {"_id": ObjectId(request_id)}
    )


# ==========================================================
# INTERNAL: AUTO CLEAN (IST SAFE)
# ==========================================================
def auto_mark_unchecked():
    start, _ = ist_today_range_utc()

    # 1️⃣ Mark older requests as unchecked, distinguishing mentor vs HOD stage
    # - REQUESTED or PENDING_MENTOR -> MENTOR_UNCHECKED
    # - APPROVED_BY_MENTOR or PENDING_HOD -> HOD_UNCHECKED
    requests.update_many(
        {
            "request_time": {"$lt": start},
            "status": {"$in": ["REQUESTED", "PENDING_MENTOR"]}
        },
        {"$set": {"status": "MENTOR_UNCHECKED"}}
    )

    requests.update_many(
        {
            "request_time": {"$lt": start},
            "status": {"$in": ["APPROVED_BY_MENTOR", "PENDING_HOD"]}
        },
        {"$set": {"status": "HOD_UNCHECKED"}}
    )

    # 2️⃣ APPROVED but NOT LEFT → APPROVED_NOT_LEFT
    requests.update_many(
        {
            "approval_time": {"$lt": start},
            "status": "APPROVED",
            "left_time": {"$exists": False}
        },
        {"$set": {"status": "APPROVED_NOT_LEFT"}}
    )


# ==========================================================
# TODAY (IST)
# ==========================================================
def get_todays_requests():
    start, end = ist_today_range_utc()

    return list(
        requests.find({
            "request_time": {"$gte": start, "$lt": end},
            "status": {"$in": ["REQUESTED", "PENDING_MENTOR", "PENDING_HOD"]}
        }).sort("request_time", -1)
    )


def get_todays_approved_requests():
    start, end = ist_today_range_utc()

    return list(
        requests.find({
            "approval_time": {"$gte": start, "$lt": end},
            "status": "APPROVED"
        }).sort("approval_time", 1)
    )


def get_todays_requests_for_hod(hod_id):
    start, end = ist_today_range_utc()

    return list(
        requests.find({
            "hod_id": hod_id,
            "request_time": {"$gte": start, "$lt": end},
            "status": {"$in": ["REQUESTED", "PENDING_MENTOR", "PENDING_HOD"]}
        }).sort("request_time", -1)
    )


def get_todays_requests_for_student(student_id):
    start, end = ist_today_range_utc()

    return list(
        requests.find({
            "student_id": student_id,
            "request_time": {"$gte": start, "$lt": end}
        }).sort("request_time", 1)
    )


def get_todays_requests_for_mentor(mentor_id: str):
    """Get today's pending requests for a mentor"""
    from data.student_mentor_repo import get_students_for_mentor
    
    start, end = ist_today_range_utc()
    student_ids = get_students_for_mentor(mentor_id)
    
    if not student_ids:
        return []
    
    student_ids_str = [str(sid) for sid in student_ids]
    
    return list(
        requests.find({
            "student_id": {"$in": student_ids_str},
            "request_time": {"$gte": start, "$lt": end},
            "status": {"$in": ["REQUESTED", "PENDING_MENTOR"]}
        }).sort("request_time", -1)
    )


# ==========================================================
# PENDING REQUESTS FOR HOD
# ==========================================================
def get_pending_requests_for_hod(hod_id: str):
    student_ids = [
        m["student_id"]
        for m in db["student_hod"].find({"hod_id": hod_id})
    ]

    if not student_ids:
        return []

    return list(
        requests.find({
            "student_id": {"$in": student_ids},
            "status": {"$in": ["APPROVED_BY_MENTOR", "PENDING_HOD"]},
            "hod_id": None
        })
    )


def get_approved_requests_for_guard_college(college: str):
    return list(
        requests.find({
            "status": "APPROVED",
            "college": college
        }).sort("approval_time", -1)
    )


# ==========================================================
# ACTIVE REQUEST CHECK
# ==========================================================
def has_active_request(student_id: str, session=None) -> bool:
    return requests.find_one(
        {
            "student_id": student_id,
            "status": {"$in": ["REQUESTED", "PENDING_MENTOR", "APPROVED", "PENDING_HOD", "APPROVED_BY_MENTOR"]}
        },
        session=session
    ) is not None


# ==========================================================
# TODAY REQUEST COUNT (IST)
# ==========================================================
def count_todays_requests(student_id: str, session=None) -> int:
    start, end = ist_today_range_utc()

    return requests.count_documents(
        {
            "student_id": student_id,
            "request_time": {"$gte": start, "$lt": end}
        },
        session=session
    )


def delete_request_if_requested(request_id: str, session=None):
    return requests.delete_one(
        {
            "_id": ObjectId(request_id),
            "status": "REQUESTED"
        },
        session=session
    )

def auto_mark_approved_not_left():
    """
    Marks requests as APPROVED_NOT_LEFT if:
    - Approved by HOD
    - Student did not leave campus
    - Approval happened before today (IST safe)
    """
    start, _ = ist_today_range_utc()

    return requests.update_many(
        {
            "status": "APPROVED",
            "approval_time": {"$lt": start},
            "left_time": {"$exists": False}
        },
        {
            "$set": {"status": "APPROVED_NOT_LEFT"}
        }
    )
